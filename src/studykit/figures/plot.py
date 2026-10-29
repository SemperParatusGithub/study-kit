"""Plot templates. Every builder returns a `Figure` with SVG, PNG, facts and alt text."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

import matplotlib.pyplot as plt
import numpy as np
import sympy as sp

from studykit.figures import core, keypoints, labels
from studykit.figures.keypoints import Point
from studykit.figures.palette import BG, FG, MUTED, color

# The control and signal templates live in signals.py; scripts call them as plot.bode etc.
from studykit.figures.signals import (
    bode,
    nyquist,
    phasor,
    pole_zero,
    root_locus,
    signals,
    step_response,
)

MARKS = ("roots", "intersections", "extrema", "inflections")
MARK_PREFIX = {"root": "N", "intersection": "S", "maximum": "H", "minimum": "T", "inflection": "W"}
MARK_PREFIX_EN = {
    "root": "R",
    "intersection": "P",
    "maximum": "Max",
    "minimum": "Min",
    "inflection": "I",
}


def _named(fns: Sequence[str | tuple[str, str]]) -> list[tuple[str, str]]:
    names = "fghpqr"
    out = []
    for i, fn in enumerate(fns):
        out.append(fn if isinstance(fn, tuple) else (names[i % len(names)], fn))
    return out


def _break_at_poles(xs: np.ndarray, ys: np.ndarray, y_lim: tuple[float, float]) -> np.ndarray:
    """Insert gaps where the curve jumps through infinity so no vertical line is drawn."""
    ys = ys.copy()
    span = y_lim[1] - y_lim[0]
    jump = np.abs(np.diff(ys)) > 2 * span
    ys[1:][jump] = np.nan
    ys[(ys > y_lim[1] + 10 * span) | (ys < y_lim[0] - 10 * span)] = np.nan
    return ys


def _auto_ylim(curves: list[np.ndarray], points: list[Point]) -> tuple[float, float]:
    finite = np.concatenate([c[np.isfinite(c)] for c in curves] or [np.array([0.0])])
    if finite.size == 0:
        return (-1.0, 1.0)
    lo, hi = np.percentile(finite, [2, 98])
    for p in points:
        lo, hi = min(lo, p.y), max(hi, p.y)
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    pad = 0.08 * (hi - lo)
    return (float(lo - pad), float(hi + pad))


def _cross_axes(ax, x_rng, y_rng) -> str:
    """Engineering style: axes through the origin when it is in view.

    Returns the axes ('x', 'y') whose 0 tick label would sit on the other axis.
    """
    blank = ""
    if x_rng[0] < 0 < x_rng[1]:
        ax.spines["left"].set_position(("data", 0))
        blank += "x"
    if y_rng[0] < 0 < y_rng[1]:
        ax.spines["bottom"].set_position(("data", 0))
        blank += "y"
    return blank


# Label positions around a marked point, best first: (dx, dy) in points, ha, va.
POINT_LABEL_SPOTS = [
    (5, 4, "left", "bottom"),
    (-5, 4, "right", "bottom"),
    (5, -4, "left", "top"),
    (-5, -4, "right", "top"),
    (0, 7, "center", "bottom"),
    (0, -7, "center", "top"),
    (7, 0, "left", "center"),
    (-7, 0, "right", "center"),
]


# Legend corners inside the axes, best first; above the axes when none is free.
LEGEND_SPOTS = (
    "upper left",
    "upper right",
    "lower right",
    "lower left",
    "upper center",
    "lower center",
    "center left",
    "center right",
)


def _scene(ax, marks: list[tuple[float, float, str]], curves: list):
    """What labels must not hide, in display coordinates: drawn points and text boxes."""
    fig = ax.figure
    fig.draw_without_rendering()
    renderer = fig.canvas.get_renderer()
    drawn = [labels.marker_points(ax, [complex(x, y) for x, y, _ in marks], radius_pt=3.5)]
    for xs, ys in curves:  # each run between poles separately, so no jump is sampled
        finite = np.isfinite(ys)
        edges = np.flatnonzero(np.diff(np.r_[0, finite.astype(int), 0]))
        for a, b in zip(edges[::2], edges[1::2], strict=True):
            drawn.append(labels.polyline_points(ax, xs[a:b] + 1j * ys[a:b]))
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    if x0 < 0 < x1:
        drawn.append(labels.segment_points(ax, (0, y0), (0, y1), 200))
    if y0 < 0 < y1:
        drawn.append(labels.segment_points(ax, (x0, 0), (x1, 0), 200))
    texts = [*ax.get_xticklabels(), *ax.get_yticklabels(), *ax.texts]
    placed = [t.get_window_extent(renderer) for t in texts if t.get_text()]
    placed += [a.get_window_extent(renderer) for a in (ax.xaxis.label, ax.yaxis.label)]
    return np.concatenate(drawn), placed


def _place_legend(ax, avoid: np.ndarray, placed: list) -> bool:
    """Put the legend in the first corner it hides nothing in; True if it went outside."""
    renderer = ax.figure.canvas.get_renderer()
    best = None
    for loc in LEGEND_SPOTS:
        box = ax.legend(loc=loc, labelcolor=FG).get_window_extent(renderer)
        score = box.count_contains(avoid) + 100 * sum(box.overlaps(b) for b in placed)
        if best is None or score < best[0]:
            best = (score, loc)
        if score == 0:
            break
    if best[0] == 0:
        ax.legend(loc=best[1], labelcolor=FG)
        return False
    n = len(ax.get_legend_handles_labels()[0])
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1.02), ncols=n, labelcolor=FG, borderaxespad=0)
    return True


def _annotate(ax, marks: list[tuple[float, float, str]], curves: list, legend: bool) -> None:
    """Legend and point labels, each where it hides no curve, axis, tick label or label."""
    avoid, placed = _scene(ax, marks, curves)
    if legend and _place_legend(ax, avoid, placed):
        avoid, placed = _scene(ax, marks, curves)  # the axes shrank for the legend above
    if ax.get_legend() is not None:
        placed.append(ax.get_legend().get_window_extent(ax.figure.canvas.get_renderer()))
    for x, y, text in marks:
        spots = [
            {"xy": (x, y), "xytext": (dx, dy), "ha": ha, "va": va}
            for dx, dy, ha, va in POINT_LABEL_SPOTS
        ]
        labels.place(ax, text, spots, avoid, placed, [(x, y), (x, y)], color=FG, fontsize=7)


def _merge(points: list[Point], names: list[str], span: float) -> list[tuple[Point, list[str]]]:
    """One mark per location: a root of f and g that is also their intersection is one."""
    tol = 1e-9 * max(span, 1.0)
    out: list[tuple[Point, list[str]]] = []
    for p, name in zip(points, names, strict=True):
        for q, group in out:
            if abs(p.x - q.x) <= tol and abs(p.y - q.y) <= tol:
                group.append(name)
                break
        else:
            out.append((p, [name]))
    return out


def _point_label(p: Point, index: int) -> str:
    prefix = (MARK_PREFIX if core.locale() == "de" else MARK_PREFIX_EN)[p.kind]
    if len(prefix) > 1:  # a word such as Max is upright, not a product of italic letters
        prefix = rf"\mathrm{{{prefix}}}"
    return f"${prefix}_{{{index}}}$"


def _coord_text(p: Point) -> str:
    x = p.exact_x if p.exact_x else core.fmt_number(p.x)
    y = core.fmt_number(p.y if abs(p.y) > 1e-12 else 0.0)
    sep = r"\,|\," if core.locale() == "de" else r",\ "
    return f"$({x}{sep}{y})$"


def functions(
    fns: Sequence[str | tuple[str, str]],
    x: tuple[float, float] = (-3.0, 3.0),
    y: tuple[float, float] | None = None,
    mark: Sequence[str] = (),
    exact: bool = True,
    coords: bool = True,
    x_label: str = "x",
    y_label: str = "y",
    legend: bool = True,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Plot functions of x and mark computed key points.

    fns: expressions in SymPy syntax ('x**2 - 2', 'exp(-x)') or (name, expr) pairs.
    mark: any of 'roots', 'intersections', 'extrema', 'inflections'.
    """
    unknown = set(mark) - set(MARKS)
    if unknown:
        raise ValueError(f"unknown mark {sorted(unknown)}; use {MARKS}")
    named = _named(fns)
    exprs = [(name, keypoints.parse(expr)) for name, expr in named]
    lo, hi = x

    points: list[Point] = []
    owners: list[str] = []
    for name, e in exprs:
        found: list[Point] = []
        if "roots" in mark:
            found += keypoints.roots(e, lo, hi, exact=exact)
        if "extrema" in mark:
            found += keypoints.extrema(e, lo, hi, exact=exact)
        if "inflections" in mark:
            found += keypoints.inflections(e, lo, hi, exact=exact)
        points += found
        owners += [name] * len(found)
    if "intersections" in mark:
        for (n1, e1), (n2, e2) in combinations(exprs, 2):
            found = keypoints.intersections(e1, e2, lo, hi, exact=exact)
            points += found
            owners += [f"{n1}={n2}"] * len(found)

    xs = np.linspace(lo, hi, 2001)
    raw = [keypoints.lambdify(e)(xs) for _, e in exprs]
    y_rng = y or _auto_ylim(raw, points)

    fig, ax = core.new_figure(size)
    curves = []
    for i, ((name, e), ys) in enumerate(zip(exprs, raw, strict=True)):
        label = f"${name}(x) = {core.localize_tex(sp.latex(e))}$"
        curves.append((xs, _break_at_poles(xs, ys, y_rng)))
        ax.plot(*curves[-1], color=color(i), label=label)

    counters: dict[str, int] = {}
    names = []
    for p in points:
        counters[p.kind] = counters.get(p.kind, 0) + 1
        names.append(_point_label(p, counters[p.kind]))
    marks = []
    for p, group in _merge(points, names, hi - lo):
        ax.plot([p.x], [p.y], "o", ms=4.5, mfc=BG, mec=FG, mew=1.1, zorder=9)
        text = ", ".join(group)
        marks.append((p.x, p.y, text + " " + _coord_text(p) if coords else text))

    ax.set_xlim(lo, hi)
    ax.set_ylim(*y_rng)
    blank = _cross_axes(ax, (lo, hi), y_rng)
    ax.set_xlabel(f"${x_label}$", loc="right")
    ax.set_ylabel(f"${y_label}$", loc="top", rotation=0)
    core.apply_locale(ax, blank_zero=blank)
    if blank == "xy":  # one 0 for both axes, below left of the origin
        ax.annotate(
            "0",
            (0, 0),
            xytext=(-3, -3),
            textcoords="offset points",
            ha="right",
            va="top",
            fontsize=plt.rcParams["xtick.labelsize"],
            color=FG,
        )
    _annotate(ax, marks, curves, legend and bool(exprs))

    facts = {
        "template": "plot.functions",
        "x_range": [lo, hi],
        "y_range": list(y_rng),
        "functions": [{"name": n, "expr": str(e), "latex": sp.latex(e)} for n, e in exprs],
        "points": [{**p.as_dict(), "of": o} for p, o in zip(points, owners, strict=True)],
    }
    if alt is None:
        names = ", ".join(f"{n}(x) = {e}" for n, e in exprs)
        found = "; ".join(f"{p.kind} at x = {p.x:.4g}" for p in points) or "no marked points"
        alt = f"Graph of {names} for x from {lo:g} to {hi:g}; {found}."
    return core.finish(fig, alt, facts)


class custom:
    """Escape hatch for anything the templates do not cover, still in house style.

    with plot.custom(alt="...") as c:
        c.ax.plot(t, u)
        c.facts["peak"] = float(u.max())
    return c.figure
    """

    def __init__(self, alt: str, size: str = "col", **subplot_kw):
        self.alt = alt
        self.fig, self.ax = core.new_figure(size, **subplot_kw)
        self.facts: dict = {"template": "plot.custom"}
        self.figure: core.Figure | None = None

    def __enter__(self) -> custom:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            axes = self.ax if isinstance(self.ax, np.ndarray) else [self.ax]
            for ax in np.ravel(axes):
                core.apply_locale(ax)
            self.figure = core.finish(self.fig, self.alt, self.facts)


__all__ = [
    "MARKS",
    "MUTED",
    "bode",
    "custom",
    "functions",
    "nyquist",
    "phasor",
    "pole_zero",
    "root_locus",
    "signals",
    "step_response",
]
