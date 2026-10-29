"""Validate a figure SVG before it can be used on the site or in a PDF."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from studykit.figures.palette import BG, HEX_TO_ROLE, ROLES, TEXT_CONTRAST, TEXT_ROLES, contrast

MAX_BYTES = 400_000
FORBIDDEN_TAGS = {"script", "foreignObject", "text", "iframe", "object", "embed"}
HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
NAMED_COLOR = re.compile(r"(?:fill|stroke|stop-color)\s*:\s*(?!none|var\(|url\(|#|currentColor)\w+")
FILL = re.compile(r"(?:^|;)\s*fill\s*:\s*([^;]+)")
# matplotlib draws text as <use> of glyph paths (ids `DejaVuSans-52`, `Cmr10-31`) and markers
# as <use> of `m<hash>` paths; finalize prefixes both with the slug.
MARKER_ID = re.compile(r"(?:^|-)m[0-9a-f]{6,}$")
TEXT_HEX = {ROLES[role].lower() for role in TEXT_ROLES}


def _tag(el: ET.Element) -> str:
    return el.tag.rsplit("}", 1)[-1]


def _text_colour_problems(root: ET.Element) -> list[str]:
    """Text drawn in a colour that is not readable on the page (WCAG 1.4.3)."""
    parent = {child: el for el in root.iter() for child in el}
    problems = []
    for el in root.iter():
        if _tag(el) != "use":
            continue
        ref = next((v for k, v in el.attrib.items() if k.rsplit("}", 1)[-1] == "href"), "")
        if not ref.startswith("#") or MARKER_ID.search(ref[1:]):
            continue
        node: ET.Element | None = el
        fill = None
        while node is not None and fill is None:
            m = FILL.search(node.get("style", ""))
            fill = m.group(1) if m else node.get("fill")
            node = parent.get(node)
        found = HEX.findall(fill or "")
        if found and found[-1].lower() in HEX_TO_ROLE and found[-1].lower() not in TEXT_HEX:
            hex_ = found[-1].lower()
            problems.append(
                f"text in {HEX_TO_ROLE[hex_]} ({hex_}) has {contrast(hex_, BG):.1f}:1 contrast "
                f"on the page, below {TEXT_CONTRAST}:1: draw labels in fg and let a coloured "
                "line or marker be the key"
            )
    return problems


def validate_svg(svg: str) -> list[str]:
    """Return a list of problems; an empty list means the SVG is acceptable."""
    problems: list[str] = []
    size = len(svg.encode("utf-8"))
    if size > MAX_BYTES:
        problems.append(f"SVG is {size // 1000} kB, more than {MAX_BYTES // 1000} kB")
    try:
        root = ET.fromstring(svg.encode("utf-8"))
    except ET.ParseError as exc:
        return [*problems, f"SVG does not parse: {exc}"]
    if _tag(root) != "svg":
        problems.append(f"root element is <{_tag(root)}>, not <svg>")
    view_box = root.get("viewBox", "").split()
    if len(view_box) != 4:
        problems.append("missing viewBox")
    elif float(view_box[2]) <= 0 or float(view_box[3]) <= 0:
        problems.append("empty viewBox")

    drawn = 0
    for el in root.iter():
        tag = _tag(el)
        if tag in FORBIDDEN_TAGS:
            problems.append(f"forbidden element <{tag}>")
        if tag in {"path", "use", "line", "rect", "circle", "ellipse", "polygon", "polyline"}:
            drawn += 1
        for attr, value in el.attrib.items():
            name = attr.rsplit("}", 1)[-1]
            if name.lower().startswith("on"):
                problems.append(f"event handler attribute {name} on <{tag}>")
            if name == "href" and not (value.startswith("#") or value.startswith("data:image/")):
                problems.append(f"external reference {value[:60]!r}")
            for hex_ in HEX.findall(value):
                if hex_.lower() not in HEX_TO_ROLE:
                    problems.append(f"colour {hex_} on <{tag}> is not in the palette")
            if NAMED_COLOR.search(value):
                problems.append(f"named colour in {value[:60]!r} on <{tag}>")
    if drawn == 0:
        problems.append("SVG draws nothing")
    problems += _text_colour_problems(root)
    # De-duplicate while keeping order.
    return list(dict.fromkeys(problems))
