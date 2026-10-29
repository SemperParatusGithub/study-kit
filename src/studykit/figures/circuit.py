"""Circuit schematics in IEC / DIN EN 60617 style, drawn with schemdraw onto house axes.

Symbols follow the European university convention: resistor = rectangle, inductor = filled
rectangle (or IEC arcs), capacitor = two plates, ideal voltage source = circle with the
conductor running through it, ideal current source = circle with a bar across the conductor,
operational amplifier = DIN box with ``▷ ∞``. Reference arrows (Zählpfeile) are drawn as
arrows beside an element for voltages (`zaehlpfeil_u`) and as arrowheads on a wire for
currents (`zaehlpfeil_i`); a voltage arrow points from the + to the - reference node.

Templates (`voltage_divider`, `rc`, `rl`, `rlc`, `opamp`, `bridge`) take component values as
strings with units (``R1='4.7 kΩ'``), plain numbers in SI units (``C=1e-7``) or symbols
(``R2='2R'``). Their facts list every component with its value, SI value and the two nodes it
connects, every reference arrow with its nodes, and derived numbers (gain, cut-off frequency)
so a verifier can check the figure against an exercise.

The escape hatch for circuits no template covers is `drawing`:

    with circuit.drawing(alt="...") as c:
        r = c.resistor("R_1", "1 kΩ", nodes=("1", "2")).right()
        c.capacitor("C", "10 nF", nodes=("2", "0")).down()
        circuit.zaehlpfeil_u(r, "U_1")
    return c.figure
"""

from __future__ import annotations

import dataclasses
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

import schemdraw
import schemdraw.elements as elm
from schemdraw.elements.elements import Element, Element2Term, gap
from schemdraw.segments import Segment, SegmentCircle, SegmentPoly, SegmentText
from schemdraw.util import Point

from studykit.figures import core
from studykit.figures.palette import FG, ROLES

# Length of a two-terminal element (body plus leads) in drawing units.
UNIT = 2.5

# Per figure size: inches per drawing unit (upper bound), label font size, stroke width.
STYLE: dict[str, dict[str, float]] = {
    "col": {"ipu": 0.34, "fontsize": 9, "lw": 1.1},
    "half": {"ipu": 0.28, "fontsize": 8, "lw": 1.0},
    "full": {"ipu": 0.38, "fontsize": 9, "lw": 1.2},
    "cs": {"ipu": 0.22, "fontsize": 7, "lw": 0.9},
}
MIN_IPU = 0.12
FONT = "DejaVu Sans"

# Reference arrow geometry (drawing units).
U_HEAD = (0.24, 0.13)  # length, width
I_HEAD = (0.3, 0.2)
LABEL_GAP = 0.12

# --------------------------------------------------------------------------------------
# Values with units
# --------------------------------------------------------------------------------------

PREFIXES: dict[str, int] = {
    "p": -12,
    "n": -9,
    "µ": -6,
    "μ": -6,
    "u": -6,
    "m": -3,
    "": 0,
    "k": 3,
    "M": 6,
    "G": 9,
}
PREFIX_TEX = {"µ": r"\mu", "μ": r"\mu", "u": r"\mu"}
ENG_PREFIX = {-12: "p", -9: "n", -6: "µ", -3: "m", 0: "", 3: "k", 6: "M", 9: "G"}
# Canonical unit -> TeX; aliases map onto canonical units.
UNITS: dict[str, str] = {"Ω": r"\Omega", "F": "F", "H": "H", "V": "V", "A": "A", "Hz": "Hz"}
# U+2126 OHM SIGN looks like the Greek capital omega U+03A9 but is a different code point.
UNIT_ALIASES = {"\u2126": "Ω", "Ohm": "Ω", "ohm": "Ω"}
KIND_UNIT = {
    "resistor": "Ω",
    "capacitor": "F",
    "inductor": "H",
    "voltage_source": "V",
    "current_source": "A",
}
_NUMBER = re.compile(r"^\s*(?P<num>[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?)\s*(?P<unit>\S*)\s*$")

Value = str | float | int | None


@dataclass(frozen=True)
class Quantity:
    """A component value: what the user wrote, its SI value and how the figure shows it."""

    text: str  # as given (strings) or generated (numbers), e.g. "4.7 kΩ"
    si: float | None  # None for symbolic values such as "2R"
    unit: str  # canonical unit, e.g. "Ω"; "" for symbolic values
    tex: str  # TeX without dollars, localized, e.g. r"4{,}7\,\mathrm{k\Omega}"

    @property
    def plain(self) -> str:
        """Readable text for alt text, with a decimal comma in German figures."""
        if self.si is None:
            return self.text
        return self.text.replace(".", ",") if core.locale() == "de" else self.text


def _unit_tex(prefix: str, unit: str) -> str:
    body = UNITS[unit]
    if prefix in PREFIX_TEX:
        return rf"{PREFIX_TEX[prefix]}\mathrm{{{body}}}"
    return rf"\mathrm{{{prefix}{body}}}"


def _split_unit(token: str, expected: str) -> tuple[str, str]:
    """'kΩ' -> ('k', 'Ω'); '' -> ('', expected)."""
    if not token:
        return "", expected
    for alias in sorted([*UNITS, *UNIT_ALIASES], key=len, reverse=True):
        if token.endswith(alias):
            prefix = token[: -len(alias)]
            unit = UNIT_ALIASES.get(alias, alias)
            if prefix in PREFIXES:
                return prefix, unit
    raise ValueError(f"cannot read unit {token!r}; use e.g. 'kΩ', 'nF', 'mH', 'V', 'mA'")


def _mantissa_tex(num: str) -> str:
    num = num.replace(",", ".")
    if "e" in num.lower():
        mant, exp = re.split(r"[eE]", num)
        return core.localize_tex(rf"{mant}\cdot 10^{{{int(exp)}}}")
    return core.localize_tex(num)


def quantity(value: Value, kind: str) -> Quantity | None:
    """Parse a component value for a component kind (see KIND_UNIT).

    '4.7 kΩ' and '4,7 kΩ' -> 4700 Ω; 1e-7 (a number, SI units) -> '100 nF';
    anything else ('R', '2R', 'R_0') is a symbolic value shown as TeX.
    """
    if value is None:
        return None
    expected = KIND_UNIT[kind]
    if isinstance(value, bool):
        raise TypeError(f"{kind} value must be a string or a number, not {value!r}")
    if isinstance(value, int | float):
        return _from_number(float(value), expected)
    match = _NUMBER.match(value)
    known = (*UNITS, *UNIT_ALIASES)
    if not match or (match["unit"] and not match["unit"].endswith(known)):
        # Symbolic: 'R', '2R', 'R_0' (a token that ends in no unit is a symbol, not a unit).
        return Quantity(text=value.strip(), si=None, unit="", tex=value.strip())
    prefix, unit = _split_unit(match["unit"], expected)
    if unit != expected:
        raise ValueError(f"{kind} value {value!r} has unit {unit}, expected {expected}")
    si = float(match["num"].replace(",", ".")) * 10.0 ** PREFIXES[prefix]
    tex = rf"{_mantissa_tex(match['num'])}\,{_unit_tex(prefix, unit)}"
    text = f"{match['num'].replace(',', '.')} {prefix}{unit}"
    return Quantity(text=text, si=si, unit=unit, tex=tex)


def _from_number(value: float, unit: str) -> Quantity:
    if value == 0 or not math.isfinite(value):
        exp3 = 0
    else:
        exp3 = int(math.floor(math.log10(abs(value)) / 3) * 3)
        exp3 = max(min(exp3, 9), -12)
    mant = value / 10.0**exp3
    if abs(float(f"{mant:.3g}")) >= 1000 and exp3 < 9:
        exp3 += 3
        mant = value / 10.0**exp3
    prefix = ENG_PREFIX[exp3]
    mant_text = f"{mant:.3g}"
    tex = rf"{core.fmt_number(mant, 3)}\,{_unit_tex(prefix, unit)}"
    return Quantity(text=f"{mant_text} {prefix}{unit}", si=value, unit=unit, tex=tex)


def plain_name(symbol: str) -> str:
    """TeX symbol -> plain identifier: 'R_1' -> 'R1', 'U_\\mathrm{e}' -> 'Ue'."""
    text = re.sub(r"\\(mathrm|text|underline)\s*", "", symbol)
    return re.sub(r"[\\{}_\s$]", "", text)


def value_label(symbol: str, q: Quantity | None, stacked: bool = False) -> str:
    """'$R_1 = 4{,}7\\,\\mathrm{k\\Omega}$' or '$R_1$' when there is no value.

    stacked=True puts a numeric value on a second line under the symbol, for tight spots.
    """
    if q is None:
        return f"${symbol}$"
    if stacked and q.si is not None:
        return f"${symbol}$\n${q.tex}$"
    return f"${symbol} = {q.tex}$"


# --------------------------------------------------------------------------------------
# DIN EN 60617 elements
# --------------------------------------------------------------------------------------

# Absolute label side -> schemdraw's element-relative location for vertical elements.
_VERTICAL_LOC = {"left": "top", "right": "bottom", "top": "right", "bottom": "left"}


class _Din(Element2Term):
    """Two-terminal element whose label `loc` means the side on the page.

    `loc='left'` puts the label left of the element whichever way it is drawn.
    `body_len` is the symbol length along the wire, `half_width` its half extent across.
    """

    body_len = 1.0
    half_width = 0.2

    def _place_label(self, label, theta=0):
        if abs(math.sin(math.radians(theta))) > 0.9 and label.loc in _VERTICAL_LOC:
            label = dataclasses.replace(label, loc=_VERTICAL_LOC[label.loc])
        super()._place_label(label, theta)


class Resistor(_Din):
    """Resistor: rectangle with a 2.5 : 1 aspect ratio (DIN EN 60617-4)."""

    body_len, half_width = 1.0, 0.2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        w, h = self.body_len, self.half_width
        self.segments.append(Segment([(0, 0), gap, (w, 0)]))
        self.segments.append(Segment([(0, h), (w, h), (w, -h), (0, -h), (0, h)]))


class Inductor(_Din):
    """Inductor: filled rectangle (DIN style) or, with `arcs=True`, four IEC semicircles."""

    body_len, half_width = 1.0, 0.2

    def __init__(self, *, arcs: bool = False, **kwargs):
        super().__init__(**kwargs)
        w, h = self.body_len, self.half_width
        self.segments.append(Segment([(0, 0), gap, (w, 0)]))
        if arcs:
            r = w / 8
            for i in range(4):
                x0 = i * w / 4
                pts = [
                    (x0 + r - r * math.cos(t), r * math.sin(t) * 1.6)
                    for t in (math.pi * k / 16 for k in range(17))
                ]
                self.segments.append(Segment(pts))
        else:
            self.segments.append(
                SegmentPoly([(0, h), (w, h), (w, -h), (0, -h)], fill=True, closed=True)
            )


class Capacitor(_Din):
    """Capacitor: two parallel plates (DIN EN 60617-4)."""

    body_len, half_width = 0.22, 0.38

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        g, h = self.body_len, self.half_width
        self.segments.append(Segment([(0, 0), gap, (g, 0)]))
        self.segments.append(Segment([(0, h), (0, -h)]))
        self.segments.append(Segment([(g, h), (g, -h)]))


class SourceV(_Din):
    """Ideal voltage source: circle with the conductor drawn through it.

    `ac=True` draws a sine-wave source instead: circle with ``~`` and no through line.
    The polarity is given by the voltage reference arrow, not by the symbol.
    """

    body_len, half_width = 0.9, 0.45

    def __init__(self, *, ac: bool = False, **kwargs):
        super().__init__(**kwargs)
        d = self.body_len
        r = d / 2
        self._sine: Segment | None = None
        if ac:
            self.segments.append(Segment([(0, 0), gap, (d, 0)]))
            self._sine = Segment([(r, 0)])
            self.segments.append(self._sine)
        else:
            self.segments.append(Segment([(0, 0), (d, 0)]))
        self.segments.append(SegmentCircle((r, 0), r))

    def _place(self, dwgxy, dwgtheta, **dwgparams):
        result = super()._place(dwgxy, dwgtheta, **dwgparams)
        if self._sine is not None:
            # Counter-rotate so the "~" stays horizontal on the page in any direction.
            center = Point((self.body_len / 2, 0))
            wave = [
                Point((0.26 * (k / 12 - 1), 0.16 * math.sin(math.pi * (k / 12 - 1))))
                for k in range(25)
            ]
            self._sine.path = [center + p.rotate(-self.transform.theta) for p in wave]
        return result


class SourceI(_Din):
    """Ideal current source: circle with a bar across the conductor."""

    body_len, half_width = 0.9, 0.45

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        d = self.body_len
        r = d / 2
        self.segments.append(Segment([(0, 0), gap, (d, 0)]))
        self.segments.append(SegmentCircle((r, 0), r))
        self.segments.append(Segment([(r, r), (r, -r)]))


def _lemniscate(cx: float, cy: float, a: float, n: int = 48) -> list[tuple[float, float]]:
    pts = []
    for k in range(n + 1):
        t = 2 * math.pi * k / n
        den = 1 + math.sin(t) ** 2
        pts.append((cx + a * math.cos(t) / den, cy + 1.4 * a * math.sin(t) * math.cos(t) / den))
    return pts


class Opamp(Element):
    """Operational amplifier, DIN EN 60617-13 box with ``▷ ∞`` and the input signs.

    Anchors: `minus`, `plus`, `out` (ends of the short leads), `center`, `top`, `bottom`.
    `plus_top=True` puts the non-inverting input on top.
    """

    W, H, PIN, LEAD = 2.2, 2.8, 0.7, 0.5
    _element_defaults: ClassVar[dict[str, Any]] = {"theta": 0}

    def __init__(self, *, plus_top: bool = False, **kwargs):
        super().__init__(**kwargs)
        w, h, p, lead = self.W, self.H, self.PIN, self.LEAD
        self.segments.append(
            Segment([(0, h / 2), (w, h / 2), (w, -h / 2), (0, -h / 2), (0, h / 2)])
        )
        y_minus, y_plus = (-p, p) if plus_top else (p, -p)
        self.segments.append(Segment([(-lead, y_minus), (0, y_minus)]))
        self.segments.append(Segment([(-lead, y_plus), (0, y_plus)]))
        self.segments.append(Segment([(w, 0), (w + lead, 0)]))
        s = 0.12  # half length of the sign strokes
        x = 0.32
        self.segments.append(Segment([(x - s, y_minus), (x + s, y_minus)]))
        self.segments.append(Segment([(x - s, y_plus), (x + s, y_plus)]))
        self.segments.append(Segment([(x, y_plus - s), (x, y_plus + s)]))
        # Qualifying symbol: triangle (amplifier) and infinity (ideal gain) at the top.
        tx, ty, th, tw = 0.85, h / 2 - 0.42, 0.34, 0.3
        self.segments.append(
            Segment([(tx, ty - th / 2), (tx, ty + th / 2), (tx + tw, ty), (tx, ty - th / 2)])
        )
        self.segments.append(Segment(_lemniscate(tx + tw + 0.36, ty, 0.24)))
        self.anchors.update(
            {
                "minus": (-lead, y_minus),
                "plus": (-lead, y_plus),
                "out": (w + lead, 0),
                "center": (w / 2, 0),
                "top": (w / 2, h / 2),
                "bottom": (w / 2, -h / 2),
            }
        )
        self.elmparams["drop"] = (w + lead, 0)


class OpampTriangle(elm.Opamp):
    """schemdraw's triangle op-amp with DIN anchor names (`minus`, `plus`, `out`)."""

    _element_defaults: ClassVar[dict[str, Any]] = {"theta": 0}

    def __init__(self, *, plus_top: bool = False, **kwargs):
        super().__init__(leads=True, **kwargs)
        if plus_top:
            self.flip()
        self.anchors["minus"] = self.anchors["in1"]
        self.anchors["plus"] = self.anchors["in2"]


# --------------------------------------------------------------------------------------
# Reference arrows (Zählpfeile)
# --------------------------------------------------------------------------------------


class _Overlay(Element):
    """Segments and labels in absolute drawing coordinates (arrows and their texts).

    Reference arrows are stroked thinner than wires (`thin=True`) so they never read as
    conductors.
    """

    def __init__(self, segments, texts=(), thin: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.segments.extend(segments)
        self._texts = list(texts)  # (xy, tex, halign, valign)
        self._thin = thin
        self.elmparams["theta"] = 0
        self.elmparams["at"] = (0, 0)

    def _place(self, dwgxy, dwgtheta, **dwgparams):
        if self._thin:
            for seg in self.segments:
                seg.lw = 0.75 * dwgparams.get("lw", 1.0)
        fontsize = dwgparams.get("fontsize", 9)
        for xy, tex, halign, valign in self._texts:
            self.segments.append(SegmentText(xy, tex, align=(halign, valign), fontsize=fontsize))
        self._texts = []
        return super()._place(dwgxy, dwgtheta, **dwgparams)


def _endpoints(target) -> tuple[Point, Point]:
    if isinstance(target, Element):
        start, end = target.start, target.end  # attribute access places a pending element
        return Point(start), Point(end)
    p1, p2 = target
    return Point(p1), Point(p2)


def _unit(p1: Point, p2: Point) -> tuple[Point, Point]:
    """Unit vector p1 -> p2 and its left normal."""
    dx, dy = p2.x - p1.x, p2.y - p1.y
    n = math.hypot(dx, dy)
    if n == 0:
        raise ValueError("reference arrow needs two distinct points")
    u = Point((dx / n, dy / n))
    return u, Point((-u.y, u.x))


_SIDES = {"left": (-1, 0), "right": (1, 0), "top": (0, 1), "bottom": (0, -1)}


def _side_normal(normal: Point, side: str | None, u: Point) -> Point:
    """Normal pointing to the requested page side ('left', 'right', 'top', 'bottom')."""
    if side is None:
        side = "right" if abs(u.y) > abs(u.x) else "top"
    if side not in _SIDES:
        raise ValueError(f"side must be one of {', '.join(_SIDES)}, not {side!r}")
    sx, sy = _SIDES[side]
    if normal.x * sx + normal.y * sy < 0:
        normal = Point((-normal.x, -normal.y))
    if abs(normal.x * sx + normal.y * sy) < 0.5:
        raise ValueError(f"side {side!r} is along the element, pick a side across it")
    return normal


def _align(normal: Point) -> tuple[str, str]:
    """Text alignment for a label placed in direction `normal` from its anchor."""
    halign = "left" if normal.x > 0.3 else "right" if normal.x < -0.3 else "center"
    valign = "bottom" if normal.y > 0.3 else "top" if normal.y < -0.3 else "center"
    return halign, valign


def _tex(label: str) -> str:
    return label if label.startswith("$") else f"${label}$"


def _body(target) -> tuple[float, float]:
    """(body length along the wire, half width across it) of a two-terminal element."""
    if isinstance(target, _Din):
        return target.body_len, target.half_width
    if isinstance(target, Element2Term) and "istart" in target.anchors:
        ist, iend = Point(target.anchors["istart"]), Point(target.anchors["iend"])
        bbox = target.get_bbox(includetext=False)
        return math.dist(ist, iend), max(abs(bbox.ymax), abs(bbox.ymin))
    return 0.0, 0.0


def zaehlpfeil_u(
    target,
    label: str,
    *,
    side: str | None = None,
    reverse: bool = False,
    ofst: float | None = None,
    length: float | None = None,
    color: str = "fg",
    nodes: Sequence[str] | None = None,
) -> Element:
    """Voltage reference arrow beside a two-terminal element or between two points.

    target: a placed or pending two-terminal element (the arrow runs parallel to it, from
    its start to its end) or a pair of points such as two terminals (the arrow joins them).
    label: TeX, e.g. 'U_1' or '\\underline{U}_C'. side: page side for arrow and label
    ('left', 'right', 'top', 'bottom'); default right of vertical, above horizontal ones.
    reverse: point from end to start. The arrow points from + to - (DIN 5489).
    nodes: (from, to) for the facts when the target is not a recorded component.
    """
    p1, p2 = _endpoints(target)
    if reverse:
        p1, p2 = p2, p1
    u, normal = _unit(p1, p2)
    is_points = not isinstance(target, Element)
    normal = _side_normal(normal, side, u)
    mid = Point(((p1.x + p2.x) / 2, (p1.y + p2.y) / 2))
    if is_points:
        span = math.dist(p1, p2)
        length = length if length is not None else max(span - 0.5, 0.6)
        ofst = ofst if ofst is not None else 0.0
    else:
        body, half = _body(target)
        length = length if length is not None else max(1.2, body + 0.35)
        ofst = ofst if ofst is not None else half + 0.28
    base = mid + normal * ofst
    a, b = base - u * (length / 2), base + u * (length / 2)
    hl, hw = U_HEAD
    stroke = ROLES.get(color, color)
    arrow = Segment([a, b], arrow="->", arrowlength=hl, arrowwidth=hw, color=stroke)
    text_at = base + normal * (LABEL_GAP + 0.04)
    halign, valign = _align(normal)
    el = _Overlay([arrow], [(text_at, _tex(label), halign, valign)], thin=True, color=stroke)
    _record_arrow("voltage", target, label, reverse, nodes)
    return el


def zaehlpfeil_i(
    target,
    label: str,
    *,
    pos: float | None = None,
    end: str = "start",
    side: str | None = None,
    reverse: bool = False,
    color: str = "fg",
    nodes: Sequence[str] | None = None,
) -> Element:
    """Current reference arrow: an arrowhead on the wire, label beside it.

    target: a two-terminal element (the head sits on its `end` lead, 'start' or 'end'),
    a Line, or a pair of points. pos: fraction along a line/point pair (default 0.5).
    The head points from the target's start to its end unless `reverse`.
    nodes: (from, to) for the facts when the target is not a recorded component.
    """
    p1, p2 = _endpoints(target)
    u, normal = _unit(p1, p2)
    span = math.dist(p1, p2)
    if not isinstance(target, Element2Term) or isinstance(target, elm.Line):
        center = p1 + u * (span * (0.5 if pos is None else pos))
    else:
        body, _ = _body(target)
        lead = (span - body) / 2
        if lead < I_HEAD[0] + 0.1:
            raise ValueError("element leads are too short for a current arrow; use a wire")
        if end not in ("start", "end"):
            raise ValueError("end must be 'start' or 'end'")
        along = lead / 2 if end == "start" else span - lead / 2
        center = p1 + u * along
    direction = u * (-1 if reverse else 1)
    hl, hw = I_HEAD
    tip = center + direction * (hl / 2)
    tail = center - direction * (hl / 2)
    stroke = ROLES.get(color, color)
    head = Segment([tail, tip], arrow="->", arrowlength=hl, arrowwidth=hw, color=stroke)
    if side is None:
        side = "left" if abs(u.y) > abs(u.x) else "top"
    normal = _side_normal(normal, side, u)
    text_at = center + normal * (hw / 2 + LABEL_GAP)
    halign, valign = _align(normal)
    el = _Overlay([head], [(text_at, _tex(label), halign, valign)], color=stroke, zorder=5)
    _record_arrow("current", target, label, reverse, nodes)
    return el


# --------------------------------------------------------------------------------------
# The drawing context
# --------------------------------------------------------------------------------------

_ACTIVE: list[drawing] = []


def _record_arrow(kind: str, target, label: str, reverse: bool, nodes) -> None:
    """Add the arrow to the active circuit's facts: symbol, element and node direction."""
    if not _ACTIVE:
        return
    c = _ACTIVE[-1]
    symbol = label.strip("$").split("=")[0].strip()
    entry: dict = {"kind": kind, "name": plain_name(symbol), "symbol": symbol}
    comp = c._components.get(id(target)) if isinstance(target, Element) else None
    pair = None
    if comp is not None:
        entry["element"] = comp["name"]
        pair = comp["nodes"]
    elif isinstance(target, Element) and id(target) in c._wires:
        pair = c._wires[id(target)]
    if nodes is not None:
        entry["from"], entry["to"] = str(nodes[0]), str(nodes[1])
    elif pair is not None:
        a, b = pair
        entry["from"], entry["to"] = (b, a) if reverse else (a, b)
    c.facts["arrows"].append(entry)


class drawing:
    """A schemdraw Drawing on a house-styled Matplotlib axes; yields a `Figure` on exit.

    Inside the `with` block schemdraw elements add themselves as usual. The component
    helpers (`resistor`, `capacitor`, `inductor`, `source_v`, `source_i`) also label the
    element with name and value and record it in `facts["components"]` with its nodes.

        with circuit.drawing(alt="RC low-pass") as c:
            c.resistor("R", "1 kΩ", nodes=("in", "out")).right()
            ...
        fig = c.figure
    """

    def __init__(
        self,
        alt: str | None = None,
        size: str = "col",
        template: str = "drawing",
        *,
        render_on_exit: bool = True,
    ):
        core.size(size)  # validates the name
        self.alt = alt
        self._render_on_exit = render_on_exit
        self.size = size
        self.style = STYLE[size]
        self.facts: dict = {"template": f"circuit.{template}", "components": [], "arrows": []}
        self._components: dict[int, dict] = {}
        self._wires: dict[int, tuple[str, str]] = {}
        # Parsed component values by plain name, e.g. values["R1"].si == 4700.0.
        self.values: dict[str, Quantity | None] = {}
        self.figure: core.Figure | None = None
        self.d = schemdraw.Drawing(show=False)
        self.d.config(
            unit=UNIT,
            fontsize=self.style["fontsize"],
            font=FONT,
            color=FG,
            lw=self.style["lw"],
            margin=0.1,
        )
        self.d.dwgparams["lblofst"] = 0.14

    def __enter__(self) -> drawing:
        self.d.__enter__()
        _ACTIVE.append(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.d.__exit__(exc_type, exc, tb)
        _ACTIVE.remove(self)
        if exc_type is None and self._render_on_exit:
            self.figure = self._render()

    # ---- components -------------------------------------------------------------------

    def component(
        self,
        element: Element,
        kind: str,
        symbol: str,
        value: Value = None,
        nodes: Sequence[str] = ("", ""),
        loc: str | None = "top",
        stacked: bool = False,
    ) -> Element:
        """Label `element` with symbol and value and record it in the facts.

        loc: page side of the label ('top', 'bottom', 'left', 'right') or None for no label.
        """
        q = quantity(value, kind)
        label = value_label(symbol, q, stacked) if loc is not None else None
        if label is not None:
            element.label(label, loc=loc)
        if len(nodes) != 2:
            raise ValueError("nodes must name the two nodes the element connects")
        entry = {
            "name": plain_name(symbol),
            "symbol": symbol,
            "kind": kind,
            "value": None if q is None else q.text,
            "si": None if q is None else q.si,
            "unit": KIND_UNIT[kind],
            "nodes": [str(n) for n in nodes],
            "label": label,
        }
        if any(e["name"] == entry["name"] for e in self.facts["components"]):
            raise ValueError(f"component {entry['name']} is already in the circuit")
        self.facts["components"].append(entry)
        self._components[id(element)] = entry
        self.values[entry["name"]] = q
        return element

    def resistor(self, symbol="R", value: Value = None, nodes=("", ""), loc="top", stacked=False):
        return self.component(Resistor(), "resistor", symbol, value, nodes, loc, stacked)

    def capacitor(self, symbol="C", value: Value = None, nodes=("", ""), loc="top", stacked=False):
        return self.component(Capacitor(), "capacitor", symbol, value, nodes, loc, stacked)

    def inductor(
        self, symbol="L", value: Value = None, nodes=("", ""), loc="top", stacked=False, arcs=False
    ):
        el = Inductor(arcs=arcs)
        return self.component(el, "inductor", symbol, value, nodes, loc, stacked)

    def source_v(self, symbol="U_0", value: Value = None, nodes=("", ""), loc=None, ac=False):
        """Voltage source; by default unlabelled, since its reference arrow carries the label."""
        return self.component(SourceV(ac=ac), "voltage_source", symbol, value, nodes, loc)

    def source_i(self, symbol="I_0", value: Value = None, nodes=("", ""), loc=None):
        return self.component(SourceI(), "current_source", symbol, value, nodes, loc)

    def wire(self, p1, p2, nodes: Sequence[str] | None = None) -> elm.Line:
        """Straight wire between two points; `nodes` lets current arrows on it name nodes."""
        line = elm.Line().endpoints(p1, p2)
        if nodes is not None:
            self._wires[id(line)] = (str(nodes[0]), str(nodes[1]))
        return line

    def dot(self, xy) -> Element:
        """Connection dot (junction of three or more wires)."""
        return elm.Dot(radius=0.07).at(xy)

    def terminal(self, xy) -> Element:
        """Open terminal (Klemme)."""
        return elm.Dot(open=True, radius=0.1).at(xy).zorder(6)

    def ground(self, xy) -> Element:
        return elm.Ground().at(xy)

    def text(self, xy, tex: str, halign: str = "center", valign: str = "center") -> Element:
        """A label at an absolute position, e.g. a node name."""
        return _Overlay([], [(Point(xy), tex, halign, valign)])

    # ---- rendering --------------------------------------------------------------------

    def _geometry_bbox(self) -> tuple[float, float, float, float]:
        xs, ys = [], []
        for element in self.d.elements:
            bb = element.get_bbox(transform=True, includetext=False)
            if all(map(math.isfinite, bb)):
                xs += [bb.xmin, bb.xmax]
                ys += [bb.ymin, bb.ymax]
        if not xs:
            raise ValueError("the circuit drawing is empty")
        return min(xs), min(ys), max(xs), max(ys)

    def _render(self) -> core.Figure:
        fig, ax = core.new_figure(self.size)
        try:
            fig.set_layout_engine("none")
            ax.set_position((0, 0, 1, 1))
            ax.set_axis_off()
            self.d.draw(show=False, canvas=ax)
            x0, y0, x1, y1 = self._geometry_bbox()
            m = 0.15
            ax.set_xlim(x0 - m, x1 + m)
            ax.set_ylim(y0 - m, y1 + m)
            ax.set_aspect("equal", adjustable="box")
            gw, gh = x1 - x0 + 2 * m, y1 - y0 + 2 * m
            ipu = self.style["ipu"]
            max_w, max_h = core.size(self.size)
            for _ in range(3):
                fig.set_size_inches(gw * ipu, gh * ipu)
                tight = fig.get_tightbbox(fig.canvas.get_renderer())
                over_w, over_h = tight.width - gw * ipu, tight.height - gh * ipu
                if tight.width <= max_w + 1e-3 and tight.height <= max_h + 1e-3:
                    break
                ipu = max(MIN_IPU, min((max_w - over_w) / gw, (max_h - over_h) / gh, ipu))
            self.facts["scale_in_per_unit"] = round(ipu, 4)
            nodes = {n for e in self.facts["components"] for n in e["nodes"] if n}
            nodes |= {a[k] for a in self.facts["arrows"] for k in ("from", "to") if k in a}
            self.facts["nodes"] = sorted(nodes)
        except Exception:
            core.plt.close(fig)
            raise
        if not self.alt:
            core.plt.close(fig)
            raise ValueError("every figure needs alt text describing what it shows")
        return core.finish(fig, self.alt, self.facts)


__all__ = [
    "Capacitor",
    "Inductor",
    "Opamp",
    "OpampTriangle",
    "Quantity",
    "Resistor",
    "SourceI",
    "SourceV",
    "drawing",
    "quantity",
    "value_label",
    "zaehlpfeil_i",
    "zaehlpfeil_u",
]
