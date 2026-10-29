"""State machines, flowcharts and the course topic map, drawn with `schemdraw.flow`.

    graph.state_machine(['S0', 'S1'], [('S0', 'S1', '1'), ('S1', 'S0', '0')], initial='S0')
    graph.flowchart([('a', 'start', 'Start'), ('b', 'process', 'x = 0')], [('a', 'b')])
    graph.topic_map(course_dir)   # `fig:topic-map` of the overview, from course.yaml

Positions are computed here (ring/row/grid layouts, layered graphs, label placement that
avoids states, edges and other labels); schemdraw only draws. Labels containing `$`, `_`,
`^` or a backslash are TeX math, anything else is plain text.
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
from studykit.figures.block import FONT_PT, LABEL_PT, Sheet, text_size
from studykit.figures.palette import BG, FG, MUTED, color

ARROW = {"arrowwidth": 0.15, "arrowlength": 0.25}

# ---------------------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------------------


def _rich(text: str) -> tuple[str, bool]:
    """(text, parse_math): TeX when it has $ _ ^ or a backslash, plain text otherwise."""
    text = str(text).strip()
    if "$" in text:
        return text, True
    if any(ch in text for ch in "_^\\"):
        return f"${core.localize_tex(text)}$", True
    return text, False


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


def _route_edge(
    edge: _Edge, pos: dict[str, np.ndarray], r: float, paired: bool, looped: set[str]
) -> None:
    """Straight if nothing is in the way, else the flattest arc that clears other states."""
    p0, p2 = pos[edge.src], pos[edge.dst]
    d = p2 - p0
    perp = np.array([-d[1], d[0]])
    others = [
        (c, r + CLEAR + (LOOP_ROOM if name in looped else 0.0))
        for name, c in pos.items()
        if name not in (edge.src, edge.dst)
    ]
    ks = (0.2, 0.32, 0.45, 0.6) if paired else (0.0, 0.2, -0.2, 0.32, -0.32, 0.45, -0.45, 0.6)
    chosen = ks[-1]
    for k in ks:
        p1 = p0 + d / 2 + k * perp
        pts = _quad(p0, p1, p2, np.linspace(0.05, 0.95, 48))
        if all(np.min(np.linalg.norm(pts - c, axis=1)) > clear for c, clear in others):
            chosen = k
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


def _free_direction(occupied: list[float], prefer: list[tuple[float, float]]) -> float:
    best, best_score = 90.0, -math.inf
    for th in range(0, 360, 5):
        gap = min((_angdiff(th, a) for a in occupied), default=180.0)
        score = min(gap, 90.0) + sum(w * math.cos(math.radians(th - p)) for p, w in prefer)
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
    far = float(np.linalg.norm(centre - c) + radius)
    return a, b, radius, ring, far


def _extent_along(direction: np.ndarray, w: float, h: float) -> float:
    return (abs(direction[0]) * w + abs(direction[1]) * h) / 2


def _rect_points_dist(rect: Rect, pts: np.ndarray) -> float:
    if len(pts) == 0:
        return math.inf
    dx = np.maximum(np.maximum(rect[0] - pts[:, 0], pts[:, 0] - rect[2]), 0.0)
    dy = np.maximum(np.maximum(rect[1] - pts[:, 1], pts[:, 1] - rect[3]), 0.0)
    return float(np.min(np.hypot(dx, dy)))


NEAR = 0.35  # labels keep this distance from edges they do not belong to


def _place_edge_label(
    edge: _Edge,
    w: float,
    h: float,
    pos: dict[str, np.ndarray],
    r: float,
    placed: list[Rect],
    others: list[np.ndarray],
) -> np.ndarray:
    """Beside the edge (outside of its bend), clear of states, labels and other edges."""
    sides = [1.0, -1.0] if abs(edge.k) < 1e-9 else [math.copysign(1.0, edge.k)]
    best, best_score = None, math.inf
    index = 0
    for t in (0.5, 0.42, 0.58, 0.34, 0.66):
        pt = _quad(edge.q0, edge.q1, edge.q2, t)[0]
        tan = _quad_tangent(edge.q0, edge.q1, edge.q2, t)
        tan = tan / (np.linalg.norm(tan) or 1.0)
        normal = np.array([-tan[1], tan[0]])
        for side in sides:
            n = side * normal
            centre = pt + n * (LABEL_GAP + _extent_along(n, w, h))
            rect = _rect(centre, w, h)
            score = 0.04 * index
            index += 1
            for c in pos.values():
                gap = _rect_circle_gap(rect, c, r)
                if gap < 0.06:
                    score += 10 + 20 * (0.06 - gap)
            score += sum(25 * _overlap(rect, other) for other in placed)
            score += 2.0 * _inside(rect, edge.samples)
            for path in others:
                score += 2.0 * _inside(rect, path)
                score += 4.0 * max(NEAR - _rect_points_dist(rect, path), 0.0)
            if score < best_score:
                best, best_score = centre, score
    return best


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
    occupied: dict[str, list[float]] = {n: [] for n in names}
    for (src, dst), e in edges.items():
        if src == dst:
            continue
        _route_edge(e, pos, r, paired=(dst, src) in edges, looped=looped)
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

    paths: list[np.ndarray] = []
    placed: list[Rect] = []
    loops = {}
    for (src, dst), e in edges.items():
        if src != dst:
            continue
        theta = _free_direction(occupied[src], [(outward(src), 40.0), (90.0, 8.0)])
        occupied[src] += [theta, theta + LOOP_HALF, theta - LOOP_HALF]
        a, b, radius, ring, far = _loop_geometry(pos[src], r, theta)
        e.route, e.direction, e.q0, e.q2, e.samples = "loop", theta, a, b, ring
        loops[src] = (a, b, radius)
        if e.text:
            w, h = label_sizes[(src, dst)]
            u = _unit(theta)
            e.label_xy = pos[src] + u * (far + LABEL_GAP + _extent_along(u, w, h))
            placed.append(_rect(e.label_xy, w, h))
    init_dir = None
    if initial is not None:
        init_dir = _free_direction(
            occupied[initial], [(180.0, 30.0), (outward(initial), 0.0 if flat else 10.0)]
        )
        u = _unit(init_dir)
        start = pos[initial] + u * (r + INIT_LEN)
        paths.append(np.linspace(start, pos[initial] + u * r, 12))
    for e in edges.values():
        paths.append(e.samples)
    for key, e in edges.items():
        if e.route != "loop" and e.text:
            w, h = label_sizes[key]
            others = [p for p in paths if p is not e.samples]
            e.label_xy = _place_edge_label(e, w, h, pos, r, placed, others)
            placed.append(_rect(e.label_xy, w, h))

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
                "label_xy": _round(e.label_xy) if e.label_xy is not None else None,
            }
            for e in edges.values()
        ],
        "initial": initial,
        "accepting": accepting,
        "reachable": reachable,
        "unreachable": [n for n in names if reachable is not None and n not in reachable],
        "radius": round(r, 3),
        "spacing": round(spacing, 3),
        "label_overlaps": _count_overlaps(placed),
        # Smallest distance from any label box to any state (negative = label on a state).
        "label_state_gap": round(
            min(
                (_rect_circle_gap(rect, c, r) for rect in placed for c in pos.values()), default=0.0
            ),
            3,
        ),
    }
    if alt is None:
        alt = _state_alt(kind, names, outputs, trans, initial, accepting)
    return sheet.render(size, alt, facts)


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
    states = ", ".join(
        f"{n} ({'Ausgabe' if de else 'output'} {outputs[n]})" if outputs.get(n) else n
        for n in names
    )
    arrows = "; ".join(f"{s} → {d}" + (f" ({lbl})" if lbl else "") for s, d, lbl in trans)
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


def _flow_text(text: str) -> tuple[str, bool]:
    return (text, True) if "$" in text else (text, False)


def _node_size(node: _Node) -> tuple[float, float]:
    shown, math_ = _flow_text(node.text)
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
    taken: set[tuple[int, int]] = set()
    placed: set[str] = set()
    for u in topo:
        node = by_id[u]
        if u not in placed:
            col = 0
            while (node.layer, col) in taken:
                col += 1
            node.col = col
            taken.add((node.layer, col))
            placed.add(u)
        children = [edges[i][1] for i in out_edges[u] if i not in back]
        j = 0
        for v in children:
            if v in placed:
                continue
            child = by_id[v]
            col = node.col + j
            while (child.layer, col) in taken:
                col += 1
            child.col = col
            taken.add((child.layer, col))
            placed.add(v)
            j += 1
    return back


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
    down; further branches of a decision go right; edges back to an earlier node (loops)
    run up on the left and join the target from above.
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
    col_x = np.cumsum(
        [0.0] + [col_w[c] / 2 + col_w[c + 1] / 2 + FLOW_H_GAP for c in range(cols - 1)]
    )
    row_y = -np.cumsum(
        [0.0] + [row_h[r] / 2 + row_h[r + 1] / 2 + FLOW_V_GAP for r in range(rows - 1)]
    )
    for n in nodes_:
        n.xy = np.array([col_x[n.col], row_y[n.layer]])
    cells = {(n.layer, n.col) for n in nodes_}

    def lane(col: int, side: str) -> float:
        edge = col_x[col] + (col_w[col] / 2 if side == "E" else -col_w[col] / 2)
        return edge + (FLOW_H_GAP / 2 if side == "E" else -FLOW_H_GAP / 2)

    channel_targets: dict[int, list[str]] = {}
    lane_use: dict[tuple[int, str], int] = {}

    def channel_above(v: _Node) -> float:
        targets = channel_targets.setdefault(v.layer, [])
        if v.id not in targets:
            targets.append(v.id)
        i = targets.index(v.id)
        offset = (0, TRACK, -TRACK, 2 * TRACK, -2 * TRACK)[min(i, 4)]
        return row_y[v.layer] + row_h[v.layer] / 2 + FLOW_V_GAP / 2 + offset

    def channel_below(u: _Node) -> float:
        return row_y[u.layer] - row_h[u.layer] / 2 - FLOW_V_GAP / 2

    def lane_x(col: int, side: str) -> float:
        i = lane_use.get((col, side), 0)
        lane_use[(col, side)] = i + 1
        return lane(col, side) + (i * TRACK if side == "E" else -i * TRACK)

    def column_clear(col: int, lo: int, hi: int) -> bool:
        return all((layer, col) not in cells for layer in range(lo + 1, hi))

    used_ports: dict[str, set[str]] = {n.id: set() for n in nodes_}
    routes = []
    for i, (u_id, v_id, label) in enumerate(edges_):
        u, v = by_id[u_id], by_id[v_id]
        free = [p for p in ("S", "E", "W") if p not in used_ports[u_id]]
        is_back = i in back
        if u.kind != "decision":
            port = "S"
        elif is_back:
            port = "W" if "W" in free else ("E" if "E" in free else "S")
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
            side = "E" if port == "E" else "W"
            x_l = lane_x(u.col, side)
            y_c = channel_above(v)
            if port == "S":
                pts = [start, (u.xy[0], channel_below(u)), (x_l, channel_below(u))]
            else:
                pts = [start, (x_l, start[1])]
            pts += [(x_l, y_c), (v.xy[0], y_c), end]
        elif port == "S" and v.col == u.col and column_clear(u.col, u.layer, v.layer):
            pts = [start, end]
        elif port == "S":
            y_c = channel_above(v)
            if column_clear(u.col, u.layer, v.layer):
                pts = [start, (u.xy[0], y_c), (v.xy[0], y_c), end]
            else:
                x_l = lane_x(u.col, "E")
                y_b = channel_below(u)
                pts = [start, (u.xy[0], y_b), (x_l, y_b), (x_l, y_c), (v.xy[0], y_c), end]
        else:
            step = 1 if port == "E" else -1
            row_free = all(
                (u.layer, c) not in cells for c in range(u.col + step, v.col + step, step)
            )
            if row_free and column_clear(v.col, u.layer - 1, v.layer) and v.col != u.col:
                pts = [start, (v.xy[0], start[1]), end]
            else:
                x_l = lane_x(u.col, port)
                y_c = channel_above(v)
                pts = [start, (x_l, start[1]), (x_l, y_c), (v.xy[0], y_c), end]
        pts = [np.asarray(p, dtype=float) for p in pts]
        routes.append(
            {"src": u_id, "dst": v_id, "label": label, "port": port, "back": is_back, "pts": pts}
        )

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
            shown, math_ = _flow_text(route["label"])
            if side == "S":
                sheet.text(p + _v(0.1, -0.06), shown, ha="left", va="top", math=math_)
            elif side == "E":
                sheet.text(p + _v(0.08, 0.06), shown, ha="left", va="bottom", math=math_)
            else:
                sheet.text(p + _v(-0.08, 0.06), shown, ha="right", va="bottom", math=math_)
    for n in nodes_:
        sheet.add(_node_element(n).fill(BG))
        shown, math_ = _flow_text(n.text)
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
    }
    if alt is None:
        alt = _flow_alt(nodes_, edges_)
    return sheet.render(size, alt, facts)


def _flow_alt(nodes: list[_Node], edges: list[tuple[str, str, str]]) -> str:
    de = core.locale() == "de"
    by_id = {n.id: n for n in nodes}
    steps = "; ".join(
        f"{by_id[u].text.replace(chr(10), ' ')} → {by_id[v].text.replace(chr(10), ' ')}"
        + (f" ({lbl})" if lbl else "")
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


def _map_layout(
    direction: str, layers: list[list[str]], topics: dict[str, _Topic], links: list[tuple[str, str]]
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
        return NODE_GAP if real(a) and real(b) else DUMMY_GAP

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


def topic_map(
    course_dir: Path, *, size: str = "full", direction: str = "auto", alt: str | None = None
) -> core.Figure:
    """The course topic map: a layered DAG of the topics in course.yaml.

    Layers follow prerequisite depth (left to right; top to bottom when that fits the
    page much better, or with direction='tb'). Box height grows with the topic weight,
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

    # Layers with bend points for edges that skip layers.
    n_layers = max(depth.values()) + 1
    layers: list[list[str]] = [[] for _ in range(n_layers)]
    for t in topics:
        layers[depth[t.id]].append(t.id)
    links: list[tuple[str, str]] = []
    chains: list[tuple[str, str, list[str]]] = []
    for t in topics:
        for p in t.prereq:
            chain = [p]
            for li in range(depth[p] + 1, depth[t.id]):
                key = f"{p}{DUMMY}{t.id}#{li}"
                layers[li].append(key)
                chain.append(key)
            chain.append(t.id)
            links += list(itertools.pairwise(chain))
            chains.append((p, t.id, chain))
    layers = _order_layers(layers, links)
    crossings = _crossings(layers, links)

    target_w = core.size(size)[0] * 72 / 18.0  # drawing units at natural scale
    layout = _map_layout("lr" if direction != "tb" else "tb", layers, by_id, links)
    reason = "requested" if direction != "auto" else "fits"
    if direction == "auto" and layout.width * 0.72 > target_w:
        tb = _map_layout("tb", layers, by_id, links)
        if tb.width < layout.width:
            layout, reason = tb, "left-to-right too wide"

    sheet = Sheet()
    _draw_map(sheet, layout, by_id, chains)
    left = min(layout.centre[k][0] - layout.box[k][0] / 2 for k in by_id)
    bottom = min(layout.centre[k][1] - layout.box[k][1] / 2 for k in by_id)
    _draw_legend(sheet, left, bottom - 0.6, focus, skip)

    facts = {
        "template": "graph.topic_map",
        "direction": layout.direction,
        "direction_reason": reason,
        "layers": [[k for k in layer if k in by_id] for layer in layout.layers],
        "order": [k for layer in layout.layers for k in layer if k in by_id],
        "depth": depth,
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
        step = min(PORT_GAP, max(side - 0.3, 0.0) / max(m, 1))
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
            straight = abs(p[1] - q[1]) < 1e-9 if lr else abs(p[0] - q[0]) < 1e-9
            pieces.append(["line" if straight else "curve", p, q])
        merged: list[list] = []
        for piece in pieces:
            if np.allclose(piece[1], piece[2]):
                continue
            joins = merged and merged[-1][0] == "line" and np.allclose(merged[-1][2], piece[1])
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
