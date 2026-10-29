"""Thin wrapper around the pinned pandoc binary and the study-kit filter set.

Course files go through `pandoc -d common -d <target>` with the Lua filter in
`pandoc/filters/` (docs/architecture.md §3.1). The filter needs metadata about the file
(`-M sk-index=… -M sk-course=… -M sk-lang=… -M sk-file=…`, plus `sk-solutions` and
`sk-figdir` for Typst); `argv()` builds that list so no caller assembles it by hand, and
`run_filtered()` runs one course file end to end.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from studykit import tools

# The one Markdown dialect study-kit accepts (docs/architecture.md §2.3).
READER = "commonmark_x-smart-raw_html-raw_attribute-yaml_metadata_block-alerts-emoji"

Target = Literal["html", "typst", "json"]
Solutions = Literal["inline", "appendix", "none"]

# Target name -> defaults file in pandoc/defaults/ (combined with common.yaml).
DEFAULTS: dict[str, str] = {"html": "web", "typst": "typst", "json": "json"}

# Exit status of the filter when it reported findings (sysexits EX_DATAERR).
EXIT_FINDINGS = 65

# `path:line:col SK-CODE message (fix: …)`, the finding format of every study-kit check.
FINDING = re.compile(
    r"^(?P<path>\S+?):(?P<line>\d+):(?P<col>\d+) (?P<code>SK-[A-Z]+) (?P<message>.*)$"
)


class PandocError(RuntimeError):
    pass


class FilterError(PandocError):
    """The filter rejected the document; `findings` holds one formatted line each."""

    def __init__(self, findings: list[str], stderr: str) -> None:
        super().__init__("\n".join(findings) or stderr.strip())
        self.findings = findings
        self.stderr = stderr


def pandoc_bin() -> Path:
    return tools.bin_path(tools.repo_root(), "pandoc")


def run(
    args: list[str], stdin: str | None = None, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [str(pandoc_bin()), *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        cwd=cwd,
    )
    if proc.returncode == EXIT_FINDINGS:
        findings = [ln for ln in proc.stderr.splitlines() if FINDING.match(ln)]
        raise FilterError(findings, proc.stderr)
    if proc.returncode != 0:
        raise PandocError(proc.stderr.strip() or f"pandoc exited with {proc.returncode}")
    return proc


def to_json(markdown: str) -> dict:
    return json.loads(run(["-f", READER, "-t", "json"], stdin=markdown).stdout)


def walk(node: object) -> Iterator[dict]:
    """Yield every pandoc AST element (dicts with a "t" key), depth first."""
    if isinstance(node, dict):
        if "t" in node:
            yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def math_nodes(markdown: str) -> list[tuple[str, bool]]:
    """All formulas in document order as (tex, is_display)."""
    out = []
    for el in walk(to_json(markdown)["blocks"]):
        if el["t"] == "Math":
            kind, tex = el["c"]
            out.append((tex, kind["t"] == "DisplayMath"))
    return out


# --- the filter set ---------------------------------------------------------------------


@dataclass(frozen=True)
class Document:
    """What the filter needs to know about one source file (the -M sk-* metadata)."""

    course: str
    lang: str
    file: str  # course-relative path; decides the file kind (summary, mc, exercise, …)
    index: Path  # absolute path of courses/<c>/_build/index.json
    solutions: Solutions = "appendix"  # Typst only
    figdir: Path | None = None  # Typst only: absolute directory of the built figures


def defaults_dir(root: Path | None = None) -> Path:
    return (root or tools.repo_root()) / "pandoc" / "defaults"


def argv(doc: Document, target: Target, *, root: Path | None = None) -> list[str]:
    """pandoc arguments (without the binary and the input) for `doc` and `target`."""
    if target not in DEFAULTS:
        raise ValueError(f"unknown target {target!r}; expected one of {sorted(DEFAULTS)}")
    defaults = defaults_dir(root)
    args = [
        "-d",
        str(defaults / "common.yaml"),
        "-d",
        str(defaults / f"{DEFAULTS[target]}.yaml"),
        "-M",
        f"sk-index={Path(doc.index).resolve()}",
        "-M",
        f"sk-course={doc.course}",
        "-M",
        f"sk-lang={doc.lang}",
        "-M",
        f"sk-file={doc.file}",
    ]
    if target == "typst":
        args += ["-M", f"sk-solutions={doc.solutions}"]
        if doc.figdir is not None:
            args += ["-M", f"sk-figdir={Path(doc.figdir).resolve()}"]
    return args


def blank_frontmatter(text: str) -> str:
    """Replace a leading `---` YAML block with empty lines, keeping line numbers intact.

    pandoc never sees frontmatter (the reader has yaml_metadata_block off); blanking it
    instead of cutting it means the filter's line numbers match the file on disk.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") in ("---", "..."):
            return "\n" * (i + 1) + "".join(lines[i + 1 :])
    return text


def convert(body: str, doc: Document, target: Target, *, root: Path | None = None) -> str:
    """Run the filter set on `body` (frontmatter already removed or blanked).

    pandoc runs in the repository root and reads the body from a temporary file, so the
    guard can check fence lines and Typst figure paths come out relative to the root.
    Raises FilterError with the formatted findings when the filter rejects the file.
    """
    root = root or tools.repo_root()
    with tempfile.TemporaryDirectory(prefix="studykit-pandoc-") as tmp:
        source = Path(tmp) / "input.md"
        source.write_text(body, encoding="utf-8")
        return run([*argv(doc, target, root=root), str(source)], cwd=root).stdout


def course_document(
    course_dir: Path,
    relpath: str,
    *,
    index: Path | None = None,
    solutions: Solutions = "appendix",
    figdir: Path | None = None,
) -> Document:
    """The Document for a file of a course tree, with course id and language from the index."""
    index = (index or course_dir / "_build" / "index.json").resolve()
    data = json.loads(index.read_text(encoding="utf-8"))
    return Document(
        course=data.get("course") or course_dir.name,
        lang=data.get("lang") or "de",
        file=relpath,
        index=index,
        solutions=solutions,
        figdir=(figdir or course_dir / "_build" / "figures").resolve(),
    )


def run_filtered(
    course_dir: Path,
    relpath: str,
    target: Target,
    *,
    index: Path | None = None,
    solutions: Solutions = "appendix",
    figdir: Path | None = None,
    root: Path | None = None,
) -> str:
    """Convert `course_dir/relpath` for `target` (html fragment, typst source or json AST)."""
    doc = course_document(course_dir, relpath, index=index, solutions=solutions, figdir=figdir)
    body = blank_frontmatter((course_dir / relpath).read_text(encoding="utf-8"))
    return convert(body, doc, target, root=root)
