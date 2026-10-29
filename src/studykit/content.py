"""Course content on disk: discovery, frontmatter, the fence-line scanner and the id index.

Everything here is pure Python, so `studykit lint` can check a file in a few milliseconds
without pandoc (docs/architecture.md §2.1, §2.3, §4.3). Fences and math are scanned line by
line; links are found per paragraph, because their text may wrap. The scanners skip fenced
code; they report positions as file line and column, both 1-based.
"""

from __future__ import annotations

import bisect
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from studykit import model, tools, yamlio
from studykit.findings import Finding

K = model.KEBAB

# Course-relative path -> file kind. Anything else in a content directory is SK-STRUCT-PATH.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("course", re.compile(r"^course\.yaml$")),
    ("overview", re.compile(r"^overview\.md$")),
    ("cheatsheet", re.compile(r"^cheatsheet\.md$")),
    ("plan", re.compile(r"^plan\.yaml$")),
    ("summary", re.compile(rf"^summary/(?P<nn>[0-9]{{2}})-(?P<topic>{K})\.md$")),
    ("exercise", re.compile(rf"^exercises/(?P<topic>{K})/(?P<id>ex-{K})\.md$")),
    ("mc", re.compile(rf"^mc/(?P<topic>{K})\.md$")),
    ("exam", re.compile(rf"^exams/(?P<exam>{K})/exam\.yaml$")),
    ("exam-mc", re.compile(rf"^exams/(?P<exam>{K})/mc\.md$")),
    (
        "exam-task",
        re.compile(rf"^exams/(?P<exam>{K})/(?P<nn>[0-9]{{2}})-(?P<id>{K}-t[0-9]+)\.md$"),
    ),
    ("figure", re.compile(rf"^figures/(?P<slug>{K})\.py$")),
    ("exam-profile", re.compile(r"^analysis/exam-profile\.yaml$")),
    ("notation", re.compile(r"^analysis/notation\.yaml$")),
    ("manifest", re.compile(r"^sources/manifest\.yaml$")),
    ("outline", re.compile(r"^sources/outline\.md$")),
]
# Expected layout per directory, for the SK-STRUCT-PATH hint.
LAYOUT = {
    "": "course.yaml, overview.md, cheatsheet.md, plan.yaml",
    "summary": "summary/NN-<topic>.md",
    "exercises": "exercises/<topic>/<ex-id>.md",
    "mc": "mc/<topic>.md",
    "exams": "exams/<exam-id>/{exam.yaml, NN-<task-id>.md, mc.md}",
    "figures": "figures/<slug>.py",
    "analysis": "analysis/{exam-profile.yaml, notation.yaml}",
    "sources": "sources/{manifest.yaml, outline.md}",
}
# Generated or private trees that discovery never enters.
SKIP_DIRS = {"_build", "_history", "state", "progress", "checks", "__pycache__"}
SKIP_SUBTREES = {"sources/raw", "sources/text", "sources/notes"}
MARKDOWN_KINDS = {"overview", "summary", "exercise", "mc", "exam-mc", "exam-task", "cheatsheet"}
YAML_KINDS = {"course", "plan", "exam", "exam-profile", "notation", "manifest"}

BLOCKS = ("hint", "solution", "definition", "theorem", "example", "note", "warning", "takeaways")
ALLOWED_BLOCKS = {
    "exercise": {"hint", "solution"},
    "exam-task": {"hint", "solution"},
    "summary": {"definition", "theorem", "example", "note", "warning", "takeaways"},
    "cheatsheet": {"definition", "note", "warning"},
    "mc": {"mcq"},
    "exam-mc": {"mcq"},
    "overview": set(),
}
CODE_LANGUAGES = [
    "python",
    "matlab",
    "octave",
    "c",
    "cpp",
    "vhdl",
    "verilog",
    "systemverilog",
    "julia",
    "text",
]


def courses_dir() -> Path:
    return Path(os.environ.get("STUDYKIT_COURSES_DIR", tools.repo_root() / "courses"))


def display_path(path: Path) -> str:
    """How findings name a file: relative to the repository when inside it."""
    path = path.resolve()
    try:
        return path.relative_to(tools.repo_root().resolve()).as_posix()
    except ValueError:
        return str(path)


def classify(rel: str) -> tuple[str, dict[str, str]]:
    for kind, rx in PATTERNS:
        m = rx.match(rel)
        if m:
            return kind, m.groupdict()
    return "unknown", {}


def find_course_root(path: Path) -> Path | None:
    """The course directory containing `path` (the nearest ancestor with course.yaml)."""
    path = path.resolve()
    for parent in [path, *path.parents]:
        if (parent / "course.yaml").is_file():
            return parent
    return None


def resolve_course(arg: str) -> Path:
    """A course given by id (in the courses directory) or by path."""
    candidate = Path(arg)
    if candidate.is_dir():
        return candidate.resolve()
    return (courses_dir() / arg).resolve()


def list_courses() -> list[Path]:
    base = courses_dir()
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if (p / "course.yaml").is_file())


# --- frontmatter --------------------------------------------------------------------------


@dataclass
class Split:
    yaml: str | None  # the frontmatter text, without the --- fences
    body: str
    yaml_line: int  # file line of the first YAML line
    body_line: int  # file line of the first body line
    error: str | None = None


def split_frontmatter(text: str) -> Split:
    """Split a leading `---` YAML block from the Markdown body (pandoc never sees it)."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        return Split(None, text, 1, 1, "the file does not start with a --- frontmatter block")
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r") == "---":
            return Split("\n".join(lines[1:i]) + "\n", "\n".join(lines[i + 1 :]), 2, i + 2)
    return Split(None, text, 1, 1, "the frontmatter block has no closing --- line")


# --- body scanner -------------------------------------------------------------------------

CODE_FENCE_RE = re.compile(r"^(?P<indent>\s*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
DIV_FENCE_RE = re.compile(r"^(?P<indent>\s*)(?P<colons>:{3,})(?P<rest>.*)$")
NAME_RE = re.compile(r"^ (?P<name>[A-Za-z][\w-]*)\s*$")
ATTRS_RE = re.compile(r"^ ?\{(?P<attrs>.*)\}\s*$")
ATTR_TOKEN_RE = re.compile(
    r'\s*(?:(?P<cls>\.[\w-]+)|(?P<id>#[\w-]+)|(?P<key>[\w-]+)=(?:"(?P<qval>[^"]*)"|(?P<val>[^\s"}]+)))'
)


def parse_attrs(text: str) -> tuple[list[str], str | None, dict[str, str], str | None]:
    """Pandoc attributes `{.cls #id key="v"}` -> (classes, id, pairs, error)."""
    classes: list[str] = []
    ident = None
    pairs: dict[str, str] = {}
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        m = ATTR_TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            return classes, ident, pairs, f"cannot read attributes near '{text[pos:].strip()}'"
        if m["cls"]:
            classes.append(m["cls"][1:])
        elif m["id"]:
            if ident is not None:
                return classes, ident, pairs, "more than one #id"
            ident = m["id"][1:]
        else:
            key = m["key"]
            if key in pairs:
                return classes, ident, pairs, f"attribute '{key}' appears twice"
            pairs[key] = m["qval"] if m["qval"] is not None else m["val"]
        pos = m.end()
    return classes, ident, pairs, None


@dataclass
class Line:
    no: int  # file line number
    text: str
    in_code: bool = False


@dataclass
class Block:
    name: str
    colons: int
    open_line: int  # index into Body.lines
    close_line: int | None = None
    ident: str | None = None
    classes: list[str] = field(default_factory=list)
    attrs: dict[str, str] = field(default_factory=dict)
    parent: Block | None = None
    children: list[Block] = field(default_factory=list)
    known: bool = True  # False for unknown names and malformed fences (already reported)


@dataclass
class Option:
    line: int  # file line
    correct: bool
    paragraphs: list[list[str]]

    @property
    def text(self) -> str:
        return " ".join(s.strip() for s in self.paragraphs[0])

    @property
    def why(self) -> str:
        return " ".join(s.strip() for s in self.paragraphs[1]) if len(self.paragraphs) > 1 else ""


@dataclass
class Question:
    block: Block
    line: int  # file line of the opening fence
    stem: list[str] = field(default_factory=list)
    options: list[Option] = field(default_factory=list)
    explanations: list[tuple[int, str]] = field(default_factory=list)  # (file line, text)

    @property
    def id(self) -> str | None:
        return self.block.ident

    @property
    def type(self) -> str | None:
        return self.block.attrs.get("type")


@dataclass
class Formula:
    tex: str
    display: bool
    line: int
    col: int


@dataclass
class Link:
    image: bool
    text: str
    target: str
    line: int
    col: int
    alone: bool  # alone in its paragraph (figures must be)
    attrs: bool  # followed by {…}


OPTION_RE = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<text>\S.*)$")
OPTIONISH_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s*\[.?\]")
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
BLOCK_MARKER_RE = re.compile(r"^\s*(?:[=+\-*#>]|[0-9]+[.)])")
HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
# The delimiter row of a pipe table (`|---|:--:|`), without its container's prefix; it
# needs a `|`, or `---` is a rule.
TABLE_DELIMITER_RE = re.compile(r"^\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")
QUOTE_PREFIX_RE = re.compile(r"^(?: {0,3}>[ ]?)+")
LIST_MARKER_RE = re.compile(r"^[ \t]*(?:[-+*]|[0-9]{1,9}[.)])(?:[ \t]+|$)")
UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")
# A word broken with a hyphen at the end of a line: `[RC-` + newline + `Tiefpass]`.
LINE_END_HYPHEN_RE = re.compile(r"[^\W\d_]-$")
LINE_START_LETTER_RE = re.compile(r"^[^\W\d_]")
# Words after which a line-final hyphen is a suspended compound („Ein- und Ausgang“).
SUSPENDED_HYPHEN_WORDS = {"und", "oder", "bzw.", "sowie", "bis", "wie", "noch", "and", "or", "to"}


def _container(text: str) -> tuple[int, bool, str]:
    """A line's block-quote depth, whether it opens a list item, and its text without both."""
    quote = QUOTE_PREFIX_RE.match(text)
    depth = quote.group().count(">") if quote else 0
    rest = text[quote.end() :] if quote else text
    item = LIST_MARKER_RE.match(rest)
    if item:
        rest = rest[item.end() :]
    return depth, item is not None, rest.strip()


def _mask(text: str, start: int, end: int) -> str:
    return text[:start] + " " * (end - start) + text[end:]


# --- inline links -----------------------------------------------------------------------------
#
# A small CommonMark subset, enough to find every link pandoc would build: link text may wrap
# onto the next line, a destination may be <bracketed> and carry a title, and reference links
# resolve through `[label]: target` definitions. Code spans, math and backslash escapes are
# masked first, because brackets inside them never start a link.

HIDDEN = "\x00"  # placeholder for masked characters; never whitespace, never a bracket
ASCII_PUNCT = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
ESCAPE_RE = re.compile(r"\\([!-/:-@\[-`{-~])")
AUTOLINK_RE = re.compile(r"<([A-Za-z][A-Za-z0-9+.\-]{1,31}:[^\s<>\x00]*)>")
REF_DEF_RE = re.compile(
    r"[ ]{0,3}\[(?P<label>(?:[^\[\]\\]|\\.)+)\]:"
    r"[ \t]*\n?[ \t]*(?P<dest><[^<>\n]*>|[^\s<]\S*)"
    r"(?:(?:[ \t]*\n[ \t]*|[ \t]+)(?P<title>\"[^\"]*\"|'[^']*'|\([^()]*\)))?[ \t]*(?:\n|\Z)"
)
TITLE_CLOSE = {'"': '"', "'": "'", "(": ")"}


def normalize_label(label: str) -> str:
    return " ".join(label.split()).casefold()


def mask_inline(text: str) -> str:
    """`text` with escapes, code spans and $…$ math replaced by HIDDEN (same length)."""
    out = list(text)
    n = len(text)
    i = 0

    def hide(a: int, b: int) -> None:
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = HIDDEN

    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n and text[i + 1] in ASCII_PUNCT:
            hide(i, i + 2)
            i += 2
        elif c == "`":
            run = len(text[i:]) - len(text[i:].lstrip("`"))
            m = re.compile(rf"(?<!`)`{{{run}}}(?!`)").search(text, i + run)
            if m is None:
                i += run
                continue
            hide(i, m.end())
            i = m.end()
        elif c == "$":
            if text.startswith("$$", i):
                end = text.find("$$", i + 2)
                end = n if end < 0 else end + 2
                hide(i, end)
                i = end
                continue
            end = _inline_math_end(text, i)
            if end is None:
                i += 1
                continue
            hide(i, end)
            i = end
        else:
            i += 1
    return "".join(out)


def _inline_math_end(text: str, i: int) -> int | None:
    """End of $…$ math opening at i (pandoc's rule), or None if this $ is literal."""
    if i + 1 >= len(text) or text[i + 1].isspace():
        return None
    k = i + 1
    while k < len(text) and text[k] != "\n":
        if text[k] == "\\":
            k += 2
            continue
        if text[k] == "$" and not text[k - 1].isspace():
            after = text[k + 1 : k + 2]
            if not after.isdigit():
                return k + 1
        k += 1
    return None


@dataclass
class FoundLink:
    start: int  # offset of `!` or `[` (or `<` of an autolink)
    end: int  # offset after the link, including {attrs}
    text_start: int
    text_end: int
    image: bool
    text: str
    target: str
    attrs: bool


def _close_bracket(masked: str, i: int) -> int | None:
    """Offset of the `]` matching the `[` at i, allowing nested balanced brackets."""
    depth = 0
    for k in range(i, len(masked)):
        if masked[k] == "[":
            depth += 1
        elif masked[k] == "]":
            depth -= 1
            if depth == 0:
                return k
    return None


def _skip_space(masked: str, k: int) -> int:
    """Skip spaces and tabs with at most one line break."""
    newline = False
    while k < len(masked) and masked[k] in " \t\n":
        if masked[k] == "\n":
            if newline:
                break
            newline = True
        k += 1
    return k


def _inline_destination(masked: str, text: str, k: int) -> tuple[str, int] | None:
    """Parse `(dest "title")` starting after the `(` at k-1; return (dest, end) or None."""
    k = _skip_space(masked, k)
    n = len(masked)
    if k < n and masked[k] == "<":
        close = masked.find(">", k + 1)
        if close < 0 or "\n" in masked[k:close] or "<" in masked[k + 1 : close]:
            return None
        dest = text[k + 1 : close]
        k = close + 1
    else:
        start, depth = k, 0
        while k < n and not masked[k].isspace():
            if masked[k] == "(":
                depth += 1
            elif masked[k] == ")":
                if depth == 0:
                    break
                depth -= 1
            k += 1
        if depth:
            return None
        dest = text[start:k]
    gap = _skip_space(masked, k)
    if gap > k and gap < n and masked[gap] in TITLE_CLOSE:
        close = masked.find(TITLE_CLOSE[masked[gap]], gap + 1)
        if close < 0:
            return None
        k = _skip_space(masked, close + 1)
    else:
        k = gap
    if k >= n or masked[k] != ")":
        return None
    return ESCAPE_RE.sub(r"\1", dest), k + 1


def scan_links(masked: str, text: str, defs: dict[str, str]) -> list[FoundLink]:
    """Every link in one paragraph; `masked` is `text` after mask_inline()."""
    found: list[FoundLink] = []
    for i, c in enumerate(masked):
        if c != "[":
            continue
        close = _close_bracket(masked, i)
        if close is None:
            continue
        image = i > 0 and masked[i - 1] == "!"
        label = text[i + 1 : close]
        target: str | None = None
        end = close + 1
        nxt = masked[close + 1 : close + 2]
        if nxt == "(":
            parsed = _inline_destination(masked, text, close + 2)
            if parsed is not None:
                target, end = parsed
        elif nxt == "[":
            label_end = masked.find("]", close + 2)
            if label_end >= 0 and "[" not in masked[close + 2 : label_end]:
                ref = text[close + 2 : label_end] or label
                if normalize_label(ref) in defs:
                    target, end = defs[normalize_label(ref)], label_end + 1
        if target is None and normalize_label(label) in defs:
            target, end = defs[normalize_label(label)], close + 1
        if target is None:
            continue
        attrs = masked[end : end + 1] == "{"
        if attrs:
            brace = masked.find("}", end)
            end = brace + 1 if brace >= 0 else len(masked)
        start = i - 1 if image else i
        found.append(FoundLink(start, end, i + 1, close, image, label, target, attrs))
    # CommonMark: a link never contains another link (images may), and nothing inside a
    # destination, title or attribute block is a link.
    kept = []
    for f in found:
        inside_other = any(
            o is not f
            and o.start <= f.start
            and f.end <= o.end
            and not o.text_start <= f.start < o.text_end
            for o in found
        )
        has_inner_link = not f.image and any(
            o is not f and not o.image and f.text_start <= o.start < f.text_end for o in found
        )
        if not inside_other and not has_inner_link:
            kept.append(f)
    for m in AUTOLINK_RE.finditer(masked):
        if any(f.start <= m.start() < f.end for f in kept):
            continue
        kept.append(FoundLink(m.start(), m.end(), m.start(1), m.end(1), False, m[1], m[1], False))
    kept.sort(key=lambda f: f.start)
    return kept


@dataclass
class Paragraph:
    lines: list[Line]
    display: list[bool]  # line is display math ($$ fences included)

    @cached_property
    def text(self) -> str:
        return "\n".join(ln.text for ln in self.lines)

    @cached_property
    def starts(self) -> list[int]:
        out, offset = [], 0
        for ln in self.lines:
            out.append(offset)
            offset += len(ln.text) + 1
        return out

    @cached_property
    def _without_definitions(self) -> tuple[str, list[tuple[str, str]]]:
        """Leading `[label]: target` definitions blanked out, and the definitions."""
        text, defs, pos = self.text, [], 0
        while (m := REF_DEF_RE.match(text, pos)) is not None:
            label = normalize_label(m["label"])
            if not label:
                break
            dest = m["dest"][1:-1] if m["dest"].startswith("<") else m["dest"]
            defs.append((label, ESCAPE_RE.sub(r"\1", dest)))
            pos = m.end()
        blanked = re.sub(r"[^\n]", " ", text[:pos]) + text[pos:]
        return blanked, defs

    @property
    def definitions(self) -> list[tuple[str, str]]:
        return self._without_definitions[1]

    @cached_property
    def masked(self) -> str:
        """The paragraph with definitions blanked and math, code and escapes hidden."""
        lines = self._without_definitions[0].split("\n")
        pairs = zip(lines, self.display, strict=True)
        lines = [HIDDEN * len(ln) if display else ln for ln, display in pairs]
        return mask_inline("\n".join(lines))

    def position(self, offset: int) -> tuple[int, int]:
        """File (line, column) of a character offset, both 1-based."""
        k = bisect.bisect_right(self.starts, offset) - 1
        return self.lines[k].no, offset - self.starts[k] + 1


class Body:
    """The Markdown body of a file: code-aware lines, fences, blocks, math and links."""

    def __init__(self, text: str, first_line: int, path: str, kind: str):
        self.path = path
        self.kind = kind
        self.lines = [Line(first_line + i, t) for i, t in enumerate(text.split("\n"))]
        self.findings: list[Finding] = []
        self.code_blocks: list[tuple[int, str]] = []  # (file line, info string)
        self._mark_code()

    def finding(self, line: int, col: int, code: str, message: str, fix: str, severity="error"):
        self.findings.append(Finding(self.path, line, col, code, message, fix, severity))

    def _mark_code(self) -> None:
        open_fence: tuple[str, int, int] | None = None  # (char, length, line index)
        for i, ln in enumerate(self.lines):
            m = CODE_FENCE_RE.match(ln.text)
            if open_fence is None:
                if m:
                    open_fence = (m["fence"][0], len(m["fence"]), i)
                    self.code_blocks.append((ln.no, m["info"].strip()))
                    ln.in_code = True
            else:
                ln.in_code = True
                char, length, _ = open_fence
                if (
                    m
                    and m["fence"][0] == char
                    and len(m["fence"]) >= length
                    and not m["info"].strip()
                ):
                    open_fence = None
        if open_fence is not None:
            no = self.lines[open_fence[2]].no
            self.finding(
                no,
                1,
                "SK-BLOCK-CODE",
                "code fence is never closed",
                "close it with ``` on its own line",
            )

    def text_lines(self) -> Iterator[tuple[int, Line]]:
        for i, ln in enumerate(self.lines):
            if not ln.in_code:
                yield i, ln

    # --- fenced divs ---

    @cached_property
    def blocks(self) -> list[Block]:
        """Top-level blocks (children nested); fence problems become findings."""
        top: list[Block] = []
        stack: list[Block] = []
        allowed = ALLOWED_BLOCKS.get(self.kind, set())
        for i, ln in self.text_lines():
            m = DIV_FENCE_RE.match(ln.text)
            if not m:
                continue
            colons, rest = len(m["colons"]), m["rest"]
            if m["indent"]:
                self.finding(
                    ln.no, 1, "SK-BLOCK-FENCE", "fence is indented", "start ::: fences in column 1"
                )
                continue
            if not rest.strip():  # closing fence
                if not stack:
                    self.finding(
                        ln.no,
                        1,
                        "SK-BLOCK-FENCE",
                        "closing fence without an open block",
                        "delete it or add the missing opening fence",
                    )
                    continue
                block = stack.pop()
                block.close_line = i
                if colons != block.colons:
                    self.finding(
                        ln.no,
                        1,
                        "SK-BLOCK-FENCE",
                        f"closing fence has {colons} colons, but '{block.name}' opened with "
                        f"{block.colons}",
                        "close ::: blocks with ::: and the mcq block with ::::",
                    )
                self._check_blank_after(i)
                continue
            block = self._open_fence(ln, colons, rest)
            block.open_line = i
            self._check_blank_before(i)
            if stack:
                parent = stack[-1]
                block.parent = parent
                parent.children.append(block)
                if block.known and not (parent.name == "mcq" and block.name == "explanation"):
                    self.finding(
                        ln.no,
                        1,
                        "SK-BLOCK-NESTING",
                        f"'{block.name}' is nested inside '{parent.name}'",
                        "close the outer block first; only explanation may sit inside mcq",
                    )
            else:
                top.append(block)
                if not block.known:
                    pass
                elif block.name == "explanation":
                    self.finding(
                        ln.no,
                        1,
                        "SK-BLOCK-PLACEMENT",
                        "explanation outside an mcq block",
                        "put ::: explanation inside the :::: {.mcq …} block, after the options",
                    )
                elif block.name not in allowed:
                    where = ", ".join(sorted(allowed)) or "no blocks"
                    self.finding(
                        ln.no,
                        1,
                        "SK-BLOCK-PLACEMENT",
                        f"'{block.name}' is not allowed in {self.kind} files",
                        f"this file kind allows: {where}",
                    )
            stack.append(block)
        for block in stack:
            self.finding(
                self.lines[block.open_line].no,
                1,
                "SK-BLOCK-FENCE",
                f"'{block.name}' block is never closed",
                "add the closing fence (::: or :::: for mcq) after its content",
            )
        return top

    def _open_fence(self, ln: Line, colons: int, rest: str) -> Block:
        name_m = NAME_RE.match(rest)
        attrs_m = ATTRS_RE.match(rest)
        if name_m:
            name = name_m["name"]
            if name == "mcq":
                self.finding(
                    ln.no,
                    1,
                    "SK-BLOCK-FENCE",
                    "mcq block without attributes",
                    'write :::: {.mcq #mc-<topic>-NNN type="single" difficulty="2"}',
                )
                return Block("mcq", colons, 0)
            if name not in (*BLOCKS, "explanation"):
                self.finding(
                    ln.no,
                    1,
                    "SK-BLOCK-UNKNOWN",
                    f"unknown block '{name}'",
                    f"use one of: {', '.join((*BLOCKS, 'explanation'))}",
                )
                return Block(name, colons, 0, known=False)
            if colons != 3:
                self.finding(
                    ln.no,
                    1,
                    "SK-BLOCK-FENCE",
                    f"'{name}' fence has {colons} colons",
                    f"write exactly '::: {name}'",
                )
            return Block(name, colons, 0)
        if attrs_m:
            classes, ident, pairs, error = parse_attrs(attrs_m["attrs"])
            name = classes[0] if classes else ""
            if name != "mcq":
                known = name in (*BLOCKS, "explanation")
                self.finding(
                    ln.no,
                    1,
                    "SK-BLOCK-FENCE" if known else "SK-BLOCK-UNKNOWN",
                    f"block '{name or '{…}'}' with attributes",
                    f"write '::: {name}' without attributes"
                    if known
                    else "only :::: {.mcq …} takes attributes",
                )
                return Block(name or "?", colons, 0, known=False)
            if colons != 4:
                self.finding(
                    ln.no,
                    1,
                    "SK-BLOCK-FENCE",
                    f"mcq fence has {colons} colons",
                    "open and close mcq blocks with exactly four colons (::::)",
                )
            block = Block("mcq", colons, 0, ident=ident, classes=classes, attrs=pairs)
            if error:
                self.finding(
                    ln.no,
                    1,
                    "SK-MCQ-ATTR",
                    f"mcq attributes: {error}",
                    'write :::: {.mcq #mc-<topic>-NNN type="single" difficulty="2"}',
                )
            return block
        self.finding(
            ln.no,
            1,
            "SK-BLOCK-FENCE",
            f"malformed fence '{ln.text.strip()}'",
            "write '::: name' (one space, one known name) or ':::' alone to close",
        )
        return Block("?", colons, 0, known=False)

    def _is_fence(self, i: int) -> bool:
        ln = self.lines[i]
        return not ln.in_code and DIV_FENCE_RE.match(ln.text) is not None

    def _check_blank_before(self, i: int) -> None:
        if i > 0 and self.lines[i - 1].text.strip() and not self._is_fence(i - 1):
            self.finding(
                self.lines[i].no,
                1,
                "SK-BLOCK-BLANK",
                "no blank line before the opening fence",
                "insert an empty line above the fence",
            )

    def _check_blank_after(self, i: int) -> None:
        if i + 1 < len(self.lines) and self.lines[i + 1].text.strip() and not self._is_fence(i + 1):
            self.finding(
                self.lines[i].no,
                1,
                "SK-BLOCK-BLANK",
                "no blank line after the closing fence",
                "insert an empty line below the fence",
            )

    def all_blocks(self) -> Iterator[Block]:
        stack = list(reversed(self.blocks))
        while stack:
            block = stack.pop()
            yield block
            stack.extend(reversed(block.children))

    def block_text(self, block: Block) -> list[Line]:
        """Lines strictly inside a block, excluding nested blocks."""
        end = block.close_line if block.close_line is not None else len(self.lines)
        skip: set[int] = set()
        for child in block.children:
            child_end = child.close_line if child.close_line is not None else end
            skip.update(range(child.open_line, child_end + 1))
        return [self.lines[i] for i in range(block.open_line + 1, end) if i not in skip]

    def outside_blocks(self) -> list[Line]:
        inside: set[int] = set()
        for block in self.blocks:
            end = block.close_line if block.close_line is not None else len(self.lines) - 1
            inside.update(range(block.open_line, end + 1))
        return [ln for i, ln in enumerate(self.lines) if i not in inside]

    # --- multiple choice ---

    @cached_property
    def questions(self) -> list[Question]:
        out = []
        for block in self.all_blocks():
            if block.name == "mcq":
                out.append(self._parse_question(block))
        return out

    def _parse_question(self, block: Block) -> Question:
        q = Question(block, self.lines[block.open_line].no)
        end = block.close_line if block.close_line is not None else len(self.lines)
        explanation_starts = {c.open_line: c for c in block.children if c.name == "explanation"}
        children = {
            i for c in block.children for i in range(c.open_line, (c.close_line or end) + 1)
        }
        current: Option | None = None
        pending_break = False
        after_explanation = False
        for i in range(block.open_line + 1, end):
            ln = self.lines[i]
            if i in explanation_starts:
                child = explanation_starts[i]
                text = " ".join(x.text.strip() for x in self.block_text(child) if x.text.strip())
                q.explanations.append((ln.no, text))
                if not q.options:
                    self.finding(
                        ln.no,
                        1,
                        "SK-MCQ-FORMAT",
                        "explanation comes before the options",
                        "order the question as stem, options, explanation",
                    )
                after_explanation = True
                current = None
                continue
            if i in children:
                continue
            text = ln.text
            if not text.strip():
                pending_break = True
                continue
            if after_explanation:
                self.finding(
                    ln.no,
                    1,
                    "SK-MCQ-FORMAT",
                    "text after the explanation",
                    "end the question with its explanation block and the closing ::::",
                )
                after_explanation = False  # report once
                continue
            m = OPTION_RE.match(text)
            if m:
                current = Option(ln.no, m["mark"] in "xX", [[m["text"]]])
                q.options.append(current)
                pending_break = False
                continue
            if not ln.in_code and OPTIONISH_RE.match(text):
                self.finding(
                    ln.no,
                    1,
                    "SK-MCQ-FORMAT",
                    f"malformed option '{text.strip()[:30]}'",
                    "write options as '- [x] text' or '- [ ] text' in column 1",
                )
                continue
            if current is None:
                q.stem.append(text)
                pending_break = False
                continue
            indented = text.startswith("  ")
            if pending_break and not indented:
                self.finding(
                    ln.no,
                    1,
                    "SK-MCQ-FORMAT",
                    "unindented text after an option",
                    "indent the why paragraph by two spaces; general remarks go into the "
                    "explanation",
                )
                current = None
                pending_break = False
                continue
            if pending_break:
                current.paragraphs.append([text])
            else:
                current.paragraphs[-1].append(text)
            pending_break = False
        return q

    # --- math ---

    @cached_property
    def formulas(self) -> list[Formula]:
        """Every formula with its position; syntax problems become findings."""
        out: list[Formula] = []
        display: list[str] | None = None
        start = (0, 0)
        for _, ln in self.text_lines():
            stripped = ln.text.strip()
            if display is not None:
                if stripped == "$$":
                    if display:
                        out.append(Formula("\n".join(display), True, *start))
                    else:
                        self.finding(
                            start[0], start[1], "SK-MATH-DISPLAY", "empty display math", "delete it"
                        )
                    display = None
                elif not stripped:
                    self.finding(
                        ln.no,
                        1,
                        "SK-MATH-DISPLAY",
                        "blank line inside display math",
                        "remove the blank line; display math must be one block",
                    )
                    display = None
                else:
                    if BLOCK_MARKER_RE.match(ln.text):
                        self.finding(
                            ln.no,
                            len(ln.text) - len(ln.text.lstrip()) + 1,
                            "SK-MATH-BLOCKMARK",
                            f"line inside $$ starts with '{stripped[:2]}', which Markdown reads "
                            "as a heading, list or quote",
                            "keep the operator at the end of the previous line (or start the "
                            "line with {})",
                        )
                    display.append(ln.text.strip())
                continue
            if stripped == "$$":
                display = []
                start = (ln.no, ln.text.index("$") + 1)
                continue
            if ln.no not in self.table_rows:
                out.extend(self._inline_math(ln))
                continue
            for f in self._inline_math(ln):
                if "|" in f.tex:
                    self.finding(
                        ln.no,
                        f.col,
                        "SK-BLOCK-TABLE",
                        "'|' inside inline math on a table row ends the cell there ('\\|' "
                        "too, as an escaped '|'): pandoc cuts the row, or in the header row "
                        "turns the table into a paragraph",
                        "write \\lvert … \\rvert for an absolute value, \\lVert … \\rVert for "
                        "a norm, \\mid for a divider",
                    )
                else:
                    out.append(f)
            self._check_table_code(ln)
        if display is not None:
            self.finding(
                start[0],
                start[1],
                "SK-MATH-DISPLAY",
                "display math is never closed",
                "close it with $$ alone on a line",
            )
        return out

    def _inline_math(self, ln: Line) -> list[Formula]:
        text = INLINE_CODE_RE.sub(lambda m: " " * len(m.group()), ln.text)
        if "$$" in text:
            self.finding(
                ln.no,
                text.index("$$") + 1,
                "SK-MATH-DISPLAY",
                "$$ inside a line",
                "put $$ alone on its own line before and after the formula",
            )
            return []
        dollars = [i for i, c in enumerate(text) if c == "$" and (i == 0 or text[i - 1] != "\\")]
        out = []
        for k in range(0, len(dollars) - 1, 2):
            o, c = dollars[k], dollars[k + 1]
            tex = text[o + 1 : c]
            if tex[0].isspace() or tex[-1].isspace():
                self.finding(
                    ln.no,
                    o + 1,
                    "SK-MATH-INLINE",
                    "space just inside the $ of inline math",
                    "write $x$, not $ x $",
                )
            elif c + 1 < len(text) and text[c + 1].isdigit():
                self.finding(
                    ln.no,
                    c + 2,
                    "SK-MATH-INLINE",
                    "digit right after the closing $",
                    "move the digit into the math or add a space",
                )
            else:
                out.append(Formula(tex, False, ln.no, o + 1))
        if len(dollars) % 2:
            self.finding(
                ln.no,
                dollars[-1] + 1,
                "SK-MATH-INLINE",
                "unmatched $",
                "close the inline math on the same line, or write \\$ for a dollar sign",
            )
        return out

    # --- tables and line breaks ---

    @cached_property
    def table_rows(self) -> set[int]:
        """File lines of pipe-table rows: the header row and the rows below the delimiter.

        As in pandoc's commonmark_x pipe tables: a table starts a paragraph in its
        container (a block quote, a list item, also one indented four spaces or more), with
        a header line and a delimiter row (`|---|---|`); it cannot interrupt a paragraph.
        Its body is every following line of the same quote with a `|` in it.
        """
        rows: set[int] = set()
        in_list = False  # the previous paragraph belongs to a list, so indented text is too
        for para in self.paragraphs:
            parts = [_container(ln.text) for ln in para.lines]
            depth, first = parts[0][0], para.lines[0].text
            if not depth:
                indent = len(first.expandtabs(4)) - len(first.expandtabs(4).lstrip(" "))
                if LIST_MARKER_RE.match(first) and (indent < 4 or in_list):
                    in_list = True
                elif indent < 2:
                    in_list = False
                elif indent >= 4 and not in_list:
                    continue  # an indented code block
            k = 0
            while k < len(para.lines) - 1:
                (d0, item, head), (d1, _, delim) = parts[k], parts[k + 1]
                # first line of the paragraph, of a list item, of a quote, or after a `>` line
                starts = k == 0 or item or d0 != parts[k - 1][0] or not parts[k - 1][2]
                if (
                    starts
                    and d0 == d1
                    and "|" in head
                    and not para.display[k]
                    and not para.display[k + 1]
                    and "|" in delim
                    and TABLE_DELIMITER_RE.match(delim)
                ):
                    rows.add(para.lines[k].no)
                    k += 2
                    while k < len(para.lines) and parts[k][0] == d0 and "|" in parts[k][2]:
                        rows.add(para.lines[k].no)
                        k += 1
                    continue
                k += 1
        return rows

    def _check_table_code(self, ln: Line) -> None:
        """A bare '|' in a code span on a table row ends the cell, as in math."""
        for m in INLINE_CODE_RE.finditer(ln.text):
            if UNESCAPED_PIPE_RE.search(m.group()):
                self.finding(
                    ln.no,
                    m.start() + 1,
                    "SK-BLOCK-TABLE",
                    "'|' inside inline code on a table row ends the cell there",
                    "escape it as \\| inside the code span; pandoc shows a plain '|'",
                )

    @cached_property
    def hyphen_breaks(self) -> list[Finding]:
        """Warnings for a word broken across lines after a hyphen (`[RC-` / `Tiefpass]`).

        Markdown joins the lines with a space, so the text reads „RC- Tiefpass“. A line
        that continues with „und“, „oder“, „bzw.“ … is a suspended compound and fine.
        """
        out = []
        for para in self.paragraphs:
            lines = para.masked.split("\n")
            for k in range(len(lines) - 1):
                if para.display[k] or para.display[k + 1]:
                    continue
                end, rest = lines[k].rstrip(), lines[k + 1].lstrip()
                if not LINE_END_HYPHEN_RE.search(end) or not LINE_START_LETTER_RE.match(rest):
                    continue
                if rest.split()[0].casefold() in SUSPENDED_HYPHEN_WORDS:
                    continue
                before = para.lines[k].text.rstrip().split()[-1]
                after = para.lines[k + 1].text.split()[0]
                out.append(
                    Finding(
                        self.path,
                        para.lines[k].no,
                        len(end),
                        "SK-BLOCK-HYPHEN",
                        f"a word is broken after the hyphen at the end of the line: Markdown "
                        f"joins the lines with a space, so it reads '{before} {after}'",
                        "keep the hyphenated word on one line (a line break is only fine "
                        "before „und“, „oder“, „bzw.“, „sowie“: „Ein- und Ausgang“)",
                        "warning",
                    )
                )
        self.findings.extend(out)
        return out

    # --- links and figures ---

    @cached_property
    def paragraphs(self) -> list[Paragraph]:
        """Runs of text lines between blank lines, fences, code and ATX headings."""
        out: list[Paragraph] = []
        run: list[Line] = []
        masks: list[bool] = []
        display = False

        def flush() -> None:
            if run:
                out.append(Paragraph(list(run), list(masks)))
                run.clear()
                masks.clear()

        for i, ln in enumerate(self.lines):
            if ln.in_code or not ln.text.strip() or self._is_fence(i):
                flush()
                display = False
                continue
            if HEADING_RE.match(ln.text):
                flush()
                out.append(Paragraph([ln], [False]))
                continue
            is_delim = ln.text.strip() == "$$"
            run.append(ln)
            masks.append(display or is_delim)
            if is_delim:
                display = not display
        flush()
        return out

    @cached_property
    def link_definitions(self) -> dict[str, str]:
        """Reference definitions `[label]: target`, keyed by normalized label."""
        defs: dict[str, str] = {}
        for para in self.paragraphs:
            for label, target in para.definitions:
                defs.setdefault(label, target)
        return defs

    @cached_property
    def links(self) -> list[Link]:
        """Inline, reference and autolinks, found per paragraph like CommonMark does."""
        out = []
        for para in self.paragraphs:
            for found in scan_links(para.masked, para.text, self.link_definitions):
                line, col = para.position(found.start)
                rest = para.masked[: found.start] + para.masked[found.end :]
                out.append(
                    Link(
                        found.image,
                        found.text,
                        found.target,
                        line,
                        col,
                        not rest.strip(),
                        found.attrs,
                    )
                )
        return out

    def headings(self, level: int) -> list[tuple[int, str]]:
        prefix = "#" * level + " "
        return [
            (ln.no, ln.text[len(prefix) :].strip())
            for _, ln in self.text_lines()
            if ln.text.startswith(prefix)
        ]


# --- documents and courses ------------------------------------------------------------------


@dataclass
class Item:
    id: str
    kind: str  # exercise | mc | exam-task | summary | overview | cheatsheet | exam
    title: str
    topic: str | None
    rel: str
    line: int


def shorten(text: str, limit: int = 80) -> str:
    """Cut `text` to about `limit` characters at a space, never inside $…$ math."""
    if len(text) <= limit:
        return text
    cut = limit - 1
    for m in model.INLINE_MATH_RE.finditer(text):
        if m.start() < cut < m.end():
            cut = m.start()
            break
    space = text.rfind(" ", 0, cut)
    cut = space if space > 0 else cut
    return text[:cut].rstrip() + "…"


class Doc:
    """One course file, parsed lazily."""

    def __init__(self, course: CourseTree, path: Path):
        self.course = course
        self.path = path
        self.rel = path.relative_to(course.root).as_posix()
        self.kind, self.parts = classify(self.rel)
        self.display = display_path(path)

    def __repr__(self) -> str:
        return f"Doc({self.rel!r}, {self.kind})"

    @cached_property
    def text(self) -> str:
        # Undecodable bytes become U+FFFD instead of crashing the whole run.
        return self.path.read_text(encoding="utf-8", errors="replace")

    @property
    def is_markdown(self) -> bool:
        return self.kind in MARKDOWN_KINDS

    @property
    def is_yaml(self) -> bool:
        return self.kind in YAML_KINDS

    @cached_property
    def split(self) -> Split:
        return split_frontmatter(self.text)

    @cached_property
    def yaml(self) -> yamlio.Document | None:
        """The YAML document (frontmatter for Markdown files), or None if there is none."""
        if self.is_yaml:
            return yamlio.load(self.text, path=self.display, forbid_latex=self.kind == "course")
        if self.is_markdown and self.split.yaml is not None:
            return yamlio.load(
                self.split.yaml, path=self.display, line_offset=self.split.yaml_line - 1
            )
        return None

    @property
    def data(self) -> Any:
        return self.yaml.data if self.yaml else None

    def get(self, key: str) -> Any:
        return self.data.get(key) if isinstance(self.data, dict) else None

    @cached_property
    def body(self) -> Body | None:
        if not self.is_markdown:
            return None
        s = self.split
        return Body(s.body, s.body_line, self.display, self.kind)

    @cached_property
    def validated(self) -> tuple[Any, list[Finding]]:
        """(pydantic model or None, SK-SCHEMA findings) for files that have a model."""
        cls = model.MODELS.get(self.kind)
        if cls is None or self.yaml is None or not self.yaml.ok:
            return None, []
        data = {} if self.data is None else self.data
        try:
            if self.kind == "course":
                return model.validate_course(data), []
            return cls.model_validate(data, context=self.course.context), []
        except ValidationError as exc:
            return None, schema_findings(self.yaml, exc)

    @property
    def model(self) -> Any:
        return self.validated[0]


def schema_findings(doc: yamlio.Document, exc: ValidationError) -> list[Finding]:
    out = []
    for err in exc.errors():
        loc = [p for p in err["loc"] if isinstance(p, (str, int))]
        line, col = doc.locate(loc)
        where = ".".join(str(p) for p in loc) or "(top level)"
        etype = err["type"]
        ctx = err.get("ctx") or {}
        if etype.startswith("SK-"):
            code, message, fix = etype, err["msg"], str(ctx.get("fix", ""))
            if loc:
                message = f"{where}: {message}"
        elif etype == "missing":
            code, message = "SK-SCHEMA-MISSING", f"missing required field '{where}'"
            fix = "add it; see schemas/ for every field"
        elif etype == "extra_forbidden":
            code, message = "SK-SCHEMA-UNKNOWN", f"unknown field '{where}'"
            fix = "remove it or fix its spelling; see schemas/ for the allowed fields"
        else:
            code = "SK-SCHEMA-VALUE"
            shown = repr(err.get("input"))
            shown = shown if len(shown) <= 40 else shown[:37] + "..."
            message = f"{where}: {err['msg']} (got {shown})"
            fix = _value_fix(etype, ctx)
        out.append(Finding(doc.path, line, col, code, message, fix))
    return out


BOUNDS = {
    "greater_than": "greater than {gt}",
    "greater_than_equal": "at least {ge}",
    "less_than": "less than {lt}",
    "less_than_equal": "at most {le}",
}


def _value_fix(etype: str, ctx: dict) -> str:
    if etype in BOUNDS:
        return "use a value " + BOUNDS[etype].format(**ctx)
    if etype == "bool_type":
        return "write true or false (yes/no/on/off are strings in YAML 1.2)"
    if etype in {"int_type", "float_type"}:
        return "write a bare number without quotes"
    if etype == "string_type":
        return "write text; quote it with single quotes if it looks like a number or date"
    if etype == "literal_error":
        return f"use one of: {ctx.get('expected', '')}"
    if etype in {"date_type", "date_from_datetime_parsing", "datetime_type"}:
        return "write the date as YYYY-MM-DD"
    if etype == "string_pattern_mismatch":
        return f"match the pattern {ctx.get('pattern', '')}"
    if etype in {"too_short", "string_too_short"}:
        return "this must not be empty"
    if etype in {"model_type", "dict_type", "model_attributes_type"}:
        return "write a mapping of fields (key: value)"
    if etype == "list_type":
        return "write a list: [a, b] or one '- item' per line"
    return "fix the value; see schemas/ for the allowed values"


class CourseTree:
    """A course directory and its files."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.id = self.root.name
        self.docs: dict[str, Doc] = {}
        for path in self._walk():
            doc = Doc(self, path)
            self.docs[doc.rel] = doc

    def _walk(self) -> Iterator[Path]:
        for dirpath, dirnames, filenames in os.walk(self.root):
            rel_dir = Path(dirpath).relative_to(self.root).as_posix()
            rel_dir = "" if rel_dir == "." else rel_dir
            dirnames[:] = sorted(
                d
                for d in dirnames
                if not d.startswith(".")
                and d not in SKIP_DIRS
                and f"{rel_dir}/{d}".lstrip("/") not in SKIP_SUBTREES
            )
            for name in sorted(filenames):
                if name.startswith("."):
                    continue
                if Path(name).suffix in {".md", ".yaml", ".yml", ".py"}:
                    yield Path(dirpath) / name

    def __iter__(self) -> Iterator[Doc]:
        return iter(self.docs.values())

    def of_kind(self, *kinds: str) -> list[Doc]:
        return [d for d in self.docs.values() if d.kind in kinds]

    def get(self, rel: str) -> Doc | None:
        return self.docs.get(rel)

    @cached_property
    def course_doc(self) -> Doc | None:
        return self.docs.get("course.yaml")

    @cached_property
    def model(self) -> model.Course | None:
        doc = self.course_doc
        return doc.model if doc else None

    @cached_property
    def context(self) -> dict[str, Any]:
        """Pydantic validation context for item frontmatter."""
        if self.model:
            return model.course_context(self.model)
        return {"topics": self.topics} if self.topics else {}

    @cached_property
    def topics(self) -> list[str]:
        """Topic ids from course.yaml, even when the rest of it does not validate."""
        if self.model:
            return self.model.topic_ids
        data = self.course_doc.data if self.course_doc else None
        topics = data.get("topics") if isinstance(data, dict) else None
        if not isinstance(topics, list):
            return []
        return [t["id"] for t in topics if isinstance(t, dict) and isinstance(t.get("id"), str)]

    @cached_property
    def items(self) -> list[Item]:
        """Every addressable item with its id, in discovery order (duplicates included)."""
        out: list[Item] = []
        for doc in self:
            title = doc.get("title")
            title = title if isinstance(title, str) else ""
            if doc.kind in {"exercise", "exam-task"} and isinstance(doc.get("id"), str):
                line = doc.yaml.locate(["id"])[0] if doc.yaml else 1
                topic = doc.get("topic") if isinstance(doc.get("topic"), str) else None
                out.append(Item(doc.get("id"), doc.kind, title, topic, doc.rel, line))
            elif doc.kind == "exam" and isinstance(doc.get("id"), str):
                line = doc.yaml.locate(["id"])[0] if doc.yaml else 1
                out.append(Item(doc.get("id"), "exam", title, None, doc.rel, line))
            elif doc.kind in {"mc", "exam-mc"} and doc.body is not None:
                for q in doc.body.questions:
                    if q.id:
                        stem = shorten(" ".join(s.strip() for s in q.stem))
                        out.append(Item(q.id, "mc", stem, model.mc_topic(q.id), doc.rel, q.line))
            elif doc.kind == "summary":
                topic = doc.parts.get("topic")
                out.append(Item(f"summary-{topic}", "summary", title, topic, doc.rel, 1))
            elif doc.kind in {"overview", "cheatsheet"}:
                out.append(Item(doc.kind, doc.kind, title, None, doc.rel, 1))
        return out

    def ids(self, kind: str) -> dict[str, Item]:
        return {item.id: item for item in self.items if item.kind == kind}

    @cached_property
    def figure_slugs(self) -> list[str]:
        slugs = {d.parts["slug"] for d in self.of_kind("figure")}
        slugs.add("topic-map")  # built for every course from course.yaml (§2.12)
        return sorted(slugs)

    @cached_property
    def sources(self) -> dict[str, dict[str, Any]]:
        """Source documents from sources/manifest.yaml: doc id -> {title, pages}."""
        doc = self.get("sources/manifest.yaml")
        data = doc.data if doc else None
        entries: Any = None
        if isinstance(data, dict):
            entries = data.get("documents", data.get("docs"))
        out: dict[str, dict[str, Any]] = {}
        if isinstance(entries, dict):
            entries = [{"id": k, **v} for k, v in entries.items() if isinstance(v, dict)]
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                pages = entry.get("pages")
                out[entry["id"]] = {
                    "title": str(entry.get("title") or entry["id"]),
                    "pages": pages
                    if isinstance(pages, int) and not isinstance(pages, bool)
                    else None,
                }
        return out

    @cached_property
    def archetypes(self) -> set[str] | None:
        """Archetype ids from analysis/exam-profile.yaml, or None without a profile."""
        doc = self.get("analysis/exam-profile.yaml")
        data = doc.data if doc else None
        if not isinstance(data, dict):
            return None
        entries = data.get("archetypes")
        if isinstance(entries, dict):
            return set(map(str, entries))
        if isinstance(entries, list):
            return {
                str(e["id"]) if isinstance(e, dict) and "id" in e else str(e)
                for e in entries
                if isinstance(e, (dict, str))
            }
        return set()


def describe(tree: CourseTree) -> list[dict[str, Any]]:
    """`studykit ls <course> --json`: every discovered file with its kind and id."""
    rows = []
    for doc in tree:
        row: dict[str, Any] = {"path": doc.display, "rel": doc.rel, "kind": doc.kind}
        ident = doc.get("id") if doc.kind in {"exercise", "exam-task", "exam"} else None
        topic = doc.parts.get("topic") or (doc.get("topic") if doc.is_markdown else None)
        if ident:
            row["id"] = ident
        if isinstance(topic, str):
            row["topic"] = topic
        rows.append(row)
    return rows
