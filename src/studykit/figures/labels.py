"""Label placement shared by the templates: put a text where it hides nothing.

Everything works in display coordinates on a figure whose layout is final (the caller
runs `fig.draw_without_rendering()` first): the drawing is sampled into points
(`polyline_points`, `marker_points`, `segment_points`), and `place` tries candidate
positions until a label's box misses those points, the axes edge and earlier labels.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence

import numpy as np
from matplotlib.transforms import Bbox

from studykit.figures.palette import BG, FG

LABEL_BOX = {"boxstyle": "square,pad=0.1", "fc": BG, "ec": "none", "alpha": 0.85}


def polyline_points(ax, z: np.ndarray, step: float = 2.0) -> np.ndarray:
    """Display points along the complex polyline z, at most `step` pixels apart.

    Non-finite samples are dropped; segments are cut at 2000 points, which only the parts
    far outside the view reach.
    """
    z = np.asarray(z, dtype=complex)
    z = z[np.isfinite(z)]
    if z.size == 0:
        return np.empty((0, 2))
    d = ax.transData.transform(np.column_stack([z.real, z.imag]))
    out = [d[:1]]
    for a, b in itertools.pairwise(d):
        k = int(min(math.hypot(*(b - a)) / step, 2000)) + 1
        out.append(np.linspace(a, b, k + 1)[1:])
    return np.concatenate(out)


def marker_points(ax, zs: Sequence[complex], radius_pt: float = 4.0) -> np.ndarray:
    """Display points covering round markers of radius_pt at the complex points zs."""
    if not zs:
        return np.empty((0, 2))
    centre = ax.transData.transform(np.array([[z.real, z.imag] for z in zs]))
    r = radius_pt * ax.figure.dpi / 72
    ring = np.array([(0, 0)] + [(math.cos(a), math.sin(a)) for a in np.linspace(0, 6.3, 12)])
    return np.concatenate([c + r * ring for c in centre])


def segment_points(ax, a, b, n: int = 60) -> np.ndarray:
    """n points along the data segment a-b, in display coordinates (for `_place`)."""
    xy = np.linspace(np.asarray(a, dtype=float), np.asarray(b, dtype=float), n)
    return ax.transData.transform(xy)


def nearest(box, pts: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Distance from box to the nearest of pts, that point and the box point facing it.

    All in display coordinates; pts is an (n, 2) array.
    """
    gap = np.column_stack([np.clip(pts[:, 0], box.x0, box.x1), np.clip(pts[:, 1], box.y0, box.y1)])
    d = np.hypot(*(pts - gap).T)
    i = int(np.argmin(d))
    return float(d[i]), pts[i], gap[i]


def place(
    ax,
    text: str,
    options: Sequence[dict],
    avoid: np.ndarray,
    placed: list,
    target: Sequence[tuple[float, float]] | None = None,
    **style,
):
    """Annotate at the first candidate whose text box misses the drawing and other labels.

    options: annotate() keyword sets (xy, xytext, ha, va, optional xycoords), best first.
    avoid: points of everything drawn (curves, lines, arrows) in display coordinates.
    target: the data segment the label explains (an arrow, a line: its two end points).
    When no candidate is free, the label moves to the free spot of the axes nearest to it;
    a label that ends up away from its target gets a thin leader line to it. Without a
    free spot the candidate with the fewest conflicts is kept; the page-coloured backing
    and a zorder above the curves keep it readable either way. The figure layout must be
    final (the caller ran draw_without_rendering); labels are kept out of the layout so
    they cannot move the axes afterwards.
    """
    renderer = ax.figure.canvas.get_renderer()
    frame = ax.get_window_extent(renderer)
    style = {"bbox": LABEL_BOX, "zorder": 8} | style
    pt = ax.figure.dpi / 72

    def score(box) -> int:
        hits = box.count_contains(avoid) + 100 * sum(box.overlaps(o) for o in placed)
        inside = frame.x0 <= box.x0 and box.x1 <= frame.x1
        inside = inside and frame.y0 <= box.y0 and box.y1 <= frame.y1
        return hits + 50 * (not inside)

    best = None
    for option in options:
        ann = ax.annotate(text, textcoords="offset points", **option, **style)
        ann.set_in_layout(False)
        box = ann.get_window_extent(renderer).padded(1.5 * pt)
        sc = score(box)
        if best is None or sc < best[0]:
            if best is not None:
                best[1].remove()
            best = (sc, ann, box)
        else:
            ann.remove()
        if sc == 0:
            break
    sc, ann, box = best
    near = None if target is None else segment_points(ax, *target, 40)
    if sc > 0 and near is not None:
        w, h = box.width, box.height
        free = []
        for cx in np.linspace(frame.x0 + w / 2, frame.x1 - w / 2, 28):
            for cy in np.linspace(frame.y0 + h / 2, frame.y1 - h / 2, 18):
                cand = Bbox.from_bounds(cx - w / 2, cy - h / 2, w, h)
                if score(cand) == 0:
                    free.append((nearest(cand, near)[0], cx, cy, cand))
        if free:
            _, cx, cy, box = min(free, key=lambda f: f[0])
            ann.remove()
            ann = ax.annotate(
                text,
                tuple(ax.transAxes.inverted().transform((cx, cy))),
                xycoords="axes fraction",
                ha="center",
                va="center",
                **style,
            )
            ann.set_in_layout(False)
    if near is not None:
        dist, at, gap = nearest(box, near)
        if dist > 8 * pt:
            (ax_, ay), (bx, by) = ax.transData.inverted().transform(np.array([at, gap]))
            ax.plot([ax_, bx], [ay, by], color=style.get("color", FG), lw=0.6, zorder=7)
    placed.append(box)
    return ann
