"""Course content on disk: discovery, frontmatter, the fence-line scanner and the id index.

Everything here is pure Python and line based, so `studykit lint` can check a file in a
few milliseconds without pandoc (docs/architecture.md §2.1, §2.3, §4.3). The scanners
skip fenced code; they report positions as file line and column, both 1-based.
"""

from __future__ import annotations

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
LINK_RE = re.compile(r"(?P<bang>!?)\[(?P<text>(?:[^\[\]]|\[[^\[\]]*\])*)\]\((?P<target>[^()\s]*)\)")


def _mask(text: str, start: int, end: int) -> str:
    return text[:start] + " " * (end - start) + text[end:]


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

    def _boundary(self, i: int) -> bool:
        """Whether line i ends a paragraph: outside the body, blank, or a fence."""
        return not 0 <= i < len(self.lines) or not self.lines[i].text.strip() or self._is_fence(i)

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
            out.extend(self._inline_math(ln))
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

    # --- links and figures ---

    @cached_property
    def links(self) -> list[Link]:
        out = []
        for i, ln in self.text_lines():
            text = INLINE_CODE_RE.sub(lambda m: " " * len(m.group()), ln.text)
            for m in LINK_RE.finditer(text):
                after = text[m.end() :]
                attrs = after.startswith("{")
                if attrs and "}" in after:
                    after = after[after.index("}") + 1 :]
                alone = (
                    self._boundary(i - 1)
                    and self._boundary(i + 1)
                    and not text[: m.start()].strip()
                    and not after.strip()
                )
                out.append(
                    Link(
                        bool(m["bang"]), m["text"], m["target"], ln.no, m.start() + 1, alone, attrs
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
