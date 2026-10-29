"""`studykit lint <files…> [--hook]`: the fast per-file check.

Lint is `validate --quick` restricted to the given files: Structure, Schema, Fences, MC,
Math and the Pandoc backstop, each file checked in the context of its course so topic ids,
retired ids and duplicates are known.

With `--hook` it is the Claude Code PostToolUse hook for Write and Edit: it reads the hook
JSON from stdin, lints `tool_input.file_path` when that is a file of a course (a
`course.yaml` above it) under `courses/**` or `examples/**` (or $STUDYKIT_COURSES_DIR), and
exits 2 with the findings on stderr so Claude fixes them right away. Anything else exits 0
silently.
"""

from __future__ import annotations

import json
import os
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


def hook_target(payload: object) -> Path | None:
    """The file a PostToolUse payload wrote, if the lint hook should check it."""
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    raw = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        cwd = payload.get("cwd")
        path = Path(cwd) / path if isinstance(cwd, str) else path
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
    path = hook_target(payload)
    if path is None:
        return 0, ""
    report = lint_files([path], config)
    shown = [f for f in report.findings if f.severity in {"error", "warning"}]
    if not shown:
        return 0, ""
    lines = [f.format() for f in shown]
    lines.append("studykit lint: fix these now; docs/content-format/errors.md explains each code")
    return 2, "\n".join(lines) + "\n"
