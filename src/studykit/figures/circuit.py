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

The escape hatch for circuits no template covers is `drawing`. A component label goes above
a horizontal and left of a vertical element unless `loc` says otherwise; a voltage arrow
without `side` takes the other side, so label and arrow never meet:

    with circuit.drawing(alt="...") as c:
        r = c.resistor("R_1", "1 kΩ", nodes=("1", "2")).right()
        c.capacitor("C", "10 nF", nodes=("2", "0"), loc="right").down()
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

import numpy as np
import schemdraw
import schemdraw.elements as elm
from schemdraw import drawing_stack as schemdraw_stack
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
UNIT_ALIASES = {"\u2126": "Ω", "Ohm": "Ω", "ohm": "Ω", "Ohms": "Ω", "ohms": "Ω"}
KIND_UNIT = {
    "resistor": "Ω",
    "capacitor": "F",
    "inductor": "H",
    "voltage_source": "V",
    "current_source": "A",
}
_NUMBER = re.compile(r"^\s*(?P<num>[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?)\s*(?P<unit>.*?)\s*$")
# A unit written in a way `quantity` does not read: SPICE shorthand ('4.7k', '4k7', '1Meg')
# or a prefix or unit in the wrong case ('10 nf', '5 v', '1 KΩ'). Such values are errors,
# never symbols: SPICE 'M' is milli but SI 'M' is mega, and a silent symbol would show
# '4.7k' verbatim with no unit and no derived numbers.
_PREFIX_LIKE = r"(?P<prefix>[pnuµμmkKMG]|(?i:meg))"
_SPICE = re.compile(rf"^{_PREFIX_LIKE}(?P<digits>\d*)$")
_WRONG_CASE = re.compile(rf"^{_PREFIX_LIKE}?(?P<unit>(?i:Ω|ohms?|f|h|v|a|hz))$")
_UNIT_BY_LOWER = {"ω": "Ω", "ohm": "Ω", "ohms": "Ω", "f": "F", "h": "H", "v": "V", "a": "A"}
_PREFIX_FIX = {"K": "k", "u": "µ", "μ": "µ"}

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


def _split_unit(token: str, expected: str) -> tuple[str, str] | None:
    """'kΩ' -> ('k', 'Ω'); '' -> ('', expected); None if `token` is no prefixed unit."""
    if not token:
        return "", expected
    for alias in sorted([*UNITS, *UNIT_ALIASES], key=len, reverse=True):
        if token.endswith(alias):
            prefix = token[: -len(alias)]
            unit = UNIT_ALIASES.get(alias, alias)
            if prefix in PREFIXES:
                return prefix, unit
    return None


def _unit_error(value: str, num: str, token: str, expected: str) -> ValueError | None:
    """The error for a number followed by a unit `quantity` cannot read.

    None when the token is a symbol instead ('2R', '2 R_1', '2\\pi f L').
    """
    spice, wrong_case = _SPICE.match(token), _WRONG_CASE.match(token)
    ends_in_unit = token.isalpha() and token.endswith((*UNITS, *UNIT_ALIASES))
    has_ohm = "Ω" in token or "\u2126" in token or "ohm" in token.lower()
    if not (spice or wrong_case or ends_in_unit or has_ohm):
        return None
    found = spice or wrong_case
    prefix = (found["prefix"] or "") if found else ""
    prefix = "M" if prefix.lower() == "meg" else _PREFIX_FIX.get(prefix, prefix)
    unit = expected
    if wrong_case:
        unit = _UNIT_BY_LOWER.get(wrong_case["unit"].lower(), "Hz")
    if spice and spice["digits"] and re.fullmatch(r"\d+", num):
        num = f"{num}.{spice['digits']}"  # SPICE '4k7' is 4.7 k
    hint = f", e.g. {f'{num} {prefix}{unit}'!r}" if found else ""
    return ValueError(
        f"cannot read unit {token!r} in {value!r}; write the unit out, case-sensitive, with "
        f"an SI prefix (p, n, µ, m, k, M, G){hint}"
    )


def _mantissa_tex(num: str) -> str:
    num = num.replace(",", ".")
    if "e" in num.lower():
        mant, exp = re.split(r"[eE]", num)
        return core.localize_tex(rf"{mant}\cdot 10^{{{int(exp)}}}")
    return core.localize_tex(num)


def quantity(value: Value, kind: str) -> Quantity | None:
    """Parse a component value for a component kind (see KIND_UNIT).

    '4.7 kΩ' and '4,7 kΩ' -> 4700 Ω; 1e-7 (a number, SI units) -> '100 nF';
    symbols ('R', '2R', 'R_0') are shown as TeX. A number with a unit this cannot read
    ('4.7k', '10 nf', '1 KΩ') raises ValueError instead of turning into a symbol, and so do
    non-finite numbers and negative resistances, capacitances and inductances.
    """
    if value is None:
        return None
    expected = KIND_UNIT[kind]
    if isinstance(value, bool):
        raise TypeError(f"{kind} value must be a string or a number, not {value!r}")
    if isinstance(value, int | float):
        _check_si(float(value), kind, value)
        return _from_number(float(value), expected)
    symbolic = Quantity(text=value.strip(), si=None, unit="", tex=value.strip())
    match = _NUMBER.match(value)
    if not match:
        return symbolic
    token = re.sub(r"\s+", "", match["unit"])
    parsed = _split_unit(token, expected)
    if parsed is None:
        if error := _unit_error(value, match["num"], token, expected):
            raise error
        return symbolic
    prefix, unit = parsed
    if unit != expected:
        raise ValueError(f"{kind} value {value!r} has unit {unit}, expected {expected}")
    si = float(match["num"].replace(",", ".")) * 10.0 ** PREFIXES[prefix]
    tex = rf"{_mantissa_tex(match['num'])}\,{_unit_tex(prefix, unit)}"
    text = f"{match['num'].replace(',', '.')} {prefix}{unit}"
    _check_si(si, kind, value)
    return Quantity(text=text, si=si, unit=unit, tex=tex)


def _check_si(si: float, kind: str, value: Value) -> None:
    """Reject values no circuit can have: non-finite numbers and negative R, L or C."""
    if not math.isfinite(si):
        raise ValueError(f"{kind} value {value!r} is not a finite number")
    if si < 0 and kind in ("resistor", "capacitor", "inductor"):
        raise ValueError(f"{kind} value {value!r} is negative")


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
    """'$R_1 = 4{,}7\\,\\mathrm{k\\Omega}$', or '$R_1$' when there is no value or the value
    is the symbol itself (opamp('inverting', 'R_1', 'R_2') draws 'R_1', not 'R_1 = R_1').

    stacked=True puts a numeric value on a second line under the symbol, for tight spots.
    """
    if q is None or (q.si is None and q.tex == symbol):
        return f"${symbol}$"
    if stacked and q.si is not None:
        return f"${symbol}$\n${q.tex}$"
    return f"${symbol} = {q.tex}$"


# --------------------------------------------------------------------------------------
# DIN EN 60617 elements
# --------------------------------------------------------------------------------------

# Page side -> schemdraw's element-relative location for vertical elements.
_VERTICAL_LOC = {"left": "top", "right": "bottom"}
# Page sides as unit vectors, and the sides across an element with the label default first.
_SIDES = {"left": (-1, 0), "right": (1, 0), "top": (0, 1), "bottom": (0, -1)}
_ACROSS = {"horizontal": ("top", "bottom"), "vertical": ("left", "right")}


def _orientation(theta: float) -> str:
    """'horizontal', 'vertical' or 'diagonal' for a drawing angle in degrees."""
    s = abs(math.sin(math.radians(theta)))
    return "vertical" if s > 0.9 else "horizontal" if s < 0.45 else "diagonal"


class _Din(Element2Term):
    """Two-terminal element whose label `loc` means the side on the page.

    `loc='left'` puts the label left of the element whichever way it is drawn; 'auto' puts
    it above a horizontal and left of a vertical element. A side along the element (top or
    bottom of a vertical one) is an error, since the label would land on a lead end.
    `body_len` is the symbol length along the wire, `half_width` its half extent across.
    The page sides the labels ended up on are in `label_sides` once the element is placed.
    """

    body_len = 1.0
    half_width = 0.2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.label_sides: set[str] = set()

    def _place(self, dwgxy, dwgtheta, **dwgparams):
        self.label_sides = set()
        return super()._place(dwgxy, dwgtheta, **dwgparams)

    def _place_label(self, label, theta=0):
        orientation = _orientation(theta)
        loc = label.loc
        if orientation == "diagonal":
            loc = "top" if loc == "auto" else loc
        elif loc == "auto" or loc in _SIDES:
            across = _ACROSS[orientation]
            loc = across[0] if loc == "auto" else loc
            if loc not in across:
                raise ValueError(
                    f"label {label.label!r}: side {loc!r} runs along the {orientation} "
                    f"element, use {' or '.join(repr(s) for s in across)}"
                )
            self.label_sides.add(loc)
            if orientation == "vertical":
                loc = _VERTICAL_LOC[loc]
        super()._place_label(dataclasses.replace(label, loc=loc), theta)


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


def _default_side(target, u: Point, kind: str) -> str:
    """Default page side for a reference arrow label beside `target` (direction `u`).

    A voltage arrow goes to the side the element's own label leaves free (right of a
    vertical, above a horizontal element when there is no label). A current label sits on a
    lead: beside a vertical element it shares the side of the element label, which is
    centred on the body, and so stays clear of the voltage arrow; beside a horizontal
    element the wide value label reaches over the leads, so it takes the free side.
    """
    vertical = abs(u.y) > abs(u.x)
    labelled = getattr(target, "label_sides", set())
    if kind == "current" and vertical:
        return "left" if "left" in labelled or not labelled else "right"
    order = ("right", "left") if vertical else ("top", "bottom")
    return next((s for s in order if s not in labelled), order[0])


def _side_normal(normal: Point, side: str, u: Point) -> Point:
    """Normal pointing to the requested page side ('left', 'right', 'top', 'bottom')."""
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
    ('left', 'right', 'top', 'bottom'); default the side the element's own label does not
    use (below a horizontal element labelled above it, right of a vertical one labelled on
    the left), else right of vertical and above horizontal elements.
    reverse: point from end to start. The arrow points from + to - (DIN 5489).
    nodes: (from, to) for the facts when the target is not a recorded component.
    """
    p1, p2 = _endpoints(target)
    if reverse:
        p1, p2 = p2, p1
    u, normal = _unit(p1, p2)
    is_points = not isinstance(target, Element)
    normal = _side_normal(normal, side or _default_side(target, u, "voltage"), u)
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
    The head points from the target's start to its end unless `reverse`. side: page side
    of the label; default left of vertical and above horizontal wires, and for an element
    the side that stays clear of its value label and voltage arrow (see `_default_side`).
    nodes: (from, to) for the facts when the target is not a recorded component.
    """
    p1, p2 = _endpoints(target)
    u, normal = _unit(p1, p2)
    span = math.dist(p1, p2)
    outward = None  # on an element lead: direction along the wire away from the body
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
        outward = u * (-1 if end == "start" else 1)
    direction = u * (-1 if reverse else 1)
    hl, hw = I_HEAD
    tip = center + direction * (hl / 2)
    tail = center - direction * (hl / 2)
    stroke = ROLES.get(color, color)
    head = Segment([tail, tip], arrow="->", arrowlength=hl, arrowwidth=hw, color=stroke)
    if side is None:
        side = _default_side(target, u, "current")
    normal = _side_normal(normal, side, u)
    text_at = center + normal * (hw / 2 + LABEL_GAP)
    halign, valign = _align(normal)
    if outward is not None and abs(u.x) > abs(u.y):
        # Beside a horizontal element the label runs outward, clear of the voltage arrow.
        halign = "right" if outward.x < 0 else "left"
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
        stack = schemdraw_stack.drawing_stack
        try:
            if exc_type is not None and self.d in stack:
                # Nothing is rendered: drop the pending element instead of placing it, since
                # placing it may be what failed (e.g. a label side along the element).
                stack[self.d] = None
            self.d.__exit__(exc_type, exc, tb)
        finally:
            _ACTIVE.remove(self)
            stack.pop(self.d, None)  # schemdraw leaves it there when placing raised
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
        loc: str | None = "auto",
        stacked: bool = False,
    ) -> Element:
        """Label `element` with symbol and value and record it in the facts.

        loc: page side of the label across the element ('top' or 'bottom' of a horizontal,
        'left' or 'right' of a vertical element), 'auto' (above horizontal, left of vertical
        elements) or None for no label. A voltage arrow without a `side` goes opposite.
        """
        q = quantity(value, kind)
        label = value_label(symbol, q, stacked) if loc is not None else None
        if label is not None:
            if loc == "auto" and not isinstance(element, _Din):
                loc = "top"
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

    def resistor(self, symbol="R", value: Value = None, nodes=("", ""), loc="auto", stacked=False):
        return self.component(Resistor(), "resistor", symbol, value, nodes, loc, stacked)

    def capacitor(self, symbol="C", value: Value = None, nodes=("", ""), loc="auto", stacked=False):
        return self.component(Capacitor(), "capacitor", symbol, value, nodes, loc, stacked)

    def inductor(
        self, symbol="L", value: Value = None, nodes=("", ""), loc="auto", stacked=False, arcs=False
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


# --------------------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------------------


def _de() -> bool:
    return core.locale() == "de"


def _sym(letter: str, sub: str = "", phasor: bool = False) -> str:
    """TeX symbol: _sym('U', 'R', True) -> '\\underline{U}_{R}'."""
    base = rf"\underline{{{letter}}}" if phasor else letter
    return f"{base}_{{{sub}}}" if sub else base


def _io_subs() -> tuple[str, str]:
    return (r"\mathrm{e}", r"\mathrm{a}") if _de() else (r"\mathrm{in}", r"\mathrm{out}")


def _desc(c: drawing, name: str) -> str:
    """'R1 = 4,7 kΩ' or 'R1' for alt text."""
    q = c.values.get(name)
    return name if q is None else f"{name} = {q.plain}"


def _si(c: drawing, *names: str) -> list[float] | None:
    """SI values of the named components, or None if any of them is symbolic or missing."""
    out = []
    for name in names:
        q = c.values.get(name)
        if q is None or q.si is None:
            return None
        out.append(q.si)
    return out


def _sig(x: float) -> float:
    """Round derived numbers to 6 significant digits for stable facts."""
    return float(f"{x:.6g}")


def _parallel(a: float, b: float) -> float:
    """Resistance of a and b in parallel; a zero resistance shorts the pair."""
    return 0.0 if a == 0 or b == 0 else a * b / (a + b)


def _finish_template(c: drawing, alt: str | None, auto_alt: str) -> core.Figure:
    c.alt = alt or auto_alt
    return c._render()


def voltage_divider(
    R1: Value = None,
    R2: Value = None,
    U0: Value = None,
    *,
    RL: Value | bool = None,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Voltage divider: source U0 feeding R1 and R2 in series; optional load RL across R2.

    Reference arrows: current I through R1, voltages U1 across R1 and U2 across R2 (top to
    bottom); with a load also I2 through R2 and IL through RL. Nodes: '1' top, '2' tap,
    '0' bottom. `RL=True` draws the load without a value.
    """
    loaded = RL is not None and RL is not False
    h, x_r, x_l = 2 * UNIT, 4.0, 7.0
    c = drawing(alt=alt, size=size, template="voltage_divider", render_on_exit=False)
    with c:
        src = c.source_v("U_0", U0, nodes=("1", "0")).at((0, h)).down(h)
        top = c.wire((0, h), (x_r, h), nodes=("1", "1"))
        r1 = c.resistor("R_1", R1, nodes=("1", "2"), loc="left").at((x_r, h)).down()
        r2 = c.resistor("R_2", R2, nodes=("2", "0"), loc="left").down()
        c.wire((x_r, 0), (0, 0))
        zaehlpfeil_u(src, value_label("U_0", c.values["U0"]), side="left")
        zaehlpfeil_i(top, "I", side="top", nodes=("1", "2"))
        c.facts["arrows"][-1]["element"] = "R1"
        zaehlpfeil_u(r1, "U_1", side="right")
        zaehlpfeil_u(r2, "U_2", side="right")
        if loaded:
            tap = c.wire((x_r, UNIT), (x_l, UNIT), nodes=("2", "2"))
            load_value = None if RL is True else RL
            rl = c.resistor(r"R_\mathrm{L}", load_value, nodes=("2", "0"), loc="right")
            rl.at((x_l, UNIT)).down()
            c.wire((x_l, 0), (x_r, 0))
            c.dot((x_r, UNIT))
            c.dot((x_r, 0))
            zaehlpfeil_i(r2, "I_2", side="left")
            zaehlpfeil_i(tap, r"I_\mathrm{L}", side="top", nodes=("2", "0"))
            c.facts["arrows"][-1]["element"] = "RL"

    derived: dict = {}
    vals = _si(c, "R1", "R2")
    if vals:
        r1v, r2v = vals
        r_low = r2v
        if loaded and (rlv := _si(c, "RL")):
            r_low = _parallel(r2v, rlv[0])
            derived["R2_parallel_RL"] = _sig(r_low)
        # With R1 and the lower branch both 0 Ω the source is shorted: no ratio, no current.
        if (not loaded or "R2_parallel_RL" in derived) and r1v + r_low > 0:
            ratio = r_low / (r1v + r_low)
            derived["ratio_U2_U0"] = _sig(ratio)
            if u0 := _si(c, "U0"):
                derived["I"] = _sig(u0[0] / (r1v + r_low))
                derived["U2"] = _sig(u0[0] * ratio)
                derived["U1"] = _sig(u0[0] * (1 - ratio))
    c.facts["derived"] = derived
    c.facts["loaded"] = loaded

    parts = [_desc(c, n) for n in ("U0", "R1", "R2")]
    if _de():
        auto = (
            f"Schaltbild eines {'belasteten ' if loaded else ''}Spannungsteilers: "
            f"Die Spannungsquelle {parts[0]} speist die Reihenschaltung aus {parts[1]} und "
            f"{parts[2]}"
            + (f"; parallel zu R2 liegt der Lastwiderstand {_desc(c, 'RL')}" if loaded else "")
            + ". Zählpfeile: Strom I durch R1, Spannungen U1 an R1 und U2 an R2, jeweils "
            "vom oberen zum unteren Knoten."
        )
    else:
        auto = (
            f"Circuit diagram of a {'loaded ' if loaded else ''}voltage divider: the voltage "
            f"source {parts[0]} drives {parts[1]} and {parts[2]} in series"
            + (f"; the load {_desc(c, 'RL')} is connected across R2" if loaded else "")
            + ". Reference arrows: current I through R1, voltages U1 across R1 and U2 across "
            "R2, each from the upper to the lower node."
        )
    return _finish_template(c, alt, auto)


def _two_port(
    template: str,
    kind: str,
    series: tuple[str, str, Value],
    shunt: tuple[str, str, Value],
    phasors: bool,
    size: str,
    alt: str | None,
) -> drawing:
    """First-order two-port: series element on top, shunt element to the bottom rail."""
    if kind not in ("lowpass", "highpass"):
        raise ValueError(f"kind must be 'lowpass' or 'highpass', not {kind!r}")
    h, x_n, x_o = UNIT, 3.0, 5.0
    sub_in, sub_out = _io_subs()
    c = drawing(alt=alt, size=size, template=template, render_on_exit=False)
    adders = {"R": c.resistor, "C": c.capacitor, "L": c.inductor}
    with c:
        s_kind, s_sym, s_val = series
        adders[s_kind](s_sym, s_val, nodes=("in", "out"), loc="top").at((0, h)).right(x_n)
        p_kind, p_sym, p_val = shunt
        adders[p_kind](p_sym, p_val, nodes=("out", "0"), loc="left").at((x_n, h)).down(h)
        c.wire((x_n, h), (x_o, h))
        c.wire((0, 0), (x_o, 0))
        c.dot((x_n, h))
        c.dot((x_n, 0))
        for xy in ((0, h), (0, 0), (x_o, h), (x_o, 0)):
            c.terminal(xy)
        zaehlpfeil_u(((0, h), (0, 0)), _sym("U", sub_in, phasors), side="left", nodes=("in", "0"))
        zaehlpfeil_u(
            ((x_o, h), (x_o, 0)), _sym("U", sub_out, phasors), side="right", nodes=("out", "0")
        )
    c.facts["kind"] = kind
    return c


def rc(
    kind: str = "lowpass",
    R: Value = None,
    C: Value = None,
    *,
    phasors: bool = False,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """First-order RC filter as a two-port with input and output voltage arrows.

    kind='lowpass': R in series, C across the output; 'highpass': C in series, R across
    the output. Nodes: 'in', 'out', '0'. `phasors=True` labels complex amplitudes.
    """
    parts = (("R", "R", R), ("C", "C", C))
    series, shunt = parts if kind == "lowpass" else parts[::-1]
    c = _two_port("rc", kind, series, shunt, phasors, size, alt)
    derived: dict = {}
    if vals := _si(c, "R", "C"):
        tau = vals[0] * vals[1]
        derived["tau"] = _sig(tau)
        if tau > 0:  # R = 0 or C = 0 has no finite cut-off frequency
            derived.update({"omega_c": _sig(1 / tau), "f_c": _sig(1 / (2 * math.pi * tau))})
    c.facts["derived"] = derived
    c.facts["transfer"] = "1/(1 + j*w*tau)" if kind == "lowpass" else "j*w*tau/(1 + j*w*tau)"
    return _finish_template(c, alt, _filter_alt("RC", kind, c, series, shunt))


def rl(
    kind: str = "lowpass",
    R: Value = None,
    L: Value = None,
    *,
    phasors: bool = False,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """First-order RL filter as a two-port with input and output voltage arrows.

    kind='lowpass': L in series, R across the output; 'highpass': R in series, L across
    the output. Nodes: 'in', 'out', '0'.
    """
    parts = (("L", "L", L), ("R", "R", R))
    series, shunt = parts if kind == "lowpass" else parts[::-1]
    c = _two_port("rl", kind, series, shunt, phasors, size, alt)
    derived: dict = {}
    if vals := _si(c, "R", "L"):
        r_v, l_v = vals
        if r_v > 0:  # tau = L/R is infinite for R = 0
            derived["tau"] = _sig(l_v / r_v)
        if l_v > 0:  # omega_c = R/L is infinite for L = 0
            derived.update({"omega_c": _sig(r_v / l_v), "f_c": _sig(r_v / (2 * math.pi * l_v))})
    c.facts["derived"] = derived
    c.facts["transfer"] = "1/(1 + j*w*tau)" if kind == "lowpass" else "j*w*tau/(1 + j*w*tau)"
    return _finish_template(c, alt, _filter_alt("RL", kind, c, series, shunt))


def _filter_alt(name: str, kind: str, c: drawing, series, shunt) -> str:
    s, p = _desc(c, plain_name(series[1])), _desc(c, plain_name(shunt[1]))
    if _de():
        art = "Tiefpass" if kind == "lowpass" else "Hochpass"
        return (
            f"Schaltbild eines {name}-{art}es als Vierpol: {s} liegt im Längszweig, {p} im "
            "Querzweig parallel zu den Ausgangsklemmen. Zählpfeile: Eingangsspannung Ue und "
            "Ausgangsspannung Ua, jeweils von der oberen zur unteren Klemme."
        )
    art = "low-pass" if kind == "lowpass" else "high-pass"
    return (
        f"Circuit diagram of an {name} {art} filter as a two-port: {s} in the series path, "
        f"{p} in the shunt path across the output terminals. Reference arrows: input voltage "
        "Uin and output voltage Uout, each from the upper to the lower terminal."
    )


def rlc(
    topology: str = "series",
    R: Value = None,
    L: Value = None,
    C: Value = None,
    *,
    U0: Value = None,
    I0: Value = None,
    source: str | None = None,
    ac: bool = True,
    phasors: bool = False,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Series or parallel RLC circuit fed by a voltage or current source.

    source: 'voltage' or 'current'; default voltage for series, current for parallel.
    ac=True draws a sine-wave voltage source. Series: arrows I, U_R, U_L, U_C and U at the
    source. Parallel: arrows U, I_R, I_L, I_C and the source current. Nodes: '1', '0'
    (series also '2', '3' between R-L and L-C).
    """
    if topology not in ("series", "parallel"):
        raise ValueError(f"topology must be 'series' or 'parallel', not {topology!r}")
    source = source or ("voltage" if topology == "series" else "current")
    if source not in ("voltage", "current"):
        raise ValueError(f"source must be 'voltage' or 'current', not {source!r}")
    if (source == "voltage" and I0 is not None) or (source == "current" and U0 is not None):
        raise ValueError("give U0 for a voltage source and I0 for a current source")
    # The source quantity carries index 0; the other one is the circuit's U or I.
    if source == "voltage":
        u_tex, i_tex = _sym("U", "0", phasors), _sym("I", "", phasors)
    else:
        u_tex, i_tex = _sym("U", "", phasors), _sym("I", "0", phasors)
    h = 3.0
    c = drawing(alt=alt, size=size, template="rlc", render_on_exit=False)
    with c:
        if source == "voltage":
            src = c.source_v("U_0", U0, nodes=("1", "0"), ac=ac)
        else:
            src = c.source_i("I_0", I0, nodes=("1", "0"))
        src.at((0, h)).down(h)
        u_lbl = value_label(u_tex, c.values.get("U0")) if source == "voltage" else f"${u_tex}$"
        i_lbl = value_label(i_tex, c.values.get("I0")) if source == "current" else f"${i_tex}$"
        zaehlpfeil_u(src, u_lbl, side="left")
        zaehlpfeil_i(src, i_lbl, end="start", reverse=True, side="left")
        if topology == "series":
            c.wire((0, h), (0.5, h))
            r = c.resistor("R", R, nodes=("1", "2"), loc="bottom").at((0.5, h)).right()
            ind = c.inductor("L", L, nodes=("2", "3"), loc="bottom").right()
            c.wire((5.5, h), (6.5, h))
            cap = c.capacitor("C", C, nodes=("3", "0"), loc="left").at((6.5, h)).down(h)
            c.wire((6.5, 0), (0, 0))
            zaehlpfeil_u(r, f"${_sym('U', 'R', phasors)}$", side="top")
            zaehlpfeil_u(ind, f"${_sym('U', 'L', phasors)}$", side="top")
            zaehlpfeil_u(cap, f"${_sym('U', 'C', phasors)}$", side="right")
        else:
            xs = (2.8, 5.4, 8.0)
            c.wire((0, h), (xs[-1], h))
            c.wire((xs[-1], 0), (0, 0))
            adders = (c.resistor, c.inductor, c.capacitor)
            for x, add, (sym, val) in zip(xs, adders, (("R", R), ("L", L), ("C", C)), strict=True):
                el = add(sym, val, nodes=("1", "0"), loc="right", stacked=True)
                el.at((x, h)).down(h)
                zaehlpfeil_i(el, f"${_sym('I', sym, phasors)}$", side="left")
            for x in xs[:-1]:
                c.dot((x, h))
                c.dot((x, 0))

    derived: dict = {}
    if (lc := _si(c, "L", "C")) and lc[0] > 0 and lc[1] > 0:
        l_v, c_v = lc
        w0 = 1 / math.sqrt(l_v * c_v)
        derived = {"omega_0": _sig(w0), "f_0": _sig(w0 / (2 * math.pi))}
        # Q and bandwidth need a numeric R; keys that would be infinite are left out: the
        # ideal series LC circuit (R = 0) has no Q, the parallel one with R = 0 no bandwidth.
        r_v = r[0] if (r := _si(c, "R")) else None
        if r_v is not None and topology == "series":
            if r_v > 0:
                derived["Q"] = _sig(math.sqrt(l_v / c_v) / r_v)
            derived["bandwidth_Hz"] = _sig(r_v / (2 * math.pi * l_v))
        elif r_v is not None:
            derived["Q"] = _sig(r_v * math.sqrt(c_v / l_v))
            if r_v > 0:
                derived["bandwidth_Hz"] = _sig(1 / (2 * math.pi * r_v * c_v))
    c.facts.update({"topology": topology, "source": source, "ac": ac, "derived": derived})

    src_desc = _desc(c, "U0" if source == "voltage" else "I0")
    comps = ", ".join(_desc(c, n) for n in ("R", "L", "C"))
    if _de():
        quelle = "Spannungsquelle" if source == "voltage" else "Stromquelle"
        art = "Reihenschwingkreis" if topology == "series" else "Parallelschwingkreis"
        how = "in Reihe" if topology == "series" else "parallel"
        auto = f"Schaltbild: {art}. Eine {quelle} {src_desc} speist {comps} {how}. Zählpfeile " + (
            "für den Strom I und die Spannungen an R, L und C."
            if topology == "series"
            else "für die Spannung U und die Zweigströme durch R, L und C."
        )
    else:
        kind = "voltage" if source == "voltage" else "current"
        how = "in series" if topology == "series" else "in parallel"
        auto = (
            f"Circuit diagram of a {topology} RLC circuit: a {kind} source {src_desc} drives "
            f"{comps} {how}. Reference arrows "
            + (
                "for the current I and the voltages across R, L and C."
                if topology == "series"
                else "for the voltage U and the branch currents through R, L and C."
            )
        )
    return _finish_template(c, alt, auto)


OPAMP_KINDS = ("inverting", "non_inverting", "follower", "integrator", "differentiator")


def opamp(
    kind: str = "inverting",
    R1: Value = None,
    R2: Value = None,
    *,
    R: Value = None,
    C: Value = None,
    symbol: str = "din",
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Basic op-amp circuits with input and output voltage arrows to the ground rail.

    kind: 'inverting' (R1 input, R2 feedback), 'non_inverting' (R1 to ground, R2 feedback),
    'follower', 'integrator' (R input, C feedback), 'differentiator' (C input, R feedback).
    symbol: 'din' (DIN EN 60617 box) or 'triangle'. Nodes: 'in', 'n' (inverting input),
    'out', '0'.
    """
    if kind not in OPAMP_KINDS:
        raise ValueError(f"kind must be one of {', '.join(OPAMP_KINDS)}, not {kind!r}")
    if symbol not in ("din", "triangle"):
        raise ValueError(f"symbol must be 'din' or 'triangle', not {symbol!r}")
    wanted = {
        "inverting": {"R1", "R2"},
        "non_inverting": {"R1", "R2"},
        "follower": set(),
        "integrator": {"R", "C"},
        "differentiator": {"R", "C"},
    }[kind]
    given = {n for n, v in (("R1", R1), ("R2", R2), ("R", R), ("C", C)) if v is not None}
    if given - wanted:
        raise ValueError(f"{kind} uses {sorted(wanted) or 'no components'}, not {sorted(given)}")
    sub_in, sub_out = _io_subs()
    inverting = kind in ("inverting", "integrator", "differentiator")
    op_cls = Opamp if symbol == "din" else OpampTriangle
    c = drawing(alt=alt, size=size, template="opamp", render_on_exit=False)
    with c:
        x_in = 4.5
        op = op_cls(plus_top=not inverting).anchor("minus" if inverting else "plus")
        op.at((x_in, 0.7))
        minus, plus, out = Point(op.minus), Point(op.plus), Point(op.out)
        bb = op.get_bbox(transform=True, includetext=False)
        x_n, x_o = minus.x - 1.0, out.x + 0.8
        x_t = x_o + 1.5
        if inverting:
            parts = {
                "inverting": (("R", "R_1", R1), ("R", "R_2", R2)),
                "integrator": (("R", "R", R), ("C", "C", C)),
                "differentiator": (("C", "C", C), ("R", "R", R)),
            }[kind]
            adders = {"R": c.resistor, "C": c.capacitor}
            (k_in, s_in, v_in), (k_fb, s_fb, v_fb) = parts
            y_fb = bb.ymax + 1.2
            adders[k_in](s_in, v_in, nodes=("in", "n"), loc="top").at((0, minus.y)).right(x_n - 0.5)
            c.wire((x_n - 0.5, minus.y), minus)
            c.wire((x_n, minus.y), (x_n, y_fb))
            adders[k_fb](s_fb, v_fb, nodes=("n", "out"), loc="top").at((x_n, y_fb)).right(x_o - x_n)
            c.wire((x_o, y_fb), (x_o, out.y))
            c.dot((x_n, minus.y))
            y_rail = bb.ymin - 0.8
            x_g = plus.x - 0.5
            c.wire(plus, (x_g, plus.y))
            c.wire((x_g, plus.y), (x_g, y_rail))
            c.dot((x_g, y_rail))
            c.ground((x_g, y_rail))
        else:
            c.wire((0, plus.y), plus)
            y_fb = bb.ymin - 0.6
            c.wire(minus, (x_n, minus.y))
            c.wire((x_n, minus.y), (x_n, y_fb))
            c.wire((x_o, out.y), (x_o, y_fb))
            if kind == "follower":
                c.wire((x_n, y_fb), (x_o, y_fb))
                y_rail = y_fb - 1.4
                x_g = x_n
            else:
                c.resistor("R_2", R2, nodes=("n", "out"), loc="bottom").at((x_n, y_fb)).right(
                    x_o - x_n
                )
                c.resistor("R_1", R1, nodes=("n", "0"), loc="left").at((x_n, y_fb)).down()
                c.dot((x_n, y_fb))
                y_rail = y_fb - UNIT
                x_g = x_n
            c.dot((x_g, y_rail))
            c.ground((x_g, y_rail))
        c.wire(out, (x_t, out.y))
        c.dot((x_o, out.y))
        c.wire((0, y_rail), (x_t, y_rail))
        y_top_in = minus.y if inverting else plus.y
        for xy in ((0, y_top_in), (0, y_rail), (x_t, out.y), (x_t, y_rail)):
            c.terminal(xy)
        zaehlpfeil_u(
            ((0, y_top_in), (0, y_rail)), f"$U_{{{sub_in}}}$", side="left", nodes=("in", "0")
        )
        zaehlpfeil_u(
            ((x_t, out.y), (x_t, y_rail)), f"$U_{{{sub_out}}}$", side="right", nodes=("out", "0")
        )

    derived: dict = {}
    if kind == "follower":
        derived["gain"] = 1.0
    elif kind in ("inverting", "non_inverting") and (vals := _si(c, "R1", "R2")) and vals[0] > 0:
        g = -vals[1] / vals[0] if kind == "inverting" else 1 + vals[1] / vals[0]
        derived["gain"] = _sig(g)
    elif kind in ("integrator", "differentiator") and (vals := _si(c, "R", "C")):
        derived["tau"] = _sig(vals[0] * vals[1])
    relation = {
        "inverting": "Ua = -R2/R1 * Ue",
        "non_inverting": "Ua = (1 + R2/R1) * Ue",
        "follower": "Ua = Ue",
        "integrator": "Ua = -1/(R*C) * integral(Ue dt)",
        "differentiator": "Ua = -R*C * dUe/dt",
    }[kind]
    # Which node each op-amp pin connects to.
    pins = {"minus": "n", "plus": "0", "out": "out"}
    if not inverting:
        pins = {"minus": "out" if kind == "follower" else "n", "plus": "in", "out": "out"}
    c.facts.update(
        {
            "kind": kind,
            "symbol": symbol,
            "opamp_pins": pins,
            "relation": relation,
            "derived": derived,
        }
    )

    comps = ", ".join(_desc(c, n) for n in sorted(e["name"] for e in c.facts["components"]))
    names_de = {
        "inverting": "invertierender Verstärker",
        "non_inverting": "nichtinvertierender Verstärker",
        "follower": "Spannungsfolger (Impedanzwandler)",
        "integrator": "Integrierer",
        "differentiator": "Differenzierer",
    }
    if _de():
        auto = (
            f"Schaltbild: Operationsverstärker als {names_de[kind]}"
            + (f" mit {comps}" if comps else "")
            + ". Zählpfeile: Eingangsspannung Ue und Ausgangsspannung Ua, jeweils gegen Masse."
        )
    else:
        auto = (
            f"Circuit diagram: op-amp {kind.replace('_', '-')} "
            + ("amplifier" if kind in ("inverting", "non_inverting") else "circuit")
            + (f" with {comps}" if comps else "")
            + ". Reference arrows: input voltage Uin and output voltage Uout, both to ground."
        )
    return _finish_template(c, alt, auto)


_BRIDGE_ENDS = {
    "R1": ("T", "A"),
    "R2": ("A", "0"),
    "R3": ("T", "B"),
    "R4": ("B", "0"),
    "R5": ("A", "B"),
}


def _bridge_voltages(u0: float, resistors: dict[str, float]) -> tuple[float, float] | None:
    """Node voltages (U_A, U_B) of the bridge with T at u0 and node 0 at ground.

    A 0 Ω resistor merges its two nodes, so a shorted diagonal (R5 = 0) or branch still
    solves. None when the merged nodes short the source (T joined to 0).
    """
    parent = {n: n for n in "TAB0"}

    def root(n: str) -> str:
        while parent[n] != n:
            n = parent[n]
        return n

    for name, r in resistors.items():
        if r == 0:
            a, b = (root(n) for n in _BRIDGE_ENDS[name])
            parent[a] = b
    if root("T") == root("0"):
        return None
    fixed = {root("T"): u0, root("0"): 0.0}
    free = sorted({root("A"), root("B")} - fixed.keys())
    index = {n: i for i, n in enumerate(free)}
    g_matrix = np.zeros((len(free), len(free)))
    currents = np.zeros(len(free))
    for name, r in resistors.items():
        a, b = (root(n) for n in _BRIDGE_ENDS[name])
        if r == 0 or a == b:
            continue
        for here, there in ((a, b), (b, a)):
            if here not in index:
                continue
            g_matrix[index[here], index[here]] += 1 / r
            if there in index:
                g_matrix[index[here], index[there]] -= 1 / r
            else:
                currents[index[here]] += fixed[there] / r
    # Every free node reaches T or 0 through a resistor > 0, so the matrix is regular.
    solved = dict(zip(free, np.linalg.solve(g_matrix, currents), strict=True)) if free else {}
    volts = {**fixed, **solved}
    return float(volts[root("A")]), float(volts[root("B")])


def bridge(
    kind: str = "wheatstone",
    R1: Value = None,
    R2: Value = None,
    R3: Value = None,
    R4: Value = None,
    U0: Value = None,
    *,
    R5: Value = None,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Wheatstone bridge: two dividers R1-R2 and R3-R4 on a source U0, bridge voltage U_AB.

    Nodes: 'T' top, '0' bottom, 'A' between R1 and R2, 'B' between R3 and R4. `R5`
    optionally connects A and B (detector or load resistance).
    """
    if kind != "wheatstone":
        raise ValueError(f"kind must be 'wheatstone', not {kind!r}")
    h, xa, xb = 2 * UNIT, 3.5, 7.5
    c = drawing(alt=alt, size=size, template="bridge", render_on_exit=False)
    with c:
        src = c.source_v("U_0", U0, nodes=("T", "0")).at((0, h)).down(h)
        c.wire((0, h), (xb, h))
        c.wire((xb, 0), (0, 0))
        c.resistor("R_1", R1, nodes=("T", "A"), loc="left").at((xa, h)).down()
        c.resistor("R_2", R2, nodes=("A", "0"), loc="left").down()
        c.resistor("R_3", R3, nodes=("T", "B"), loc="right").at((xb, h)).down()
        c.resistor("R_4", R4, nodes=("B", "0"), loc="right").down()
        for xy in ((xa, h), (xa, 0), (xa, UNIT), (xb, UNIT)):
            c.dot(xy)
        c.text((xa - 0.16, UNIT + 0.08), r"$\mathrm{A}$", "right", "bottom")
        c.text((xb + 0.16, UNIT + 0.08), r"$\mathrm{B}$", "left", "bottom")
        zaehlpfeil_u(src, value_label("U_0", c.values["U0"]), side="left")
        zaehlpfeil_i(src, "I", end="start", reverse=True, side="left")
        label = r"$U_\mathrm{AB}$"
        if R5 is not None:
            r5 = c.resistor("R_5", R5, nodes=("A", "B"), loc="bottom").at((xa, UNIT)).right(xb - xa)
            zaehlpfeil_u(r5, label, side="top")
        else:
            zaehlpfeil_u(((xa, UNIT), (xb, UNIT)), label, side="top", nodes=("A", "B"))

    derived: dict = {}
    if vals := _si(c, "R1", "R2", "R3", "R4"):
        r1v, r2v, r3v, r4v = vals
        derived["balanced"] = math.isclose(r1v * r4v, r2v * r3v, rel_tol=1e-9)
        u0 = _si(c, "U0")
        r5v = _si(c, "R5") if R5 is not None else []  # None while R5 is symbolic
        resistors = dict(zip(("R1", "R2", "R3", "R4", "R5"), [*vals, *(r5v or [])], strict=False))
        # The node voltages are undefined (None) when 0 Ω resistors short the source.
        if u0 and r5v is not None and (volts := _bridge_voltages(u0[0], resistors)):
            ua, ub = volts
            # A balanced bridge has U_AB = 0 exactly; the solver would leave rounding noise.
            uab = 0.0 if derived["balanced"] else ua - ub
            derived.update({"U_A": _sig(ua), "U_B": _sig(ub), "U_AB": _sig(uab)})
    c.facts.update({"kind": kind, "derived": derived})

    comps = ", ".join(_desc(c, n) for n in ("R1", "R2", "R3", "R4"))
    extra_de = f"; {_desc(c, 'R5')} verbindet A und B" if R5 is not None else ""
    extra_en = f"; {_desc(c, 'R5')} connects A and B" if R5 is not None else ""
    if _de():
        auto = (
            f"Schaltbild einer Wheatstone-Brücke: Die Spannungsquelle {_desc(c, 'U0')} speist "
            f"die Spannungsteiler R1-R2 (Mittelpunkt A) und R3-R4 (Mittelpunkt B); {comps}"
            f"{extra_de}. Zählpfeil der Brückenspannung UAB von A nach B."
        )
    else:
        auto = (
            f"Circuit diagram of a Wheatstone bridge: the voltage source {_desc(c, 'U0')} feeds "
            f"the dividers R1-R2 (midpoint A) and R3-R4 (midpoint B); {comps}{extra_en}. "
            "Reference arrow for the bridge voltage UAB from A to B."
        )
    return _finish_template(c, alt, auto)


__all__ = [
    "Capacitor",
    "Inductor",
    "Opamp",
    "OpampTriangle",
    "Quantity",
    "Resistor",
    "SourceI",
    "SourceV",
    "bridge",
    "drawing",
    "opamp",
    "quantity",
    "rc",
    "rl",
    "rlc",
    "value_label",
    "voltage_divider",
    "zaehlpfeil_i",
    "zaehlpfeil_u",
]
