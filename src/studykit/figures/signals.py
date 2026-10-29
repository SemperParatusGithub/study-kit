"""Control-engineering and signal templates.

Bode and Nyquist diagrams, pole-zero maps, step responses, root loci, phasor diagrams and
time-domain signals. python-control, NumPy and SciPy only compute; house code draws every
line. Every number a figure shows is computed and recorded in `facts`. Gain and phase
margins and their crossover frequencies are computed twice, by python-control's polynomial
method and by an independent SciPy frequency scan refined with brentq; facts record whether
they agree, and a disagreement also raises a RuntimeWarning.

A transfer function `G` can be given as a python-control `TransferFunction`, as
`(num, den)` coefficient lists (highest power first) or as a SymPy string in `s`
(`'10/((s+1)*(s+10))'`), or in `z` for discrete-time pole-zero maps and root loci.
"""

from __future__ import annotations

import cmath
import itertools
import math
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property

import control as ct
import numpy as np
import sympy as sp
from matplotlib import ticker
from matplotlib.lines import Line2D
from matplotlib.patches import Arc, Circle, FancyArrowPatch
from scipy import signal as sps
from scipy.optimize import brentq

from studykit.figures import core
from studykit.figures.labels import (
    marker_points,
    place,
    polyline_points,
    segment_points,
)
from studykit.figures.palette import BG, FG, MUTED, color

S = sp.Symbol("s")
Z = sp.Symbol("z")
ANNOTATIONS = ("final", "overshoot", "rise", "settling")
TINY = 1e-9
MARGIN_RTOL = 1e-5

TransferFunctionLike = ct.TransferFunction | tuple | list | str


# --------------------------------------------------------------------------------------
# Transfer functions
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Plant:
    """A SISO transfer function as real coefficients, highest power first, monic denominator."""

    num: np.ndarray
    den: np.ndarray
    dt: float | bool  # 0 = continuous time, True or a sample time = discrete time
    latex: str

    @property
    def discrete(self) -> bool:
        return self.dt is True or (not isinstance(self.dt, bool) and bool(self.dt))

    @property
    def var(self) -> str:
        return "z" if self.discrete else "s"

    @cached_property
    def tf(self) -> ct.TransferFunction:
        return ct.tf(self.num, self.den, self.dt)

    def poles(self) -> np.ndarray:
        return _clean_roots(ct.poles(self.tf))

    def zeros(self) -> np.ndarray:
        return _clean_roots(ct.zeros(self.tf))

    def as_dict(self) -> dict:
        return {
            "num": [float(c) for c in self.num],
            "den": [float(c) for c in self.den],
            "variable": self.var,
            "latex": self.latex,
        }


def _clean_roots(roots) -> np.ndarray:
    """Merge numerically split repeated roots, snap tiny real/imaginary parts to 0, sort.

    np.roots splits a k-fold root into k roots about eps**(1/k) apart (a triple pole at -1
    comes back as -1 +- 1e-5j); each cluster is replaced by its mean, which is exact to
    rounding because the sum of the roots is a coefficient.
    """
    raw = list(np.atleast_1d(np.asarray(roots, dtype=complex)))
    clusters: list[list[complex]] = []
    for r in raw:
        for c in clusters:
            if abs(c[0] - r) <= 1e-4 * max(1.0, abs(r)):
                c.append(r)
                break
        else:
            clusters.append([r])
    out = []
    for c in clusters:
        mean = complex(np.mean(c))
        scale = max(1.0, abs(mean))
        # 12 significant digits: -1.0000000000000009 from rounding noise reads as -1.
        re = 0.0 if abs(mean.real) < TINY * scale else float(f"{mean.real:.12g}")
        im = 0.0 if abs(mean.imag) < TINY * scale else float(f"{mean.imag:.12g}")
        out += [complex(re, im)] * len(c)
    return np.array(sorted(out, key=lambda c: (c.real, c.imag)), dtype=complex)


def _nice_coeff(c: float) -> sp.Expr:
    c = float(f"{c:.12g}")  # 6.000000000000001 after normalising is 6
    return sp.Integer(round(c)) if c.is_integer() else sp.Float(f"{c:.6g}")


def _coeff_latex(num: np.ndarray, den: np.ndarray, var: sp.Symbol) -> str:
    def poly(cs):
        return sum(_nice_coeff(c) * var**k for k, c in enumerate(cs[::-1]))

    return sp.latex(poly(num) / poly(den))


def _poly_coeffs(expr: sp.Expr, var: sp.Symbol, source: str) -> np.ndarray:
    try:
        coeffs = sp.Poly(sp.expand(expr), var).all_coeffs()
        return np.array([float(c) for c in coeffs], dtype=float)
    except (sp.PolynomialError, TypeError) as exc:
        raise ValueError(
            f"{source!r} is not a rational function of {var} with real coefficients "
            "(dead time exp(-sT) is not supported)"
        ) from exc


def plant(G: TransferFunctionLike) -> Plant:
    """Normalise any accepted transfer-function input to a `Plant`."""
    if isinstance(G, Plant):
        return G
    if isinstance(G, ct.TransferFunction):
        if (G.ninputs, G.noutputs) != (1, 1):
            raise ValueError("only SISO transfer functions are supported")
        num = np.asarray(G.num[0][0], dtype=float)
        den = np.asarray(G.den[0][0], dtype=float)
        dt = G.dt or 0
        latex = _coeff_latex(num, den, Z if dt else S)
    elif isinstance(G, str):
        expr = sp.sympify(G, locals={"s": S, "z": Z, "e": sp.E, "pi": sp.pi})
        free = expr.free_symbols
        if free - {S, Z} or free == {S, Z}:
            names = ", ".join(sorted(str(x) for x in free))
            raise ValueError(f"{G!r} must be a function of s or of z only, not of {names}")
        var = Z if Z in free else S
        n, d = sp.fraction(sp.together(expr))
        num, den = _poly_coeffs(n, var, G), _poly_coeffs(d, var, G)
        dt = True if var == Z else 0
        latex = sp.latex(expr)
    elif isinstance(G, tuple | list) and len(G) == 2:
        num = np.atleast_1d(np.asarray(G[0], dtype=float))
        den = np.atleast_1d(np.asarray(G[1], dtype=float))
        dt = 0
        latex = _coeff_latex(num, den, S)
    else:
        raise TypeError("G must be a control.TransferFunction, (num, den) or a string in s")
    num, den = np.trim_zeros(num, "f"), np.trim_zeros(den, "f")
    if not num.size:
        raise ValueError("the numerator of G is zero")
    if not den.size:
        raise ValueError("the denominator of G is zero")
    lead = den[0]
    return Plant(num / lead, den / lead, dt, latex)


def _continuous(G: TransferFunctionLike, template: str, proper: bool = False) -> Plant:
    p = plant(G)
    if p.discrete:
        raise ValueError(f"{template} supports continuous-time systems only")
    if proper and len(p.num) > len(p.den):
        raise ValueError(f"{template} needs a proper transfer function (deg num <= deg den)")
    return p


@dataclass(frozen=True)
class Structure:
    """Bode normal form G(s) = k_bode / s**typ * prod(1 +- s/w_i)^(+-1)."""

    typ: int  # poles minus zeros at the origin (number of integrators)
    k_bode: float  # lim s->0 of s**typ G(s)
    lead: float  # num[0] / den[0], the high-frequency gain factor
    rel_degree: int  # deg den - deg num
    zeros: np.ndarray  # zeros not at the origin
    poles: np.ndarray  # poles not at the origin


def structure(p: Plant) -> Structure:
    num_t, den_t = np.trim_zeros(p.num, "b"), np.trim_zeros(p.den, "b")
    zeros = _clean_roots(np.roots(num_t)) if len(num_t) > 1 else np.array([], dtype=complex)
    poles = _clean_roots(np.roots(den_t)) if len(den_t) > 1 else np.array([], dtype=complex)
    return Structure(
        typ=(len(p.den) - len(den_t)) - (len(p.num) - len(num_t)),
        k_bode=float(num_t[-1] / den_t[-1]),
        lead=float(p.num[0] / p.den[0]),
        rel_degree=len(p.den) - len(p.num),
        zeros=zeros,
        poles=poles,
    )


def _interesting_frequencies(st: Structure) -> list[float]:
    """Corner frequencies plus where the low- and high-frequency asymptotes cross 0 dB."""
    out = [abs(r) for r in (*st.zeros, *st.poles)]
    if st.typ != 0:
        out.append(abs(st.k_bode) ** (1 / st.typ))
    if st.rel_degree != 0:
        out.append(abs(st.lead) ** (1 / st.rel_degree))
    return [f for f in out if f > 0 and math.isfinite(f)] or [1.0]


def _number(x) -> float | None:
    x = float(x)
    return x if math.isfinite(x) else None


def _pair(z: complex) -> list[float]:
    return [float(z.real), float(z.imag)]


def _tr(de: str, en: str) -> str:
    return de if core.locale() == "de" else en


def _num_tex(x: float, digits: int = 3) -> str:
    return core.fmt_number(x if abs(x) > 1e-12 else 0.0, digits)


# --------------------------------------------------------------------------------------
# Frequency response, margins
# --------------------------------------------------------------------------------------


def _root_angle(omega: np.ndarray, r: complex) -> np.ndarray:
    """arg(j omega - r) in radians on a branch without a cut for omega >= 0.

    j omega - r = -a + j (omega - b) for r = a + j b. With a < 0 the point stays in the
    right half-plane, where atan2 is continuous. With a > 0 it stays in the left half-plane;
    pi - atan2(omega - b, a) is the angle there taken in (pi/2, 3 pi/2), so it passes
    omega = b without the 2 pi jump of atan2 (and of np.angle). A root on the imaginary
    axis (a = 0) is a true 180-degree step of the phase at omega = b.
    """
    a, b = r.real, r.imag
    if a > 0:
        return math.pi - np.arctan2(omega - b, a)
    return np.arctan2(omega - b, abs(a))  # abs: never -0.0, which atan2 reads as pi


def phase_deg(p: Plant, omega: np.ndarray, st: Structure | None = None) -> np.ndarray:
    """Continuous phase in degrees, anchored so that phase(0+) = -90 typ (-180 if k < 0).

    The phase is the sum of the angles of the root factors (j omega - r), each taken on a
    branch it never leaves (`_root_angle`), so it is continuous in omega without unwrapping
    heuristics; only roots on the imaginary axis make it step by 180 degrees. The anchor
    is the usual textbook convention.
    """
    st = st or structure(p)
    w = np.asarray(omega, dtype=float)
    ph = np.zeros(w.shape)
    low = 0.0  # the same sum at omega = 0+
    for roots, sign in ((st.zeros, 1), (st.poles, -1)):
        for r in roots:
            ph += sign * _root_angle(w, r)
            low += sign * float(_root_angle(np.array(0.0), r))
    origin = 90.0 * -st.typ + (180.0 if st.lead < 0 else 0.0)
    ph = np.degrees(ph) + origin
    low = math.degrees(low) + origin
    convention = -90.0 * st.typ - (180.0 if st.k_bode < 0 else 0.0)
    return ph + 360.0 * round((convention - low) / 360.0)


def bode_asymptotes(p: Plant, omega: np.ndarray, st: Structure | None = None):
    """Straight-line Bode approximation: magnitude in dB and phase in degrees.

    Each root at |r| = w_c bends the magnitude by +-20 dB/decade; a real root ramps the
    phase by +-90 degrees between w_c/10 and 10 w_c, a complex pair steps by +-180 at w_n.
    """
    st = st or structure(p)
    lw = np.log10(np.asarray(omega, dtype=float))
    mag = 20 * math.log10(abs(st.k_bode)) - 20 * st.typ * lw
    ph = np.full(lw.shape, -90.0 * st.typ - (180.0 if st.k_bode < 0 else 0.0))
    for roots, sign in ((st.zeros, 1), (st.poles, -1)):
        for r in roots:
            lc = math.log10(abs(r))
            mag = mag + sign * 20 * np.maximum(0.0, lw - lc)
            direction = 1 if r.real <= 0 else -1
            ramp = np.clip((lw - lc + 1) / 2, 0.0, 1.0)  # real root: w_c/10 .. 10 w_c
            jump = (lw >= lc).astype(float)  # complex pair: a step at w_n
            ph = ph + sign * direction * 90 * (ramp if r.imag == 0 else jump)
    return mag, ph


def _group_roots(roots: np.ndarray) -> list[tuple[complex, int]]:
    groups: list[list] = []
    for r in roots:
        for g in groups:
            if abs(g[0] - r) <= 1e-4 * max(1.0, abs(r)):
                g[1] += 1
                break
        else:
            groups.append([r, 1])
    return [(complex(g[0]), g[1]) for g in groups]


def _corners(st: Structure) -> list[dict]:
    out = []
    for roots, kind, sign in ((st.zeros, "zero", 1), (st.poles, "pole", -1)):
        seen: dict[tuple[float, bool], dict] = {}
        for r, mult in _group_roots(roots):
            if r.imag < 0:
                continue
            wc = abs(r)
            order = mult * (2 if r.imag > 0 else 1)
            entry = seen.setdefault(
                (round(wc, 9), r.imag > 0),
                {"omega": wc, "kind": kind, "order": 0, "complex": r.imag > 0},
            )
            if r.imag > 0:
                entry["zeta"] = -r.real / wc
            entry["order"] += order
        for entry in seen.values():
            entry["slope_change_db_per_decade"] = sign * 20 * entry["order"]
            out.append(entry)
    return sorted(out, key=lambda e: e["omega"])


def _on_axis_root(st: Structure, w: float) -> bool:
    """omega = w is a zero or pole of G on the imaginary axis (the origin included).

    G is 0 or infinite there and its phase is undefined, so a "crossover" found there is
    an artefact of the method (python-control reports gm = 1/|G| = 4.5e15 at a zero).
    """
    axis = [abs(r.imag) for r in (*st.zeros, *st.poles) if r.real == 0]
    if st.typ != 0:
        axis.append(0.0)
    return any(abs(w - a) <= 1e-7 * max(1.0, a) for a in axis)


def _first_smallest(scores: Sequence[float]) -> int:
    """Index of the smallest score; near-ties (1e-7) go to the first, the lowest frequency.

    k s / (s^2 + a s + b) has two gain crossovers with phase margins +x and -x that differ
    only by rounding; both methods must pick the same one.
    """
    best = min(scores)
    return next(k for k, v in enumerate(scores) if v <= best * (1 + 1e-7) + 1e-12)


def _pick_margins(phase_x, gms, gain_x, pms) -> dict:
    """python-control's choice: the gain margin closest to 1, the smallest |phase margin|.

    The crossover lists are sorted by frequency.
    """
    out = {"gm": None, "gm_db": None, "w_pc": None, "pm_deg": None, "w_gc": None}
    if gms:
        i = _first_smallest([abs(math.log(g)) for g in gms])
        out.update(gm=gms[i], gm_db=20 * math.log10(gms[i]), w_pc=float(phase_x[i]))
    if pms:
        i = _first_smallest([abs(m) for m in pms])
        out.update(pm_deg=pms[i], w_gc=float(gain_x[i]))
    return out


def _margins_control(p: Plant, st: Structure) -> dict:
    """Margins by python-control's polynomial method, without on-axis artefacts."""
    gms, pms, _sm, wpcs, wgcs, _wms = ct.stability_margins(p.tf, returnall=True)
    phase = [
        (float(w), float(g))
        for w, g in zip(np.atleast_1d(wpcs), np.atleast_1d(gms), strict=True)
        if math.isfinite(g) and g > 0 and not _on_axis_root(st, float(w))
    ]
    gain = [
        (float(w), float(m))
        for w, m in zip(np.atleast_1d(wgcs), np.atleast_1d(pms), strict=True)
        if math.isfinite(m) and not _on_axis_root(st, float(w))
    ]
    phase_x, gms = [w for w, _ in sorted(phase)], [g for _, g in sorted(phase)]
    gain_x, pms = [w for w, _ in sorted(gain)], [m for _, m in sorted(gain)]
    return {
        "method": "control.stability_margins",
        "gain_crossovers": gain_x,
        "phase_crossovers": phase_x,
    } | _pick_margins(phase_x, gms, gain_x, pms)


def _real_on_axis(p: Plant) -> bool:
    """G(j omega) is real for every omega: num(j omega) den(-j omega) has no imaginary part."""
    powers = np.array([1, 1j, -1, -1j])

    def at_jw(c: np.ndarray, sign: int) -> np.ndarray:  # coefficients in omega
        k = np.arange(len(c) - 1, -1, -1)
        return c * powers[(sign * k) % 4]

    prod = np.polymul(at_jw(p.num, 1), at_jw(p.den, -1))
    return bool(np.all(np.abs(prod.imag) <= 1e-12 * np.max(np.abs(prod))))


def _margins_check(p: Plant, st: Structure) -> dict:
    """Independent margins: scipy.signal.freqresp scan, refined with brentq.

    A type-0 loop with G(0) < 0 starts on the negative real axis: its phase crossover is
    omega = 0 with gain margin 1/|G(0)| (an unstable plant stabilised by a gain, 10/(s-1)).
    The scan sees only omega > 0, so that crossover is added explicitly. When G(j omega)
    is real for every omega (undamped plants such as 1/(s^2 + 1)) no phase crossover is
    isolated and none is reported, as python-control does.
    """
    freqs = _interesting_frequencies(st)
    w = [np.logspace(math.log10(min(freqs)) - 3, math.log10(max(freqs)) + 3, 20001)]
    # Lightly damped roots make |G| and the phase change within a tiny band around
    # omega = Im r; geometric steps down to 1e-10 of Im r on both sides resolve it.
    near = np.logspace(-10, -0.5, 200)
    for r in (*st.poles, *st.zeros):
        if r.imag > 0:
            w += [r.imag * (1 - near), r.imag * (1 + near)]
    w = np.unique(np.concatenate(w))
    _, H = sps.freqresp((p.num, p.den), w)

    def h(x: float) -> complex:
        return complex(np.polyval(p.num, 1j * x) / np.polyval(p.den, 1j * x))

    with np.errstate(divide="ignore"):
        logmag = np.log(np.abs(H))
    gain_x = []
    for i in np.flatnonzero(np.sign(logmag[:-1]) * np.sign(logmag[1:]) < 0):
        gain_x.append(brentq(lambda x: math.log(abs(h(x))), w[i], w[i + 1], xtol=1e-14 * w[i]))
    ang = np.angle(H)
    sin_a = np.sin(ang)
    real_line = _real_on_axis(p)
    cand = (sin_a[:-1] * sin_a[1:] < 0) & (np.cos(ang[:-1]) < 0) & (np.cos(ang[1:]) < 0)
    phase_x = [0.0] if st.typ == 0 and st.k_bode < 0 and not real_line else []

    def sin_phase(x: float) -> float:
        return math.sin(cmath.phase(h(x)))

    for i in np.flatnonzero(cand) if not real_line else []:
        fa, fb = sin_phase(w[i]), sin_phase(w[i + 1])
        if fa * fb <= 0:
            x = brentq(sin_phase, w[i], w[i + 1], xtol=1e-14 * w[i])
        else:  # the crossover is a grid point, its sine rounded to the neighbour's sign
            x = float(w[i] if abs(fa) < abs(fb) else w[i + 1])
        hx = h(x)
        if _on_axis_root(st, x) or not 0 < abs(hx) < math.inf:
            continue
        new = not phase_x or abs(x - phase_x[-1]) > 1e-9 * x
        if new and abs(math.sin(cmath.phase(hx))) < 1e-8 and hx.real < 0:
            phase_x.append(x)
    gain_x = [x for x in gain_x if not _on_axis_root(st, x)]

    gms = [1 / abs(h(x)) for x in phase_x]
    pms = [(math.degrees(cmath.phase(h(x))) % 360.0) - 180.0 for x in gain_x]
    return {
        "method": "scipy.signal.freqresp + brentq",
        "gain_crossovers": [float(x) for x in gain_x],
        "phase_crossovers": [float(x) for x in phase_x],
    } | _pick_margins(phase_x, gms, gain_x, pms)


def _close(a: float | None, b: float | None, rtol: float = MARGIN_RTOL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= rtol * max(1.0, abs(a), abs(b))


MARGIN_KEYS = ("gm", "w_pc", "pm_deg", "w_gc")


def stability_margins(G: TransferFunctionLike) -> dict:
    """Gain and phase margin with crossover frequencies, cross-checked two ways.

    Returns `{"gm", "gm_db", "w_pc", "pm_deg", "w_gc", "agree", "mismatch", "control",
    "check"}`: frequencies in rad/s, None where a margin does not exist. The values are
    python-control's; `check` holds the independent SciPy scan. A disagreement never
    raises: `agree` is False, `mismatch` names the quantities that differ and a
    RuntimeWarning carries both results.
    """
    p = _continuous(G, "margins")
    st = structure(p)
    ctl = _margins_control(p, st)
    check = _margins_check(p, st)
    mismatch = [k for k in MARGIN_KEYS if not _close(ctl[k], check[k])]
    if mismatch:
        warnings.warn(
            f"margin cross-check differs in {', '.join(mismatch)}: control {ctl} vs scipy {check}",
            RuntimeWarning,
            stacklevel=2,
        )
    return {k: ctl[k] for k in ("gm", "gm_db", "w_pc", "pm_deg", "w_gc")} | {
        "agree": not mismatch,
        "mismatch": mismatch,
        "control": ctl,
        "check": check,
    }


def _nice_step(span: float, candidates: Sequence[float], max_ticks: int = 6) -> float:
    for step in candidates:
        if span / step <= max_ticks:
            return step
    return candidates[-1] * math.ceil(span / (candidates[-1] * max_ticks))


def _pad_range(lo: float, hi: float, frac: float = 0.08) -> tuple[float, float]:
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    pad = frac * (hi - lo)
    return lo - pad, hi + pad


def _double_arrow(ax, a, b, col: str, lw: float = 1.0) -> None:
    ax.add_patch(
        FancyArrowPatch(
            a,
            b,
            arrowstyle="<|-|>",
            mutation_scale=6,
            color=col,
            lw=lw,
            shrinkA=0,
            shrinkB=0,
            zorder=6,
        )
    )


def bode(
    G: TransferFunctionLike,
    w: Sequence[float] | np.ndarray | None = None,
    unit: str = "rad/s",
    asymptotes: bool = False,
    margins: bool = False,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Bode diagram: magnitude in dB over phase in degrees on a shared log frequency axis.

    w: (low, high) range or an array of frequencies, in `unit` ('rad/s' or 'Hz').
    asymptotes: straight-line approximation (real and complex roots).
    margins: gain and phase margin with their crossover frequencies marked.
    """
    if unit not in ("rad/s", "Hz"):
        raise ValueError("unit must be 'rad/s' or 'Hz'")
    p = _continuous(G, "bode")
    st = structure(p)
    to_x = 1 / (2 * math.pi) if unit == "Hz" else 1.0
    mg = stability_margins(p) if margins else None

    if w is None:
        freqs = [abs(r) for r in (*st.zeros, *st.poles)] or _interesting_frequencies(st)
        if mg:
            freqs += [x for x in (mg["w_gc"], mg["w_pc"]) if x]
        lo = 10 ** (math.floor(math.log10(min(freqs))) - 1)
        hi = 10 ** (math.ceil(math.log10(max(freqs))) + 1)
        omega = np.logspace(math.log10(lo), math.log10(hi), 1200)
    else:
        arr = np.asarray(w, dtype=float) / to_x
        if np.any(arr <= 0):
            raise ValueError("frequencies must be positive")
        omega = np.logspace(*np.log10(arr), 1200) if arr.size == 2 else np.sort(arr)
    H = p.tf(1j * omega)
    mag = 20 * np.log10(np.abs(H))
    ph = phase_deg(p, omega, st)
    x = omega * to_x

    fig, (ax_m, ax_p) = core.new_figure(size, nrows=2, sharex=True)
    width, height = core.size(size)
    fig.set_size_inches(width, height * 1.5)
    ax_m.semilogx(x, mag, color=color(0), zorder=4)
    ax_p.semilogx(x, ph, color=color(0), zorder=4)

    facts: dict = {
        "template": "signals.bode",
        "G": p.as_dict(),
        "unit": unit,
        "omega_range": [float(omega[0]), float(omega[-1])],
        "type": st.typ,
        "k_bode": st.k_bode,
        "k_bode_db": 20 * math.log10(abs(st.k_bode)),
        "corners": _corners(st),
        "magnitude_db_range": [float(mag.min()), float(mag.max())],
        "phase_deg_range": [float(ph.min()), float(ph.max())],
        "peak": {"omega": float(omega[np.argmax(mag)]), "db": float(mag.max())},
    }
    m_lo, m_hi = float(mag.min()), float(mag.max())
    p_lo, p_hi = float(ph.min()), float(ph.max())

    if asymptotes:
        a_mag, a_ph = bode_asymptotes(p, omega, st)
        style = {"color": color(1), "lw": 1.0, "ls": (0, (4, 2)), "zorder": 3}
        ax_m.semilogx(x, np.clip(a_mag, m_lo - 40, m_hi + 40), **style)
        ax_p.semilogx(x, a_ph, **style)
        p_lo, p_hi = min(p_lo, float(a_ph.min())), max(p_hi, float(a_ph.max()))
        facts["asymptotes"] = {
            "low_frequency_slope_db_per_decade": -20 * st.typ,
            "high_frequency_slope_db_per_decade": -20 * st.rel_degree,
        }

    if mg is not None:
        facts["margins"] = mg
        if unit == "Hz":
            facts["crossovers_hz"] = {
                "f_gc": None if mg["w_gc"] is None else mg["w_gc"] * to_x,
                "f_pc": None if mg["w_pc"] is None else mg["w_pc"] * to_x,
            }
        m_lo, m_hi, p_lo, p_hi = _draw_margins(
            ax_m, ax_p, p, st, mg, to_x, (x[0], x[-1]), m_lo, m_hi, p_lo, p_hi
        )

    ax_m.set_ylim(*_pad_range(m_lo, m_hi))
    ax_p.set_ylim(*_pad_range(p_lo, p_hi))
    ax_m.yaxis.set_major_locator(
        ticker.MultipleLocator(_nice_step(m_hi - m_lo, (5, 10, 20, 40, 60), 5))
    )
    ax_p.yaxis.set_major_locator(
        ticker.MultipleLocator(_nice_step(p_hi - p_lo, (15, 30, 45, 90, 180), 5))
    )
    ax_m.set_xlim(x[0], x[-1])
    ax_m.set_ylabel(_tr("Betrag in dB", "Magnitude / dB"))
    ax_p.set_ylabel(_tr("Phase in °", "Phase / °"))
    if unit == "Hz":
        ax_p.set_xlabel(_tr("Frequenz $f$ in Hz", "Frequency $f$ / Hz"))
    else:
        ax_p.set_xlabel(
            _tr(r"Kreisfrequenz $\omega$ in rad/s", r"Angular frequency $\omega$ / (rad/s)")
        )
    for ax in (ax_m, ax_p):
        ax.xaxis.set_major_locator(ticker.LogLocator(base=10, numticks=12))
        ax.xaxis.set_minor_locator(ticker.LogLocator(base=10, subs=np.arange(2, 10), numticks=12))
        ax.grid(True, which="minor", axis="x", lw=0.3)
        core.apply_locale(ax)
    fig.align_ylabels([ax_m, ax_p])

    if alt is None:
        alt = (
            f"Bode diagram of G({p.var}) = {_plain(p)} from {omega[0] * to_x:.3g} to "
            f"{omega[-1] * to_x:.3g} {unit}: magnitude in dB above, phase in degrees below"
        )
        if mg is not None:
            alt += "; " + _margins_alt(mg, to_x, unit)
        alt += "."
    return core.finish(fig, alt, facts)


def _plain(p: Plant) -> str:
    """Readable G for alt text: the SymPy string of num/den."""
    var = sp.Symbol(p.var)

    def poly(cs):
        return sum(_nice_coeff(c) * var**k for k, c in enumerate(cs[::-1]))

    return str(poly(p.num) / poly(p.den)).replace("**", "^")


def _margins_alt(mg: dict, to_x: float, unit: str) -> str:
    parts = []
    if mg["pm_deg"] is not None:
        parts.append(f"phase margin {mg['pm_deg']:.3g} degrees at {mg['w_gc'] * to_x:.3g} {unit}")
    else:
        parts.append("no gain crossover, so no phase margin")
    if mg["gm_db"] is not None:
        parts.append(f"gain margin {mg['gm_db']:.3g} dB at {mg['w_pc'] * to_x:.3g} {unit}")
    else:
        parts.append("the phase never reaches -180 degrees, so the gain margin is infinite")
    return ", ".join(parts)


def _draw_margins(ax_m, ax_p, p, st, mg, to_x, x_span, m_lo, m_hi, p_lo, p_hi):
    de = core.locale() == "de"
    var = r"\omega" if to_x == 1.0 else "f"
    # Margin labels get a page-coloured backing so grid and asymptote lines stay behind.
    label_style = {
        "textcoords": "offset points",
        "va": "center",
        "fontsize": 7,
        "bbox": {"boxstyle": "square,pad=0.1", "fc": BG, "ec": "none", "alpha": 0.85},
        "zorder": 8,
    }
    marks: list[tuple[float, str]] = []
    ax_m.axhline(0, color=FG, lw=0.7, zorder=2)
    if mg["w_gc"] is not None:
        wgc = mg["w_gc"]
        ph_gc = float(phase_deg(p, np.array([wgc]), st)[0])
        ref = ph_gc - mg["pm_deg"]
        ax_p.axhline(ref, color=FG, lw=0.7, zorder=2)
        xg = wgc * to_x
        for ax in (ax_m, ax_p):
            ax.axvline(xg, color=MUTED, lw=0.8, ls=":", zorder=2)
        _double_arrow(ax_p, (xg, ref), (xg, ph_gc), color(2))
        ax_p.plot([xg], [ph_gc], "o", ms=3.5, color=color(2), zorder=7)
        sym = r"\varphi_\mathrm{R}" if de else r"\varphi_\mathrm{m}"
        falling = float(phase_deg(p, np.array([wgc * 1.05]), st)[0]) < ph_gc
        ax_p.annotate(
            f"${sym} = {_num_tex(mg['pm_deg'])}^\\circ$",
            (xg, (ref + ph_gc) / 2),
            **_free_side(falling, ph_gc < ref),
            color=FG,
            **label_style,
        )
        marks.append((xg, rf"${var}_\mathrm{{D}}$" if de else rf"${var}_\mathrm{{gc}}$"))
        p_lo, p_hi = min(p_lo, ref), max(p_hi, ref)
    else:
        ax_p.axhline(-180.0, color=FG, lw=0.7, zorder=2)
        p_lo, p_hi = min(p_lo, -180.0), max(p_hi, -180.0)
    if mg["w_pc"] is not None:
        wpc = mg["w_pc"]
        pc_name = rf"{var}_\pi" if de else rf"{var}_\mathrm{{pc}}"
        sym = r"A_\mathrm{R}" if de else r"\mathrm{GM}"
        text = rf"{sym} = {_num_tex(mg['gm_db'])}\,\mathrm{{dB}}"
        if wpc > 0:
            m_pc = float(20 * np.log10(np.abs(p.tf(1j * wpc))))
            xp = wpc * to_x
            for ax in (ax_m, ax_p):
                ax.axvline(xp, color=MUTED, lw=0.8, ls=":", zorder=2)
            falling = float(20 * np.log10(np.abs(p.tf(1j * wpc * 1.05)))) < m_pc
            where, side = (xp, m_pc / 2), _free_side(falling, m_pc < 0)
            marks.append((xp, f"${pc_name}$"))
        else:
            # G(0) < 0: the phase crossover is omega = 0, which a log axis cannot show.
            # The arrow stands just inside the left edge at the DC gain, which the flat
            # type-0 magnitude has there, and the label says omega_pc = 0. The curve
            # leaves the left edge sideways, so the label goes right of the arrow; an
            # arrow too short to carry it (|GM| near 0 dB) gets it above its top end.
            m_pc = 20 * math.log10(abs(st.k_bode))
            xp = x_span[0] * (x_span[1] / x_span[0]) ** 0.04
            text += rf"\;({pc_name} = 0)"
            span = max(m_hi, 0.0) - min(m_lo, 0.0)
            if abs(m_pc) >= 0.2 * span:
                where, side = (xp, m_pc / 2), {"xytext": (4, 0), "ha": "left"}
            else:
                where = (xp, max(m_pc, 0.0))
                side = {"xytext": (3, 4), "ha": "left", "va": "bottom"}
                m_hi = max(m_hi, max(m_pc, 0.0) + 0.15 * span)
        _double_arrow(ax_m, (xp, m_pc), (xp, 0.0), color(1))
        ax_m.plot([xp], [m_pc], "o", ms=3.5, color=color(1), zorder=7)
        ax_m.annotate(f"${text}$", where, color=FG, **(label_style | side))
        m_lo, m_hi = min(m_lo, m_pc, 0.0), max(m_hi, m_pc, 0.0)
    # Crossover names at the top, right of their line; when the two lines are close the
    # lower frequency's name moves to the left of its line so the names do not collide.
    marks.sort()
    close = len(marks) == 2 and math.log10(marks[1][0] / marks[0][0]) < 0.4
    for i, (x, text) in enumerate(marks):
        left = close and i == 0
        ax_m.annotate(
            text,
            (x, 1),
            xycoords=("data", "axes fraction"),
            xytext=(-2 if left else 2, -2),
            textcoords="offset points",
            ha="right" if left else "left",
            va="top",
            fontsize=7,
            color=MUTED,
        )
    m_lo, m_hi = min(m_lo, 0.0), max(m_hi, 0.0)
    return m_lo, m_hi, p_lo, p_hi


def _free_side(falling: bool, curve_end_is_bottom: bool) -> dict:
    """Put a margin label beside its arrow on the side the curve moves away from.

    The arrow spans from a reference line to the curve; past the arrow a falling curve
    leaves the span downwards, so the far side is free exactly when the curve's end of
    the arrow is its bottom end (and vice versa for a rising curve).
    """
    right = falling == curve_end_is_bottom
    return {"xytext": (4, 0) if right else (-4, 0), "ha": "left" if right else "right"}


# --------------------------------------------------------------------------------------
# Complex-plane helpers
# --------------------------------------------------------------------------------------


def _arrowhead(ax, a: complex, b: complex, col: str, scale: float = 11) -> None:
    """A filled arrowhead at b pointing from a to b (a and b close together)."""
    ax.add_patch(
        FancyArrowPatch(
            (a.real, a.imag),
            (b.real, b.imag),
            arrowstyle="-|>,head_length=0.5,head_width=0.25",
            mutation_scale=scale,
            color=col,
            lw=0.5,
            shrinkA=0,
            shrinkB=0,
            zorder=6,
        )
    )


def _arrows_along(ax, z: np.ndarray, fractions, col: str, box, reverse: bool = False) -> None:
    """Arrowheads at arc-length fractions of the part of path z inside box.

    A path that leaves the view and comes back (poles on the imaginary axis) is split into
    its visible runs; each long enough run gets one arrow in its middle.
    """
    (x0, x1), (y0, y1) = box
    span = max(x1 - x0, y1 - y0)
    ok = np.isfinite(z) & (z.real >= x0) & (z.real <= x1) & (z.imag >= y0) & (z.imag <= y1)
    breaks = np.flatnonzero(np.diff(ok.astype(int)) != 0) + 1
    runs = [r for r in np.split(np.arange(z.size), breaks) if ok[r[0]] and r.size >= 5]
    lengths = [float(np.sum(np.abs(np.diff(z[r])))) for r in runs]
    runs = [r for r, n in zip(runs, lengths, strict=True) if n > 0.15 * span]
    if len(runs) > 1:
        targets = [(r, 0.5) for r in runs]
    else:
        targets = [(r, f) for r in runs for f in fractions]
    eps = 1e-3 * span
    for run, f in targets:
        zz = z[run]
        cum = np.concatenate([[0.0], np.cumsum(np.abs(np.diff(zz)))])
        i = int(np.clip(np.searchsorted(cum, f * cum[-1]), 1, zz.size - 2))
        d = zz[i + 1] - zz[i - 1]
        if abs(d) == 0:
            continue
        d = d / abs(d) * eps * (-1 if reverse else 1)
        _arrowhead(ax, zz[i] - d, zz[i], col)


def _complex_axes(ax, var: str) -> None:
    ax.axhline(0, color=FG, lw=0.7, zorder=1)
    ax.axvline(0, color=FG, lw=0.7, zorder=1)
    ax.set_xlabel(rf"$\mathrm{{Re}}\{{{var}\}}$")
    ax.set_ylabel(rf"$\mathrm{{Im}}\{{{var}\}}$")
    core.apply_locale(ax)


def _fit_equal(ax, box, frame: tuple[float, float] = (0.6, 0.45)):
    """Grow box to the axes' shape so equal scaling fills the figure, then fix the limits.

    frame: inches taken by tick and axis labels (horizontal, vertical); the axes box keeps
    the resulting shape exactly (adjustable='box'), so no limit is silently overridden.
    """
    (x0, x1), (y0, y1) = box
    w_in, h_in = ax.figure.get_size_inches()
    target = max(w_in - frame[0], 0.5) / max(h_in - frame[1], 0.5)
    ratio = (x1 - x0) / (y1 - y0)
    if ratio < target:
        grow = ((y1 - y0) * target - (x1 - x0)) / 2
        x0, x1 = x0 - grow, x1 + grow
    else:
        grow = ((x1 - x0) / target - (y1 - y0)) / 2
        y0, y1 = y0 - grow, y1 + grow
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")
    return (x0, x1), (y0, y1)


def _set_box(ax, pts: Sequence[complex], pad: float = 0.12, min_span: float = 1.0):
    re = [z.real for z in pts]
    im = [z.imag for z in pts]
    x0, x1, y0, y1 = min(re), max(re), min(im), max(im)
    span = max(x1 - x0, y1 - y0, min_span)
    if x1 - x0 < 0.3 * span:
        cx = (x0 + x1) / 2
        x0, x1 = cx - 0.15 * span, cx + 0.15 * span
    if y1 - y0 < 0.3 * span:
        cy = (y0 + y1) / 2
        y0, y1 = cy - 0.15 * span, cy + 0.15 * span
    box = ((x0 - pad * span, x1 + pad * span), (y0 - pad * span, y1 + pad * span))
    return _fit_equal(ax, box)


# --------------------------------------------------------------------------------------
# Nyquist
# --------------------------------------------------------------------------------------


def _frequency_grid(st: Structure, lo: float, hi: float, n: int) -> np.ndarray:
    """Log grid with extra points around lightly damped poles and zeros."""
    w = [np.logspace(math.log10(lo), math.log10(hi), n)]
    for r in (*st.poles, *st.zeros):
        if r.imag > 0 and lo < r.imag < hi:
            w.append(r.imag * (1 + np.linspace(-0.2, 0.2, 801)))
    w = np.unique(np.concatenate(w))
    axis = [abs(r.imag) for r in st.poles if r.real == 0 and r.imag != 0]
    for wa in axis:  # never evaluate exactly on a pole of the imaginary axis
        w = w[np.abs(w - wa) > 1e-9 * wa]
    return w


def _encirclements_cw(p: Plant, st: Structure, omega, H, h0, h_inf) -> int:
    """Clockwise encirclements of -1 by the image of the whole Nyquist contour.

    The mirror branch turns by the same angle as the branch for omega > 0. Poles on the
    imaginary axis are bypassed on small semicircles to their right; a k-fold pole there
    maps to a clockwise arc of k half-turns at infinity.
    """
    axis = {}
    for q in p.poles():
        if q.real == 0 and q.imag > 0:
            axis[q.imag] = axis.get(q.imag, 0) + 1
    for z in p.zeros():
        if z.real == 0 and z.imag in axis:
            axis[z.imag] -= 1
    total = 0.0
    pieces = np.split(np.arange(omega.size), np.searchsorted(omega, sorted(axis)))
    for j, idx in enumerate(pieces):
        vals = H[idx]
        if j == 0 and h0 is not None:
            vals = np.concatenate([[h0], vals])
        if j == len(pieces) - 1:
            vals = np.concatenate([vals, [h_inf]])
        if vals.size > 1:
            turns = np.unwrap(np.angle(vals + 1))
            total += float(turns[-1] - turns[0])
    half_turns = max(st.typ, 0) + 2 * sum(max(k, 0) for k in axis.values())
    return -round((2 * total - math.pi * half_turns) / (2 * math.pi))


def nyquist(
    G: TransferFunctionLike,
    mark_critical: bool = True,
    w: Sequence[float] | None = None,
    lim: float | None = None,
    name: str = "G",
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Nyquist plot of G(j omega): omega > 0 solid with arrows, the mirror branch dashed.

    w: (low, high) frequency range in rad/s; by default a wide range around all corners,
    closed with the end points G(0) and G(j inf). A range that stops short of them (a
    partial sweep) draws only G(j omega) for low <= omega <= high, without the omega = 0
    marker. Encirclements, real-axis crossings and the stability verdict in facts always
    come from the full Nyquist contour (facts: sweep, criterion_omega_range).
    lim: radius of the region kept in view when G has poles on the imaginary axis
    (the curve then runs off to infinity).
    """
    p = _continuous(G, "nyquist", proper=True)
    st = structure(p)
    freqs = _interesting_frequencies(st)
    full_lo, full_hi = min(freqs) * 1e-3, max(freqs) * 1e3
    if w is None:
        lo, hi = full_lo, full_hi
    else:
        lo, hi = float(w[0]), float(w[-1])
        if not 0 <= lo < hi:
            raise ValueError("w must be (low, high) in rad/s with 0 <= low < high")
    # The end points G(0) and G(j inf) belong to the curve only when the sweep reaches
    # them; 0 and inf themselves cannot go on a log grid and stand for the default ends.
    from_0, to_inf = lo <= full_lo, hi >= full_hi
    lo, hi = (full_lo if lo == 0 else lo), (full_hi if math.isinf(hi) else hi)
    omega = _frequency_grid(st, lo, hi, 6000)
    H = p.tf(1j * omega)
    axis_poles = [q for q in p.poles() if q.real == 0]
    h0 = None if st.typ > 0 else (0j if st.typ < 0 else complex(st.k_bode))
    h_inf = complex(st.lead) if st.rel_degree == 0 else 0j
    head = [h0] if from_0 and h0 is not None else []
    pos = np.concatenate([head, H, [h_inf] if to_inf else []]).astype(complex)

    # View: the whole curve, or (with poles on the imaginary axis) the part within radius.
    if axis_poles:
        # Size the view by the bounded part of the curve: away from the poles on the
        # imaginary axis and, with integrators, above the slowest other corner.
        keep = np.ones(omega.shape, dtype=bool)
        for q in axis_poles:
            if q.imag > 0:
                keep &= np.abs(omega / q.imag - 1) > 0.3
        if st.typ > 0:
            others = [abs(q) for q in st.poles if q.real != 0]
            keep &= omega >= (min(others) if others else np.inf)
        auto = max(3.0, 1.5 * float(np.max(np.abs(H[keep])))) if keep.any() else 3.0
        radius = lim or auto
        shown = pos[np.abs(pos) <= radius]
    else:
        radius = lim
        shown = pos if lim is None else pos[np.abs(pos) <= lim]
    pts = [*shown, *np.conj(shown), 0j]
    if mark_critical:
        pts.append(-1 + 0j)
    fig, ax = core.new_figure(size)
    box = _set_box(ax, pts, pad=0.1, min_span=0.5)
    far = 50 * max(box[0][1] - box[0][0], box[1][1] - box[1][0])
    draw = np.where(np.abs(pos) > far, np.nan, pos)
    _complex_axes(ax, rf"{name}(\mathrm{{j}}\omega)")
    ax.plot(draw.real, -draw.imag, color=color(0), lw=1.2, ls=(0, (4, 2)), zorder=3)
    ax.plot(draw.real, draw.imag, color=color(0), zorder=4)
    _arrows_along(ax, pos, (0.3, 0.7), color(0), box)
    _arrows_along(ax, np.conj(pos), (0.3, 0.7), color(0), box, reverse=True)

    if mark_critical:
        ax.plot([-1], [0], marker="+", ms=8, mew=1.6, color=color(1), zorder=8)
        ax.annotate(
            "$-1$",
            (-1, 0),
            xytext=(-3, 4),
            textcoords="offset points",
            ha="right",
            va="bottom",
            fontsize=7,
            color=FG,
        )
    if from_0 and h0 is not None and abs(h0) <= far:
        ax.plot([h0.real], [0], "o", ms=3, color=color(0), zorder=7)
        ax.annotate(
            r"$\omega = 0$",
            (h0.real, 0),
            xytext=(3, 4),
            textcoords="offset points",
            fontsize=7,
            color=FG,
        )

    # Stability: encirclements of -1 (clockwise positive) and closed-loop poles, always
    # over the full contour, whatever part of it is drawn.
    full = from_0 and to_inf
    w_crit = omega if full else _frequency_grid(st, full_lo, full_hi, 6000)
    H_crit = H if full else p.tf(1j * w_crit)
    p_rhp = int(sum(q.real > 0 for q in p.poles()))
    cl = _clean_roots(np.roots(np.polyadd(p.den, p.num)))
    z_rhp = int(sum(q.real > 0 for q in cl))
    n_cw = _encirclements_cw(p, st, w_crit, H_crit, h0, h_inf)
    crossings = []
    unit_im = H_crit.imag / np.abs(H_crit)  # sin of the phase: smooth, unlike Im G near poles
    for i in np.flatnonzero(np.sign(unit_im[:-1]) * np.sign(unit_im[1:]) < 0):
        x = brentq(
            lambda v: math.sin(cmath.phase(complex(p.tf(1j * v)))),
            w_crit[i],
            w_crit[i + 1],
            xtol=1e-14 * w_crit[i],
        )
        hx = complex(p.tf(1j * x))
        if abs(hx.imag) <= 1e-8 * abs(hx) and math.isfinite(abs(hx)):
            crossings.append({"omega": float(x), "re": hx.real})
    first = h0 if from_0 else complex(H[0])  # h0 is None: G(0) is infinite
    facts = {
        "template": "signals.nyquist",
        "G": p.as_dict(),
        "sweep": "full" if full else "partial",
        "omega_range": [float(omega[0]), float(omega[-1])],
        "criterion_omega_range": [float(w_crit[0]), float(w_crit[-1])],
        "start": None if first is None else _pair(first),
        "end": _pair(h_inf if to_inf else complex(H[-1])),
        "unbounded": bool(axis_poles),
        "view_radius": radius,
        "real_axis_crossings": crossings,
        "open_loop_rhp_poles": p_rhp,
        "encirclements_cw": n_cw,
        "closed_loop_poles": [_pair(q) for q in cl],
        "closed_loop_rhp_poles": z_rhp,
        "closed_loop_stable": bool(all(q.real < 0 for q in cl)),
        "nyquist_criterion_consistent": n_cw + p_rhp == z_rhp,
    }
    if alt is None:
        verdict = "stable" if facts["closed_loop_stable"] else "unstable"
        alt = (
            f"Nyquist plot of {name}(j omega) for G(s) = {_plain(p)}; the branch for "
            f"omega > 0 is solid with arrows for increasing omega, the mirror branch dashed"
        )
        if mark_critical:
            alt += "; the critical point -1 is marked"
        if n_cw == 0:
            turns = "does not encircle -1"
        else:
            sense = "clockwise" if n_cw > 0 else "counter-clockwise"
            turns = f"encircles -1 {abs(n_cw)} {'time' if abs(n_cw) == 1 else 'times'} {sense}"
        if full:
            alt += f"; the curve {turns}; the closed loop is {verdict}."
        else:
            alt += (
                f"; only omega from {omega[0]:.3g} to {omega[-1]:.3g} rad/s is drawn; the full "
                f"Nyquist curve {turns} and the closed loop is {verdict}."
            )
    return core.finish(fig, alt, facts)


# --------------------------------------------------------------------------------------
# Pole-zero map and root locus
# --------------------------------------------------------------------------------------


def _stability_hint(ax, discrete: bool, box) -> None:
    hint = color(2)
    label = _tr("stabil", "stable")
    if discrete:
        ax.add_patch(Circle((0, 0), 1, facecolor=hint, alpha=0.10, edgecolor="none", zorder=0))
        ax.add_patch(Circle((0, 0), 1, fill=False, edgecolor=MUTED, lw=0.9, ls="--", zorder=2))
        ax.annotate(
            label,
            (math.cos(math.radians(225)), math.sin(math.radians(225))),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7,
            color=FG,
        )
    else:
        x0 = box[0][0]
        ax.axvspan(min(x0, 0) - 1e3 * abs(x0 or 1), 0, color=hint, alpha=0.08, lw=0, zorder=0)
        ax.annotate(
            label,
            (0, 1),
            xycoords=("data", "axes fraction"),
            xytext=(-4, -4),
            textcoords="offset points",
            ha="right",
            va="top",
            fontsize=7,
            color=FG,
        )


def _mark_roots(ax, poles, zeros, pole_color: str, zero_color: str) -> None:
    for roots, marker, col in ((poles, "x", pole_color), (zeros, "o", zero_color)):
        for r, mult in _group_roots(roots):
            style = {"ms": 7, "mew": 1.6, "color": col, "zorder": 8}
            if marker == "o":
                style.update(ms=6, mfc=BG, mew=1.4)
            ax.plot([r.real], [r.imag], marker, ls="none", **style)
            if mult > 1:
                ax.annotate(
                    f"({mult})",
                    (r.real, r.imag),
                    xytext=(4, 4),
                    textcoords="offset points",
                    fontsize=7,
                    color=FG,
                )


def _root_facts(roots, discrete: bool) -> list[dict]:
    out = []
    for r, mult in _group_roots(roots):
        entry = {"value": _pair(r), "multiplicity": mult, "magnitude": abs(r)}
        if not discrete and r.imag != 0:
            wn = abs(r)
            entry.update(omega_n=wn, zeta=-r.real / wn)
        out.append(entry)
    return out


def pole_zero(
    G: TransferFunctionLike,
    discrete: bool = False,
    stability: bool = True,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Pole-zero map: poles as x, zeros as o, multiplicities in brackets.

    discrete: z-plane with the unit circle (implied when G is a function of z).
    stability: shade the stability region (left half-plane or inside the unit circle).
    """
    p = plant(G)
    discrete = discrete or p.discrete
    var = "z" if discrete else "s"
    poles, zeros = p.poles(), p.zeros()
    fig, ax = core.new_figure(size)
    pts = [*poles, *zeros, 0j]
    if discrete:
        pts += [1, -1, 1j, -1j]
    box = _set_box(ax, pts, pad=0.18, min_span=2.0 if discrete else 1.0)
    _complex_axes(ax, var)
    if stability:
        _stability_hint(ax, discrete, box)
    elif discrete:
        ax.add_patch(Circle((0, 0), 1, fill=False, edgecolor=MUTED, lw=0.9, ls="--", zorder=2))
    _mark_roots(ax, poles, zeros, color(1), color(0))
    stable = bool(all(abs(q) < 1 for q in poles) if discrete else all(q.real < 0 for q in poles))
    facts = {
        "template": "signals.pole_zero",
        "G": p.as_dict(),
        "discrete": discrete,
        "poles": _root_facts(poles, discrete),
        "zeros": _root_facts(zeros, discrete),
        "stable": stable,
    }
    if not discrete and stable:
        facts["dc_gain"] = float(np.real(ct.dcgain(p.tf)))
    if alt is None:

        def fmt(rs):
            return (
                ", ".join(
                    f"{_complex_str(r)}" + (f" ({m}x)" if m > 1 else "")
                    for r, m in _group_roots(rs)
                )
                or "none"
            )

        region = "inside the unit circle" if discrete else "in the left half-plane"
        alt = (
            f"Pole-zero map of G({var}) = {_plain(p)} in the {var}-plane: poles (x) at "
            f"{fmt(poles)}; zeros (o) at {fmt(zeros)}; the system is "
            f"{'stable' if stable else 'not stable'} (all poles {region} required)."
        )
    return core.finish(fig, alt, facts)


def _complex_str(r: complex) -> str:
    if r.imag == 0:
        return f"{r.real:.4g}"
    sign = "+" if r.imag > 0 else "-"
    return f"{r.real:.4g} {sign} {abs(r.imag):.4g}j"


def _imag_axis_crossings(p: Plant) -> list[dict]:
    """Gains K > 0 where 1 + K G(s) has roots on the imaginary axis (s = j omega)."""
    k = np.arange(len(p.den) - 1, -1, -1)
    den_jw = p.den * (1j**k)  # coefficients of den(j omega) in omega
    kn = np.arange(len(p.num) - 1, -1, -1)
    num_mjw = p.num * ((-1j) ** kn)  # num(-j omega) = conj(num(j omega))
    prod = np.polymul(den_jw, num_mjw)
    im = np.trim_zeros(np.imag(prod), "f")
    out = []
    if im.size == 0:
        return out
    omegas = [0.0] if abs(im[-1]) < TINY else []
    if im.size > 1:
        for r in np.roots(im):
            if abs(r.imag) < 1e-7 * max(1, abs(r)) and r.real > 1e-9:
                omegas.append(float(r.real))
    for om in sorted(set(round(x, 12) for x in omegas)):
        nj = np.polyval(p.num, 1j * om)
        if abs(nj) < TINY:
            continue
        kk = -np.polyval(p.den, 1j * om) / nj
        if abs(kk.imag) < 1e-6 * max(1, abs(kk)) and kk.real > 0:
            out.append({"k": float(kk.real), "omega": float(om)})
    return out


def _breakaway(p: Plant) -> list[dict]:
    poly = np.polysub(np.polymul(p.num, np.polyder(p.den)), np.polymul(p.den, np.polyder(p.num)))
    poly = np.trim_zeros(poly, "f")
    out = []
    if poly.size < 2:
        return out
    for r in np.roots(poly):
        if abs(r.imag) > 1e-7 * max(1, abs(r)):
            continue
        s = float(r.real)
        nv = np.polyval(p.num, s)
        if abs(nv) < TINY:
            continue
        k = -np.polyval(p.den, s) / nv
        if k > 0:
            out.append({"s": s, "k": float(k)})
    return sorted(out, key=lambda e: e["s"])


def root_locus(
    G: TransferFunctionLike,
    gains: Sequence[float] | np.ndarray | None = None,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Root locus of 1 + K G = 0 over K >= 0, with open-loop poles (x) and zeros (o).

    Also computed and marked: asymptotes (centroid and angles), breakaway points and,
    for continuous systems, the critical gain where branches cross the imaginary axis.
    """
    p = plant(G)
    discrete = p.discrete
    var = "z" if discrete else "s"
    rl = ct.root_locus_map(p.tf, None if gains is None else np.asarray(gains, dtype=float))
    loci = np.asarray(rl.loci, dtype=complex)
    ks = np.asarray(rl.gains, dtype=float)
    poles, zeros = p.poles(), p.zeros()
    n, m = len(poles), len(zeros)
    st_pts: list[complex] = [*poles, *zeros, 0j]
    asym = None
    if n > m:
        centroid = float((np.sum(poles) - np.sum(zeros)).real / (n - m))
        angles = [(2 * q + 1) * 180.0 / (n - m) for q in range(n - m)]
        asym = {"centroid": centroid, "angles_deg": angles}
        if n - m > 1:
            st_pts.append(complex(centroid))
    crossings = [] if discrete else _imag_axis_crossings(p)
    for c in crossings:
        st_pts += [complex(0, c["omega"]), complex(0, -c["omega"])]
    breaks = _breakaway(p)
    st_pts += [complex(b["s"]) for b in breaks]
    if discrete:
        st_pts += [1, -1, 1j, -1j]

    fig, ax = core.new_figure(size)
    box = _set_box(ax, st_pts, pad=0.35, min_span=2.0 if discrete else 1.0)
    span = max(box[0][1] - box[0][0], box[1][1] - box[1][0])
    _complex_axes(ax, var)
    if discrete:
        ax.add_patch(Circle((0, 0), 1, fill=False, edgecolor=MUTED, lw=0.9, ls="--", zorder=2))
    drawn: list[np.ndarray] = []  # polylines (complex) the K_crit label must keep clear of
    if asym is not None and n - m >= 1:
        for a in asym["angles_deg"]:
            if a % 180 == 0:  # lies on the real axis, which is drawn anyway
                continue
            d = cmath.exp(1j * math.radians(a)) * 10 * span
            c0 = asym["centroid"]
            ax.plot([c0, c0 + d.real], [0, d.imag], color=MUTED, lw=0.8, ls=(0, (4, 2)), zorder=2)
            drawn.append(np.array([c0, c0 + d / 5]))  # 2 spans: beyond the view
    for j in range(loci.shape[1]):
        branch = loci[:, j]
        ax.plot(branch.real, branch.imag, color=color(0), zorder=4)
        _arrows_along(ax, branch, (0.5,), color(0), box)
        drawn.append(branch)
    for c in crossings:
        for sgn in (1, -1):
            ax.plot([0], [sgn * c["omega"]], "o", ms=3.5, color=FG, zorder=9)
    for b in breaks:
        ax.plot([b["s"]], [0], "o", ms=3, color=color(0), zorder=9)
    _mark_roots(ax, poles, zeros, color(1), color(0))
    ax.set_xlim(*box[0])
    ax.set_ylim(*box[1])
    if crossings:
        (x0, x1), (y0, y1) = box
        drawn += [np.array([x0, x1], dtype=complex), np.array([1j * y0, 1j * y1])]  # axes
        if discrete:
            drawn.append(np.exp(1j * np.linspace(0, 2 * math.pi, 181)))
        marks = [*poles, *zeros, *(complex(b["s"]) for b in breaks)]
        marks += [complex(0, sgn * c["omega"]) for c in crossings for sgn in (1, -1)]
        ax.figure.draw_without_rendering()
        avoid = np.concatenate([polyline_points(ax, z) for z in drawn] + [marker_points(ax, marks)])
        c = max(crossings, key=lambda e: e["omega"])
        at = (0.0, c["omega"])
        sym = r"K_\mathrm{krit}" if core.locale() == "de" else r"K_\mathrm{crit}"
        place(
            ax,
            f"${sym} = {_num_tex(c['k'])}$",
            [  # beside the crossing, never across the imaginary axis it sits on
                {"xy": at, "xytext": (dx, dy), "ha": ha, "va": va}
                for dx, ha in ((5, "left"), (-5, "right"))
                for dy, va in ((3, "bottom"), (-3, "top"), (0, "center"))
            ],
            avoid,
            [],
            [at, at],
            color=FG,
            fontsize=7,
        )

    cl_check = []
    for c in crossings:
        cl = np.roots(np.polyadd(p.den, c["k"] * p.num))
        cl_check.append(float(np.min(np.abs(cl - 1j * c["omega"]))))
    facts = {
        "template": "signals.root_locus",
        "G": p.as_dict(),
        "discrete": discrete,
        "gain_range": [float(ks.min()), float(ks.max())],
        "open_loop_poles": [_pair(q) for q in poles],
        "open_loop_zeros": [_pair(q) for q in zeros],
        "asymptotes": asym,
        "breakaway": breaks,
        "imag_axis_crossings": crossings,
        "imag_axis_crossing_residuals": cl_check,
        "k_crit": min((c["k"] for c in crossings), default=None),
    }
    if not discrete and crossings:
        gm = ct.stability_margins(p.tf)[0]
        facts["k_crit_check_gm"] = _number(gm)
    if alt is None:
        alt = (
            f"Root locus of 1 + K G({var}) = 0 with G({var}) = {_plain(p)}: {n} branches start "
            f"at the open-loop poles (x) and {m} end at the zeros (o)"
        )
        if n - m == 1:
            alt += ", 1 runs to infinity along the negative real axis"
        elif n > m:
            alt += f", {n - m} run to infinity along asymptotes from {asym['centroid']:.3g}"
        if facts["k_crit"] is not None:
            alt += f"; branches cross the imaginary axis at K = {facts['k_crit']:.4g}"
        alt += "."
    return core.finish(fig, alt, facts)


# --------------------------------------------------------------------------------------
# Step response
# --------------------------------------------------------------------------------------


def _first_crossing(t: np.ndarray, r: np.ndarray, level: float) -> float | None:
    idx = np.flatnonzero(r >= level)
    if idx.size == 0:
        return None
    i = int(idx[0])
    if i == 0:
        return float(t[0])
    return float(t[i - 1] + (t[i] - t[i - 1]) * (level - r[i - 1]) / (r[i] - r[i - 1]))


def step_metrics(t: np.ndarray, y: np.ndarray, final: float, band: float = 0.02) -> dict:
    """Overshoot (%), peak, 10-90 % rise time and settling time into +-band of `final`.

    Crossings are linearly interpolated and the peak is refined with a parabola through
    the three samples around the maximum.
    """
    r = y / final
    t10, t90 = _first_crossing(t, r, 0.1), _first_crossing(t, r, 0.9)
    i = int(np.argmax(r))
    t_peak, r_peak = float(t[i]), float(r[i])
    if 0 < i < len(r) - 1:
        a, b, c = r[i - 1], r[i], r[i + 1]
        denom = a - 2 * b + c
        if denom < 0:
            shift = 0.5 * (a - c) / denom
            h = t[i + 1] - t[i]
            t_peak = float(t[i] + shift * h)
            r_peak = float(b - 0.25 * (a - c) * shift)
    overshoot = max(0.0, (r_peak - 1) * 100)
    err = np.abs(r - 1) - band
    outside = np.flatnonzero(err > 0)
    if outside.size == 0:
        t_s: float | None = float(t[0])
    elif outside[-1] == len(r) - 1:
        t_s = None
    else:
        k = int(outside[-1])
        t_s = float(t[k] + (t[k + 1] - t[k]) * err[k] / (err[k] - err[k + 1]))
    return {
        "final": final,
        "overshoot_percent": overshoot,
        "peak": r_peak * final if overshoot > 0 else None,
        "peak_time": t_peak if overshoot > 0 else None,
        "t10": t10,
        "t90": t90,
        "rise_time": (t90 - t10) if t10 is not None and t90 is not None else None,
        "settling_time": t_s,
        "settling_band": band,
    }


def _nice_ceil(x: float) -> float:
    exp = math.floor(math.log10(x))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * 10**exp >= x * (1 - 1e-12):
            return m * 10**exp
    return 10 ** (exp + 1)


def step_response(
    G: TransferFunctionLike,
    t: Sequence[float] | np.ndarray | None = None,
    annotate: Sequence[str] = ANNOTATIONS,
    settling_band: float = 0.02,
    unit: str = "s",
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Step response h(t) with computed annotations.

    t: time grid or (start, end); by default long enough to show settling.
    annotate: any of 'final', 'overshoot', 'rise' (10-90 %), 'settling' (+-settling_band).
    """
    unknown = set(annotate) - set(ANNOTATIONS)
    if unknown:
        raise ValueError(f"unknown annotation {sorted(unknown)}; use {ANNOTATIONS}")
    p = _continuous(G, "step_response", proper=True)
    poles = p.poles()
    stable = bool(all(q.real < 0 for q in poles))
    final = float(np.real(ct.dcgain(p.tf))) if stable else None
    use = final is not None and abs(final) > 1e-12

    def simulate(tt):
        resp = ct.step_response(p.tf, tt)
        return np.asarray(resp.time, dtype=float), np.asarray(resp.outputs, dtype=float)

    if t is None:
        t_end = float(ct.step_response(p.tf).time[-1])
        tt = np.linspace(0, t_end, 4001)
        if use:
            for _ in range(6):
                info = step_metrics(*simulate(tt), final, settling_band)
                ts = info["settling_time"]
                if ts is not None and ts < 0.85 * t_end:
                    break
                t_end *= 2
                tt = np.linspace(0, t_end, 4001)
            ts = info["settling_time"] or 0.0
            need = max(ts, info["peak_time"] or 0.0, info["t90"] or 0.0)
            if need > 0:
                tt = np.linspace(0, _nice_ceil(1.5 * need), 4001)
    else:
        tt = np.asarray(t, dtype=float)
        if tt.size == 2:
            tt = np.linspace(tt[0], tt[1], 4001)
    time, y = simulate(tt)
    info = step_metrics(time, y, final, settling_band) if use else None
    _, y_scipy = sps.step((p.num, p.den), T=time)

    scale, shown_unit = _time_display(float(np.max(np.abs(time))), unit)
    fig, ax = core.new_figure(size)
    ax.plot(time * scale, y, color=color(0), zorder=4)
    de = core.locale() == "de"
    hname = "h" if de else "y"
    y_lo, y_hi = min(0.0, float(y.min())), max(0.0, float(y.max()))
    if info is not None:
        y_lo = min(y_lo, final * (1 - settling_band))
        y_hi = max(y_hi, final * (1 + settling_band))
    ax.set_xlim(time[0] * scale, time[-1] * scale)
    pad = 0.12 * (y_hi - y_lo or 1)
    ax.set_ylim(y_lo - (pad if y_lo < 0 else 0.03 * (y_hi - y_lo)), y_hi + pad)
    ax.set_xlabel(core.axis_label("t", _unit_text(shown_unit)))
    ax.set_ylabel(f"${hname}(t)$")
    core.apply_locale(ax)
    if info is not None:
        _annotate_step(ax, info, annotate, scale, shown_unit, hname, (time * scale, y))

    info_ctl = ct.step_info(p.tf, time, SettlingTimeThreshold=settling_band) if use else None
    facts = {
        "template": "signals.step_response",
        "G": p.as_dict(),
        "stable": stable,
        "t_range": [float(time[0]), float(time[-1])],
        "time_axis": {"unit": shown_unit, "scale": scale},
        "metrics": info,
        "final_sample": float(y[-1]),
        "scipy_max_abs_diff": float(np.max(np.abs(y - y_scipy))),
        "step_info": {k: float(v) for k, v in info_ctl.items()} if info_ctl else None,
        "annotate": list(annotate) if info is not None else [],
    }
    if alt is None:
        label = "µs" if shown_unit == "us" else (shown_unit or "")

        def at(seconds: float) -> str:
            return f"{seconds * scale:.3g} {label}".rstrip()

        alt = f"Step response of G(s) = {_plain(p)} for t from {at(time[0])} to {at(time[-1])}"
        if info is not None:
            bits = [f"final value {final:.4g}"]
            if info["overshoot_percent"] > 0:
                os_ = info["overshoot_percent"]
                bits.append(f"overshoot {os_:.3g} % at t = {at(info['peak_time'])}")
            if info["rise_time"] is not None:
                bits.append(f"10-90 % rise time {at(info['rise_time'])}")
            if info["settling_time"] is not None:
                ts = info["settling_time"]
                bits.append(f"{settling_band * 100:g} % settling time {at(ts)}")
            alt += ": " + ", ".join(bits)
        elif not stable:
            alt += "; the system is unstable"
        alt += "."
    return core.finish(fig, alt, facts)


TIME_SCALES = ((1.0, "s"), (1e3, "ms"), (1e6, "us"), (1e9, "ns"))


def _time_display(t_max: float, unit: str | None) -> tuple[float, str | None]:
    """Times are given in seconds; show them in s, ms, us or ns, whichever reads best."""
    if unit != "s" or t_max <= 0:
        return 1.0, unit
    for scale, name in TIME_SCALES:
        if t_max * scale >= 0.2:
            return scale, name
    return TIME_SCALES[-1]


def _unit_text(unit: str | None) -> str | None:
    return r"$\mu$s" if unit == "us" else unit


def _unit_math(unit: str | None) -> str:
    if not unit:
        return ""
    return r"\,\mu\mathrm{s}" if unit == "us" else rf"\,\mathrm{{{unit}}}"


def _annotate_step(
    ax,
    info: dict,
    annotate: Sequence[str],
    scale: float,
    unit: str | None,
    hname: str,
    curve: tuple[np.ndarray, np.ndarray],
) -> None:
    """Draw the marks first, then place every label clear of all of them."""
    de = core.locale() == "de"
    final = info["final"]
    u = _unit_math(unit)
    up = final > 0  # labels go below a level the response approaches from below
    ax.figure.draw_without_rendering()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    avoid = [ax.transData.transform(np.column_stack(curve))]
    labels: list[tuple] = []  # (text, options, target, colour), placed in this order
    small = {"fontsize": 7}

    if "overshoot" in annotate and info["overshoot_percent"] > 0.05:
        tp, yp = info["peak_time"] * scale, info["peak"]
        ax.plot([tp], [yp], "o", ms=3, color=color(1), zorder=6)
        _double_arrow(ax, (tp, final), (tp, yp), color(1), lw=0.9)
        avoid.append(segment_points(ax, (tp, final), (tp, yp)))
        sym = r"\ddot{u}" if de else r"M_\mathrm{p}"
        mid = (tp, (final + yp) / 2)
        labels.append(
            (
                rf"${sym} = {_num_tex(info['overshoot_percent'])}\,\%$",
                [  # beyond the peak first: nothing of the curve lies further out
                    {
                        "xy": (tp, yp),
                        "xytext": (dx, 3 if up else -3),
                        "ha": ha,
                        "va": "bottom" if up else "top",
                    }
                    for dx, ha in ((4, "left"), (0, "center"), (-4, "right"))
                ]
                + [
                    {"xy": mid, "xytext": (4, 0), "ha": "left", "va": "center"},
                    {"xy": mid, "xytext": (-4, 0), "ha": "right", "va": "center"},
                ],
                [(tp, final), (tp, yp)],
                FG,
            )
        )
    if "rise" in annotate and info["rise_time"] is not None:
        t10, t90 = info["t10"] * scale, info["t90"] * scale
        y10, y90 = 0.1 * final, 0.9 * final
        # c4: c5 and c6 have less than 3:1 contrast on white (WCAG 1.4.11)
        ax.plot([t10, t90], [y10, y90], "o", ms=3, color=color(3), zorder=6)
        ax.plot([t10, t10], [y10, y90], color=color(3), lw=0.8, ls=":", zorder=3)
        _double_arrow(ax, (t10, y90), (t90, y90), color(3), lw=0.9)
        avoid += [
            segment_points(ax, (t10, y10), (t10, y90)),
            segment_points(ax, (t10, y90), (t90, y90)),
        ]
        va = "top" if up else "bottom"
        labels.append(
            (
                rf"$t_\mathrm{{r}} = {_num_tex(info['rise_time'] * scale)}{u}$",
                [
                    {"xy": (t90, y90), "xytext": (5, -1 if up else 1), "ha": "left", "va": va},
                    {"xy": (t90, 0.5 * final), "xytext": (5, 0), "ha": "left", "va": "center"},
                    {"xy": (t10, y90), "xytext": (-4, 0), "ha": "right", "va": "center"},
                ],
                [(t10, y90), (t90, y90)],
                FG,
            )
        )
    if "final" in annotate:
        ax.axhline(final, color=MUTED, lw=0.9, ls=(0, (4, 2)), zorder=2)
        avoid.append(segment_points(ax, (x0, final), (x1, final), 200))
        right = {"xy": (1, final), "xycoords": ("axes fraction", "data"), "ha": "right"}
        labels.append(
            (
                f"${hname}_\\infty = {_num_tex(final)}$",
                [
                    {**right, "xytext": (-2, -4 if up else 4), "va": "top" if up else "bottom"},
                    {**right, "xytext": (-2, 4 if up else -4), "va": "bottom" if up else "top"},
                ],
                [(x0, final), (x1, final)],
                MUTED,
            )
        )
    if "settling" in annotate and info["settling_time"] is not None:
        band = info["settling_band"]
        lo, hi = sorted((final * (1 - band), final * (1 + band)))
        ax.axhspan(lo, hi, color=color(2), alpha=0.15, lw=0, zorder=1)
        ts = info["settling_time"] * scale
        ax.axvline(ts, color=color(2), lw=0.9, ls=":", zorder=2)
        avoid.append(segment_points(ax, (ts, y0), (ts, y1), 200))
        sym = r"t_\mathrm{aus}" if de else r"t_\mathrm{s}"
        labels.append(
            (
                f"${sym} = {_num_tex(ts)}{u}$",
                [
                    {"xy": (ts, f * final), "xytext": (dx, 0), "ha": ha, "va": "center"}
                    for f in (0.25, 0.5, 0.1, 0.4, 0.65)
                    for dx, ha in ((3, "left"), (-3, "right"))
                ],
                [(ts, y0), (ts, y1)],
                FG,
            )
        )
    points = np.concatenate(avoid)
    placed: list = []
    for text, options, target, col in labels:
        place(ax, text, options, points, placed, target, color=col, **small)


# --------------------------------------------------------------------------------------
# Phasors
# --------------------------------------------------------------------------------------


def _phasor_tex(name: str) -> str:
    """'U_R' -> '$\\underline{U}_R$'; names already in $...$ are used as they are."""
    if name.startswith("$"):
        return name
    base, _, sub = name.partition("_")
    sub = sub if not sub or sub.startswith("{") else f"{{{sub}}}"
    return f"$\\underline{{{base}}}" + (f"_{sub}$" if sub else "$")


def _label_offset(direction: complex, dist: float = 7.0) -> dict:
    d = direction / abs(direction) if abs(direction) else 1j
    ha = "left" if d.real > 0.35 else "right" if d.real < -0.35 else "center"
    va = "bottom" if d.imag > 0.35 else "top" if d.imag < -0.35 else "center"
    return {"xytext": (dist * d.real, dist * d.imag), "ha": ha, "va": va}


def _shared(a0: complex, a: complex, b0: complex, b: complex, tol: float):
    """Stretch (t1, t2) of segment a0 -> a0 + a, measured from a0 along a, that segment
    b0 -> b0 + b runs along on the same line; None if the two share no such stretch."""
    if abs(a) == 0 or abs(b) == 0:
        return None
    u = a / abs(a)
    if abs((u.conjugate() * b).imag) > 1e-6 * abs(b) or abs((u.conjugate() * (b0 - a0)).imag) > tol:
        return None
    t1, t2 = sorted(((u.conjugate() * (b0 - a0)).real, (u.conjugate() * (b0 + b - a0)).real))
    lo, hi = max(0.0, t1), min(abs(a), t2)
    return (lo, hi) if hi - lo > tol else None


def _chain_offsets(
    starts: Sequence[complex], comps: Sequence[complex], centre: complex, span: float
) -> tuple[list[complex], dict[int, list[tuple[float, float]]]]:
    """Sideways shifts for chained phasors that would run back over an earlier one.

    U_C after U_L in a series RLC diagram points straight back down U_L and would hide
    it; as in textbooks it is drawn beside it, shifted along its normal to the outer side
    (away from the diagram's centre) by a few per cent of the diagram, further if that
    spot is taken too. Returns the shifts and, per covered phasor, the stretches that a
    shifted phasor runs alongside (for placing its name). Start and tip stay exact.
    """
    step = 0.035 * span
    tol = 1e-9 * span
    offsets = [0j] * len(comps)
    covered: dict[int, list[tuple[float, float]]] = {}
    for i, c in enumerate(comps):
        if abs(c) == 0:
            continue
        drawn = [(starts[j] + offsets[j], comps[j]) for j in range(i)]
        hits = {j: _shared(a0, a, starts[i], c, tol) for j, (a0, a) in enumerate(drawn)}
        hits = {j: h for j, h in hits.items() if h is not None}
        if not hits:
            continue
        normal = 1j * c / abs(c)
        if (normal.conjugate() * (starts[i] + c / 2 - centre)).real < 0:
            normal = -normal
        for k in range(1, 6):
            shift = k * step * normal
            if all(_shared(a0, a, starts[i] + shift, c, tol) is None for a0, a in drawn):
                break
        offsets[i] = shift
        for j, h in hits.items():
            covered.setdefault(j, []).append(h)
    return offsets, covered


def _free_stretch(length: float, taken: list[tuple[float, float]]) -> tuple[float, float]:
    """Longest part of [0, length] outside the taken stretches."""
    gaps, at = [], 0.0
    for lo, hi in sorted(taken):
        gaps.append((at, lo))
        at = max(at, hi)
    gaps.append((at, length))
    return max(gaps, key=lambda g: g[1] - g[0])


def _inside(a, b, box) -> float:
    """Length of the segment a -> b (display coordinates) that runs inside `box` (clipped)."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - box.x0), (dx, box.x1 - x0), (-dy, y0 - box.y0), (dy, box.y1 - y0)):
        if p == 0:
            if q < 0:
                return 0.0
        elif p < 0:
            t0 = max(t0, q / p)
        else:
            t1 = min(t1, q / p)
        if t0 >= t1:
            return 0.0
    return (t1 - t0) * math.hypot(dx, dy)


@dataclass
class _Scene:
    """What a phasor diagram's labels must stay clear of: lines (data coordinates) and texts.

    The axes count half: a name across an axis reads better than one across a phasor.
    """

    fig: object
    ax: object
    lines: list[tuple[complex, complex]] = field(default_factory=list)
    axes: list[tuple[complex, complex]] = field(default_factory=list)
    texts: list = field(default_factory=list)

    def clash(self, label, extra: Sequence[tuple[complex, complex]] = ()) -> float:
        """How badly `label` collides: the length of lines through it plus overlapped text (px).

        `extra`: lines of a layout being tried (an angle arc), counted like phasors.
        """
        renderer = self.fig.canvas.get_renderer()
        box = label.get_window_extent(renderer).padded(2.0)
        to_px = self.ax.transData.transform

        def through(lines: list[tuple[complex, complex]]) -> float:
            return sum(
                _inside(to_px((a.real, a.imag)), to_px((b.real, b.imag)), box) for a, b in lines
            )

        score = through([*self.lines, *extra]) + 0.5 * through(self.axes)
        for other in self.texts:
            if other is label:
                continue
            o = other.get_window_extent(renderer)
            w = min(box.x1, o.x1) - max(box.x0, o.x0)
            h = min(box.y1, o.y1) - max(box.y0, o.y0)
            if w > 0 and h > 0:
                score += math.sqrt(w * h)
        return score


def _put(label, at: complex, direction: complex, dist: float = 7.0) -> None:
    """Move an annotation to `at`, offset by `dist` points along `direction` (_label_offset)."""
    offset = _label_offset(direction, dist)
    label.xy = (at.real, at.imag)
    label.xyann = offset["xytext"]
    label.set_horizontalalignment(offset["ha"])
    label.set_verticalalignment(offset["va"])


@dataclass(frozen=True)
class _Layout:
    """Places for some labels, tried together: (label, at, direction, dist) for _put each."""

    places: Sequence[tuple]
    lines: Sequence[tuple[complex, complex]] = ()  # drawn only with this layout (an arc)
    cost: float = 0.0  # px added to its clash score: a less natural place


def _place(scene: _Scene, layouts: Sequence[_Layout]) -> int:
    """Apply the first layout whose labels clash with nothing, else the least bad one.

    Scores within half a pixel count as equal, so the earlier layout wins a tie; returns
    the index of the layout applied.
    """
    scene.fig.draw_without_rendering()  # fixes the equal-aspect axes box and the renderer
    best, best_score = 0, math.inf
    for k, layout in enumerate(layouts):
        for spot in layout.places:
            _put(*spot)
        score = layout.cost + sum(scene.clash(spot[0], layout.lines) for spot in layout.places)
        if score == 0:
            return k
        if score < best_score - 0.5:
            best, best_score = k, score
    for spot in layouts[best].places:
        _put(*spot)
    return best


def _arc_lines(radius: float, a0: float, a1: float, n: int = 16) -> list[tuple[complex, complex]]:
    """An arc around the origin (degrees a0 to a1) as n straight pieces, for clash scores."""
    pts = [radius * cmath.exp(1j * math.radians(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
    return list(itertools.pairwise(pts))


def _reference(reference: Mapping[str, tuple[float, float]]) -> tuple[str, float, float]:
    if len(reference) != 1:
        raise ValueError("reference takes one phasor, e.g. {'I': (2, 0)}")
    ((name, (mag, ang)),) = reference.items()
    if mag <= 0:
        raise ValueError(f"magnitude of the reference {name} must be > 0")
    return name, float(mag), float(ang)


def phasor(
    vectors: Mapping[str, tuple[float, float]],
    chain: bool = False,
    total: str | None = None,
    show_angle: bool = True,
    size: str = "col",
    alt: str | None = None,
    reference: Mapping[str, tuple[float, float]] | None = None,
    angle_name: str = r"\varphi",
) -> core.Figure:
    """Phasor diagram in the complex plane: {name: (magnitude, angle in degrees)}.

    chain: draw the phasors head to tail and their sum from the origin (U_R + U_L = U);
    `total` names the sum (default: the common letter, e.g. 'U'), `show_angle` marks its
    phase angle, named `angle_name` (TeX, e.g. '\\varphi_u'). Names are rendered
    underlined: 'U_R' -> U_R with an underlined U.

    reference: one phasor of another quantity that the others refer to, drawn to its own
    scale, e.g. {'I': (2, 0)}, the current of a series circuit. It runs from the origin
    along its angle, shifted beside that axis to the side away from the diagram, so it
    hides nothing; the names of phasors on that axis move to the other side, and the phase
    angle is measured from the reference.

    The reference's name and the angle's name are placed clear of the phasors, the axes
    and the other names where the diagram leaves room (a long angle name in a narrow
    angle goes beside the sum, outside the angle).
    """
    if not vectors:
        raise ValueError("phasor needs at least one vector")
    ref = _reference(reference) if reference is not None else None
    names = list(vectors)
    comps = []
    for nm in names:
        mag, ang = vectors[nm]
        if mag < 0:
            raise ValueError(f"magnitude of {nm} must be >= 0")
        comps.append(float(mag) * cmath.exp(1j * math.radians(float(ang))))
    starts = list(np.cumsum([0j, *comps[:-1]])) if chain else [0j] * len(comps)
    tips = [s + c for s, c in zip(starts, comps, strict=True)]
    resultant = complex(sum(comps))
    if total is None:
        bases = {nm.partition("_")[0] for nm in names}
        total = bases.pop() if len(bases) == 1 and not names[0].startswith("$") else r"\Sigma"

    fig, ax = core.new_figure(size)
    ax.set_axis_off()
    pts = [0j, *starts, *tips]
    re_lo, re_hi = min(z.real for z in pts), max(z.real for z in pts)
    im_lo, im_hi = min(z.imag for z in pts), max(z.imag for z in pts)
    span = max(re_hi - re_lo, im_hi - im_lo, 1e-9)
    centre = complex(np.mean(pts))
    offsets, covered = (
        _chain_offsets(starts, comps, centre, span) if chain else ([0j] * len(comps), {})
    )
    pts += [s + o for s, o in zip(starts, offsets, strict=True) if o]
    pts += [t + o for t, o in zip(tips, offsets, strict=True) if o]
    ref_dir = cmath.exp(1j * math.radians(ref[2])) if ref else 1 + 0j
    ref_side = 0j  # unit normal of the reference axis pointing to the reference phasor
    if ref:
        # Own scale: about half of the diagram's extent along the reference axis.
        along = max((ref_dir.conjugate() * z).real for z in pts)
        ref_len = 0.45 * (along if along > 0.2 * span else span)
        ref_side = 1j * ref_dir
        if (ref_side.conjugate() * centre).real > 0:  # the diagram lies on that side
            ref_side = -ref_side
        ref_start = 0.07 * span * ref_side
        ref_tip = ref_start + ref_len * ref_dir
        pts += [ref_start, ref_tip]
    re_lo, re_hi = min(z.real for z in pts), max(z.real for z in pts)
    im_lo, im_hi = min(z.imag for z in pts), max(z.imag for z in pts)
    pad = 0.18 * span
    box = ((min(re_lo, 0) - pad, re_hi + pad), (min(im_lo, 0) - pad, im_hi + pad))
    box = _fit_equal(ax, box, frame=(0.1, 0.1))
    axis_style = {"arrowstyle": "-|>", "mutation_scale": 8, "color": FG, "lw": 0.8}
    ax.add_patch(
        FancyArrowPatch((box[0][0], 0), (box[0][1], 0), shrinkA=0, shrinkB=0, **axis_style)
    )
    ax.add_patch(
        FancyArrowPatch((0, box[1][0]), (0, box[1][1]), shrinkA=0, shrinkB=0, **axis_style)
    )
    scene = _Scene(fig, ax)
    scene.axes += [(complex(box[0][0], 0), complex(box[0][1], 0))]
    scene.axes += [(complex(0, box[1][0]), complex(0, box[1][1]))]
    re_label = ax.annotate(
        r"$\mathrm{Re}$",
        (box[0][1], 0),
        xytext=(0, -4),
        textcoords="offset points",
        ha="right",
        va="top",
        fontsize=8,
        color=FG,
    )
    im_label = ax.annotate(
        r"$\mathrm{Im}$",
        (0, box[1][1]),
        xytext=(-4, 0),
        textcoords="offset points",
        ha="right",
        va="top",
        fontsize=8,
        color=FG,
    )

    scene.texts += [re_label, im_label]
    inner = None  # (label, start, phasor, side) of a name moved off the reference at the origin
    for i, (nm, s0, c) in enumerate(zip(names, starts, comps, strict=True)):
        col = color(i)
        s = s0 + offsets[i]  # drawn start: shifted sideways off a phasor it would cover
        moved = False
        if abs(c) > 0:
            ax.add_patch(
                FancyArrowPatch(
                    (s.real, s.imag),
                    ((s + c).real, (s + c).imag),
                    arrowstyle="-|>",
                    mutation_scale=10,
                    color=col,
                    lw=1.6,
                    shrinkA=0,
                    shrinkB=0,
                    zorder=5,
                )
            )
            scene.lines.append((s, s + c))
        if chain:
            mid = s + c / 2
            normal = 1j * c / abs(c) if abs(c) else 1j
            if (normal.conjugate() * (mid - centre)).real < 0:
                normal = -normal
            on_ref_axis = (
                ref is not None
                and abs((ref_dir.conjugate() * s).imag) <= 1e-9 * span
                and abs((ref_dir.conjugate() * c).imag) <= 1e-9 * span
            )
            moved = on_ref_axis and (normal.conjugate() * ref_side).real > 0
            if moved:
                # The reference runs beside this phasor: its name goes to the other side,
                # past the angle arc when it starts at the origin.
                normal = -normal
                if abs(s) <= 1e-9 * span:
                    mid = s + 0.8 * c
            if i in covered:  # a shifted phasor runs alongside on the outer side
                lo, hi = _free_stretch(abs(c), covered[i])
                if hi - lo >= 0.3 * abs(c):  # name beside the part left free
                    mid = s + c / abs(c) * (lo + hi) / 2
                else:  # covered (nearly) all along: name on the inner side
                    normal = -normal
            where, direction = mid, normal
        else:
            # Beyond the tip, turned 30 degrees counter-clockwise so a phasor along an
            # axis does not put its name on the axis line.
            where, direction = s + c, (c if abs(c) else 1j) * cmath.exp(1j * math.pi / 6)
        label = ax.annotate(
            _phasor_tex(nm),
            (where.real, where.imag),
            textcoords="offset points",
            fontsize=9,
            color=FG,
            zorder=7,
            **_label_offset(direction),
        )
        scene.texts.append(label)
        if chain and moved and abs(s) <= 1e-9 * span:
            inner = (label, s, c, direction)
    ref_label = None
    if ref:
        ax.add_patch(
            FancyArrowPatch(
                (ref_start.real, ref_start.imag),
                (ref_tip.real, ref_tip.imag),
                arrowstyle="-|>",
                mutation_scale=9,
                color=color(len(names)),
                lw=1.2,
                shrinkA=0,
                shrinkB=0,
                zorder=5,
            )
        )
        scene.lines.append((ref_start, ref_tip))
        ref_label = ax.annotate(
            _phasor_tex(ref[0]),
            (ref_tip.real, ref_tip.imag),
            textcoords="offset points",
            fontsize=9,
            color=FG,
            zorder=7,
            **_label_offset(ref_dir, 3.0),
        )
        scene.texts.append(ref_label)
    phi = math.degrees(cmath.phase(resultant)) if abs(resultant) > 0 else 0.0
    base, rel = 0.0, phi  # the phase angle is measured from Re, or from the reference
    if ref:
        base, rel = ref[2], (phi - ref[2]) % 360.0
        rel = rel - 360.0 if rel > 180.0 else rel  # in (-180, 180]
    if chain:
        ax.add_patch(
            FancyArrowPatch(
                (0, 0),
                (resultant.real, resultant.imag),
                arrowstyle="-|>",
                mutation_scale=11,
                color=FG,
                lw=2.0,
                shrinkA=0,
                shrinkB=0,
                zorder=6,
            )
        )
        scene.lines.append((0j, resultant))
        mid = resultant / 2
        normal = 1j * resultant / abs(resultant) if abs(resultant) else 1j
        tip_centre = complex(np.mean(tips))
        if (normal.conjugate() * (tip_centre - mid)).real > 0:
            normal = -normal
        scene.texts.append(
            ax.annotate(
                _phasor_tex(total),
                (mid.real, mid.imag),
                textcoords="offset points",
                fontsize=9,
                color=FG,
                zorder=7,
                **_label_offset(normal),
            )
        )
    if ref_label is not None:
        # Beyond the tip; if a phasor runs there (a reference at an angle lies close beside
        # one), turned to the side away from the diagram, or beside the reference's middle.
        _place(
            scene,
            [
                _Layout([(ref_label, ref_tip, ref_dir, 3.0)]),
                _Layout([(ref_label, ref_tip, ref_dir + ref_side, 3.0)]),
                _Layout([(ref_label, ref_start + ref_len / 2 * ref_dir, ref_side, 3.0)]),
            ],
        )
    if chain and show_angle and abs(rel) > 3 and abs(resultant) > 0:
        # The angle's name goes where it clashes with no phasor, axis or name, tried in this
        # order: on the bisector just outside the arc, with the arc shrinking; beside the
        # sum just outside the angle, at the arc's end (a long name such as \varphi_{u,i} in
        # a narrow angle); on the bisector of a larger arc; centred above or below the
        # bisector point. A name moved off the reference may slide towards its tip at each
        # spot. Spots outside the angle or centred cost a few px, so a spot on the
        # bisector wins a near tie; with no free spot the least bad one is taken.
        half = cmath.exp(1j * math.radians(base + rel / 2))
        end = resultant / abs(resultant)
        outside = end * (1j if rel > 0 else -1j)  # normal of the sum, away from the angle
        angle_label = ax.annotate(
            rf"${angle_name} = {_num_tex(rel)}^\circ$",
            (0, 0),
            textcoords="offset points",
            fontsize=7,
            color=FG,
            **_label_offset(half, 2.0),
        )
        scene.texts.append(angle_label)
        spots = [(f, f * 1.12 * half, half, 2.0, 0.0) for f in (0.3, 0.25, 0.2)]
        spots += [(f, f * end, outside, 4.0, 4.0) for f in (0.3, 0.25, 0.4, 0.5)]
        spots += [(f, f * 1.12 * half, half, 2.0, 0.0) for f in (0.36, 0.42)]
        vertical = 1j if half.imag > 0 else -1j  # centred above or below the bisector point
        spots += [(f, f * 1.12 * half, vertical, 2.0, 2.0) for f in (0.36, 0.42, 0.5)]
        fracs = (0.8, 0.84, 0.88, 0.92) if inner is not None else (None,)
        a0, a1 = sorted((base, base + rel))
        layouts, radii = [], []
        for f, at, direction, dist, cost in spots:
            radius = f * abs(resultant)
            for frac in fracs:
                places = [(angle_label, at * abs(resultant), direction, dist)]
                if inner is not None:
                    label, s, c, side = inner
                    places.append((label, s + frac * c, side, 7.0))
                layouts.append(_Layout(places, _arc_lines(radius, a0, a1), cost))
                radii.append(radius)
        radius = radii[_place(scene, layouts)]
        ax.add_patch(
            Arc((0, 0), 2 * radius, 2 * radius, theta1=a0, theta2=a1, color=FG, lw=0.8, zorder=4)
        )
    facts = {
        "template": "signals.phasor",
        "chain": chain,
        "vectors": [
            {
                "name": nm,
                "magnitude": abs(c),
                "angle_deg": float(vectors[nm][1]),
                "re": c.real,
                "im": c.imag,
                "start": _pair(s),
                "drawn_offset": _pair(o),
            }
            for nm, s, c, o in zip(names, starts, comps, offsets, strict=True)
        ],
        "resultant": {
            "name": total,
            "magnitude": abs(resultant),
            "angle_deg": phi,
            "re": resultant.real,
            "im": resultant.imag,
        },
    }
    if ref:
        facts["resultant"]["angle_to_reference_deg"] = rel
        facts["reference"] = {
            "name": ref[0],
            "magnitude": ref[1],
            "angle_deg": ref[2],
            "re": (ref[1] * ref_dir).real,
            "im": (ref[1] * ref_dir).imag,
            "own_scale": True,
            "drawn_start": _pair(ref_start),
            "drawn_length": ref_len,
        }
    if alt is None:
        listing = ", ".join(
            f"{nm} = {vectors[nm][0]:g} at {float(vectors[nm][1]):g} degrees" for nm in names
        )
        alt = f"Phasor diagram in the complex plane: {listing}"
        if chain:
            alt += (
                f"; drawn head to tail, their sum {total} has magnitude {abs(resultant):.4g} "
                f"at {phi:.4g} degrees"
            )
        if ref:
            alt += (
                f"; the reference {ref[0]} = {ref[1]:g} at {ref[2]:g} degrees is drawn to "
                f"its own scale"
            )
            if chain:
                alt += f", {total} is {rel:.4g} degrees from it"
        alt += "."
    return core.finish(fig, alt, facts)


# --------------------------------------------------------------------------------------
# Time-domain signals
# --------------------------------------------------------------------------------------


def _signal_tex(name: str, stem: bool) -> str:
    if "$" in name:
        return name
    if "(" in name or "[" in name:
        return f"${name}$"
    return f"${name}[n]$" if stem else f"${name}(t)$"


def _legend_above(ax, handles: list) -> None:
    """Legend above the plot area, right-aligned, in as few rows as the width allows.

    Stems and periodic signals (three-phase voltages) leave no free spot inside the axes,
    and the house style draws legends without a frame, so the legend never goes inside.
    """
    fig = ax.figure
    for ncol in range(len(handles), 0, -1):
        leg = ax.legend(
            handles=handles,
            loc="lower right",
            bbox_to_anchor=(1.0, 1.0),
            ncol=ncol,
            labelcolor=FG,
            borderaxespad=0.2,
        )
        fig.draw_without_rendering()
        renderer = fig.canvas.get_renderer()
        room = ax.get_window_extent(renderer).x1 - fig.get_window_extent(renderer).x0
        if leg.get_window_extent(renderer).width <= 0.98 * room:
            return


def signals(
    t: Sequence[float] | np.ndarray,
    series: Mapping[str, np.ndarray | Sequence[float] | Callable[[np.ndarray], np.ndarray]],
    stem: bool = False,
    unit: str | None = "s",
    y_label: str | None = None,
    y_unit: str | None = None,
    legend: bool | None = None,
    size: str = "col",
    alt: str | None = None,
) -> core.Figure:
    """Time-domain plot of one or more signals; stem=True draws sequences x[n].

    t: sample times (in seconds when unit='s'; the axis then switches to ms, us or ns as
    the range calls for) or the indices n of a sequence.
    series: {name: samples or a callable of t}; 'u_C' is labelled u_C(t) (or u_C[n]).
    y_label: TeX quantity for the y axis (default: the single series' name).
    """
    if not series:
        raise ValueError("signals needs at least one series")
    tt = np.asarray(t, dtype=float)
    if tt.ndim != 1 or tt.size < 2:
        raise ValueError("t must be a 1-D array with at least two samples")
    data: dict[str, np.ndarray] = {}
    for nm, v in series.items():
        y = v(tt) if callable(v) else v
        data[nm] = np.broadcast_to(np.asarray(y, dtype=float), tt.shape).copy()

    scale, shown_unit = (1.0, None) if stem else _time_display(float(np.max(np.abs(tt))), unit)
    x = tt * scale
    fig, ax = core.new_figure(size)
    k = len(data)
    step = float(np.min(np.diff(tt)))
    width = 0.12 * step if stem and k > 1 else 0.0
    handles = []
    for i, (nm, y) in enumerate(data.items()):
        label = _signal_tex(nm, stem)
        if stem:
            cont = ax.stem(x + (i - (k - 1) / 2) * width, y)
            cont.markerline.set(color=color(i), mfc=color(i), mec=color(i), ms=3.5, zorder=5)
            cont.stemlines.set(color=color(i), lw=1.1)
            cont.baseline.set(color=FG, lw=0.8)
            handles.append(Line2D([], [], color=color(i), marker="o", ms=3.5, lw=1.1, label=label))
        else:
            handles += ax.plot(x, y, color=color(i), label=label, zorder=4)
    all_y = np.concatenate(list(data.values()))
    finite = all_y[np.isfinite(all_y)]
    lo, hi = (float(finite.min()), float(finite.max())) if finite.size else (-1.0, 1.0)
    if stem:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
        ax.set_xlim(x[0] - 0.6 * step, x[-1] + 0.6 * step)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax.set_xlabel("$n$")
    else:
        ax.set_xlim(x[0], x[-1])
        ax.set_xlabel(core.axis_label("t", _unit_text(shown_unit)))
        if lo < 0 < hi:
            ax.axhline(0, color=FG, lw=0.7, zorder=2)
    ax.set_ylim(*_pad_range(lo, hi))
    if y_label is not None:
        ax.set_ylabel(core.axis_label(y_label, y_unit))
    elif k == 1:
        quantity = _signal_tex(next(iter(data)), stem).strip("$")
        ax.set_ylabel(core.axis_label(quantity, y_unit))
    if legend if legend is not None else k > 1:
        _legend_above(ax, handles)
    core.apply_locale(ax)

    facts: dict = {
        "template": "signals.signals",
        "stem": stem,
        "t_range": [float(tt[0]), float(tt[-1])],
        "time_axis": None if stem else {"unit": shown_unit, "scale": scale},
        "samples": int(tt.size),
        "series": {},
    }
    duration = float(tt[-1] - tt[0])
    for nm, y in data.items():
        if stem:
            mean, rms = float(np.nanmean(y)), float(np.sqrt(np.nanmean(y**2)))
        else:  # time averages over [t0, t1] by the trapezoidal rule
            mean = float(np.trapezoid(y, tt) / duration)
            rms = float(np.sqrt(np.trapezoid(y**2, tt) / duration))
        entry = {"min": float(np.nanmin(y)) + 0.0, "max": float(np.nanmax(y)) + 0.0}
        entry |= {"mean": mean, "rms": rms}
        if stem and tt.size <= 64:
            entry["values"] = [float(v) + 0.0 for v in y]
        facts["series"][nm] = entry
    if alt is None:
        kind = "Stem plot of the sequence" if stem else "Time-domain plot of"
        listing = ", ".join(
            f"{nm} (from {e['min']:.3g} to {e['max']:.3g})" for nm, e in facts["series"].items()
        )
        if stem:
            span = f"n from {tt[0]:g} to {tt[-1]:g}"
        else:
            span = f"t from {tt[0]:g} to {tt[-1]:g}" + (f" {unit}" if unit else "")
        alt = f"{kind} {listing} for {span}."
    return core.finish(fig, alt, facts)


__all__ = [
    "ANNOTATIONS",
    "Plant",
    "bode",
    "bode_asymptotes",
    "nyquist",
    "phase_deg",
    "phasor",
    "plant",
    "pole_zero",
    "root_locus",
    "signals",
    "stability_margins",
    "step_metrics",
    "step_response",
    "structure",
]
