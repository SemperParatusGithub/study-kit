"""`studykit fig build`: render every course figure script, in parallel and cached.

Each `courses/<c>/figures/<slug>.py` runs in its own isolated interpreter with a timeout.
Outputs go to `courses/<c>/_build/figures/` together with `manifest.json`; a figure is
rebuilt only when its cache key changes (script, studykit sources, lockfile, locale).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from studykit import tools
from studykit.figures import core
from studykit.figures.child import write_outputs

TIMEOUT_S = 60
SLUG_OK = set("abcdefghijklmnopqrstuvwxyz0123456789-")

# Figures every course gets without a script: slug -> builder(course_dir) -> Figure.
# studykit.figures.builtins fills it (the topic map).
BUILTINS: dict[str, Callable[[Path], core.Figure]] = {}


@dataclass
class Outcome:
    slug: str
    status: str  # built | cached | failed
    problems: list[str] = field(default_factory=list)
    source: str = ""


def courses_dir() -> Path:
    return Path(os.environ.get("STUDYKIT_COURSES_DIR", tools.repo_root() / "courses"))


def course_locale(course: Path) -> str:
    meta = course / "course.yaml"
    if meta.is_file():
        data = yaml.safe_load(meta.read_text()) or {}
        return str(data.get("lang", "en"))
    return "en"


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((root / "src" / "studykit").rglob("*")):
        if path.is_file() and path.suffix in {".py", ".mplstyle"}:
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    lock = root / "uv.lock"
    if lock.is_file():
        digest.update(lock.read_bytes())
    return digest.hexdigest()


def _key(parts: list[bytes]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(hashlib.sha256(part).digest())
    return digest.hexdigest()


def _outputs_exist(out_dir: Path, slug: str) -> bool:
    return all((out_dir / f"{slug}{ext}").is_file() for ext in (".svg", ".web.svg", ".png"))


def _rel(script: Path) -> str:
    """Script path relative to its course directory, e.g. figures/rc-bode.py."""
    return f"{script.parent.name}/{script.name}"


def _run_script(script: Path, out_dir: Path, slug: str, locale: str) -> Outcome:
    env = {
        **os.environ,
        "STUDYKIT_LOCALE": locale,
        "MPLBACKEND": "Agg",
        "MPLCONFIGDIR": str(tools.repo_root() / ".cache" / "mpl"),
        "SOURCE_DATE_EPOCH": "0",
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-m", "studykit.figures.child", str(script), str(out_dir), slug],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Outcome(slug, "failed", [f"timed out after {TIMEOUT_S} s"], _rel(script))
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")]
    if lines:
        result = json.loads(lines[-1])
        if result.get("ok"):
            return Outcome(slug, "built", source=_rel(script))
        return Outcome(slug, "failed", result.get("problems", []), _rel(script))
    tail = "\n".join(proc.stderr.strip().splitlines()[-8:]) or f"exit code {proc.returncode}"
    return Outcome(slug, "failed", [tail], _rel(script))


def _run_builtin(name: str, course: Path, out_dir: Path, locale: str) -> Outcome:
    os.environ["STUDYKIT_LOCALE"] = locale
    try:
        fig = BUILTINS[name](course)
    except Exception as exc:
        return Outcome(name, "failed", [f"{type(exc).__name__}: {exc}"], f"builtin:{name}")
    problems = write_outputs(fig, out_dir, name)
    return Outcome(name, "failed" if problems else "built", problems, f"builtin:{name}")


def build_course(course: Path, only: set[str] | None = None, force: bool = False) -> list[Outcome]:
    # Registers the builtins; imported here because builtins imports this module.
    from studykit.figures import builtins  # noqa: F401

    root = tools.repo_root()
    out_dir = course / "_build" / "figures"
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    locale = course_locale(course)
    tree = _tree_digest(root).encode()

    jobs: list[tuple[str, bytes, Callable[[], Outcome]]] = []
    scripts = sorted((course / "figures").glob("*.py")) if (course / "figures").is_dir() else []
    for script in scripts:
        slug = script.stem
        if only and slug not in only:
            continue
        if not set(slug) <= SLUG_OK:
            jobs.append(
                (
                    slug,
                    b"",
                    lambda s=slug: Outcome(
                        s, "failed", ["slug must be kebab-case"], f"figures/{s}.py"
                    ),
                )
            )
            continue
        key = _key([script.read_bytes(), tree, locale.encode()])
        jobs.append(
            (slug, key.encode(), lambda s=script, g=slug: _run_script(s, out_dir, g, locale))
        )
    builtin_input = (
        (course / "course.yaml").read_bytes() if (course / "course.yaml").is_file() else b""
    )
    for name in sorted(BUILTINS):
        if only and name not in only:
            continue
        key = _key([name.encode(), builtin_input, tree, locale.encode()])
        jobs.append((name, key.encode(), lambda n=name: _run_builtin(n, course, out_dir, locale)))

    outcomes: dict[str, Outcome] = {}
    todo = []
    for slug, key, run in jobs:
        cached = manifest.get(slug, {})
        if not force and cached.get("key") == key.decode() and _outputs_exist(out_dir, slug):
            outcomes[slug] = Outcome(slug, "cached", source=cached.get("source", ""))
        else:
            todo.append((slug, key, run))

    # Builtins run in-process and touch os.environ, so they run first and serially.
    builtin_jobs = [j for j in todo if j[0] in BUILTINS]
    script_jobs = [j for j in todo if j[0] not in BUILTINS]
    for slug, _, run in builtin_jobs:
        outcomes[slug] = run()
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        for (slug, _, _), outcome in zip(
            script_jobs, pool.map(lambda j: j[2](), script_jobs), strict=True
        ):
            outcomes[slug] = outcome

    for slug, key, _run in todo:
        outcome = outcomes[slug]
        if outcome.status == "built":
            manifest[slug] = {"key": key.decode(), "source": outcome.source}
        else:
            manifest.pop(slug, None)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(dict(sorted(manifest.items())), indent=2))
    return [outcomes[slug] for slug, _, _ in jobs]


def build(course_id: str | None, only: set[str] | None = None, force: bool = False) -> int:
    base = courses_dir()
    if course_id:
        courses = [base / course_id]
        if not courses[0].is_dir():
            print(f"error: no course directory {courses[0]}", file=sys.stderr)
            return 1
    else:
        courses = sorted(p for p in base.iterdir() if (p / "course.yaml").is_file())
    failed = 0
    for course in courses:
        outcomes = build_course(course, only=only, force=force)
        built = sum(o.status == "built" for o in outcomes)
        cached = sum(o.status == "cached" for o in outcomes)
        failures = len(outcomes) - built - cached
        print(f"{course.name}: {built} built, {cached} cached, {failures} failed")
        for o in outcomes:
            if o.status == "failed":
                failed += 1
                print(f"  FAIL {o.slug} ({o.source})")
                for problem in o.problems:
                    print("    " + problem.replace("\n", "\n    "))
    return 1 if failed else 0
