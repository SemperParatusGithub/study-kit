"""`studykit cheatsheet fit <course>`: the cheat sheet within its page limit (§3.3).

The limit is `max = min(3, course.yaml cheatsheet.max_pages, frontmatter max_pages)`.
`studykit pdf` compiles cheatsheet.pdf at densities 0 to 4 (9, 8.5, 8, 7.5 and 7 pt as the
floor, with tighter leading and margins; typst/studykit.typ) and keeps the first density
with at most `max` pages; the manifest entry records that density and the page count.

When even density 4 overflows, `typst eval … --in _build/typ/cheatsheet.typ` reads where
`<cs-end>` and each `##` section heading sit on the page, and `cheatsheet fit` exits with
code 3 and the overflow as JSON, which the condensing procedure works from:

    {"overflow_pages": 0.42,
     "largest_sections": [{"title": "RC-Filter", "line": 41, "height_pages": 0.61}, …],
     "pages": 3, "max_pages": 2, "density": 4, "used_pages": 2.42, …}

`used_pages` is how far the content runs (2.42: page 3, a fifth of the way down its first
column); `overflow_pages` is `used_pages - max`. A section's height runs from its heading to
the next heading (or to the end), in pages, and `line` is its heading in cheatsheet.md.

A cheat sheet over its limit is a failed document: it leaves the manifest and the previous
valid cheatsheet.pdf stays in place. More than 3 pages is never allowed, whatever the
course says (the schema caps both settings at 3 as well).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from studykit import content, model, pdf

HARD_LIMIT = 3
DENSITIES = (0, 1, 2, 3, 4)
FONT_PT = (9, 8.5, 8, 7.5, 7)  # the body size at each density (typst/studykit.typ)
EXIT_OVERFLOW = 3
SHOWN_SECTIONS = 5

# What `typst eval --in cheatsheet.typ` returns: the page geometry the house library records,
# where the content ends, and where each section heading starts (positions in pt, pages
# from 1). Heading titles are read as plain text; the source titles are preferred.
MEASURE = """{
  let plain(c) = if type(c) == str { c } else if c.has("text") { plain(c.text) } else if (
    c.has("children")
  ) { c.children.map(plain).sum(default: "") } else if c.has("body") { plain(c.body) } else if (
    c.func() == [ ].func()
  ) { " " } else { "" }
  (
    page: query(<cs-page>).first().value,
    end: query(<cs-end>).first().location().position(),
    sections: query(heading.where(level: 2)).map(h => (
      title: plain(h.body),
      at: h.location().position(),
    )),
  )
}"""


def limit(course: model.Course, frontmatter: dict[str, Any]) -> int:
    """max = min(3, course.cheatsheet.max_pages, frontmatter max_pages) (§3.3)."""
    value = min(HARD_LIMIT, course.cheatsheet.max_pages)
    own = frontmatter.get("max_pages")
    if isinstance(own, int) and not isinstance(own, bool) and own >= 1:
        value = min(value, own)
    return value


@dataclass
class Fit:
    fits: bool
    density: int  # the density that fits, or the last one tried
    pages: int | None  # pages at that density (None when it did not compile)
    problems: list = field(default_factory=list)  # pdf.Problem: it did not compile
    tried: list[tuple[int, int]] = field(default_factory=list)  # (density, pages)


def fit(compile: Callable[[int], list], count: Callable[[], int], max_pages: int) -> Fit:
    """Compile at densities 0 to 4 and stop at the first one with at most `max_pages`.

    `compile(density)` writes the PDF and returns its problems; `count()` reads its pages.
    """
    tried: list[tuple[int, int]] = []
    pages = None
    for density in DENSITIES:
        problems = compile(density)
        if problems:
            return Fit(False, density, None, problems, tried)
        pages = count()
        tried.append((density, pages))
        if pages <= max_pages:
            return Fit(True, density, pages, [], tried)
    return Fit(False, DENSITIES[-1], pages, [], tried)


def _pt(value: Any) -> float:
    """A Typst length as JSON ("12.5pt") or a number, in pt."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text.endswith("pt"):
        raise ValueError(f"expected a length in pt, got {value!r}")
    return float(text[:-2])


def position(at: dict[str, Any], page: dict[str, Any]) -> float:
    """How far into the document a point is, in pages: the columns fill one after the
    other, so the top of page 2's second column of two is 1.5."""
    width, height = _pt(page["width"]), _pt(page["height"])
    margin, gutter = _pt(page["margin"]), _pt(page["gutter"])
    columns = max(1, int(page["columns"]))
    column = (width - 2 * margin + gutter) / columns
    col = int((_pt(at["x"]) - margin + 1) // column)  # 1pt of slack for rounding
    col = min(columns - 1, max(0, col))
    down = (_pt(at["y"]) - margin) / (height - 2 * margin)
    down = min(1.0, max(0.0, down))
    return (int(at["page"]) - 1) + (col + down) / columns


def overflow(
    layout: dict[str, Any],
    max_pages: int,
    pages: int,
    sections: Sequence[tuple[int, str]] = (),
) -> dict[str, Any]:
    """The overflow report from what MEASURE returned at density 4.

    `sections` are the `##` headings of cheatsheet.md as (line, title); when there are as
    many as the document has, they name the sections, otherwise the Typst text does.
    """
    page = layout["page"]
    end = position(layout["end"], page)
    heads = layout.get("sections") or []
    starts = [position(h["at"], page) for h in heads]
    own = list(sections) if len(sections) == len(heads) else []
    rows = []
    for i, start in enumerate(starts):
        stop = starts[i + 1] if i + 1 < len(starts) else end
        row: dict[str, Any] = {}
        if own:
            row["title"], row["line"] = own[i][1], own[i][0]
        else:
            row["title"] = " ".join(str(heads[i].get("title") or "").split())
        row["height_pages"] = round(max(0.0, stop - start), 2)
        rows.append(row)
    largest = sorted(rows, key=lambda r: -r["height_pages"])[:SHOWN_SECTIONS]
    return {
        "overflow_pages": round(max(end - max_pages, 0.01), 2),
        "largest_sections": largest,
        "pages": pages,
        "max_pages": max_pages,
        "density": DENSITIES[-1],
        "used_pages": round(end, 2),
    }


def overflow_unmeasured(max_pages: int, pages: int, reason: str) -> dict[str, Any]:
    """The overflow when `typst eval` could not measure it: whole pages only."""
    return {
        "overflow_pages": max(pages - max_pages, 1),
        "largest_sections": [],
        "pages": pages,
        "max_pages": max_pages,
        "density": DENSITIES[-1],
        "note": f"the layout could not be measured: {reason.strip()[:300]}",
    }


def overflow_message(over: dict[str, Any]) -> str:
    pages, max_pages = over["pages"], over["max_pages"]
    density = over["density"]
    text = (
        f"the cheat sheet has {pages} page{'s' if pages != 1 else ''} even at density "
        f"{density} ({FONT_PT[density]:g} pt), {over['overflow_pages']:g} "
        f"page{'s' if over['overflow_pages'] != 1 else ''} over its limit of {max_pages}"
    )
    if pages > HARD_LIMIT:
        text += f" (more than {HARD_LIMIT} pages is never allowed)"
    sections = over.get("largest_sections") or []
    if sections:
        text += "; largest sections: " + ", ".join(
            f"{s['title']} ({s['height_pages']:g})" for s in sections[:3]
        )
    return text


# --- the command ------------------------------------------------------------------------------


def run(course_dir: Path, *, force: bool = False, figures: bool = True) -> tuple[int, dict]:
    """Build cheatsheet.pdf with the fit. Returns (exit code, result): 0 when it fits,
    3 when it overflows (the result carries the overflow), 1 when it does not build.
    Raises ValueError when the course has no cheat sheet."""
    build = pdf.make(course_dir, ["cheatsheet"], force=force, figures=figures)
    target = course_dir.resolve() / "_build" / "pdf" / "cheatsheet.pdf"
    result: dict[str, Any] = {"course": build.course, "file": content.display_path(target)}
    if not build.outcomes:
        raise ValueError(f"{build.course} has no cheat sheet to build")
    (out,) = build.outcomes
    result |= {"status": out.status, "max_pages": out.max_pages}
    if build.notes:
        result["notes"] = build.notes
    if out.ok:
        result |= {"fits": True, "density": out.density, "pages": out.pages}
        return 0, result
    result["fits"] = False
    if out.overflow is not None:
        result |= out.overflow
        result["kept"] = content.display_path(target) if target.is_file() else None
        return EXIT_OVERFLOW, result
    result["errors"] = out.errors
    return 1, result


def format_text(result: dict[str, Any]) -> str:
    head = f"cheatsheet {result['course']}:"
    if result.get("fits"):
        density = result["density"]
        lines = [
            f"{head} fits: {result['pages']} of {result['max_pages']} "
            f"page{'s' if result['max_pages'] != 1 else ''} at density {density} "
            f"({FONT_PT[density]:g} pt), {result['status']}",
            f"  {result['file']}",
        ]
    elif "overflow_pages" in result:
        lines = [f"{head} does not fit: " + overflow_message(result)]
        for s in result["largest_sections"]:
            where = f" (cheatsheet.md:{s['line']})" if "line" in s else ""
            lines.append(f"  {s['height_pages']:>5.2f} pages  {s['title']}{where}")
        if result.get("note"):
            lines.append(f"  note: {result['note']}")
        kept = result.get("kept")
        lines.append(f"  kept the previous {kept}" if kept else "  no previous cheatsheet.pdf")
    else:
        lines = [f"{head} failed", *(f"  {e}" for e in result.get("errors", []))]
    lines += [f"  note: {n}" for n in result.get("notes", [])]
    return "\n".join(lines)
