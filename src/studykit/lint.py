"""`studykit lint <files…> [--hook]`: the fast per-file check.

Lint is `validate --quick` restricted to the given files: Structure, Schema, Fences, MC,
Math and the Pandoc backstop, each file checked in the context of its course so topic ids,
retired ids and duplicates are known.

With `--hook` it is the PostToolUse hook for file edits: it reads the hook JSON from stdin
and lints the files the edit wrote when they are files of a course (a `course.yaml` above
them) under `courses/**` or `examples/**` (or $STUDYKIT_COURSES_DIR), and exits 2 with the
findings on stderr so the agent fixes them right away. Anything else exits 0 silently. The
written files are Claude Code's `tool_input.file_path` (Write, Edit) or, for Codex, the
`*** Add File:`, `*** Update File:` and `*** Move to:` lines of the `apply_patch` patch in
`tool_input.command`.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from studykit import content, tools, validate
from studykit.findings import Finding

LINTED_SUFFIXES = {".md", ".yaml", ".yml"}


def lint_files(files: list[Path], config: validate.Config | None = None) -> validate.Report:
    config = config or validate.Config()
    report = validate.Report()
    groups: dict[Path, list[Path]] = {}
    orphans: list[Finding] = []
    for file in files:
        if not file.is_file():
            orphans.append(
                Finding(str(file), 1, 1, "SK-STRUCT-MISSING", "file not found", "check the path")
            )
            continue
        root = content.find_course_root(file.parent)
        if root is None:
            orphans.append(
                Finding(
                    content.display_path(file),
                    1,
                    1,
                    "SK-STRUCT-PATH",
                    "file is not inside a course (no course.yaml above it)",
                    "course files live in courses/<id>/ next to course.yaml",
                )
            )
            continue
        groups.setdefault(root, []).append(file)
    if orphans:
        report.courses.append(validate.CourseReport("-", "-", findings=orphans))
    for root, group in groups.items():
        tree = content.CourseTree(root)
        selected = {f.resolve().relative_to(tree.root).as_posix() for f in group}
        for rel in sorted(selected - set(tree.docs)):
            report.notes.append(f"{rel}: not a checked course file (generated or private area)")
        report.courses.append(
            validate.run_course(tree, config, selected=selected & set(tree.docs), quick=True)
        )
    return report


def hook_roots() -> list[Path]:
    root = tools.repo_root()
    roots = [root / "courses", root / "examples"]
    if os.environ.get("STUDYKIT_COURSES_DIR"):
        roots.append(Path(os.environ["STUDYKIT_COURSES_DIR"]))
    return [r.resolve() for r in roots]


# the files an apply_patch patch (Codex) writes
PATCH_FILE = re.compile(r"^\*\*\* (?:Add File|Update File|Move to): (.+?)\s*$", re.MULTILINE)


def hook_targets(payload: object) -> list[Path]:
    """The files a PostToolUse payload wrote that the lint hook should check."""
    if not isinstance(payload, dict):
        return []
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    raws: list[str] = []
    if isinstance(tool_input.get("file_path"), str):
        raws.append(tool_input["file_path"])
    elif payload.get("tool_name") == "apply_patch" and isinstance(tool_input.get("command"), str):
        raws.extend(PATCH_FILE.findall(tool_input["command"]))
    cwd = payload.get("cwd")
    targets: list[Path] = []
    for raw in raws:
        path = _hook_path(raw, cwd if isinstance(cwd, str) else None)
        if path is not None and path not in targets:
            targets.append(path)
    return targets


def _hook_path(raw: str, cwd: str | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute() and cwd is not None:
        path = Path(cwd) / path
    path = path.resolve()
    if path.suffix not in LINTED_SUFFIXES or not path.is_file():
        return None
    if not any(path.is_relative_to(r) for r in hook_roots()):
        return None
    # files beside the courses (examples/sample-materials, a course folder before its
    # course.yaml exists) are not course content
    if content.find_course_root(path.parent) is None:
        return None
    return path


def run_hook(stdin_text: str, config: validate.Config | None = None) -> tuple[int, str]:
    """(exit code, stderr text) for one PostToolUse event."""
    try:
        payload = json.loads(stdin_text or "{}")
    except json.JSONDecodeError:
        return 0, ""
    paths = hook_targets(payload)
    if not paths:
        return 0, ""
    report = lint_files(paths, config)
    shown = [f for f in report.findings if f.severity in {"error", "warning"}]
    if not shown:
        return 0, ""
    lines = [f.format() for f in shown]
    lines.append("studykit lint: fix these now; docs/content-format/errors.md explains each code")
    return 2, "\n".join(lines) + "\n"
