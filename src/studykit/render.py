"""`studykit render <course>`: the website's bridge to the pandoc filter set.

The site's content loader (site/src/loaders/pandoc.ts, docs/architecture.md §3.2) runs this
instead of assembling pandoc arguments itself, so the argv stays in one place
(`studykit.pandoc`). One run:

1. writes `_build/index.json` (`index.write`), which the filter resolves references against;
2. picks the files: overview, summary, exercise, mc, exam-mc, exam-task and cheatsheet are
   rendered to HTML, exam.yaml comes back as data only; `paths` narrows the selection;
3. computes each file's digest: sha256 of a format tag, the pandoc version, the filter tree
   (`pandoc/` plus the studykit modules that shape the output), the index and the file
   bytes. A file whose digest the caller already holds (`known`) comes back as `cached`
   without running pandoc;
4. renders the rest with `pandoc.run_filtered(target="html")` in a thread pool.

Output (`--json`), one document:

    {"schema": 1, "course": "<id>", "lang": "de", "root": "<absolute course dir>",
     "pandoc": "3.13", "files": [
       {"rel": "summary/02-rc-tiefpass.md", "kind": "summary", "digest": "<sha256>",
        "cached": false, "data": {…}, "html": "<h2 …", "findings": [{path, line, col,
        code, message, fix, severity}]}],
     "skipped": [{"rel": "…", "reason": "…"}]}

`data` is the frontmatter (or exam.yaml) as plain JSON: the pydantic model dumped in JSON
mode when it validates, otherwise the raw mapping plus a schema finding. `html` is null for
exam.yaml, for cached files and when the filter rejects the file. The html run has no source
positions, so a rejected file is run once more with the json target (+sourcepos) to give
its findings a line and column. Filter findings never raise: they are returned.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from studykit import content, index, pandoc, tools
from studykit import findings as findings_mod
from studykit.findings import Finding

RENDER_SCHEMA = 1
FORMAT_TAG = b"studykit-render/1"
HTML_KINDS = ("overview", "summary", "exercise", "mc", "exam-mc", "exam-task", "cheatsheet")
DATA_KINDS = ("exam",)
KINDS = HTML_KINDS + DATA_KINDS
# Modules whose code decides what the bridge returns besides pandoc itself.
SHAPING_MODULES = ("content.py", "findings.py", "index.py", "model.py", "pandoc.py", "render.py")


def pandoc_version() -> str:
    """The version of the pinned pandoc binary, e.g. "3.13"."""
    first = pandoc.run(["--version"]).stdout.splitlines()[0]
    return first.split()[-1]


def tree_digest(root: Path | None = None) -> str:
    """sha256 over the filter tree and the studykit modules that shape the output."""
    root = root or tools.repo_root()
    files = sorted(
        p
        for p in (root / "pandoc").rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.parts)
    )
    files += [Path(__file__).with_name(name) for name in SHAPING_MODULES]
    h = hashlib.sha256()
    for path in files:
        try:
            name = path.relative_to(root).as_posix()
        except ValueError:
            name = path.name
        h.update(name.encode() + b"\0" + path.read_bytes() + b"\0")
    return h.hexdigest()


def file_digest(base: bytes, path: Path) -> str:
    return hashlib.sha256(base + b"\0" + path.read_bytes()).hexdigest()


def jsonable(value: Any) -> Any:
    """YAML data as plain JSON (dates become ISO strings, keys strings)."""
    if isinstance(value, Mapping):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def doc_data(doc: content.Doc) -> tuple[Any, list[Finding]]:
    """(frontmatter as JSON, schema and YAML findings) for one file."""
    if doc.is_markdown and doc.split.error:
        fix = "start the file with a '---' line, the YAML fields, and a closing '---' line"
        return {}, [Finding(doc.display, 1, 1, "SK-SCHEMA-FRONTMATTER", doc.split.error, fix)]
    if doc.yaml is None:
        return {}, []
    found = [f for f in doc.yaml.findings if f.is_error]
    model, schema = doc.validated
    found += schema
    if model is not None:
        return model.model_dump(mode="json", by_alias=True), found
    raw = doc.data if isinstance(doc.data, Mapping) else {}
    return jsonable(raw), found


def _course_findings(root: Path, text: str) -> list[Finding]:
    """Findings from filter output, with course-relative paths turned into display paths."""
    out = []
    for f in findings_mod.parse(text):
        path = Path(f.path)
        if not path.is_absolute() and (root / path).exists():
            f = Finding(
                content.display_path(root / path),
                f.line,
                f.col,
                f.code,
                f.message,
                f.fix,
                f.severity,
            )
        out.append(f)
    return out


def render_html(root: Path, doc: content.Doc) -> tuple[str | None, list[Finding]]:
    """(html fragment or None, findings) for one Markdown file."""
    try:
        return pandoc.run_filtered(root, doc.rel, "html"), []
    except pandoc.FilterError as exc:
        found = _course_findings(root, "\n".join(exc.findings))
        try:  # the json run has +sourcepos, so its findings carry line and column
            pandoc.run_filtered(root, doc.rel, "json")
        except pandoc.PandocError as again:
            positioned = _course_findings(root, str(again))
            if positioned:
                found = positioned
        if not found:
            last = exc.stderr.strip().splitlines()[-1:] or ["the filter rejected the file"]
            found = [_fail(doc, last[0])]
        return None, found
    except (pandoc.PandocError, OSError) as exc:
        last = str(exc).strip().splitlines()[-1:] or [type(exc).__name__]
        return None, [_fail(doc, last[0])]


def _fail(doc: content.Doc, message: str) -> Finding:
    return Finding(
        doc.display,
        1,
        1,
        "SK-PANDOC-FAIL",
        f"pandoc failed: {message}",
        "run `studykit lint` on the file and fix the reported construct",
    )


def _select(
    tree: content.CourseTree, paths: Iterable[str | Path] | None
) -> tuple[list[content.Doc], list[dict[str, str]]]:
    docs = [d for d in tree if d.kind in KINDS]
    if paths is None:
        return docs, []
    wanted: list[content.Doc] = []
    skipped: list[dict[str, str]] = []
    for raw in paths:
        path = Path(raw)
        if path.is_absolute() or path.exists():
            try:
                rel = path.resolve().relative_to(tree.root).as_posix()
            except ValueError:
                skipped.append({"rel": str(raw), "reason": "outside the course directory"})
                continue
        else:
            rel = path.as_posix()
        doc = tree.get(rel)
        if doc is None:
            skipped.append({"rel": rel, "reason": "no such course file"})
        elif doc.kind not in KINDS:
            skipped.append({"rel": rel, "reason": f"{doc.kind} files are not rendered"})
        elif doc not in wanted:
            wanted.append(doc)
    return wanted, skipped


def render_course(
    course_dir: Path,
    *,
    paths: Iterable[str | Path] | None = None,
    known: Mapping[str, str] | None = None,
    jobs: int | None = None,
) -> dict[str, Any]:
    """Render a course's files for the website (see the module docstring for the shape)."""
    tree = content.CourseTree(course_dir)
    index_file, data = index.write(tree)
    version = pandoc_version()
    base = b"\0".join(
        [FORMAT_TAG, version.encode(), tree_digest().encode(), index_file.read_bytes()]
    )
    docs, skipped = _select(tree, paths)
    known = known or {}
    tree.context  # noqa: B018 - compute the shared validation context before the threads

    def one(doc: content.Doc) -> dict[str, Any]:
        digest = file_digest(base, doc.path)
        row: dict[str, Any] = {"rel": doc.rel, "kind": doc.kind, "digest": digest}
        if known.get(doc.rel) == digest:
            return {**row, "cached": True, "data": None, "html": None, "findings": []}
        fm, found = doc_data(doc)
        html = None
        if doc.kind in HTML_KINDS and not (doc.is_markdown and doc.split.error):
            html, filter_findings = render_html(tree.root, doc)
            found += filter_findings
        return {
            **row,
            "cached": False,
            "data": fm,
            "html": html,
            "findings": [f.to_dict() for f in found],
        }

    workers = max(1, jobs or os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        files = list(pool.map(one, docs))
    return {
        "schema": RENDER_SCHEMA,
        "course": data["course"],
        "lang": data["lang"],
        "root": str(tree.root),
        "pandoc": version,
        "files": files,
        "skipped": skipped,
    }
