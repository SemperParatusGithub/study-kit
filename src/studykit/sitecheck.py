"""The Site stage of `studykit validate --release` (docs/architecture.md §4.3, SK-SITE).

Three checks over the website as `just build` makes it, for one course:

1. a strict `astro build` (STUDYKIT_STRICT=1) into a temporary directory given with
   `--outDir`, so `site/dist` and `site/public` stay as the last `just build` left them,
   followed by Pagefind over that directory (the search page loads its bundle).
   STUDYKIT_COURSES_DIR is a temporary directory that holds only a link to the course, so
   the site contains this course alone and a neighbouring course can never fail its run;
2. `pnpm -C site check` (`astro check`: types of the site code against the content);
3. `studykit check-links` over the built pages.

A strict build that fails on a content problem prints the findings in the study-kit
format; they are reported under their own codes (SK-FIG-BUILD, SK-MATH-KATEX, …) at the
course's own files. Anything else that breaks the build is SK-SITE-BUILD, an `astro check`
error is SK-SITE-CHECK, and a broken link is SK-SITE-LINK at `dist/<page>`, the page's path
in the built site.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from studykit import checklinks, content, tools
from studykit import findings as findings_mod
from studykit.findings import Finding

BUILD_TIMEOUT = 600
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# `src/pages/x.astro:12:3 - error ts(2322): message` (astro check, colours off)
CHECK_RE = re.compile(
    r"^(?P<path>[^\s:][^:]*):(?P<line>\d+):(?P<col>\d+) - (?P<severity>error|warning|hint) "
    r"(?P<message>.*)$"
)
NOISE_RE = re.compile(r"^(?:\d\d:\d\d:\d\d |\$ |ELIFECYCLE|\s*at |\s*$)")


@dataclass(frozen=True)
class Run:
    code: int
    output: str  # stdout and stderr, colours removed


Runner = Callable[[list[str], dict[str, str], Path], Run]


def _run(argv: list[str], env: dict[str, str], cwd: Path) -> Run:
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=BUILD_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Run(124, f"timed out after {BUILD_TIMEOUT} s: {' '.join(argv)}")
    return Run(proc.returncode, ANSI_RE.sub("", proc.stdout + "\n" + proc.stderr))


def environment(root: Path, courses_dir: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(root / ".tools" / "bin"), env.get("PATH", "")])
    env.update(
        STUDYKIT_STRICT="1",
        STUDYKIT_COURSES_DIR=str(courses_dir.resolve()),
        ASTRO_TELEMETRY_DISABLED="1",
        NO_COLOR="1",
        FORCE_COLOR="0",
    )
    return env


def missing(root: Path) -> str | None:
    """Why the site cannot be built here, or None."""
    site = root / "site"
    if not (site / "astro.config.mjs").is_file():
        return "site/astro.config.mjs not found"
    path = environment(root, root)["PATH"]
    for tool in ("node", "pnpm"):
        if shutil.which(tool, path=path) is None:
            return f"{tool} is not on PATH (run `just setup`)"
    if not (site / "node_modules" / "astro").is_dir():
        return "site/node_modules is not installed (run `just setup`)"
    return None


def _last_lines(output: str, n: int = 3) -> str:
    lines = [ln.strip() for ln in output.splitlines() if not NOISE_RE.match(ln)]
    return " | ".join(lines[-n:]) or "no output"


def course_path(path: str, link: Path, course: Path) -> str:
    """`path` as findings name it, with the temporary course link replaced by the course.

    The site names files under STUDYKIT_COURSES_DIR as it was given (the link); the course's
    own files are what the author edits, and the temporary directory is gone afterwards.
    """
    try:
        rel = Path(path).relative_to(link)
    except ValueError:
        return path
    return content.display_path(course / rel)


def build_findings(
    run: Run, course_doc: str, rename: Callable[[str], str] = lambda path: path
) -> list[Finding]:
    """Findings of a failed strict build: the content findings it printed, or one SK-SITE-BUILD.

    `rename` maps the paths the build printed to the files they stand for (course_path).
    """
    if run.code == 0:
        return []
    found = [
        Finding(rename(f.path), f.line, f.col, f.code, f.message, f.fix, f.severity)
        for ln in run.output.splitlines()
        for f in findings_mod.parse(ln.strip())
    ]
    if found:
        return sorted(set(found))
    return [
        Finding(
            course_doc,
            1,
            1,
            "SK-SITE-BUILD",
            f"the strict site build failed: {_last_lines(run.output)}",
            "run `just build <course>` and fix the first error it prints",
        )
    ]


def check_findings(run: Run) -> list[Finding]:
    """`astro check` errors (paths are relative to site/); warnings and hints are not shown."""
    if run.code == 0:
        return []
    found = []
    for ln in run.output.splitlines():
        m = CHECK_RE.match(ln.strip())
        if m and m["severity"] == "error":
            found.append(
                Finding(
                    f"site/{m['path']}",
                    int(m["line"]),
                    int(m["col"]),
                    "SK-SITE-CHECK",
                    f"astro check: {m['message'].strip()}",
                    "fix the site code (`pnpm -C site check` shows the context)",
                )
            )
    if found:
        return found
    return [
        Finding(
            "site",
            1,
            1,
            "SK-SITE-CHECK",
            f"astro check failed: {_last_lines(run.output)}",
            "run `pnpm -C site check` and fix what it reports",
        )
    ]


def link_findings(found: list[Finding], out: Path, course_id: str) -> list[Finding]:
    """check-links findings on this course's pages and the shared ones, named `dist/<page>`.

    The temporary build is deleted afterwards, so the path names the page in the site
    (`dist/c/<course>/summary/x/index.html` is /c/<course>/summary/x/). The site is built
    for this course alone; pages of any other course are dropped all the same.
    """
    out = out.resolve()
    kept = []
    for f in found:
        path = Path(f.path)
        path = path if path.is_absolute() else tools.repo_root() / path
        try:
            rel = path.resolve().relative_to(out).as_posix()
        except ValueError:
            rel = f.path
        parts = rel.split("/")
        if parts[0] == "c" and len(parts) > 1 and parts[1] != course_id:
            continue
        kept.append(Finding(f"dist/{rel}", f.line, f.col, f.code, f.message, f.fix, f.severity))
    return kept


def check(
    root: Path,
    course: Path,
    course_id: str,
    lang: str,
    *,
    course_doc: str,
    run: Runner = _run,
    notes: list[str] | None = None,
) -> list[Finding]:
    """The Site stage's findings for `course`, a course directory (its name is the site's id)."""
    notes = notes if notes is not None else []
    site = root / "site"
    course = course.resolve()
    out_findings: list[Finding] = []
    with tempfile.TemporaryDirectory(prefix="studykit-site-") as tmp:
        courses = Path(tmp).resolve() / "courses"
        courses.mkdir()
        link = courses / course.name
        link.symlink_to(course, target_is_directory=True)
        env = environment(root, courses)
        pnpm = shutil.which("pnpm", path=env["PATH"]) or "pnpm"
        out = Path(tmp).resolve() / "dist"
        built = run(
            [pnpm, "-C", str(site), "exec", "astro", "build", "--outDir", str(out)], env, root
        )
        out_findings += build_findings(built, course_doc, lambda p: course_path(p, link, course))
        if built.code == 0:
            shutil.rmtree(out / "pagefind", ignore_errors=True)  # a copy of public/pagefind
            pagefind = site / "node_modules" / ".bin" / "pagefind"
            indexed = run([str(pagefind), "--site", str(out), "--force-language", lang], env, site)
            if indexed.code != 0:
                out_findings.append(
                    Finding(
                        course_doc,
                        1,
                        1,
                        "SK-SITE-BUILD",
                        f"pagefind failed on the built site: {_last_lines(indexed.output)}",
                        "run `just build <course>` and fix what pagefind reports",
                    )
                )
            pages = sum(1 for _ in checklinks.html_files(out))
            out_findings += link_findings(checklinks.check(out), out, course_id)
            notes.append(f"built {pages} page(s) into a temporary directory; links checked")
        else:
            notes.append("the strict site build failed, so links were not checked")
        checked = run([pnpm, "-C", str(site), "check"], env, root)
        out_findings += check_findings(checked)
    return out_findings
