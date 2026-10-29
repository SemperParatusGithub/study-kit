"""State machines, flowcharts and the course topic map, drawn with `schemdraw.flow`.

    graph.state_machine(['S0', 'S1'], [('S0', 'S1', '1'), ('S1', 'S0', '0')], initial='S0')
    graph.flowchart([('a', 'start', 'Start'), ('b', 'process', 'x = 0')], [('a', 'b')])
    graph.topic_map(course_dir)   # `fig:topic-map` of the overview, from course.yaml

Positions are computed here (ring/row/grid layouts, layered graphs, label placement that
avoids states, edges and other labels); schemdraw only draws. Labels follow the rule of
`block.label` with plain text as the default: `_`, `^` or a backslash make TeX math
('S_0', 'x_k > 0.5?'), `$…$` marks inline math ('Ausgabe $s$'), anything else is upright
text ('S0', 'n gerade?'); German figures get a decimal comma in both.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import schemdraw.elements as elm
import yaml
from schemdraw import flow

from studykit.figures import core
from studykit.figures.block import FONT_PT, LABEL_PT, MIN_SCALE, UNIT_PT, Sheet, plain, text_size
from studykit.figures.block import label as _label
from studykit.figures.palette import BG, FG, MUTED, color

ARROW = {"arrowwidth": 0.15, "arrowlength": 0.25}
UNIT_IN = UNIT_PT / 72  # one drawing unit in inches at natural scale

# ---------------------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------------------


def _rich(text: str) -> tuple[str, bool]:
    """(text, parse_math) of a state, transition or flowchart label; see `block.label`."""
    return _label(text, math=False)


def _measure(text: str, size: float, weight: str = "normal") -> tuple[float, float]:
    shown, math_ = _rich(text)
    return text_size(shown, size, math=math_, weight=weight)


def _v(x: float, y: float) -> np.ndarray:
    return np.array([x, y], dtype=float)


def _unit(deg: float) -> np.ndarray:
    rad = math.radians(deg)
    return np.array([math.cos(rad), math.sin(rad)])


def _angle(v: np.ndarray) -> float:
    return math.degrees(math.atan2(v[1], v[0])) % 360


def _angdiff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def _quad(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, t) -> np.ndarray:
    t = np.atleast_1d(np.asarray(t, dtype=float))[:, None]
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t**2 * p2


def _quad_tangent(p0, p1, p2, t: float) -> np.ndarray:
    return 2 * (1 - t) * (p1 - p0) + 2 * t * (p2 - p1)


def _leave(p0, p1, p2, centre, r, lo: float, hi: float) -> float:
    """Parameter where the curve crosses the circle (centre, r) between lo and hi."""
    inside_lo = np.linalg.norm(_quad(p0, p1, p2, lo)[0] - centre) < r
    for _ in range(50):
        mid = (lo + hi) / 2
        if (np.linalg.norm(_quad(p0, p1, p2, mid)[0] - centre) < r) == inside_lo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


Rect = tuple[float, float, float, float]


def _rect(centre: np.ndarray, w: float, h: float) -> Rect:
    return (centre[0] - w / 2, centre[1] - h / 2, centre[0] + w / 2, centre[1] + h / 2)


def _rect_circle_gap(rect: Rect, c: np.ndarray, r: float) -> float:
    dx = max(rect[0] - c[0], 0.0, c[0] - rect[2])
    dy = max(rect[1] - c[1], 0.0, c[1] - rect[3])
    return math.hypot(dx, dy) - r


def _overlap(a: Rect, b: Rect) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(w, 0.0) * max(h, 0.0)


def _inside(rect: Rect, pts: np.ndarray, pad: float = 0.04) -> int:
    if len(pts) == 0:
        return 0
    x, y = pts[:, 0], pts[:, 1]
    hit = (x > rect[0] - pad) & (x < rect[2] + pad) & (y > rect[1] - pad) & (y < rect[3] + pad)
    return int(hit.sum())


def _round(v) -> list[float]:
    return [round(float(x), 3) for x in v]


# ---------------------------------------------------------------------------------------
# State machines
# ---------------------------------------------------------------------------------------

KINDS = ("moore", "mealy")
LAYOUTS = ("ring", "row", "grid")
STATE_MIN_R = 0.62
STATE_PAD = 0.14
ACCEPT_DR = 0.11  # gap between the two rings of an accepting state
LOOP_HALF = 40.0  # degrees from the loop direction to each loop end on the state
LOOP_R = 0.42
INIT_LEN = 0.85
CLEAR = 0.3  # an edge keeps this distance from states it does not connect
LOOP_ROOM = 0.8  # ... plus this much from states with a self-loop
LABEL_GAP = 0.15  # label box to its line (the box has its own small pad)


@dataclass
class _Edge:
    src: str
    dst: str
    labels: list[str]
    route: str = "line"
    k: float = 0.0
    q0: np.ndarray = field(default_factory=lambda: np.zeros(2))
    q1: np.ndarray = field(default_factory=lambda: np.zeros(2))
    q2: np.ndarray = field(default_factory=lambda: np.zeros(2))
    samples: np.ndarray = field(default_factory=lambda: np.zeros((0, 2)))
    direction: float = 0.0  # self-loops: angle of the loop on its state
    label_xy: np.ndarray | None = None
    loop: tuple[np.ndarray, float] | None = None  # self-loops: centre and radius of the arc

    @property
    def text(self) -> str:
        return ", ".join(lbl for lbl in self.labels if lbl)


def _parse_states(states, kind: str) -> list[tuple[str, str | None]]:
    if isinstance(states, Mapping):
        items = [(str(k), None if v is None else str(v)) for k, v in states.items()]
    else:
        items = []
        for s in states:
            if isinstance(s, str):
                items.append((s, None))
            else:
                name, out = s
                items.append((str(name), None if out is None else str(out)))
    names = [n for n, _ in items]
    if not names:
        raise ValueError("a state machine needs at least one state")
    if len(set(names)) != len(names):
        raise ValueError("state names must be unique")
    if kind == "mealy" and any(out is not None for _, out in items):
        raise ValueError("a Mealy machine has its outputs on the transitions ('a/1')")
    return items


def _parse_transitions(transitions, names: list[str], kind: str) -> list[tuple[str, str, str]]:
    out = []
    for tr in transitions:
        tr = tuple(tr)
        if len(tr) == 2:
            src, dst, label = (*tr, "")
        elif len(tr) == 3:
            src, dst, label = tr
        elif len(tr) == 4:
            if kind != "mealy":
                raise ValueError("(src, dst, input, output) transitions need kind='mealy'")
            src, dst, inp, outp = tr
            label = f"{inp}/{outp}"
        else:
            raise ValueError(f"transition {tr!r}: use (src, dst, label)")
        for s in (src, dst):
            if str(s) not in names:
                raise ValueError(f"transition {tr!r} uses unknown state {s!r}")
        out.append((str(src), str(dst), str(label)))
    return out


def _positions(names: list[str], layout, spacing: float) -> dict[str, np.ndarray]:
    n = len(names)
    if isinstance(layout, Mapping):
        missing = [k for k in names if k not in layout]
        if missing:
            raise ValueError(f"layout has no coordinates for {', '.join(missing)}")
        return {k: np.asarray(layout[k], dtype=float) * spacing for k in names}
    if layout not in LAYOUTS:
        raise ValueError(f"unknown layout {layout!r}; use {', '.join(LAYOUTS)} or a dict")
    if layout == "row" or (layout == "ring" and n == 2):
        return {k: np.array([i * spacing, 0.0]) for i, k in enumerate(names)}
    if layout == "grid":
        cols = math.ceil(math.sqrt(n))
        return {
            k: np.array([(i % cols) * spacing, -(i // cols) * spacing]) for i, k in enumerate(names)
        }
    if n == 1:
        return {names[0]: np.zeros(2)}
    radius = spacing / (2 * math.sin(math.pi / n))
    start = 90 + 180 / n
    return {k: radius * _unit(start - 360 * i / n) for i, k in enumerate(names)}


DIVIDER_DODGE = 25.0  # degrees: edges and arrows keep this far off a Moore state's divider
ALONG_DIVIDER = 12.0  # a straight edge this close to horizontal would run along dividers


def _clears(pts: np.ndarray, others: list[tuple[np.ndarray, float]]) -> bool:
    return all(np.min(np.linalg.norm(pts - c, axis=1)) > clear for c, clear in others)


def _route_edge(
    edge: _Edge,
    pos: dict[str, np.ndarray],
    r: float,
    paired: bool,
    looped: set[str],
    divided: set[str],
    routed: Sequence[np.ndarray] = (),
) -> None:
    """Straight if nothing is in the way, else the flattest arc that clears other states.

    Of two equally flat arcs the one farther from the `routed` edges wins, so edges from
    one state to two others do not run side by side. A straight edge that would run along
    the divider of a Moore state (output below the name) is moved off the centre line,
    attaching at DIVIDER_DODGE degrees on its left.
    """
    p0, p2 = pos[edge.src], pos[edge.dst]
    d = p2 - p0
    perp = np.array([-d[1], d[0]])
    others = [
        (c, r + CLEAR + (LOOP_ROOM if name in looped else 0.0))
        for name, c in pos.items()
        if name not in (edge.src, edge.dst)
    ]
    theta = _angle(d)
    on_divider = abs(math.sin(math.radians(theta))) < math.sin(math.radians(ALONG_DIVIDER))
    if not paired and on_divider and {edge.src, edge.dst} & divided:
        q0 = p0 + r * _unit(theta + DIVIDER_DODGE)
        q2 = p2 + r * _unit(theta + 180 - DIVIDER_DODGE)
        if _clears(np.linspace(q0, q2, 48), others):
            edge.q0, edge.q1, edge.q2, edge.k, edge.route = q0, (q0 + q2) / 2, q2, 0.0, "line"
            edge.samples = np.linspace(q0, q2, 40)
            return
    levels = (0.2, 0.32, 0.45) if paired else (0.0, 0.2, 0.32, 0.45)
    if not paired and on_divider and {edge.src, edge.dst} & divided:
        levels = levels[1:]  # the dodged line was blocked; never fall back onto the divider
    chosen = 0.6
    for level in levels:
        fits = []
        for k in (level,) if paired or level == 0 else (level, -level):
            pts = _quad(p0, p0 + d / 2 + k * perp, p2, np.linspace(0.05, 0.95, 48))
            if _clears(pts, others):
                inner = pts[8:-8]
                room = min(
                    (float(np.min(np.linalg.norm(inner[:, None] - q, axis=2))) for q in routed),
                    default=math.inf,
                )
                fits.append((min(room, 2.0), k))
        if fits:
            chosen = max(fits, key=lambda f: (round(f[0], 1), f[1]))[1]
            break
    p1 = p0 + d / 2 + chosen * perp
    a = _leave(p0, p1, p2, p0, r, 0.0, 0.5)
    b = _leave(p0, p1, p2, p2, r, 0.5, 1.0)
    edge.q0 = _quad(p0, p1, p2, a)[0]
    edge.q2 = _quad(p0, p1, p2, b)[0]
    edge.q1 = (1 - a) * (1 - b) * p0 + ((1 - a) * b + a * (1 - b)) * p1 + a * b * p2
    dq = edge.q2 - edge.q0
    edge.k = float(np.dot(edge.q1 - edge.q0 - dq / 2, [-dq[1], dq[0]]) / np.dot(dq, dq))
    edge.route = "line" if chosen == 0 else "arc"
    edge.samples = _quad(edge.q0, edge.q1, edge.q2, np.linspace(0, 1, 40))


def _free_direction(
    occupied: list[float], prefer: list[tuple[float, float]], avoid: Sequence[float] = ()
) -> float:
    """Direction with the widest gap to `occupied`, weighted by `prefer`; never near `avoid`."""
    best, best_score = 90.0, -math.inf
    for th in range(0, 360, 5):
        gap = min((_angdiff(th, a) for a in occupied), default=180.0)
        score = min(gap, 90.0) + sum(w * math.cos(math.radians(th - p)) for p, w in prefer)
        if any(_angdiff(th, a) < DIVIDER_DODGE + 5 for a in avoid):
            score -= 1000.0
        if score > best_score + 1e-9:
            best, best_score = float(th), score
    return best


def _loop_geometry(c: np.ndarray, r: float, theta: float):
    a = c + r * _unit(theta + LOOP_HALF)
    b = c + r * _unit(theta - LOOP_HALF)
    half = np.linalg.norm(b - a) / 2
    radius = max(LOOP_R, half * 1.08)
    centre = (a + b) / 2 + math.sqrt(radius**2 - half**2) * _unit(theta)
    ts = np.linspace(0, 2 * math.pi, 60)
    ring = centre + radius * np.column_stack([np.cos(ts), np.sin(ts)])
    ring = ring[np.linalg.norm(ring - c, axis=1) > r]
    return a, b, radius, ring, centre


def _extent_along(direction: np.ndarray, w: float, h: float) -> float:
    return (abs(direction[0]) * w + abs(direction[1]) * h) / 2


def _rect_points_dist(rect: Rect, pts: np.ndarray) -> float:
    if len(pts) == 0:
        return math.inf
    dx = np.maximum(np.maximum(rect[0] - pts[:, 0], pts[:, 0] - rect[2]), 0.0)
    dy = np.maximum(np.maximum(rect[1] - pts[:, 1], pts[:, 1] - rect[3]), 0.0)
    return float(np.min(np.hypot(dx, dy)))


LABEL_MARGIN = 0.4  # each label is this much nearer to its own edge than to any other
ON_LINE_COST = 0.3  # a label on its line (which breaks for it) over one beside the line
ON_LINE_ENDS = 0.45  # ... and only where this much of the line shows on either side
LABEL_CLEAR = 0.06  # label box to states and to other labels


def _label_candidates(edge: _Edge, w: float, h: float) -> list[tuple[np.ndarray, float]]:
    """(centre, cost) of the spots a label may take, cheapest first in spirit.

    Beside the edge on either side or on it (the line then breaks for the label), from the
    middle outwards; arcs prefer their outer side. A self-loop's label goes beyond the loop
    or beside it.
    """
    if edge.loop is not None:
        centre, radius = edge.loop
        out = []
        for phi in (0, 40, -40, 80, -80, 120, -120):
            u = _unit(edge.direction + phi)
            out.append((centre + u * (radius + LABEL_GAP + _extent_along(u, w, h)), abs(phi) / 200))
        return out
    outer = math.copysign(1.0, edge.k) if abs(edge.k) > 1e-9 else None
    out = []
    for t in np.linspace(0.15, 0.85, 15):
        pt = _quad(edge.q0, edge.q1, edge.q2, t)[0]
        tan = _quad_tangent(edge.q0, edge.q1, edge.q2, t)
        tan = tan / (np.linalg.norm(tan) or 1.0)
        normal = np.array([-tan[1], tan[0]])
        cost = 0.8 * abs(t - 0.5)
        for side in (1.0, -1.0):
            n = side * normal
            inner = outer is not None and side != outer
            out.append((pt + n * (LABEL_GAP + _extent_along(n, w, h)), cost + 0.2 * inner))
        ends = np.array([edge.q0, edge.q2])
        if 0.3 <= t <= 0.7 and _rect_points_dist(_rect(pt, w, h), ends) > ON_LINE_ENDS:
            out.append((pt, cost + ON_LINE_COST))  # the arrow stays visible on both sides
    return out


@dataclass
class _LabelCheck:
    state_gap: float  # to the nearest state (negative: on a state)
    label_gap: float  # to the nearest other label box (negative: overlapping)
    crossed: int  # sample points of other edges inside the box
    own: float  # distance to its own edge
    foreign: float  # distance to the nearest other edge or arrow

    @property
    def margin(self) -> float:
        return self.foreign - self.own


def _rect_gap(a: Rect, b: Rect) -> float:
    dx = max(a[0] - b[2], b[0] - a[2])
    dy = max(a[1] - b[3], b[1] - a[3])
    if dx < 0 and dy < 0:
        return max(dx, dy)  # overlapping: minus the smaller penetration
    return math.hypot(max(dx, 0.0), max(dy, 0.0))


def _check_label(
    rect: Rect,
    edge: _Edge,
    pos: dict[str, np.ndarray],
    r: float,
    placed: list[Rect],
    others: list[np.ndarray],
) -> _LabelCheck:
    return _LabelCheck(
        state_gap=min((_rect_circle_gap(rect, c, r) for c in pos.values()), default=math.inf),
        label_gap=min((_rect_gap(rect, o) for o in placed), default=math.inf),
        crossed=sum(_inside(rect, path) for path in others),
        own=_rect_points_dist(rect, edge.samples),
        foreign=min((_rect_points_dist(rect, path) for path in others), default=math.inf),
    )


def _label_penalty(c: _LabelCheck) -> float:
    """Zero for a clean spot; collisions and doubtful attribution cost far more than taste."""
    penalty = 0.0
    if c.state_gap < LABEL_CLEAR:
        penalty += 20 + 40 * (LABEL_CLEAR - c.state_gap)
    if c.label_gap < LABEL_CLEAR:
        penalty += 20 + 40 * (LABEL_CLEAR - c.label_gap)
    penalty += 20 * c.crossed
    if c.margin < LABEL_MARGIN:
        penalty += 5 + 20 * (LABEL_MARGIN - c.margin)
    return penalty


def _place_labels(
    edges: list[_Edge],
    sizes: dict[tuple[str, str], tuple[float, float]],
    pos: dict[str, np.ndarray],
    r: float,
    paths: list[np.ndarray],
) -> None:
    """Most constrained label first, then rounds of re-placing each against the others.

    A label still in trouble afterwards is re-placed together with each nearby label (all
    pairs of their best spots), which settles two labels competing for one gap.
    """
    rects: dict[int, Rect] = {}
    spots = {i: _label_candidates(e, *sizes[(e.src, e.dst)]) for i, e in enumerate(edges)}

    def score(i: int, centre: np.ndarray, cost: float, skip: int | None = None) -> float:
        e = edges[i]
        w, h = sizes[(e.src, e.dst)]
        others = [p for p in paths if p is not e.samples]
        placed = [rect for j, rect in rects.items() if j not in (i, skip)]
        return cost + _label_penalty(_check_label(_rect(centre, w, h), e, pos, r, placed, others))

    def place(i: int, centre: np.ndarray) -> None:
        edges[i].label_xy = centre
        rects[i] = _rect(centre, *sizes[(edges[i].src, edges[i].dst)])

    def ranked(i: int, skip: int | None = None) -> list[tuple[float, np.ndarray, float]]:
        out = [(score(i, c, cost, skip), c, cost) for c, cost in spots[i]]
        return sorted(out, key=lambda x: x[0])

    clean = [sum(sc < 1.0 for sc, _, _ in ranked(i)) for i in range(len(edges))]
    for _ in range(3):
        for i in sorted(range(len(edges)), key=lambda i: clean[i]):
            place(i, ranked(i)[0][1])
    for i in range(len(edges)):
        current = score(i, edges[i].label_xy, 0.0)
        if current < 1.0:
            continue
        for j in range(len(edges)):
            if j == i or _rect_gap(rects[i], rects[j]) > 1.0:
                continue
            old_i, old_j = edges[i].label_xy, edges[j].label_xy
            best = score(i, old_i, 0.0) + score(j, old_j, 0.0)
            choice = (old_i, old_j)
            for _, ci, cost_i in ranked(i, skip=j)[:8]:
                place(i, ci)
                for _, cj, cost_j in ranked(j, skip=i)[:8]:
                    place(j, cj)
                    total = score(i, ci, cost_i) + score(j, cj, cost_j)
                    if total < best - 1e-9:
                        best, choice = total, (ci, cj)
            place(i, choice[0])
            place(j, choice[1])


def state_machine(
    states: Sequence[str | tuple[str, str]] | Mapping[str, str | None],
    transitions: Sequence[tuple],
    initial: str | None = None,
    accepting: Iterable[str] = (),
    kind: str = "moore",
    layout: str | Mapping[str, tuple[float, float]] = "ring",
    *,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """State diagram of a Moore or Mealy machine (or a plain automaton).

    states: names, or for Moore a mapping/pairs name -> output (shown inside the state).
    transitions: (src, dst, label); Mealy labels read 'input/output', or pass
    (src, dst, input, output). layout: 'ring', 'row', 'grid' or {state: (x, y)} in units of
    the state spacing. Accepting states get a double ring, `initial` an entry arrow.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    items = _parse_states(states, kind)
    names = [n for n, _ in items]
    outputs = dict(items)
    trans = _parse_transitions(transitions, names, kind)
    accepting = [str(a) for a in accepting]
    for s in [*accepting, *([initial] if initial is not None else [])]:
        if s not in names:
            raise ValueError(f"unknown state {s!r}")

    # Size of a state from its contents (uniform radius keeps the drawing calm).
    r = STATE_MIN_R
    for name, out in items:
        wn, hn = _measure(name, FONT_PT)
        if out is None:
            r = max(r, math.hypot(wn / 2, hn / 2) + STATE_PAD)
        else:
            wo, ho = _measure(out, FONT_PT)
            r = max(r, math.hypot(max(wn, wo) / 2, max(hn, ho) + 0.08) + STATE_PAD)
    edges: dict[tuple[str, str], _Edge] = {}
    for src, dst, label in trans:
        edges.setdefault((src, dst), _Edge(src, dst, [])).labels.append(label)
    label_sizes = {
        key: _measure(e.text, LABEL_PT) if e.text else (0.0, 0.0) for key, e in edges.items()
    }
    widest = max((w for w, _ in label_sizes.values()), default=0.0)
    spacing = 2 * r + min(max(widest + 0.7, 1.7), 3.4)
    pos = _positions(names, layout, spacing)
    centroid = np.mean(list(pos.values()), axis=0)

    # Edges between different states first, then loops and the entry arrow in free gaps.
    looped = {src for src, dst in edges if src == dst}
    divided = {name for name in names if outputs.get(name) is not None}
    occupied: dict[str, list[float]] = {n: [] for n in names}
    routed: list[np.ndarray] = []
    for (src, dst), e in edges.items():
        if src == dst:
            continue
        paired = (dst, src) in edges
        _route_edge(e, pos, r, paired, looped, divided, routed)
        routed.append(e.samples)
        occupied[src].append(_angle(e.q0 - pos[src]))
        occupied[dst].append(_angle(e.q2 - pos[dst]))
    for name in names:  # edges that pass close by also block loops and the entry arrow
        for (src, dst), e in edges.items():
            if src != dst and name not in (src, dst):
                near = e.samples[np.linalg.norm(e.samples - pos[name], axis=1) < r + LOOP_ROOM]
                occupied[name] += [_angle(p - pos[name]) for p in near[::3]]

    flat = np.ptp([c[1] for c in pos.values()]) < 1e-6  # a row: loops go on top

    def outward(name: str) -> float:
        v = pos[name] - centroid
        return _angle(v) if np.linalg.norm(v) > 1e-6 and not flat else 90.0

    def divider(name: str) -> tuple[float, ...]:
        return (0.0, 180.0) if name in divided else ()

    paths: list[np.ndarray] = []
    loops = {}
    for (src, dst), e in edges.items():
        if src != dst:
            continue
        theta = _free_direction(
            occupied[src], [(outward(src), 40.0), (90.0, 8.0)], avoid=divider(src)
        )
        occupied[src] += [theta, theta + LOOP_HALF, theta - LOOP_HALF]
        a, b, radius, ring, centre = _loop_geometry(pos[src], r, theta)
        e.route, e.direction, e.q0, e.q2, e.samples = "loop", theta, a, b, ring
        e.loop = (centre, radius)
        loops[src] = (a, b, radius)
    init_dir = None
    if initial is not None:
        init_dir = _free_direction(
            occupied[initial],
            [(180.0, 30.0), (outward(initial), 0.0 if flat else 10.0)],
            avoid=divider(initial),
        )
        u = _unit(init_dir)
        start = pos[initial] + u * (r + INIT_LEN)
        paths.append(np.linspace(start, pos[initial] + u * r, 12))
    for e in edges.values():
        paths.append(e.samples)
    labelled = [e for e in edges.values() if e.text]
    _place_labels(labelled, label_sizes, pos, r, paths)
    placed = [_rect(e.label_xy, *label_sizes[(e.src, e.dst)]) for e in labelled]
    checks = {
        (e.src, e.dst): _check_label(
            rect,
            e,
            pos,
            r,
            [o for o in placed if o is not rect],
            [p for p in paths if p is not e.samples],
        )
        for e, rect in zip(labelled, placed, strict=True)
    }
    _require_legible(checks)

    # Draw: edges, then states on top (filled), then texts.
    sheet = Sheet()
    for e in edges.values():
        if e.route == "loop":
            a, b, radius = loops[e.src]
            sheet.add(elm.ArcLoop(radius=radius, arrow="->", **ARROW).at(a).to(b))
        elif e.route == "line":
            sheet.add(elm.Arrow(**ARROW).at(e.q0).to(e.q2))
        else:
            sheet.add(elm.Arc2(k=e.k, arrow="->").at(e.q0).to(e.q2))
        if e.text:
            shown, math_ = _rich(e.text)
            w, h = label_sizes[(e.src, e.dst)]
            rect = _rect(e.label_xy, w, h)
            on_line = any(_inside(rect, path, pad=0.0) for path in [*paths, e.samples])
            sheet.text(e.label_xy, shown, math=math_, bg=BG if on_line else None)
    if init_dir is not None:
        u = _unit(init_dir)
        sheet.add(elm.Arrow(**ARROW).at(pos[initial] + u * (r + INIT_LEN)).to(pos[initial] + u * r))
    for name in names:
        c = pos[name]
        if name in accepting:
            node = flow.StateEnd(r=r - ACCEPT_DR, dr=ACCEPT_DR)
        else:
            node = flow.State(r=r)
        sheet.add(node.at(c).anchor("center").fill(BG))
        shown, math_ = _rich(name)
        out = outputs.get(name)
        if out is None:
            sheet.text(c, shown, size=FONT_PT, math=math_)
        else:
            inner = r - (ACCEPT_DR if name in accepting else 0.0)
            sheet.add(elm.Line().at(c - _v(inner, 0)).to(c + _v(inner, 0)))
            _, hn = _measure(name, FONT_PT)
            _, ho = _measure(out, FONT_PT)
            sheet.text(c + _v(0, 0.06 + hn / 2), shown, size=FONT_PT, math=math_)
            out_shown, out_math = _rich(out)
            sheet.text(c - _v(0, 0.06 + ho / 2), out_shown, size=FONT_PT, math=out_math)

    reachable = _reachable(initial, trans) if initial is not None else None
    facts = {
        "template": "graph.state_machine",
        "kind": kind,
        "layout": layout if isinstance(layout, str) else "coords",
        "states": [
            {
                "name": name,
                "output": outputs.get(name),
                "initial": name == initial,
                "accepting": name in accepting,
                "xy": _round(pos[name]),
            }
            for name in names
        ],
        "transitions": [{"src": s, "dst": d, "label": lbl} for s, d, lbl in trans],
        "edges": [
            {
                "src": e.src,
                "dst": e.dst,
                "label": e.text,
                "route": e.route,
                "k": round(e.k, 3),
                "ends": [_round(e.q0), _round(e.q2)],
                "label_xy": _round(e.label_xy) if e.label_xy is not None else None,
                "label_margin": (
                    round(checks[(e.src, e.dst)].margin, 3) if (e.src, e.dst) in checks else None
                ),
            }
            for e in edges.values()
        ],
        "initial": initial,
        "initial_angle": init_dir,
        "accepting": accepting,
        "reachable": reachable,
        "unreachable": [n for n in names if reachable is not None and n not in reachable],
        "radius": round(r, 3),
        "spacing": round(spacing, 3),
        "label_overlaps": _count_overlaps(placed),
        # Smallest distance from any label box to any state (negative = label on a state).
        "label_state_gap": round(min((c.state_gap for c in checks.values()), default=0.0), 3),
        # Smallest (distance to the nearest other edge) - (distance to its own edge) over all
        # labels: positive means every label sits nearer to the arrow it belongs to.
        "label_own_margin": round(min((c.margin for c in checks.values()), default=0.0), 3),
    }
    if alt is None:
        alt = _state_alt(kind, names, outputs, trans, initial, accepting)
    return sheet.render(size, alt, facts)


def _require_legible(checks: dict[tuple[str, str], _LabelCheck]) -> None:
    """Refuse to draw a diagram whose labels collide or sit nearer to a foreign edge."""
    bad = []
    for (src, dst), c in checks.items():
        if c.state_gap < 0:
            bad.append(f"{src}→{dst} lies on a state")
        elif c.label_gap < 0:
            bad.append(f"{src}→{dst} overlaps another label")
        elif c.crossed:
            bad.append(f"{src}→{dst} is crossed by another edge")
        elif c.margin <= 0:
            bad.append(f"{src}→{dst} is nearer to another edge than to its own")
    if bad:
        raise ValueError(
            "state diagram labels cannot be placed legibly ("
            + "; ".join(bad)
            + "); use another layout or layout= coordinates that spread the states"
        )


def _reachable(initial: str, trans: list[tuple[str, str, str]]) -> list[str]:
    seen, todo = [initial], [initial]
    while todo:
        cur = todo.pop()
        for s, d, _ in trans:
            if s == cur and d not in seen:
                seen.append(d)
                todo.append(d)
    return seen


def _count_overlaps(rects: list[Rect]) -> int:
    return sum(1 for i, a in enumerate(rects) for b in rects[i + 1 :] if _overlap(a, b) > 1e-6)


def _state_alt(kind, names, outputs, trans, initial, accepting) -> str:
    de = core.locale() == "de"
    kind_txt = {"moore": "Moore", "mealy": "Mealy"}[kind]
    txt = lambda x: plain(x, math=False)  # noqa: E731
    out_word = "Ausgabe" if de else "output"
    states = ", ".join(
        f"{txt(n)} ({out_word} {txt(outputs[n])})" if outputs.get(n) else txt(n) for n in names
    )
    arrows = "; ".join(
        f"{txt(s)} → {txt(d)}" + (f" ({txt(lbl)})" if lbl else "") for s, d, lbl in trans
    )
    initial = txt(initial) if initial else initial
    accepting = [txt(a) for a in accepting]
    if de:
        text = f"Zustandsdiagramm eines {kind_txt}-Automaten mit {len(names)} Zuständen: {states}."
        if initial:
            text += f" Startzustand {initial}."
        if accepting:
            text += f" Endzustände: {', '.join(accepting)}."
        return text + f" Übergänge: {arrows}."
    text = f"State diagram of a {kind_txt} machine with {len(names)} states: {states}."
    if initial:
        text += f" Initial state {initial}."
    if accepting:
        text += f" Accepting states: {', '.join(accepting)}."
    return text + f" Transitions: {arrows}."


# ---------------------------------------------------------------------------------------
# Flowcharts
# ---------------------------------------------------------------------------------------

NODE_KINDS = ("start", "end", "process", "decision", "io")
FLOW_H_GAP = 1.3  # between columns: room for vertical lanes
FLOW_V_GAP = 1.0  # between rows: room for horizontal channels
TRACK = 0.22


@dataclass
class _Node:
    id: str
    kind: str
    text: str
    w: float = 0.0
    h: float = 0.0
    layer: int = 0
    col: int = 0
    xy: np.ndarray = field(default_factory=lambda: np.zeros(2))

    def port(self, side: str) -> np.ndarray:
        dx = {"E": self.w / 2, "W": -self.w / 2}.get(side, 0.0)
        dy = {"N": self.h / 2, "S": -self.h / 2}.get(side, 0.0)
        return self.xy + _v(dx, dy)


def _parse_nodes(nodes) -> list[_Node]:
    items = nodes.items() if isinstance(nodes, Mapping) else [(n[0], tuple(n[1:])) for n in nodes]
    out = []
    for node_id, spec in items:
        spec = (spec,) if isinstance(spec, str) else tuple(spec)
        if len(spec) not in (1, 2):
            raise ValueError(f"node {node_id!r}: use (id, kind, text)")
        kind, text = spec if len(spec) == 2 else (spec[0], node_id)
        kind = {"box": "process", "stop": "end", "terminal": "start"}.get(kind, kind)
        if kind not in NODE_KINDS:
            raise ValueError(f"node {node_id!r}: kind must be one of {', '.join(NODE_KINDS)}")
        out.append(_Node(str(node_id), kind, str(text)))
    if not out:
        raise ValueError("a flowchart needs at least one node")
    if len({n.id for n in out}) != len(out):
        raise ValueError("flowchart node ids must be unique")
    return out


def _node_size(node: _Node) -> tuple[float, float]:
    shown, math_ = _rich(node.text)
    w, h = text_size(shown, FONT_PT, math=math_)
    if node.kind == "decision":
        pw, ph = w + 0.3, h + 0.2
        half = pw / 2 + ph / 1.2  # a diamond with height 0.6 x width fits the text
        return max(2 * half, 2.4), max(1.2 * half, 1.3)
    if node.kind in ("start", "end"):
        return max(w + 1.0, 2.2), max(h + 0.4, 0.95)
    return max(w + 0.8, 2.4), max(h + 0.5, 1.1)


def _node_element(node: _Node):
    w, h = node.w, node.h
    if node.kind == "decision":
        el = flow.Decision(w=w, h=h)
    elif node.kind in ("start", "end"):
        el = flow.Terminal(w=w, h=h)
    elif node.kind == "io":
        el = flow.Data(w=w - 0.5, h=h)
    else:
        el = flow.Box(w=w, h=h)
    return el.at(node.xy).anchor("center")


def _flow_layout(nodes: list[_Node], edges: list[tuple[str, str, str]]) -> set[int]:
    """Layers (longest path) and columns; returns the indices of back edges (loops)."""
    by_id = {n.id: n for n in nodes}
    out_edges: dict[str, list[int]] = {n.id: [] for n in nodes}
    for i, (u, _, _) in enumerate(edges):
        out_edges[u].append(i)
    state: dict[str, int] = {}
    order: list[str] = []
    back: set[int] = set()

    def dfs(u: str) -> None:
        state[u] = 1
        order.append(u)
        for i in out_edges[u]:
            v = edges[i][1]
            if state.get(v) == 1:
                back.add(i)
            elif v not in state:
                dfs(v)
        state[u] = 2

    for n in nodes:
        if n.id not in state:
            dfs(n.id)
    rank = {u: i for i, u in enumerate(order)}
    fwd = [(u, v) for i, (u, v, _) in enumerate(edges) if i not in back]
    indeg = {n.id: 0 for n in nodes}
    for _, v in fwd:
        indeg[v] += 1
    ready = sorted((u for u, d in indeg.items() if d == 0), key=rank.get)
    topo = []
    while ready:
        u = ready.pop(0)
        topo.append(u)
        for a, v in fwd:
            if a == u:
                indeg[v] -= 1
                if indeg[v] == 0:
                    ready.append(v)
                    ready.sort(key=rank.get)
    for u in topo:
        preds = [by_id[a].layer for a, v in fwd if v == u]
        by_id[u].layer = max(preds) + 1 if preds else 0
    # A node continues the column of the node whose first edge (straight down) reaches it;
    # further branches go to the right.
    first: dict[str, int] = {}
    for i, (u, _, _) in enumerate(edges):
        if i not in back:
            first.setdefault(u, i)
    main_parent: dict[str, str] = {}
    for u in topo:
        if u in first:
            main_parent.setdefault(edges[first[u]][1], u)
    taken: set[tuple[int, int]] = set()
    placed: set[str] = set()

    def put(node: _Node, col: int) -> None:
        while (node.layer, col) in taken:
            col += 1
        node.col = col
        taken.add((node.layer, col))
        placed.add(node.id)

    for u in topo:
        node = by_id[u]
        if u not in placed:
            put(node, 0)
        j = 0
        for i in out_edges[u]:
            v = edges[i][1]
            if i in back or v in placed or main_parent.get(v, u) != u:
                continue
            if i == first[u]:
                put(by_id[v], node.col)
            else:
                j += 1
                put(by_id[v], node.col + j)
    return back


def _track_offset(i: int, outer: int) -> float:
    """Offset of track i in a gap: alternating around the middle, outwards at the border."""
    if outer:
        return outer * i * TRACK
    return (i + 1) // 2 * TRACK * (1 if i % 2 else -1)


class _Tracks:
    """Parallel tracks in a gap between columns or rows; one key shares one track."""

    def __init__(self) -> None:
        self.keys: dict[tuple[str, int], list] = {}

    def take(self, axis: str, gap: int, key) -> int:
        keys = self.keys.setdefault((axis, gap), [])
        if key not in keys:
            keys.append(key)
        return keys.index(key)

    def count(self, axis: str, gap: int) -> int:
        return len(self.keys.get((axis, gap), []))


BRANCH_ROOM = 0.3  # a branch label's line runs on this far past the label


def _flow_routes(nodes, edges, back, cells, shape, col_w, row_h, gap_w, band_h):
    """Orthogonal routes of all edges; also the gap widths and band heights they need.

    Vertical runs use tracks in the gaps between columns, horizontal runs tracks in the
    bands between rows; every track is a physical gap position, so two edges never share
    one unless they enter the same node. Loops run up the outer lane: on the left when
    they start in the first column, else on the right.
    """
    cols, rows = shape
    by_id = {n.id: n for n in nodes}
    col_x = [0.0]
    for c in range(1, cols):
        col_x.append(col_x[-1] + col_w[c - 1] / 2 + gap_w[c] + col_w[c] / 2)
    row_y = [0.0]
    for r in range(1, rows):
        row_y.append(row_y[-1] - row_h[r - 1] / 2 - band_h[r] - row_h[r] / 2)
    for n in nodes:
        n.xy = np.array([col_x[n.col], row_y[n.layer]])
    tracks = _Tracks()

    def lane(g: int, key) -> float:
        i = tracks.take("x", g, key)
        if g == 0:
            return col_x[0] - col_w[0] / 2 - gap_w[0] / 2 + _track_offset(i, -1)
        if g == cols:
            return col_x[-1] + col_w[-1] / 2 + gap_w[g] / 2 + _track_offset(i, 1)
        left, right = col_x[g - 1] + col_w[g - 1] / 2, col_x[g] - col_w[g] / 2
        return (left + right) / 2 + _track_offset(i, 0)

    def band(b: int, key) -> float:
        i = tracks.take("y", b, key)
        if b == 0:
            return row_y[0] + row_h[0] / 2 + band_h[0] / 2 + _track_offset(i, 1)
        if b == rows:
            return row_y[-1] - row_h[-1] / 2 - band_h[b] / 2 + _track_offset(i, -1)
        top, bottom = row_y[b - 1] - row_h[b - 1] / 2, row_y[b] + row_h[b] / 2
        return (top + bottom) / 2 + _track_offset(i, 0)

    def column_clear(col: int, lo: int, hi: int) -> bool:
        return all((layer, col) not in cells for layer in range(lo + 1, hi))

    def row_clear(layer: int, a: int, b: int) -> bool:
        lo, hi = min(a, b), max(a, b)
        return all((layer, c) not in cells for c in range(lo, hi + 1))

    used_ports: dict[str, set[str]] = {n.id: set() for n in nodes}
    routes = []
    room: dict[int, float] = {}  # gap -> extra width a branch label needs
    for i, (u_id, v_id, label) in enumerate(edges):
        u, v = by_id[u_id], by_id[v_id]
        free = [p for p in ("S", "E", "W") if p not in used_ports[u_id]]
        is_back = i in back
        outer = "W" if u.col == 0 else "E"
        if u.kind != "decision":
            port = "S"
        elif is_back:
            sides = [outer, *(p for p in ("W", "E") if p != outer)]
            out_of_row = {"W": range(u.col), "E": range(u.col + 1, cols)}
            ok = [
                p
                for p in sides
                if p in free and all((u.layer, c) not in cells for c in out_of_row[p])
            ]
            port = ok[0] if ok else ("S" if "S" in free else free[0] if free else "S")
        elif v.col == u.col and "S" in free:
            port = "S"
        elif v.col > u.col and "E" in free:
            port = "E"
        elif v.col < u.col and "W" in free:
            port = "W"
        else:
            port = free[0] if free else "S"
        used_ports[u_id].add(port)
        start, end = u.port(port), v.port("N")
        if is_back:
            side = port if port in ("W", "E") else outer
            x_l = lane(0 if side == "W" else cols, i)
            y_c = band(v.layer, ("in", v_id))
            if port == "S":
                y_b = band(u.layer + 1, ("out", i))
                pts = [start, (u.xy[0], y_b), (x_l, y_b)]
            else:
                pts = [start, (x_l, start[1])]
            pts += [(x_l, y_c), (v.xy[0], y_c), end]
        elif port == "S" and v.col == u.col and column_clear(u.col, u.layer, v.layer):
            pts = [start, end]
        elif port == "S":
            y_c = band(v.layer, ("in", v_id))
            if column_clear(u.col, u.layer, v.layer):
                pts = [start, (u.xy[0], y_c), (v.xy[0], y_c), end]
            else:
                x_l = lane(u.col + 1, i)
                y_b = band(u.layer + 1, ("out", i))
                pts = [start, (u.xy[0], y_b), (x_l, y_b), (x_l, y_c), (v.xy[0], y_c), end]
        else:
            step = 1 if port == "E" else -1
            row_free = row_clear(u.layer, u.col + step, v.col)
            if row_free and column_clear(v.col, u.layer - 1, v.layer) and v.col != u.col:
                pts = [start, (v.xy[0], start[1]), end]
            else:
                g = u.col + 1 if port == "E" else u.col
                x_l = lane(g, i)
                y_c = band(v.layer, ("in", v_id))
                pts = [start, (x_l, start[1]), (x_l, y_c), (v.xy[0], y_c), end]
        pts = [np.asarray(p, dtype=float) for p in pts]
        if label and port in ("E", "W") and len(pts) > 2:
            shown, math_ = _rich(label)
            need = text_size(shown, LABEL_PT, math=math_)[0] + BRANCH_ROOM
            short = need - abs(pts[1][0] - pts[0][0])
            if short > 0:
                g = (u.col + 1 if port == "E" else u.col) if not is_back else (
                    0 if port == "W" else cols)  # fmt: skip
                room[g] = max(room.get(g, 0.0), short)
        routes.append(
            {"src": u_id, "dst": v_id, "label": label, "port": port, "back": is_back, "pts": pts}
        )

    def need(axis: str, gap: int, outer: bool, base: float, margin: float) -> float:
        n = tracks.count(axis, gap)  # tracks alternate around the middle of an inner gap
        spread = 0.0 if outer else 2 * (n // 2) * TRACK + margin
        return max(base, spread)

    # Widening a gap by 2 d moves its lanes by d, past a branch label that is d too long.
    need_w = [
        max(need("x", g, g in (0, cols), FLOW_H_GAP, 0.7), gap_w[g] + 2 * room.get(g, 0.0))
        for g in range(cols + 1)
    ]
    need_h = [need("y", b, b in (0, rows), FLOW_V_GAP, 0.6) for b in range(rows + 1)]
    return routes, need_w, need_h


def flowchart(
    nodes: Sequence[tuple[str, str, str]] | Mapping[str, tuple[str, str]],
    edges: Sequence[tuple],
    *,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Top-down flowchart (DIN 66001 shapes).

    nodes: (id, kind, text) with kind in start, end, process, decision, io.
    edges: (src, dst) or (src, dst, label). The first edge out of a node continues straight
    down, and a node stays in the column of the node whose first edge reaches it; further
    branches of a decision go right. Edges back to an earlier node (loops) run up the outer
    lane, on the left (on the right when they start right of the first column), and join
    the target from above. Node texts and edge labels follow `block.label` (plain text by
    default, `$…$` for inline math).
    """
    nodes_ = _parse_nodes(nodes)
    by_id = {n.id: n for n in nodes_}
    edges_ = []
    for e in edges:
        e = tuple(e)
        src, dst, label = (*e, "") if len(e) == 2 else e
        for x in (src, dst):
            if str(x) not in by_id:
                raise ValueError(f"edge {e!r} uses unknown node {x!r}")
        edges_.append((str(src), str(dst), str(label)))
    for n in nodes_:
        n.w, n.h = _node_size(n)
    back = _flow_layout(nodes_, edges_)

    cols = max(n.col for n in nodes_) + 1
    rows = max(n.layer for n in nodes_) + 1
    col_w = [max((n.w for n in nodes_ if n.col == c), default=1.0) for c in range(cols)]
    row_h = [max((n.h for n in nodes_ if n.layer == r), default=1.0) for r in range(rows)]
    cells = {(n.layer, n.col) for n in nodes_}
    # Gap g lies left of column g (g = cols: right of the last one), band b above row b.
    gap_w = [FLOW_H_GAP] * (cols + 1)
    band_h = [FLOW_V_GAP] * (rows + 1)
    for _ in range(3):
        routes, need_w, need_h = _flow_routes(
            nodes_, edges_, back, cells, (cols, rows), col_w, row_h, gap_w, band_h
        )
        if all(n <= w + 1e-9 for n, w in zip(need_w, gap_w, strict=True)) and all(
            n <= h + 1e-9 for n, h in zip(need_h, band_h, strict=True)
        ):
            break
        gap_w = [max(w, n) for w, n in zip(gap_w, need_w, strict=True)]
        band_h = [max(h, n) for h, n in zip(band_h, need_h, strict=True)]

    sheet = Sheet()
    for route in routes:
        pts = route["pts"]
        for j in range(len(pts) - 1):
            if np.allclose(pts[j], pts[j + 1]):
                continue
            if j == len(pts) - 2:
                sheet.add(elm.Arrow(**ARROW).at(pts[j]).to(pts[j + 1]))
            else:
                sheet.add(elm.Line().at(pts[j]).to(pts[j + 1]))
        if route["label"]:
            p, side = pts[0], route["port"]
            shown, math_ = _rich(route["label"])
            if side == "S":
                sheet.text(p + _v(0.1, -0.06), shown, ha="left", va="top", math=math_)
            elif side == "E":
                sheet.text(p + _v(0.08, 0.06), shown, ha="left", va="bottom", math=math_)
            else:
                sheet.text(p + _v(-0.08, 0.06), shown, ha="right", va="bottom", math=math_)
    for n in nodes_:
        sheet.add(_node_element(n).fill(BG))
        shown, math_ = _rich(n.text)
        sheet.text(n.xy, shown, size=FONT_PT, math=math_)

    facts = {
        "template": "graph.flowchart",
        "nodes": [
            {
                "id": n.id,
                "kind": n.kind,
                "text": n.text,
                "layer": n.layer,
                "column": n.col,
                "xy": _round(n.xy),
            }
            for n in nodes_
        ],
        "edges": [
            {
                "src": r["src"],
                "dst": r["dst"],
                "label": r["label"],
                "port": r["port"],
                "back": r["back"],
                "points": [_round(p) for p in r["pts"]],
            }
            for r in routes
        ],
        "layers": rows,
        "columns": cols,
        # Pairs of collinear, overlapping segments of edges into different nodes (0: no
        # route runs on top of another).
        "shared_segments": _shared_segments(routes),
    }
    if alt is None:
        alt = _flow_alt(nodes_, edges_)
    return sheet.render(size, alt, facts)


def _shared_segments(routes: list[dict]) -> int:
    segments = []
    for k, route in enumerate(routes):
        for a, b in itertools.pairwise(route["pts"]):
            if not np.allclose(a, b):
                segments.append((k, route["dst"], a, b))
    count = 0
    for (k1, d1, a1, b1), (k2, d2, a2, b2) in itertools.combinations(segments, 2):
        if k1 == k2 or d1 == d2:
            continue  # edges into one node merge on purpose
        for axis in (0, 1):  # 0: vertical segments (same x), 1: horizontal (same y)
            if (
                max(abs(a1[axis] - b1[axis]), abs(a2[axis] - b2[axis]), abs(a1[axis] - a2[axis]))
                > 1e-6
            ):
                continue
            o = 1 - axis
            lo = max(min(a1[o], b1[o]), min(a2[o], b2[o]))
            hi = min(max(a1[o], b1[o]), max(a2[o], b2[o]))
            if hi - lo > 1e-6:  # a plain int: numpy comparisons would make count an int64
                count += 1
    return count


def _flow_alt(nodes: list[_Node], edges: list[tuple[str, str, str]]) -> str:
    de = core.locale() == "de"
    by_id = {n.id: n for n in nodes}
    txt = lambda x: plain(x, math=False).replace("\n", " ")  # noqa: E731
    steps = "; ".join(
        f"{txt(by_id[u].text)} → {txt(by_id[v].text)}" + (f" ({txt(lbl)})" if lbl else "")
        for u, v, lbl in edges
    )
    if de:
        return f"Ablaufdiagramm mit {len(nodes)} Elementen. Abläufe: {steps}."
    return f"Flowchart with {len(nodes)} elements. Flow: {steps}."


# ---------------------------------------------------------------------------------------
# Topic map
# ---------------------------------------------------------------------------------------

TOPIC_PT = 8.0
LEGEND_PT = 7.5
WRAP_W = 4.4  # titles wider than this (drawing units) wrap onto two lines
NODE_PAD_X = 0.3
NODE_PAD_Y = 0.22
WEIGHT_EXTRA = 0.9  # the heaviest topic is this many base heights taller
LAYER_GAP = 1.5  # between layers, room for the arrows
TB_LAYER_GAP = 1.1
NODE_GAP = 0.4
DUMMY_GAP = 0.35
PORT_GAP = 0.22
PORT_END = 0.15  # ports keep clear of the rounded corners
DUMMY = "→"  # marks a bend point of a long edge in layer lists


@dataclass
class _Topic:
    id: str
    title: str
    weight: float
    prereq: list[str]
    status: str = "normal"  # normal | focus | skip
    text: str = ""
    w: float = 0.0  # box size
    h: float = 0.0

    @property
    def font_weight(self) -> str:
        return "bold" if self.status == "focus" else "normal"


def _wrap_title(title: str, weight: str) -> str:
    """At most two lines, broken where the longer line is shortest."""
    width = text_size(title, TOPIC_PT, math=False, weight=weight)[0]
    if width <= WRAP_W:
        return title
    splits = []
    for i, ch in enumerate(title):
        if ch == " ":
            splits.append((title[:i], title[i + 1 :]))
        elif ch == "-" and 0 < i < len(title) - 1 and title[i + 1] != " ":
            splits.append((title[: i + 1], title[i + 1 :]))
    if not splits:
        return title

    def longest(split: tuple[str, str]) -> float:
        return max(text_size(part, TOPIC_PT, math=False, weight=weight)[0] for part in split)

    return "\n".join(min(splits, key=longest))


def _load_topics(course_dir: Path) -> tuple[list[_Topic], list[str], list[str]]:
    data = yaml.safe_load((Path(course_dir) / "course.yaml").read_text(encoding="utf-8")) or {}
    raw = data.get("topics") or []
    if not raw:
        raise ValueError("course.yaml lists no topics")
    topics = []
    for t in raw:
        tid = str(t["id"])
        topics.append(
            _Topic(
                id=tid,
                title=str(t.get("title") or tid),
                weight=max(float(t.get("weight") or 0.0), 0.0),
                prereq=[str(p) for p in (t.get("prereq") or [])],
            )
        )
    ids = [t.id for t in topics]
    if len(set(ids)) != len(ids):
        raise ValueError("topic ids in course.yaml must be unique")
    focus = [str(x) for x in (data.get("focus") or [])]
    skip = [str(x) for x in (data.get("skip") or [])]
    for name, group in (
        ("prereq", [p for t in topics for p in t.prereq]),
        ("focus", focus),
        ("skip", skip),
    ):
        unknown = sorted(set(group) - set(ids))
        if unknown:
            raise ValueError(f"course.yaml {name} names unknown topics: {', '.join(unknown)}")
    for t in topics:
        t.status = "skip" if t.id in skip else ("focus" if t.id in focus else "normal")
    return topics, focus, skip


def _depths(topics: list[_Topic]) -> dict[str, int]:
    by_id = {t.id: t for t in topics}
    depth: dict[str, int] = {}
    visiting: set[str] = set()

    def visit(tid: str) -> int:
        if tid in depth:
            return depth[tid]
        if tid in visiting:
            raise ValueError(f"course.yaml prerequisites form a cycle through {tid!r}")
        visiting.add(tid)
        prereq = by_id[tid].prereq
        depth[tid] = 1 + max(visit(p) for p in prereq) if prereq else 0
        visiting.discard(tid)
        return depth[tid]

    for t in topics:
        visit(t.id)
    return depth


def _pair_crossings(upper: list[str], lower: list[str], links: list[tuple[str, str]]) -> int:
    """Crossings between the links from layer `upper` to layer `lower`."""
    pa = {k: i for i, k in enumerate(upper)}
    pb = {k: i for i, k in enumerate(lower)}
    pairs = [(pa[a], pb[b]) for a, b in links if a in pa and b in pb]
    return sum(
        1
        for i, (a1, b1) in enumerate(pairs)
        for a2, b2 in pairs[i + 1 :]
        if (a1 - a2) * (b1 - b2) < 0
    )


def _crossings(layers: list[list[str]], links: list[tuple[str, str]]) -> int:
    return sum(_pair_crossings(a, b, links) for a, b in itertools.pairwise(layers))


def _order_layers(layers: list[list[str]], links: list[tuple[str, str]]) -> list[list[str]]:
    """Barycentre sweeps plus adjacent swaps; keeps the arrangement with fewest crossings."""
    preds: dict[str, list[str]] = {}
    succs: dict[str, list[str]] = {}
    for a, b in links:
        succs.setdefault(a, []).append(b)
        preds.setdefault(b, []).append(a)
    layers = [list(layer) for layer in layers]
    best, best_c = [list(layer) for layer in layers], _crossings(layers, links)

    def sweep(li: int, neighbours: dict[str, list[str]], ref: list[str]) -> None:
        idx = {key: i for i, key in enumerate(ref)}
        cur = {key: i for i, key in enumerate(layers[li])}

        def key(k: str) -> tuple[float, int]:
            near = [idx[n] for n in neighbours.get(k, []) if n in idx]
            return (sum(near) / len(near) if near else float(cur[k]), cur[k])

        layers[li].sort(key=key)

    for it in range(12):
        if it % 2 == 0:
            for li in range(1, len(layers)):
                sweep(li, preds, layers[li - 1])
        else:
            for li in range(len(layers) - 2, -1, -1):
                sweep(li, succs, layers[li + 1])

        def local(li: int) -> int:
            above = _pair_crossings(layers[li - 1], layers[li], links) if li > 0 else 0
            below = (
                _pair_crossings(layers[li], layers[li + 1], links) if li + 1 < len(layers) else 0
            )
            return above + below

        improved = True
        while improved:
            improved = False
            for li, layer in enumerate(layers):
                for i in range(len(layer) - 1):
                    before = local(li)
                    layer[i], layer[i + 1] = layer[i + 1], layer[i]
                    if local(li) < before:
                        improved = True
                    else:
                        layer[i], layer[i + 1] = layer[i + 1], layer[i]
        c = _crossings(layers, links)
        if c < best_c:
            best, best_c = [list(layer) for layer in layers], c
        if best_c == 0:
            break
    return best


def _pack(desired: list[float], sizes: list[float], gaps: list[float]) -> list[float]:
    """Centres closest to `desired` (least squares) that keep order and minimum gaps."""
    offs = [0.0]
    for i in range(1, len(desired)):
        offs.append(offs[-1] + (sizes[i - 1] + sizes[i]) / 2 + gaps[i - 1])
    blocks: list[list[float]] = []  # [sum, count] of pooled values
    for d, o in zip(desired, offs, strict=True):
        blocks.append([d - o, 1.0])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s, c = blocks.pop()
            blocks[-1][0] += s
            blocks[-1][1] += c
    fitted = [b[0] / b[1] for b in blocks for _ in range(int(b[1]))]
    return [f + o for f, o in zip(fitted, offs, strict=True)]


def _straighten(layers: list[list[str]], cross: dict[str, float], size, gap) -> None:
    """Put all bend points of a long edge on one line when their neighbours leave room."""
    where = {k: (li, i) for li, layer in enumerate(layers) for i, k in enumerate(layer)}
    chains: dict[str, list[str]] = {}
    for layer in layers:
        for k in layer:
            if DUMMY in k:
                chains.setdefault(k.split("#")[0], []).append(k)
    for _ in range(3):
        for bends in chains.values():
            lo, hi = -math.inf, math.inf
            for k in bends:
                li, i = where[k]
                layer = layers[li]
                if i > 0:
                    a = layer[i - 1]
                    lo = max(lo, cross[a] + size(a) / 2 + gap(a, k))
                if i + 1 < len(layer):
                    b = layer[i + 1]
                    hi = min(hi, cross[b] - size(b) / 2 - gap(k, b))
            if lo <= hi:
                target = float(np.clip(np.median([cross[k] for k in bends]), lo, hi))
                for k in bends:
                    cross[k] = target


@dataclass
class _MapLayout:
    direction: str
    layers: list[list[str]]
    centre: dict[str, np.ndarray]
    box: dict[str, tuple[float, float]]  # node key -> (w, h); dummies (0, 0)
    span: list[tuple[float, float]]  # per layer: (start, end) along the main axis
    width: float
    height: float
    bands: int = 1  # left-to-right rows of layers, read like lines of text
    # Links from the end of one band to the start of the next: (x right, y gap, x left).
    returns: dict[tuple[str, str], tuple[float, float, float]] = field(default_factory=dict)


def _map_layout(
    direction: str,
    layers: list[list[str]],
    topics: dict[str, _Topic],
    links: list[tuple[str, str]],
    split_gap: bool = False,
) -> _MapLayout:
    lr = direction == "lr"
    real = lambda k: k in topics  # noqa: E731
    # Main-axis extent of each layer and cross-axis size of each node.
    span: list[tuple[float, float]] = []
    pos_main = 0.0
    box: dict[str, tuple[float, float]] = {}
    for layer in layers:
        if lr:
            length = max((topics[k].w for k in layer if real(k)), default=0.6)
            for k in layer:
                box[k] = (length, topics[k].h) if real(k) else (0.0, 0.0)
        else:
            length = max((topics[k].h for k in layer if real(k)), default=0.6)
            for k in layer:
                box[k] = (topics[k].w, topics[k].h) if real(k) else (0.0, 0.0)
        span.append((pos_main, pos_main + length))
        pos_main += length + (LAYER_GAP if lr else TB_LAYER_GAP)

    def cross_size(k: str) -> float:
        return box[k][1] if lr else box[k][0]

    def gap(a: str, b: str) -> float:
        # Split layers stagger their nodes, so edges to the next sub-layer pass between.
        return (SPLIT_GAP if split_gap else NODE_GAP) if real(a) and real(b) else DUMMY_GAP

    preds: dict[str, list[str]] = {}
    succs: dict[str, list[str]] = {}
    for a, b in links:
        succs.setdefault(a, []).append(b)
        preds.setdefault(b, []).append(a)
    cross: dict[str, float] = {}
    for layer in layers:
        placed = _pack(
            [0.0] * len(layer),
            [cross_size(k) for k in layer],
            [gap(a, b) for a, b in itertools.pairwise(layer)],
        )
        shift = (placed[0] + placed[-1]) / 2
        for k, c in zip(layer, placed, strict=True):
            cross[k] = c - shift
    for it in range(10):
        order = range(1, len(layers)) if it % 2 == 0 else range(len(layers) - 2, -1, -1)
        nbrs = preds if it % 2 == 0 else succs
        for li in order:
            layer = layers[li]
            desired = []
            for k in layer:
                # Bend points follow both neighbours, so long edges run straight.
                side = nbrs.get(k, []) if real(k) else preds.get(k, []) + succs.get(k, [])
                near = [cross[n] for n in side]
                desired.append(sum(near) / len(near) if near else cross[k])
            gaps = [gap(a, b) for a, b in itertools.pairwise(layer)]
            for k, c in zip(
                layer, _pack(desired, [cross_size(k) for k in layer], gaps), strict=True
            ):
                cross[k] = c
    _straighten(layers, cross, cross_size, gap)
    lo = min(cross[k] - cross_size(k) / 2 for k in cross)
    hi = max(cross[k] + cross_size(k) / 2 for k in cross)
    centre: dict[str, np.ndarray] = {}
    for li, layer in enumerate(layers):
        mid = sum(span[li]) / 2
        for k in layer:
            c = cross[k] - (lo + hi) / 2
            # Cross axis grows downward in both directions (first in order = top/left).
            centre[k] = np.array([mid, -c]) if lr else np.array([c, -mid])
    main_len = span[-1][1]
    width, height = (main_len, hi - lo) if lr else (hi - lo, main_len)
    return _MapLayout(direction, layers, centre, box, span, width, height)


BAND_GAP = 0.9  # between two bands of a wrapped topic map, plus one track per return
RETURN_PAD = 0.45  # a return route runs this far beside the band it leaves or enters
RETURN_TRACK = 0.2
SPLIT_GAP = 0.7  # node gap in a layer split into staggered sub-layers (room for edges)


def _band_layout(base: _MapLayout, k: int, links: list[tuple[str, str]]) -> _MapLayout:
    """Cut a left-to-right layout into k bands of consecutive layers, stacked downwards.

    A link from the last layer of one band to the first layer of the next returns like a
    line of text: right of its band, down through the gap, left of the next band, in.
    """
    n = len(base.layers)
    ends = [hi for _, hi in base.span]
    total = ends[-1]
    cuts = sorted(
        {min(range(1, n), key=lambda i: abs(ends[i - 1] - total * j / k)) for j in range(1, k)}
    )
    starts = [0, *cuts]
    stops = [*cuts, n]
    band_of = {
        li: b for b, (a, z) in enumerate(zip(starts, stops, strict=True)) for li in range(a, z)
    }
    level = {key: li for li, layer in enumerate(base.layers) for key in layer}
    crossing = [(a, b) for a, b in links if band_of[level[a]] != band_of[level[b]]]
    centre = {key: c.copy() for key, c in base.centre.items()}
    span = list(base.span)
    tops, bottoms, lefts, rights = [], [], [], []
    y = 0.0
    for b, (a, z) in enumerate(zip(starts, stops, strict=True)):
        keys = [key for li in range(a, z) for key in base.layers[li]]
        x0 = base.span[a][0]
        hi = max(base.centre[key][1] + base.box[key][1] / 2 for key in keys)
        lo = min(base.centre[key][1] - base.box[key][1] / 2 for key in keys)
        if b > 0:
            m = sum(1 for p, q in crossing if band_of[level[q]] == b)
            y -= BAND_GAP + 2 * RETURN_PAD + max(m - 1, 0) * RETURN_TRACK
        for key in keys:
            centre[key] = np.array([base.centre[key][0] - x0, base.centre[key][1] - hi + y])
        for li in range(a, z):
            span[li] = (base.span[li][0] - x0, base.span[li][1] - x0)
        tops.append(y)
        y -= hi - lo
        bottoms.append(y)
        lefts.append(0.0)
        rights.append(span[z - 1][1])
    returns: dict[tuple[str, str], tuple[float, float, float]] = {}
    for b in range(1, k):
        group = [(p, q) for p, q in crossing if band_of[level[q]] == b]
        group.sort(key=lambda pq: -centre[pq[0]][1])  # highest source first
        m = len(group)
        for i, (p, q) in enumerate(group):
            x_r = rights[b - 1] + RETURN_PAD + (m - 1 - i) * RETURN_TRACK
            y_g = bottoms[b - 1] - RETURN_PAD - (m - 1 - i) * RETURN_TRACK
            x_l = lefts[b] - RETURN_PAD - i * RETURN_TRACK
            returns[(p, q)] = (x_r, y_g, x_l)
    if returns:
        x_min = min(x_l for _, _, x_l in returns.values())
        x_max = max(x_r for x_r, _, _ in returns.values())
    else:
        x_min, x_max = 0.0, max(rights)
    shift = -(x_min + x_max) / 2
    for key in centre:
        centre[key][0] += shift
    span = [(a + shift, z + shift) for a, z in span]
    returns = {pq: (x_r + shift, y_g, x_l + shift) for pq, (x_r, y_g, x_l) in returns.items()}
    width = x_max - x_min
    return _MapLayout(
        "lr", base.layers, centre, base.box, span, width, -y, bands=k, returns=returns
    )


def _visual_layers(topics: list[_Topic], depth: dict[str, int], split: dict[int, int]):
    """Layer of each topic after splitting some depth levels into sub-layers.

    A split level is cut into runs of consecutive topics (course order), one run per
    sub-layer, so each sub-column still reads top to bottom in teaching order.
    """
    start, layer = {}, 0
    for d in range(max(depth.values()) + 1):
        start[d] = layer
        layer += split.get(d, 1)
    members: dict[int, list[str]] = {}
    for t in topics:
        members.setdefault(depth[t.id], []).append(t.id)
    out = {}
    for d, ids in members.items():
        per = math.ceil(len(ids) / split.get(d, 1))
        for i, tid in enumerate(ids):
            out[tid] = start[d] + i // per
    return out


def _layered(topics: list[_Topic], vlayer: dict[str, int]):
    """Layers with bend points for links that skip layers; links and chains of each edge."""
    layers: list[list[str]] = [[] for _ in range(max(vlayer.values()) + 1)]
    for t in topics:
        layers[vlayer[t.id]].append(t.id)
    links: list[tuple[str, str]] = []
    chains: list[tuple[str, str, list[str]]] = []
    for t in topics:
        for p in t.prereq:
            chain = [p]
            for li in range(vlayer[p] + 1, vlayer[t.id]):
                key = f"{p}{DUMMY}{t.id}#{li}"
                layers[li].append(key)
                chain.append(key)
            chain.append(t.id)
            links += list(itertools.pairwise(chain))
            chains.append((p, t.id, chain))
    return _order_layers(layers, links), links, chains


@dataclass
class _MapChoice:
    layout: _MapLayout
    layers: list[list[str]]
    links: list[tuple[str, str]]
    chains: list
    split: dict[int, int]
    cost: float = 0.0


def _map_cost(layout: _MapLayout, split: dict[int, int], size: str) -> float:
    """Inches of page height the map takes, plus the cost of shrinking and of wrapping."""
    target_w = core.size(size)[0]
    width, height = layout.width * UNIT_IN, layout.height * UNIT_IN
    scale = min(1.0, target_w / width)
    cost = height * max(scale, MIN_SCALE) + 4.0 * (1 - scale)
    if scale < MIN_SCALE:  # overflows the column even at the smallest legible scale
        cost += 2.0 + 20.0 * (MIN_SCALE / scale - 1)
    cost += 0.5 * len(layout.returns) + 0.1 * sum(m - 1 for m in split.values())
    return cost


def _map_choices(topics, depth, by_id, direction: str, size: str) -> list[_MapChoice]:
    """Candidate arrangements: plain, long layers split, long rows wrapped into bands."""
    plain = _layered(topics, {t.id: depth[t.id] for t in topics})
    if direction == "tb":
        return [_MapChoice(_map_layout("tb", plain[0], by_id, plain[1]), *plain, {})]
    choices = [_MapChoice(_map_layout("lr", plain[0], by_id, plain[1]), *plain, {})]
    if direction == "lr":
        return choices
    choices.append(_MapChoice(_map_layout("tb", plain[0], by_id, plain[1]), *plain, {}))
    sizes = {d: sum(1 for t in topics if depth[t.id] == d) for d in set(depth.values())}
    longest = max(sizes.values())
    splits = [{}]
    for parts in (2, 3, 4):
        cap = math.ceil(longest / parts)
        split = {d: math.ceil(n / cap) for d, n in sizes.items() if n > cap}
        if split and split not in splits:
            splits.append(split)
    for split in splits:
        layered = plain if not split else _layered(topics, _visual_layers(topics, depth, split))
        base = _map_layout("lr", layered[0], by_id, layered[1], split_gap=bool(split))
        if split:
            choices.append(_MapChoice(base, *layered, split))
        for k in range(2, min(len(layered[0]), 6) + 1):
            choices.append(_MapChoice(_band_layout(base, k, layered[1]), *layered, split))
    return choices


def topic_map(
    course_dir: Path, *, size: str = "full", direction: str = "auto", alt: str | None = None
) -> core.Figure:
    """The course topic map: a layered DAG of the topics in course.yaml.

    Layers follow prerequisite depth, left to right. With direction='auto' the map takes
    the arrangement that needs the least page height at a legible scale: plain, top to
    bottom, long levels split into staggered sub-columns (flat or fan-shaped courses), or
    long rows wrapped into bands read like lines of text (prerequisite chains);
    direction='lr' or 'tb' forces a plain layout. Box height grows with the topic weight,
    focus topics have a coloured frame and bold title, skipped topics are muted and dashed.
    """
    if direction not in ("auto", "lr", "tb"):
        raise ValueError("direction must be 'auto', 'lr' or 'tb'")
    topics, focus, skip = _load_topics(Path(course_dir))
    depth = _depths(topics)
    by_id = {t.id: t for t in topics}
    w_max = max((t.weight for t in topics), default=0.0)
    for t in topics:
        t.text = _wrap_title(t.title, t.font_weight)
    text_h = max(text_size(t.text, TOPIC_PT, math=False, weight=t.font_weight)[1] for t in topics)
    base_h = text_h + 2 * NODE_PAD_Y
    for t in topics:
        tw = text_size(t.text, TOPIC_PT, math=False, weight=t.font_weight)[0]
        t.w = tw + 2 * NODE_PAD_X
        t.h = base_h * (1 + WEIGHT_EXTRA * (t.weight / w_max if w_max > 0 else 0.0))

    choices = _map_choices(topics, depth, by_id, direction, size)
    for choice in choices:
        choice.cost = _map_cost(choice.layout, choice.split, size)
    best = min(choices, key=lambda c: c.cost)  # the first of equals: the plainest
    layout, links, chains = best.layout, best.links, best.chains
    crossings = _crossings(best.layers, links)
    if direction != "auto":
        reason = "requested"
    elif best is choices[0]:
        reason = "fits"
    elif best.layout.bands > 1:
        reason = f"wrapped into {best.layout.bands} rows"
    elif best.split:
        reason = "long layers split"
    else:
        reason = "left-to-right too wide"

    sheet = Sheet()
    _draw_map(sheet, layout, by_id, chains)
    left = min(layout.centre[k][0] - layout.box[k][0] / 2 for k in by_id)
    bottom = min(
        [layout.centre[k][1] - layout.box[k][1] / 2 for k in layout.centre]
        + [y_g for _, y_g, _ in layout.returns.values()]
    )  # below every box, bend point and return route
    _draw_legend(sheet, left, bottom - 0.6, focus, skip)

    facts = {
        "template": "graph.topic_map",
        "direction": layout.direction,
        "direction_reason": reason,
        # Topics by prerequisite depth, each level in drawing order.
        "layers": [
            [k for layer in layout.layers for k in layer if k in by_id and depth[k] == d]
            for d in range(max(depth.values()) + 1)
        ],
        "order": [k for layer in layout.layers for k in layer if k in by_id],
        "depth": depth,
        # How the drawing wraps: rows of layers read like text, depth levels split into
        # staggered sub-layers, and the drawn size in inches before scaling.
        "wrap": {
            "bands": layout.bands,
            "split": {str(d): m for d, m in sorted(best.split.items())},
            "returns": len(layout.returns),
        },
        "size_in": [round(layout.width * UNIT_IN, 3), round(layout.height * UNIT_IN, 3)],
        "crossings": crossings,
        "edges": [[p, t] for p, t, _ in chains],
        "focus": focus,
        "skip": skip,
        "nodes": {
            t.id: {
                "title": t.title,
                "lines": t.text.split("\n"),
                "weight": t.weight,
                "status": t.status,
                "box": _round(layout.box[t.id]),
                "xy": _round(layout.centre[t.id]),
            }
            for t in topics
        },
        "node_overlaps": _node_overlaps(layout, by_id),
    }
    if alt is None:
        alt = _map_alt(facts, by_id)
    return sheet.render(size, alt, facts)


def _node_overlaps(layout: _MapLayout, topics: dict[str, _Topic]) -> int:
    rects = [_rect(layout.centre[k], *layout.box[k]) for k in topics]
    return _count_overlaps(rects)


def _ports(
    layout: _MapLayout, chains, topics
) -> dict[tuple[str, str], tuple[np.ndarray, np.ndarray]]:
    """Exit and entry point of every link, spread along the node side by neighbour order."""
    lr = layout.direction == "lr"
    axis = 1 if lr else 0
    outgoing: dict[str, list[str]] = {}
    incoming: dict[str, list[str]] = {}
    for _, _, chain in chains:
        for a, b in itertools.pairwise(chain):
            outgoing.setdefault(a, []).append(b)
            incoming.setdefault(b, []).append(a)
    level = {k: li for li, layer in enumerate(layout.layers) for k in layer}

    def offsets(node: str, others: list[str]) -> dict[str, float]:
        if node not in topics:
            return dict.fromkeys(others, 0.0)
        side = layout.box[node][1] if lr else layout.box[node][0]
        ordered = sorted(others, key=lambda o: layout.centre[o][axis], reverse=lr)
        m = len(ordered)
        step = min(PORT_GAP, max(side - 2 * PORT_END, 0.0) / max(m - 1, 1))  # whole side
        sign = -1 if lr else 1  # first neighbour (top / left) gets the top / left port
        return {o: sign * (i - (m - 1) / 2) * step for i, o in enumerate(ordered)}

    def face(node: str, out: bool) -> float:
        li = level[node]
        start, end = layout.span[li]
        if node in topics:
            half = (layout.box[node][0] if lr else layout.box[node][1]) / 2
            mid = layout.centre[node][0] if lr else -layout.centre[node][1]
            start, end = mid - half, mid + half
        return end if out else start

    out_off = {k: offsets(k, v) for k, v in outgoing.items()}
    in_off = {k: offsets(k, v) for k, v in incoming.items()}
    ports = {}
    for a, bs in outgoing.items():
        for b in bs:
            ca, cb = layout.centre[a], layout.centre[b]
            if lr:
                p = np.array([face(a, True), ca[1] + out_off[a][b]])
                q = np.array([face(b, False), cb[1] + in_off[b][a]])
            else:
                p = np.array([ca[0] + out_off[a][b], -face(a, True)])
                q = np.array([cb[0] + in_off[b][a], -face(b, False)])
            ports[(a, b)] = (p, q)
    return ports


def _draw_map(sheet: Sheet, layout: _MapLayout, topics: dict[str, _Topic], chains) -> None:
    lr = layout.direction == "lr"
    ports = _ports(layout, chains, topics)
    curve = elm.ArcZ if lr else elm.ArcN
    for p_id, t_id, chain in chains:
        muted = topics[p_id].status == "skip" or topics[t_id].status == "skip"
        style = {"color": MUTED, "ls": "--"} if muted else {"color": FG}
        # Pieces of the edge: curves between layers, straight runs through bend points;
        # collinear runs merge into one line so a long edge is one clean stroke.
        pieces: list[list] = []
        for i, (a, b) in enumerate(itertools.pairwise(chain)):
            p, q = ports[(a, b)]
            if i > 0:
                pieces.append(["line", ports[(chain[i - 1], a)][1], p])
            if (a, b) in layout.returns:  # to the next band: right, down, left, in
                x_r, y_g, x_l = layout.returns[(a, b)]
                corners = [p, _v(x_r, p[1]), _v(x_r, y_g), _v(x_l, y_g), _v(x_l, q[1]), q]
                pieces += [["line", u, v] for u, v in itertools.pairwise(corners)]
                continue
            straight = abs(p[1] - q[1]) < 1e-9 if lr else abs(p[0] - q[0]) < 1e-9
            pieces.append(["line" if straight else "curve", p, q])
        merged: list[list] = []
        for piece in pieces:
            if np.allclose(piece[1], piece[2]):
                continue
            joins = merged and merged[-1][0] == "line" and np.allclose(merged[-1][2], piece[1])
            if joins and piece[0] == "line":
                d1, d2 = merged[-1][2] - merged[-1][1], piece[2] - piece[1]
                joins = abs(d1[0] * d2[1] - d1[1] * d2[0]) < 1e-9 and np.dot(d1, d2) > 0
            if joins and piece[0] == "line":
                merged[-1][2] = piece[2]
            else:
                merged.append(piece)
        for i, (kind, p, q) in enumerate(merged):
            arrow = "->" if i == len(merged) - 1 else None
            seg = (
                curve(k=0.5, arrow=arrow, **ARROW)
                if kind == "curve"
                else elm.Line(arrow=arrow, **ARROW)
            )
            sheet.add(seg.at(p).to(q).style(lw=0.8, **style))
    for tid, t in topics.items():
        w, h = layout.box[tid]
        node = flow.RoundBox(w=w, h=h, cornerradius=0.18).at(layout.centre[tid]).anchor("center")
        if t.status == "focus":
            node.style(color=color("c1"), lw=1.6, fill=BG)
        elif t.status == "skip":
            node.style(color=MUTED, lw=0.9, ls="--", fill=BG)
        else:
            node.style(color=FG, lw=0.9, fill=BG)
        sheet.add(node)
        sheet.text(
            layout.centre[tid],
            t.text,
            size=TOPIC_PT,
            math=False,
            weight=t.font_weight,
            color=MUTED if t.status == "skip" else FG,
        )


def _draw_legend(sheet: Sheet, x: float, y: float, focus: list[str], skip: list[str]) -> None:
    de = core.locale() == "de"
    entries = []
    if focus:
        entries.append(({"color": color("c1"), "lw": 1.6}, "Schwerpunkt" if de else "focus"))
    if skip:
        entries.append(
            ({"color": MUTED, "lw": 0.9, "ls": "--"}, "übersprungen" if de else "skipped")
        )
    for style, label in entries:
        sheet.add(
            flow.RoundBox(w=0.7, h=0.4, cornerradius=0.1)
            .at((x, y))
            .anchor("W")
            .style(fill=BG, **style)
        )
        sheet.text((x + 0.85, y), label, size=LEGEND_PT, ha="left", math=False)
        x += 0.85 + text_size(label, LEGEND_PT, math=False)[0] + 0.6
    note = "Höhe der Box: Gewichtung" if de else "box height: weight"
    sheet.text((x, y), note, size=LEGEND_PT, ha="left", math=False, color=MUTED)


def _map_alt(facts: dict, topics: dict[str, _Topic]) -> str:
    de = core.locale() == "de"
    title = {k: t.title for k, t in topics.items()}
    levels = "; ".join(
        f"{i + 1}: " + ", ".join(title[k] for k in layer) for i, layer in enumerate(facts["layers"])
    )
    if de:
        text = (
            f"Themenkarte mit {len(topics)} Themen in {len(facts['layers'])} Ebenen nach "
            f"Voraussetzungen ({levels}). Pfeile führen von einer Voraussetzung zum Thema, "
            "das darauf aufbaut; höhere Boxen haben mehr Gewicht."
        )
        if facts["focus"]:
            text += " Schwerpunkte: " + ", ".join(title[k] for k in facts["focus"]) + "."
        if facts["skip"]:
            text += " Übersprungen: " + ", ".join(title[k] for k in facts["skip"]) + "."
        return text
    text = (
        f"Topic map with {len(topics)} topics in {len(facts['layers'])} levels of "
        f"prerequisites ({levels}). Arrows lead from a prerequisite to the topic that builds "
        "on it; taller boxes carry more weight."
    )
    if facts["focus"]:
        text += " Focus: " + ", ".join(title[k] for k in facts["focus"]) + "."
    if facts["skip"]:
        text += " Skipped: " + ", ".join(title[k] for k in facts["skip"]) + "."
    return text


__all__ = ["flowchart", "state_machine", "topic_map"]
