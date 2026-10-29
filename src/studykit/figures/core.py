"""The Figure object and the shared rendering path every template goes through."""

from __future__ import annotations

import io
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import ticker

STYLE = Path(__file__).with_name("house.mplstyle")

# Width x height in inches. "col" fits the reading column and a PDF text column,
# "full" spans the page, "cs" is for the cheat sheet.
SIZES: dict[str, tuple[float, float]] = {
    "col": (3.6, 2.4),
    "half": (2.9, 2.1),
    "full": (6.2, 3.0),
    "cs": (2.4, 1.6),
}

plt.style.use(STYLE)


@dataclass
class Figure:
    """A rendered figure: literal-colour SVG (for Typst), PNG preview, facts, alt text."""

    svg: str
    png: bytes
    alt: str
    facts: dict = field(default_factory=dict)


def locale() -> str:
    """Language of tick labels and axis labels; the runner sets it from course.lang."""
    return os.environ.get("STUDYKIT_LOCALE", "en")


def size(name: str) -> tuple[float, float]:
    if name not in SIZES:
        raise ValueError(f"unknown size {name!r}; use one of {', '.join(SIZES)}")
    return SIZES[name]


def new_figure(size_name: str = "col", **subplot_kw):
    fig, ax = plt.subplots(figsize=size(size_name), **subplot_kw)
    return fig, ax


def fmt_number(value: float, digits: int = 3) -> str:
    """Format a number for labels in the figure locale (decimal comma for German)."""
    text = f"{value:.{digits}g}"
    if "e" in text:
        mantissa, exp = text.split("e")
        text = rf"{mantissa}\cdot 10^{{{int(exp)}}}"
    return text.replace(".", "{,}") if locale() == "de" else text


def axis_label(quantity: str, unit: str | None = None) -> str:
    """`U in V` (German, DIN 461) or `U / V` (English); quantity is TeX math."""
    if not unit:
        return f"${quantity}$"
    sep = "in" if locale() == "de" else "/"
    return f"${quantity}$ {sep} {unit}"


def apply_locale(ax) -> None:
    """Use a decimal comma in tick labels when the course is German."""
    if locale() != "de":
        return
    for axis in (ax.xaxis, ax.yaxis):
        base: Callable = axis.get_major_formatter()
        if isinstance(base, ticker.ScalarFormatter):
            base.set_useMathText(True)
        axis.set_major_formatter(
            ticker.FuncFormatter(lambda v, pos, base=base: base(v, pos).replace(".", "{,}"))
        )


def finish(fig, alt: str, facts: dict | None = None) -> Figure:
    """Render a Matplotlib figure deterministically and close it."""
    if not alt or not alt.strip():
        raise ValueError("every figure needs alt text describing what it shows")
    svg_buf, png_buf = io.StringIO(), io.BytesIO()
    fig.savefig(svg_buf, format="svg", metadata={"Date": None, "Creator": None})
    fig.savefig(png_buf, format="png", dpi=100, metadata={"Software": None})
    plt.close(fig)
    return Figure(
        svg=svg_buf.getvalue(), png=png_buf.getvalue(), alt=alt.strip(), facts=facts or {}
    )
