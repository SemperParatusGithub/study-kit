"""`studykit doctor`: assert that the local toolchain matches toolchain.toml exactly."""

from __future__ import annotations

import filecmp
import json
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from studykit import tools

REQUIRED_TYPST_FONTS = ("New Computer Modern", "New Computer Modern Math", "DejaVu Sans Mono")
DEV_PORT = 4321


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""
    severity: str = "error"  # "error" fails doctor, "warning" only reports


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False, timeout=60)


def check_binaries(root: Path, toolchain: dict) -> list[Check]:
    checks = []
    for name, spec in toolchain.get("binaries", {}).items():
        path = tools.bin_path(root, name)
        found = tools.tool_version(path, spec["version_args"], spec["version_regex"])
        checks.append(
            Check(
                name=name,
                ok=found == spec["version"],
                detail=f"{found or 'missing'} (want {spec['version']} in .tools/bin)",
                fix="just setup",
            )
        )
    return checks


def check_system_tools(toolchain: dict) -> list[Check]:
    checks = []
    for name, spec in toolchain.get("system", {}).items():
        found = tools.tool_version(name, spec["version_args"], spec["version_regex"])
        ok = found is not None and tools.parse_version(found) >= tools.parse_version(
            spec["min_version"]
        )
        checks.append(
            Check(
                name=name,
                ok=ok,
                detail=f"{found or 'missing'} (want >= {spec['min_version']})",
                fix="corepack enable pnpm" if name == "pnpm" else f"install {name} (see README)",
            )
        )
    return checks


def check_python(root: Path) -> Check:
    want = (root / ".python-version").read_text().strip()
    have = f"{sys.version_info.major}.{sys.version_info.minor}"
    return Check("python", have == want, f"{sys.version.split()[0]} (want {want}.x)", "uv sync")


def check_site(root: Path) -> list[Check]:
    package = json.loads((root / "site" / "package.json").read_text())
    pinned = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    checks = []
    for name in ("astro", "katex", "pagefind"):
        manifest = root / "site" / "node_modules" / name / "package.json"
        have = json.loads(manifest.read_text())["version"] if manifest.is_file() else None
        checks.append(
            Check(
                f"site:{name}",
                have == pinned.get(name),
                f"{have or 'missing'} (want {pinned.get(name)})",
                "pnpm -C site install --frozen-lockfile",
            )
        )
    return checks


def check_typst_fonts(root: Path) -> Check:
    typst = tools.bin_path(root, "typst")
    if not typst.exists():
        return Check("typst fonts", False, "typst missing", "just setup")
    proc = _run([str(typst), "fonts", "--ignore-system-fonts"])
    families = set(proc.stdout.splitlines())
    missing = [f for f in REQUIRED_TYPST_FONTS if f not in families]
    detail = "embedded fonts present" if not missing else f"missing: {', '.join(missing)}"
    return Check("typst fonts", not missing, detail, "reinstall typst: just setup")


HOOKS = ("commit-msg", "pre-commit")


def hooks_installed(root: Path, hooks_path: str) -> bool:
    """core.hooksPath runs this checkout's hooks: .githooks itself, or (as in a git worktree
    of this checkout) a directory holding the same hook files."""
    if not hooks_path:
        return False
    own = root / ".githooks"
    path = root / hooks_path  # an absolute hooks_path replaces root
    if path.resolve() == own.resolve():
        return True
    return all(
        (path / name).is_file() and filecmp.cmp(path / name, own / name, shallow=False)
        for name in HOOKS
    )


def check_git(root: Path) -> list[Check]:
    hooks = _run(["git", "config", "--get", "core.hooksPath"], cwd=root).stdout.strip()
    ignored = _run(["git", "check-ignore", "-q", "courses/probe/overview.md"], cwd=root)
    readme_tracked = _run(["git", "check-ignore", "-q", "courses/README.md"], cwd=root)
    return [
        Check(
            "git hooks",
            hooks_installed(root, hooks),
            f"core.hooksPath={hooks or 'unset'}",
            "git config core.hooksPath .githooks",
        ),
        Check(
            "courses ignored",
            ignored.returncode == 0 and readme_tracked.returncode != 0,
            "courses/* ignored, courses/README.md tracked"
            if ignored.returncode == 0
            else "courses/ is NOT ignored",
            "restore .gitignore from main",
        ),
    ]


def check_port() -> Check:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", DEV_PORT))
            free = True
        except OSError:
            free = False
    return Check(
        f"port {DEV_PORT}",
        free,
        "free" if free else "in use (is `just dev` already running?)",
        "stop the process using the port",
        severity="warning",
    )


def run_checks(root: Path, quick: bool = False) -> list[Check]:
    toolchain = tools.load_toolchain(root)
    checks = [
        *check_binaries(root, toolchain),
        *check_system_tools(toolchain),
        check_python(root),
        *check_git(root),
    ]
    if not quick:
        checks += [*check_site(root), check_typst_fonts(root), check_port()]
    return checks


def report(checks: list[Check], as_json: bool) -> int:
    failed = [c for c in checks if not c.ok and c.severity == "error"]
    if as_json:
        print(json.dumps({"ok": not failed, "checks": [asdict(c) for c in checks]}, indent=2))
    else:
        for c in checks:
            mark = "ok  " if c.ok else ("FAIL" if c.severity == "error" else "warn")
            line = f"{mark} {c.name:<16} {c.detail}"
            if not c.ok and c.fix:
                line += f"  -> {c.fix}"
            print(line)
        print("doctor: all good" if not failed else f"doctor: {len(failed)} problem(s)")
    return 1 if failed else 0
