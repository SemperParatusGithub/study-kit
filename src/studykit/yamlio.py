"""Restricted YAML loading plus the scalar-style lint (docs/architecture.md §2.1).

The loader resolves plain scalars like the YAML 1.2 core schema, which is what the site's
`yaml` package uses, so both sides read the same values:

- booleans are only true/false (yes/no/on/off stay strings),
- integers are decimal, 0o octal or 0x hex (no sexagesimal 1:30, no YAML 1.1 octal 010),
- floats need digits (1e3 is a float, .5 too),
- nothing is an implicit timestamp: dates stay strings and the pydantic models turn ISO
  dates into dates only where a field expects one,
- duplicate keys and `<<` merges are rejected.

The style lint works on the composed node tree, which keeps every scalar's style and
source marks: a backslash may only appear in single-quoted or `|-` block scalars, because
`"\\frac"` silently turns into a form feed.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from studykit.findings import Finding


class DuplicateKeyError(yaml.constructor.ConstructorError):
    pass


class StrictLoader(yaml.SafeLoader):
    """SafeLoader with YAML 1.2 core-schema resolution and unique keys."""

    def construct_mapping(self, node: Node, deep: bool = False) -> dict:
        if isinstance(node, MappingNode):
            seen: set = set()
            for key_node, _ in node.value:
                key = self.construct_object(key_node, deep=True)
                try:
                    duplicate = key in seen
                    seen.add(key)
                except TypeError:
                    continue  # unhashable key: SafeLoader reports it below
                if duplicate:
                    raise DuplicateKeyError(
                        "while constructing a mapping",
                        node.start_mark,
                        f"found duplicate key {key!r}",
                        key_node.start_mark,
                    )
        return super().construct_mapping(node, deep=deep)


def _construct_int(loader: yaml.SafeLoader, node: Node) -> int:
    value = str(loader.construct_scalar(node))  # type: ignore[arg-type]
    sign = -1 if value.startswith("-") else 1
    digits = value.lstrip("+-")
    if digits.startswith("0x"):
        return sign * int(digits[2:], 16)
    if digits.startswith("0o"):
        return sign * int(digits[2:], 8)
    return sign * int(digits, 10)


StrictLoader.yaml_implicit_resolvers = {}
StrictLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)
StrictLoader.add_implicit_resolver(
    "tag:yaml.org,2002:int",
    re.compile(r"^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$"),
    list("-+0123456789"),
)
StrictLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(
        r"^(?:[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
        r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$"
    ),
    list("-+.0123456789"),
)
StrictLoader.add_implicit_resolver(
    "tag:yaml.org,2002:null",
    re.compile(r"^(?:~|null|Null|NULL|)$"),
    ["~", "n", "N", ""],
)
StrictLoader.add_constructor("tag:yaml.org,2002:int", _construct_int)

# C0 controls except tab, LF and CR; DEL; C1 controls.
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]")
INLINE_MATH_RE = re.compile(r"\$[^$\s][^$]*\$")
BLOCK_HEADER_RE = re.compile(r"^([|>])([1-9]?)([-+]?)([1-9]?)")


@dataclass
class Document:
    """A parsed YAML document plus everything needed to point at its source."""

    path: str
    text: str
    line_offset: int = 0
    data: Any = None
    node: Node | None = None
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.is_error for f in self.findings)

    def position(self, mark: yaml.Mark | None) -> tuple[int, int]:
        if mark is None:
            return self.line_offset + 1, 1
        return self.line_offset + mark.line + 1, mark.column + 1

    def locate(self, loc: Sequence[str | int]) -> tuple[int, int]:
        """Source position of a pydantic error location (keys and list indices)."""
        node = self.node
        if node is None:
            return self.line_offset + 1, 1
        mark = node.start_mark
        for part in loc:
            if isinstance(node, MappingNode):
                for key_node, value_node in node.value:
                    if isinstance(key_node, ScalarNode) and key_node.value == str(part):
                        mark, node = key_node.start_mark, value_node
                        break
            elif (
                isinstance(node, SequenceNode)
                and isinstance(part, int)
                and 0 <= part < len(node.value)
            ):
                node = node.value[part]
                mark = node.start_mark
        return self.position(mark)

    def finding(
        self, mark: yaml.Mark | None, code: str, message: str, fix: str, severity="error"
    ) -> Finding:
        line, col = self.position(mark)
        return Finding(self.path, line, col, code, message, fix, severity)


def scalars(node: Node | None) -> Iterator[ScalarNode]:
    if node is None:
        return
    stack = [node]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, ScalarNode):
            yield current
        elif isinstance(current, MappingNode):
            for key, value in reversed(current.value):
                stack.extend([value, key])
        elif isinstance(current, SequenceNode):
            stack.extend(reversed(current.value))


def _control_findings(doc: Document) -> list[Finding]:
    out = []
    for lineno, line in enumerate(doc.text.splitlines(), start=1):
        for m in CONTROL_RE.finditer(line):
            out.append(
                Finding(
                    doc.path,
                    doc.line_offset + lineno,
                    m.start() + 1,
                    "SK-YAML-CONTROL",
                    f"control character U+{ord(m.group()):04X} in YAML",
                    "delete it; write symbols as UTF-8 text or inside inline math",
                )
            )
    return out


def style_findings(doc: Document, *, forbid_latex: bool = False) -> list[Finding]:
    """The scalar-style rules: where backslashes may appear, and no LaTeX at all."""
    out: list[Finding] = []
    for node in scalars(doc.node):
        raw = doc.text[node.start_mark.index : node.end_mark.index]
        style = node.style
        value = node.value
        if style == '"':
            if "\\" in raw:
                out.append(
                    doc.finding(
                        node.start_mark,
                        "SK-YAML-ESCAPE",
                        "double-quoted scalar contains a backslash, which YAML reads as an "
                        "escape (\\f becomes a form feed)",
                        "use single quotes: '\\frac{1}{2}' keeps every backslash literal",
                    )
                )
            else:
                out.append(
                    doc.finding(
                        node.start_mark,
                        "SK-YAML-DQUOTE",
                        "double-quoted scalar",
                        "use single quotes ('…'); double quotes turn backslashes into escapes",
                        severity="warning",
                    )
                )
        elif "\\" in value:
            header = BLOCK_HEADER_RE.match(raw)
            strip_block = style == "|" and header is not None and header.group(3) == "-"
            if style != "'" and not strip_block:
                kind = {None: "plain", "|": "literal block", ">": "folded block"}[style]
                out.append(
                    doc.finding(
                        node.start_mark,
                        "SK-YAML-BACKSLASH",
                        f"{kind} scalar contains a backslash",
                        "write it single-quoted ('$\\omega_\\mathrm{g}$') or as a |- block",
                    )
                )
        if forbid_latex and ("\\" in value or INLINE_MATH_RE.search(value)):
            out.append(
                doc.finding(
                    node.start_mark,
                    "SK-YAML-LATEX",
                    "course.yaml contains LaTeX",
                    "write titles and aids as plain text (Ohm instead of \\Omega); "
                    "math belongs in the Markdown files",
                )
            )
    return out


def _codepoint(character: str | int) -> int:
    return character if isinstance(character, int) else ord(character)


def load(text: str, *, path: str, line_offset: int = 0, forbid_latex: bool = False) -> Document:
    """Parse one YAML document with the strict loader and lint its scalar styles.

    `line_offset` is the number of file lines before `text` (frontmatter starts at 1).
    Problems become findings; `data` is None when the text could not be parsed.
    """
    doc = Document(path=path, text=text, line_offset=line_offset)
    control = _control_findings(doc)
    if control:
        doc.findings.extend(control)
        return doc
    try:
        loader = StrictLoader(text)
    except yaml.reader.ReaderError as exc:  # non-characters such as U+FFFE
        before = text[: exc.position]
        doc.findings.append(
            Finding(
                path,
                line_offset + before.count("\n") + 1,
                len(before) - (before.rfind("\n") + 1) + 1,
                "SK-YAML-CONTROL",
                f"character U+{_codepoint(exc.character):04X} is not allowed in YAML",
                "delete it; write symbols as UTF-8 text or inside inline math",
            )
        )
        return doc
    try:
        try:
            doc.node = loader.get_single_node()
        except yaml.MarkedYAMLError as exc:
            doc.findings.append(
                doc.finding(
                    exc.problem_mark or exc.context_mark,
                    "SK-YAML-SYNTAX",
                    f"YAML syntax error: {exc.problem or exc.context}",
                    "check indentation and quoting; values with ': ' or ' #' need quotes",
                )
            )
            return doc
        doc.findings.extend(style_findings(doc, forbid_latex=forbid_latex))
        if doc.node is None:
            doc.data = None
            return doc
        try:
            doc.data = loader.construct_document(doc.node)
        except DuplicateKeyError as exc:
            doc.findings.append(
                doc.finding(
                    exc.problem_mark,
                    "SK-YAML-DUPKEY",
                    (exc.problem or "duplicate key").replace("found ", ""),
                    "keep one entry per key; YAML would silently drop the first one",
                )
            )
        except yaml.MarkedYAMLError as exc:
            doc.findings.append(
                doc.finding(
                    exc.problem_mark,
                    "SK-YAML-SYNTAX",
                    f"YAML error: {exc.problem}",
                    "remove tags and use plain scalars, lists and mappings only",
                )
            )
    finally:
        loader.dispose()
    return doc


def safe_load(text: str) -> Any:
    """Strict load without lint, raising on errors (for trusted generated files)."""
    return yaml.load(text, Loader=StrictLoader)  # StrictLoader is a SafeLoader
