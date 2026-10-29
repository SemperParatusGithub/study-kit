"""Post-process Matplotlib SVG: stable ids, no metadata, themeable web variant."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from studykit.figures.palette import HEX_TO_ROLE

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

HREF_ATTRS = ("href", f"{{{XLINK_NS}}}href")
COLOR_ATTRS = ("fill", "stroke", "stop-color", "color")
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def _tag(el: ET.Element) -> str:
    return el.tag.rsplit("}", 1)[-1]


def _parse(svg: str) -> ET.Element:
    return ET.fromstring(svg.encode("utf-8"))


def _prefix_ids(root: ET.Element, prefix: str) -> None:
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    if not ids:
        return

    def fix_refs(text: str) -> str:
        return re.sub(
            r"url\(#([^)]+)\)",
            lambda m: f"url(#{prefix}-{m.group(1)})" if m.group(1) in ids else m.group(0),
            text,
        )

    for el in root.iter():
        if el.get("id"):
            el.set("id", f"{prefix}-{el.get('id')}")
        for attr in HREF_ATTRS:
            ref = el.get(attr)
            if ref and ref.startswith("#") and ref[1:] in ids:
                el.set(attr, f"#{prefix}-{ref[1:]}")
        for attr, value in list(el.attrib.items()):
            if "url(#" in value:
                el.set(attr, fix_refs(value))
        if _tag(el) == "style" and el.text:
            el.text = fix_refs(el.text)


def _strip_metadata(root: ET.Element) -> None:
    for parent in root.iter():
        for child in list(parent):
            if _tag(child) in {"metadata", "title", "desc"}:
                parent.remove(child)


def _themed(value: str) -> str:
    return HEX.sub(
        lambda m: (
            f"var(--fig-{HEX_TO_ROLE[m.group(0).lower()]}, {m.group(0).lower()})"
            if m.group(0).lower() in HEX_TO_ROLE
            else m.group(0)
        ),
        value,
    )


def _theme_colors(root: ET.Element) -> None:
    """Palette hex values become CSS custom properties with the hex as fallback.

    Presentation attributes cannot hold var(), so colour attributes move into `style`.
    """
    for el in root.iter():
        moved = []
        for attr in COLOR_ATTRS:
            value = el.get(attr)
            if value and HEX.fullmatch(value.strip()):
                del el.attrib[attr]
                moved.append(f"{attr}: {_themed(value.strip())}")
        style = el.get("style")
        if style:
            style = _themed(style)
        if moved:
            style = "; ".join(filter(None, [style, *moved]))
        if style:
            el.set("style", style)
        if _tag(el) == "style" and el.text:
            el.text = _themed(el.text)


def _serialize(root: ET.Element) -> str:
    return ET.tostring(root, encoding="unicode")


def finalize(svg: str, slug: str) -> tuple[str, str]:
    """Return (typst_svg, web_svg) for a figure with the given slug."""
    root = _parse(svg)
    _strip_metadata(root)
    _prefix_ids(root, slug)
    typst_svg = '<?xml version="1.0" encoding="utf-8"?>\n' + _serialize(root) + "\n"
    _theme_colors(root)
    root.set("class", "sk-fig-svg")
    for attr in ("width", "height"):
        root.attrib.pop(attr, None)
    web_svg = _serialize(root) + "\n"
    return typst_svg, web_svg
