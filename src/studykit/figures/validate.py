"""Validate a figure SVG before it can be used on the site or in a PDF."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from studykit.figures.palette import HEX_TO_ROLE

MAX_BYTES = 400_000
FORBIDDEN_TAGS = {"script", "foreignObject", "text", "iframe", "object", "embed"}
HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
NAMED_COLOR = re.compile(r"(?:fill|stroke|stop-color)\s*:\s*(?!none|var\(|url\(|#|currentColor)\w+")


def _tag(el: ET.Element) -> str:
    return el.tag.rsplit("}", 1)[-1]


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
    # De-duplicate while keeping order.
    return list(dict.fromkeys(problems))
