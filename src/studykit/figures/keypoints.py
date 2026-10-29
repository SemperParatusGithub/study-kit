"""Roots, intersections, extrema and inflection points, computed numerically.

Numbers are the truth: a dense sign scan brackets every candidate, brentq refines it,
and a residual check rejects poles (where a function changes sign by jumping through
infinity). Touching roots (no sign change, e.g. x^2) are found as roots of f' with f ~ 0.
SymPy only supplies exact closed forms for display, and only when they agree.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import sympy as sp
from scipy.optimize import brentq

X = sp.Symbol("x", real=True)
SCAN_POINTS = 4001


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    kind: str  # root | intersection | maximum | minimum | inflection
    exact_x: str | None = None  # LaTeX of an exact x when SymPy agrees

    def as_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "kind": self.kind, "exact_x": self.exact_x}


def parse(expr: str) -> sp.Expr:
    """Parse a function of x written in SymPy/Python syntax, e.g. 'x**2 - 2' or 'exp(-x)'."""
    parsed = sp.sympify(expr, locals={"x": X, "e": sp.E, "pi": sp.pi})
    extra = parsed.free_symbols - {X}
    if extra:
        names = ", ".join(sorted(str(s) for s in extra))
        raise ValueError(f"{expr!r} uses symbols other than x: {names}")
    return parsed


def lambdify(expr: sp.Expr) -> Callable[[np.ndarray], np.ndarray]:
    fn = sp.lambdify(X, expr, modules="numpy")

    def safe(x):
        with np.errstate(all="ignore"):
            y = np.asarray(fn(x), dtype=complex)
            return np.where(np.abs(y.imag) < 1e-12, y.real, np.nan)

    return safe


def _scale(y: np.ndarray) -> float:
    finite = y[np.isfinite(y)]
    return float(np.max(np.abs(finite))) if finite.size else 1.0


def _sign_change_roots(f: Callable, lo: float, hi: float) -> list[float]:
    xs = np.linspace(lo, hi, SCAN_POINTS)
    ys = f(xs)
    scale = max(_scale(ys), 1e-12)
    roots: list[float] = []
    for i in range(len(xs) - 1):
        a, b, fa, fb = xs[i], xs[i + 1], ys[i], ys[i + 1]
        if not (np.isfinite(fa) and np.isfinite(fb)):
            continue
        if fa == 0:
            roots.append(float(a))
            continue
        if fa * fb < 0:
            try:
                r = brentq(lambda t: float(f(np.array([t]))[0]), a, b, xtol=1e-14, maxiter=200)
            except ValueError:
                continue
            # A pole also changes sign; a real root has a small residual.
            if abs(float(f(np.array([r]))[0])) <= 1e-8 * scale + 1e-12:
                roots.append(float(r))
    if np.isfinite(ys[-1]) and ys[-1] == 0:
        roots.append(float(xs[-1]))
    return roots


def _dedupe(values: list[float], span: float) -> list[float]:
    tol = span * 1e-9 + 1e-12
    out: list[float] = []
    for v in sorted(values):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def _exact(expr: sp.Expr, x: float, lo: float, hi: float) -> str | None:
    """LaTeX of an exact solution of expr = 0 that matches x, if SymPy finds one quickly."""
    try:
        sols = sp.solveset(expr, X, domain=sp.Interval(lo, hi))
    except NotImplementedError, ValueError, TypeError:
        return None
    if not isinstance(sols, sp.FiniteSet):
        return None
    for s in sols:
        try:
            if abs(float(s) - x) <= 1e-9 * max(1.0, abs(x)):
                if s.is_Integer or (s.is_Rational and len(str(s)) < 8):
                    return sp.latex(s)
                text = sp.latex(sp.nsimplify(s)) if s.is_Float else sp.latex(s)
                return text if len(text) <= 40 else None
        except TypeError, ValueError:
            continue
    return None


def roots(expr: str | sp.Expr, lo: float, hi: float, exact: bool = True) -> list[Point]:
    e = parse(expr) if isinstance(expr, str) else expr
    f = lambdify(e)
    found = _sign_change_roots(f, lo, hi)
    # Touching roots: f' changes sign where f is ~0.
    d = lambdify(sp.diff(e, X))
    ys = f(np.linspace(lo, hi, SCAN_POINTS))
    scale = max(_scale(ys), 1e-12)
    for c in _sign_change_roots(d, lo, hi):
        if abs(float(f(np.array([c]))[0])) <= 1e-9 * scale:
            found.append(c)
    xs = _dedupe(found, hi - lo)
    return [Point(x, 0.0, "root", _exact(e, x, lo, hi) if exact else None) for x in xs]


def intersections(
    f_expr: str | sp.Expr, g_expr: str | sp.Expr, lo: float, hi: float, exact: bool = True
) -> list[Point]:
    f = parse(f_expr) if isinstance(f_expr, str) else f_expr
    g = parse(g_expr) if isinstance(g_expr, str) else g_expr
    diff = sp.simplify(f - g)
    fn = lambdify(f)
    return [
        Point(p.x, float(fn(np.array([p.x]))[0]), "intersection", p.exact_x)
        for p in roots(diff, lo, hi, exact=exact)
    ]


def extrema(expr: str | sp.Expr, lo: float, hi: float, exact: bool = True) -> list[Point]:
    e = parse(expr) if isinstance(expr, str) else expr
    f = lambdify(e)
    d1 = sp.diff(e, X)
    d2 = lambdify(sp.diff(e, X, 2))
    points = []
    for p in roots(d1, lo, hi, exact=exact):
        curvature = float(d2(np.array([p.x]))[0])
        if not math.isfinite(curvature) or abs(curvature) < 1e-12:
            continue  # saddle / plateau: not a strict extremum
        kind = "minimum" if curvature > 0 else "maximum"
        points.append(Point(p.x, float(f(np.array([p.x]))[0]), kind, p.exact_x))
    return points


def inflections(expr: str | sp.Expr, lo: float, hi: float, exact: bool = True) -> list[Point]:
    e = parse(expr) if isinstance(expr, str) else expr
    f = lambdify(e)
    d2 = sp.diff(e, X, 2)
    d2f = lambdify(d2)
    xs = _sign_change_roots(d2f, lo, hi)
    return [
        Point(x, float(f(np.array([x]))[0]), "inflection", _exact(d2, x, lo, hi) if exact else None)
        for x in _dedupe(xs, hi - lo)
    ]
