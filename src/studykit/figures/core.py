"""The Figure object and the shared rendering path every template goes through."""

from __future__ import annotations

import io
import os
import re
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


def decimal_comma() -> bool:
    """Whether numbers get a decimal comma.

    The runner sets STUDYKIT_DECIMAL (comma or point) from the course's notation.yaml;
    without it German figures get a comma and the others a point.
    """
    mark = os.environ.get("STUDYKIT_DECIMAL")
    if mark in ("comma", "point"):
        return mark == "comma"
    return locale() == "de"


def size(name: str) -> tuple[float, float]:
    if name not in SIZES:
        raise ValueError(f"unknown size {name!r}; use one of {', '.join(SIZES)}")
    return SIZES[name]


def new_figure(size_name: str = "col", **subplot_kw):
    fig, ax = plt.subplots(figsize=size(size_name), **subplot_kw)
    return fig, ax


def fmt_number(value: float, digits: int = 3) -> str:
    """Format a number for labels with the figure's decimal sign (`decimal_comma`)."""
    text = f"{value:.{digits}g}"
    if "e" in text:
        mantissa, exp = text.split("e")
        text = rf"{mantissa}\cdot 10^{{{int(exp)}}}"
    return text.replace(".", "{,}") if decimal_comma() else text


def localize_tex(tex: str) -> str:
    """Decimal comma inside TeX when the figure uses one: 0.5 -> 0{,}5."""
    return re.sub(r"(\d)\.(\d)", r"\1{,}\2", tex) if decimal_comma() else tex


def axis_label(quantity: str, unit: str | None = None) -> str:
    """`U in V` (German, DIN 461) or `U / V` (English); quantity is TeX math."""
    if not unit:
        return f"${quantity}$"
    sep = "in" if locale() == "de" else "/"
    return f"${quantity}$ {sep} {unit}"


class TickFormatter(ticker.ScalarFormatter):
    """ScalarFormatter with an optional decimal comma and an optional blank tick at zero.

    The blank zero is for axes that cross at the origin, where a 0 would sit on the other
    axis.
    """

    def __init__(self, comma: bool, blank_zero: bool = False):
        super().__init__(useMathText=True)
        self.comma = comma
        self.blank_zero = blank_zero

    def _localize(self, text: str) -> str:
        if not self.comma:
            return text
        return text.replace(".", "{,}") if "$" in text else text.replace(".", ",")

    def __call__(self, x, pos=None):
        span = max(map(abs, self.axis.get_view_interval())) if self.axis else 1.0
        if self.blank_zero and abs(x) <= 1e-9 * span:
            return ""
        return self._localize(super().__call__(x, pos))

    def get_offset(self):
        return self._localize(super().get_offset())


def apply_locale(ax, blank_zero: str = "") -> None:
    """Decimal comma in tick labels when the figure uses one (`decimal_comma`).

    blank_zero names the axes ('x', 'y' or 'xy') whose 0 tick label is left out because
    the other axis crosses there.
    """
    comma = decimal_comma()
    for name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
        if type(axis.get_major_formatter()) is not ticker.ScalarFormatter:
            continue
        if comma or name in blank_zero:
            axis.set_major_formatter(TickFormatter(comma, name in blank_zero))


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
