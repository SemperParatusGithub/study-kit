"""Control-engineering and signal templates.

Bode and Nyquist diagrams, pole-zero maps, step responses, root loci, phasor diagrams and
time-domain signals. python-control, NumPy and SciPy only compute; house code draws every
line. Every number a figure shows is computed and recorded in `facts`. Gain and phase
margins and their crossover frequencies are computed twice, by python-control's polynomial
method and by an independent SciPy frequency scan refined with brentq, and must agree.

A transfer function `G` can be given as a python-control `TransferFunction`, as
`(num, den)` coefficient lists (highest power first) or as a SymPy string in `s`
(`'10/((s+1)*(s+10))'`), or in `z` for discrete-time pole-zero maps and root loci.
"""

from __future__ import annotations

import cmath
import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property

import control as ct
import numpy as np
import sympy as sp
from matplotlib import ticker
from matplotlib.patches import Circle, FancyArrowPatch
from scipy import signal as sps
from scipy.optimize import brentq

from studykit.figures import core
from studykit.figures.palette import BG, FG, MUTED, color

S = sp.Symbol("s")
Z = sp.Symbol("z")
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


def _angle_at_0(r: complex) -> float:
    """Limit of arg(j omega - r) for omega -> 0+, in radians.

    For a real root the limit is taken from above the real axis: pi for r > 0, never the
    -pi that cmath.phase(-r) returns for -r = -a - 0j.
    """
    if r.imag == 0:
        return math.pi if r.real > 0 else 0.0
    return cmath.phase(-r)


def phase_deg(p: Plant, omega: np.ndarray, st: Structure | None = None) -> np.ndarray:
    """Continuous phase in degrees, anchored so that phase(0+) = -90 typ (-180 if k < 0).

    Summing the angle of each root factor gives a phase that is continuous in omega without
    any unwrapping heuristics; the anchor is the usual textbook convention.
    """
    st = st or structure(p)
    s = 1j * np.asarray(omega, dtype=float)
    ph = np.zeros(s.shape)
    low = 0.0
    for z in st.zeros:
        ph += np.angle(s - z)
        low += _angle_at_0(z)
    for q in st.poles:
        ph -= np.angle(s - q)
        low -= _angle_at_0(q)
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


def _margins_check(p: Plant, st: Structure) -> dict:
    """Independent margins: scipy.signal.freqresp scan, refined with brentq."""
    freqs = _interesting_frequencies(st)
    w = np.logspace(math.log10(min(freqs)) - 3, math.log10(max(freqs)) + 3, 20001)
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
    cand = (sin_a[:-1] * sin_a[1:] < 0) & (np.cos(ang[:-1]) < 0) & (np.cos(ang[1:]) < 0)
    phase_x = []
    for i in np.flatnonzero(cand):
        x = brentq(lambda x: math.sin(cmath.phase(h(x))), w[i], w[i + 1], xtol=1e-14 * w[i])
        if abs(math.sin(cmath.phase(h(x)))) < 1e-8 and h(x).real < 0:
            phase_x.append(x)

    gms = [1 / abs(h(x)) for x in phase_x]
    pms = [(math.degrees(cmath.phase(h(x))) % 360.0) - 180.0 for x in gain_x]
    out = {
        "method": "scipy.signal.freqresp + brentq",
        "gain_crossovers": [float(x) for x in gain_x],
        "phase_crossovers": [float(x) for x in phase_x],
        "gm": None,
        "gm_db": None,
        "w_pc": None,
        "pm_deg": None,
        "w_gc": None,
    }
    if gms:
        i = min(range(len(gms)), key=lambda k: abs(math.log(gms[k])))
        out.update(gm=gms[i], gm_db=20 * math.log10(gms[i]), w_pc=float(phase_x[i]))
    if pms:
        i = min(range(len(pms)), key=lambda k: abs(pms[k]))
        out.update(pm_deg=pms[i], w_gc=float(gain_x[i]))
    return out


def _close(a: float | None, b: float | None, rtol: float = MARGIN_RTOL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= rtol * max(1.0, abs(a), abs(b))


def stability_margins(G: TransferFunctionLike) -> dict:
    """Gain and phase margin with crossover frequencies, cross-checked two ways.

    Returns `{"gm", "gm_db", "w_pc", "pm_deg", "w_gc", "control": {...}, "check": {...}}`
    (frequencies in rad/s, None where a margin does not exist) and raises if the two
    computations disagree.
    """
    p = _continuous(G, "margins")
    st = structure(p)
    gm, pm, _sm, wpc, wgc, _wms = ct.stability_margins(p.tf)
    ctl = {
        "method": "control.stability_margins",
        "gm": _number(gm),
        "gm_db": _number(20 * math.log10(gm)) if gm > 0 and math.isfinite(gm) else None,
        "w_pc": _number(wpc),
        "pm_deg": _number(pm),
        "w_gc": _number(wgc),
    }
    check = _margins_check(p, st)
    agree = all(_close(ctl[k], check[k]) for k in ("gm", "w_pc", "pm_deg", "w_gc"))
    if not agree:
        raise RuntimeError(f"margin cross-check failed: control {ctl} vs scipy {check}")
    return {k: ctl[k] for k in ("gm", "gm_db", "w_pc", "pm_deg", "w_gc")} | {
        "control": ctl,
        "check": check,
        "agree": agree,
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
        m_lo, m_hi, p_lo, p_hi = _draw_margins(ax_m, ax_p, p, st, mg, to_x, m_lo, m_hi, p_lo, p_hi)

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


def _draw_margins(ax_m, ax_p, p, st, mg, to_x, m_lo, m_hi, p_lo, p_hi):
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
            color=color(2),
            **label_style,
        )
        marks.append((xg, rf"${var}_\mathrm{{D}}$" if de else rf"${var}_\mathrm{{gc}}$"))
        p_lo, p_hi = min(p_lo, ref), max(p_hi, ref)
    else:
        ax_p.axhline(-180.0, color=FG, lw=0.7, zorder=2)
    if mg["w_pc"] is not None:
        wpc = mg["w_pc"]
        m_pc = float(20 * np.log10(np.abs(p.tf(1j * wpc))))
        xp = wpc * to_x
        for ax in (ax_m, ax_p):
            ax.axvline(xp, color=MUTED, lw=0.8, ls=":", zorder=2)
        _double_arrow(ax_m, (xp, m_pc), (xp, 0.0), color(1))
        ax_m.plot([xp], [m_pc], "o", ms=3.5, color=color(1), zorder=7)
        sym = r"A_\mathrm{R}" if de else r"\mathrm{GM}"
        falling = float(20 * np.log10(np.abs(p.tf(1j * wpc * 1.05)))) < m_pc
        ax_m.annotate(
            rf"${sym} = {_num_tex(mg['gm_db'])}\,\mathrm{{dB}}$",
            (xp, m_pc / 2),
            **_free_side(falling, m_pc < 0),
            color=color(1),
            **label_style,
        )
        marks.append((xp, rf"${var}_\pi$" if de else rf"${var}_\mathrm{{pc}}$"))
        m_lo, m_hi = min(m_lo, m_pc, 0.0), max(m_hi, 0.0)
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

    w: (low, high) frequency range in rad/s; by default a wide range around all corners.
    lim: radius of the region kept in view when G has poles on the imaginary axis
    (the curve then runs off to infinity).
    """
    p = _continuous(G, "nyquist", proper=True)
    st = structure(p)
    freqs = _interesting_frequencies(st)
    if w is None:
        lo, hi = min(freqs) * 1e-3, max(freqs) * 1e3
    else:
        lo, hi = float(w[0]), float(w[-1])
    omega = _frequency_grid(st, lo, hi, 6000)
    H = p.tf(1j * omega)
    axis_poles = [q for q in p.poles() if q.real == 0]
    h0 = None if st.typ > 0 else (0j if st.typ < 0 else complex(st.k_bode))
    h_inf = complex(st.lead) if st.rel_degree == 0 else 0j
    pos = np.concatenate([[h0] if h0 is not None else [], H, [h_inf]]).astype(complex)

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
            color=color(1),
        )
    if h0 is not None and abs(h0) <= far:
        ax.plot([h0.real], [0], "o", ms=3, color=color(0), zorder=7)
        ax.annotate(
            r"$\omega = 0$",
            (h0.real, 0),
            xytext=(3, 4),
            textcoords="offset points",
            fontsize=7,
            color=FG,
        )

    # Stability: encirclements of -1 (clockwise positive) and closed-loop poles.
    p_rhp = int(sum(q.real > 0 for q in p.poles()))
    cl = _clean_roots(np.roots(np.polyadd(p.den, p.num)))
    z_rhp = int(sum(q.real > 0 for q in cl))
    n_cw = _encirclements_cw(p, st, omega, H, h0, h_inf)
    crossings = []
    unit_im = H.imag / np.abs(H)  # sin of the phase: smooth, unlike Im G near poles
    for i in np.flatnonzero(np.sign(unit_im[:-1]) * np.sign(unit_im[1:]) < 0):
        x = brentq(
            lambda v: math.sin(cmath.phase(complex(p.tf(1j * v)))),
            omega[i],
            omega[i + 1],
            xtol=1e-14 * omega[i],
        )
        hx = complex(p.tf(1j * x))
        if abs(hx.imag) <= 1e-8 * abs(hx) and math.isfinite(abs(hx)):
            crossings.append({"omega": float(x), "re": hx.real})
    facts = {
        "template": "signals.nyquist",
        "G": p.as_dict(),
        "omega_range": [float(omega[0]), float(omega[-1])],
        "start": _pair(h0) if h0 is not None else None,
        "end": _pair(h_inf),
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
        alt += f"; the curve {turns}; the closed loop is {verdict}."
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
            color=hint,
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
            color=hint,
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
                    color=col,
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
    if asym is not None and n - m >= 1:
        for a in asym["angles_deg"]:
            if a % 180 == 0:  # lies on the real axis, which is drawn anyway
                continue
            d = cmath.exp(1j * math.radians(a)) * 10 * span
            c0 = asym["centroid"]
            ax.plot([c0, c0 + d.real], [0, d.imag], color=MUTED, lw=0.8, ls=(0, (4, 2)), zorder=2)
    for j in range(loci.shape[1]):
        branch = loci[:, j]
        ax.plot(branch.real, branch.imag, color=color(0), zorder=4)
        _arrows_along(ax, branch, (0.5,), color(0), box)
    for c in crossings:
        for sgn in (1, -1):
            ax.plot([0], [sgn * c["omega"]], "o", ms=3.5, color=FG, zorder=9)
    if crossings:
        c = max(crossings, key=lambda e: e["omega"])
        sym = r"K_\mathrm{krit}" if core.locale() == "de" else r"K_\mathrm{crit}"
        ax.annotate(
            f"${sym} = {_num_tex(c['k'])}$",
            (0, c["omega"]),
            xytext=(5, 2),
            textcoords="offset points",
            fontsize=7,
            color=FG,
        )
    for b in breaks:
        ax.plot([b["s"]], [0], "o", ms=3, color=color(0), zorder=9)
    _mark_roots(ax, poles, zeros, color(1), color(0))
    ax.set_xlim(*box[0])
    ax.set_ylim(*box[1])

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


__all__ = [
    "Plant",
    "bode",
    "bode_asymptotes",
    "nyquist",
    "phase_deg",
    "plant",
    "pole_zero",
    "root_locus",
    "stability_margins",
    "structure",
]
