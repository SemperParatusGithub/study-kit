"""`studykit calc "<expr>"`: a SymPy calculator for agents and the examiner (§5.3).

Exact and numeric results, complex numbers written with `j`, phasor helpers and, with
`--units`, engineering units:

    studykit calc "1/(2*pi*R*C)" --subs R=2.2e3 C=47e-9
    studykit calc "par(100, 1/(j*2*pi*200*10e-6))"
    studykit calc "2.2*kohm*47*nF" --units

The expression is never handed to Python's `eval` as written. `parse()` first tokenizes
it and accepts only numbers, names, `+ - * / ** ^ ( ) ,` and calls of the functions in
`FUNCTIONS`; no attribute access, subscripts, strings, keywords or names starting with
`_`. Only then does SymPy's parser build the expression, with a namespace that holds
SymPy's number and symbol constructors and the functions below and no builtins, so the
code it evaluates can do nothing but arithmetic on SymPy objects.
"""

from __future__ import annotations

import io
import keyword
import math
import tokenize
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication,
    parse_expr,
    rationalize,
    standard_transformations,
)
from sympy.physics import units as u
from sympy.printing.str import StrPrinter

ALLOWED_OPS = {"+", "-", "*", "/", "**", "^", "(", ")", ","}
SKIP_TOKENS = {tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER, tokenize.INDENT}


class CalcError(ValueError):
    """An expression that cannot be parsed or evaluated; the message says why."""


def _deg(x: Any) -> Any:
    return x * 180 / sympy.pi


def _rad(x: Any) -> Any:
    return x * sympy.pi / 180


def _par(*values: Any) -> Any:
    """Parallel connection: 1 / (1/a + 1/b + …)."""
    if not values:
        raise CalcError("par() needs at least one value")
    return 1 / sum(1 / sympy.sympify(v) for v in values)


def _polar(magnitude: Any, angle_deg: Any) -> Any:
    """A phasor from magnitude and angle in degrees: pol(10, -45)."""
    return magnitude * sympy.exp(sympy.I * _rad(angle_deg))


def _db(x: Any) -> Any:
    return 20 * sympy.log(sympy.Abs(x), 10)


def _dbp(x: Any) -> Any:
    return 10 * sympy.log(sympy.Abs(x), 10)


def _lg(x: Any) -> Any:
    return sympy.log(x, 10)


FUNCTIONS: dict[str, Any] = {
    "sqrt": sympy.sqrt,
    "cbrt": sympy.cbrt,
    "root": sympy.root,
    "exp": sympy.exp,
    "log": sympy.log,
    "ln": sympy.log,
    "lg": _lg,
    "log10": _lg,
    "log2": lambda x: sympy.log(x, 2),
    "sin": sympy.sin,
    "cos": sympy.cos,
    "tan": sympy.tan,
    "cot": sympy.cot,
    "asin": sympy.asin,
    "acos": sympy.acos,
    "atan": sympy.atan,
    "atan2": sympy.atan2,
    "sinh": sympy.sinh,
    "cosh": sympy.cosh,
    "tanh": sympy.tanh,
    "abs": sympy.Abs,
    "Abs": sympy.Abs,
    "mag": sympy.Abs,
    "arg": sympy.arg,
    "angle": sympy.arg,
    "angd": lambda z: _deg(sympy.arg(z)),
    "re": sympy.re,
    "im": sympy.im,
    "conj": sympy.conjugate,
    "conjugate": sympy.conjugate,
    "deg": _deg,
    "rad": _rad,
    "pol": _polar,
    "polar": _polar,
    "par": _par,
    "db": _db,
    "dbp": _dbp,
    "floor": sympy.floor,
    "ceil": sympy.ceiling,
    "min": sympy.Min,
    "max": sympy.Max,
    "factorial": sympy.factorial,
    "binomial": sympy.binomial,
    "simplify": sympy.simplify,
    "expand": sympy.expand,
    "factor": sympy.factor,
    "together": sympy.together,
    "apart": sympy.apart,
    "diff": sympy.diff,
    "integrate": sympy.integrate,
    "limit": sympy.limit,
    "solve": sympy.solve,
    "Rational": sympy.Rational,
}
CONSTANTS: dict[str, Any] = {"pi": sympy.pi, "j": sympy.I, "I": sympy.I, "oo": sympy.oo}

# Units for --units. C and S stay symbols (capacitance, a switch); write coulomb, siemens.
BASE_UNITS: dict[str, Any] = {
    "V": u.volt,
    "A": u.ampere,
    "ohm": u.ohm,
    "Ω": u.ohm,
    "F": u.farad,
    "H": u.henry,
    "Hz": u.hertz,
    "s": u.second,
    "W": u.watt,
    "J": u.joule,
}
PREFIXES: dict[str, int] = {"p": -12, "n": -9, "u": -6, "μ": -6, "m": -3, "k": 3, "M": 6, "G": 9}
SI_PREFIXES = {-15: "f", -12: "p", -9: "n", -6: "µ", -3: "m", 0: "", 3: "k", 6: "M", 9: "G"}


def unit_namespace() -> dict[str, Any]:
    out: dict[str, Any] = {"coulomb": u.coulomb, "siemens": u.siemens, "VA": u.watt}
    for name, unit in BASE_UNITS.items():
        out[name] = unit
        for prefix, exponent in PREFIXES.items():
            out[prefix + name] = sympy.Integer(10) ** exponent * unit
    return out


# Result units tried in this order; the first whose quotient has no unit left wins.
RESULT_UNITS: list[tuple[str, Any]] = [
    ("V", u.volt),
    ("A", u.ampere),
    ("Ω", u.ohm),
    ("S", u.siemens),
    ("F", u.farad),
    ("H", u.henry),
    ("s", u.second),
    ("1/s", 1 / u.second),
    ("W", u.watt),
    ("J", u.joule),
    ("C", u.coulomb),
]
SI_BASE = [u.kilogram, u.meter, u.second, u.ampere]


def namespace(units: bool = False) -> dict[str, Any]:
    ns: dict[str, Any] = {**FUNCTIONS, **CONSTANTS}
    if units:
        ns.update(unit_namespace())
    return ns


def _check_tokens(text: str, ns: Mapping[str, Any]) -> None:
    try:
        tokens = [t for t in tokenize.generate_tokens(io.StringIO(text).readline)]
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        raise CalcError(f"cannot read the expression: {exc}") from exc
    tokens = [t for t in tokens if t.type not in SKIP_TOKENS]
    if not tokens:
        raise CalcError("the expression is empty")
    for i, tok in enumerate(tokens):
        if tok.type == tokenize.NUMBER:
            continue
        if tok.type == tokenize.NAME:
            name = tok.string
            if keyword.iskeyword(name) or keyword.issoftkeyword(name) or name.startswith("_"):
                raise CalcError(f"'{name}' is not allowed in an expression")
            follows = tokens[i + 1].string if i + 1 < len(tokens) else ""
            if follows == "(" and not callable(ns.get(name)):
                raise CalcError(
                    f"unknown function '{name}' (known: {', '.join(sorted(FUNCTIONS))})"
                )
            continue
        if tok.type == tokenize.OP and tok.string in ALLOWED_OPS:
            continue
        raise CalcError(
            f"'{tok.string}' is not allowed; use numbers, names, + - * / ** ^ ( ) and "
            "function calls"
        )


def parse(text: str, *, units: bool = False, symbols: Iterable[str] = ()) -> sympy.Expr:
    """A SymPy expression from `text`, parsed safely (see the module docstring).

    `^` is a power, `j` the imaginary unit, `2pi` an implicit product. `symbols` are names
    that stay plain symbols even where a function or unit has that name.
    """
    text = unicodedata.normalize("NFKC", text).strip()
    ns = namespace(units)
    for name in symbols:
        ns[name] = sympy.Symbol(name)
    _check_tokens(text, ns)
    glob = {
        "__builtins__": {},
        "Integer": sympy.Integer,
        "Float": sympy.Float,
        "Rational": sympy.Rational,
        "Symbol": sympy.Symbol,
        "I": sympy.I,
    }
    try:
        expr = parse_expr(
            text,
            local_dict=ns,
            global_dict=glob,
            transformations=(
                *standard_transformations,
                rationalize,
                convert_xor,
                implicit_multiplication,
            ),
        )
    except CalcError:
        raise
    except Exception as exc:
        raise CalcError(f"cannot evaluate '{text}': {type(exc).__name__}: {exc}") from exc
    return exact(expr)


def exact(expr: Any) -> Any:
    """Decimal numbers as the exact fractions they denote (2.2e3 -> 2200, 0.1 -> 1/10)."""
    if isinstance(expr, (list, tuple)):
        return type(expr)(exact(e) for e in expr)
    if not isinstance(expr, sympy.Basic):
        return expr
    floats = {f: sympy.Rational(str(f)) for f in expr.atoms(sympy.Float)}
    return expr.xreplace(floats) if floats else expr


def parse_subs(items: Iterable[str], *, units: bool = False) -> dict[str, Any]:
    """`name=value` pairs; each value is itself an expression (`R=2.2*kohm`, `w=2*pi*50`)."""
    out: dict[str, Any] = {}
    for item in items:
        name, sep, value = item.partition("=")
        name = unicodedata.normalize("NFKC", name.strip())
        if not sep or not name.isidentifier() or name.startswith("_"):
            raise CalcError(f"--subs takes name=value, got '{item}'")
        out[name] = parse(value, units=units)
    return out


class JPrinter(StrPrinter):
    """SymPy's string form with `j` for the imaginary unit."""

    def _print_ImaginaryUnit(self, expr: Any) -> str:
        return "j"


def show(expr: Any) -> str:
    return JPrinter().doprint(expr)


def split_unit(expr: Any) -> tuple[Any, str | None]:
    """(number or expression without units, unit name) for an expression with quantities."""
    if not expr.has(u.Quantity):
        return expr, None
    for name, unit in RESULT_UNITS:
        ratio = sympy.simplify(u.convert_to(expr / unit, SI_BASE))
        if not ratio.has(u.Quantity):
            return ratio, name
    base = sympy.simplify(u.convert_to(expr, SI_BASE))
    if not base.has(u.Quantity):
        return base, None
    coeff, rest = base.as_coeff_Mul()
    return coeff, show(rest)


def eng(value: float, unit: str | None = None, digits: int = 6) -> str:
    """`1539.24` -> `1.53924 k`, with the unit appended: `1.53924 kHz`."""
    if value == 0 or not math.isfinite(value):
        return f"{value:g}" + (f" {unit}" if unit else "")
    exponent = int(math.floor(math.log10(abs(value)) / 3) * 3)
    exponent = max(-15, min(9, exponent))
    mantissa = value / 10**exponent
    text = f"{mantissa:.{digits}g}"
    prefix = SI_PREFIXES[exponent]
    if unit == "1/s":
        return f"{text} {prefix} (1/s)".replace("  ", " ")
    return f"{text} {prefix}{unit or ''}".rstrip()


def describe(expr: Any, digits: int = 6) -> dict[str, Any]:
    """Exact and numeric forms of one result."""
    value, unit = split_unit(expr)
    out: dict[str, Any] = {
        "exact": show(exact(value)),
        "unit": unit,
        "free_symbols": sorted(str(s) for s in value.free_symbols),
        "numeric": None,
        "eng": None,
        "complex": None,
    }
    if out["free_symbols"]:
        return out
    try:
        number = complex(sympy.N(value, 17))
    except TypeError, ValueError:
        return out
    if abs(number.imag) <= 1e-14 * max(1.0, abs(number.real)):
        out["numeric"] = number.real
        out["eng"] = eng(number.real, unit, digits)
    else:
        angle = math.degrees(math.atan2(number.imag, number.real))
        out["complex"] = {"re": number.real, "im": number.imag, "abs": abs(number), "deg": angle}
    return out


def evaluate(
    text: str, subs: Iterable[str] = (), *, units: bool = False, digits: int = 6
) -> dict[str, Any]:
    """The `--json` result of `studykit calc`."""
    values = parse_subs(subs, units=units)
    symbols = [n for n in values if n not in CONSTANTS]
    expr = parse(text, units=units, symbols=symbols)
    if values:
        expr = expr.subs({sympy.Symbol(k): v for k, v in values.items()})
    results = list(expr) if isinstance(expr, (list, tuple)) else [expr]
    described = []
    for item in results:
        item = sympy.sympify(item)
        if not isinstance(item, sympy.Expr):
            raise CalcError(f"the result is not a number or expression: {show(item)}")
        described.append(describe(item, digits))
    out: dict[str, Any] = {"input": text, "subs": {k: show(v) for k, v in values.items()}}
    if isinstance(expr, (list, tuple)):
        out["values"] = described
    else:
        out.update(described[0])
    return out


def _fmt(x: float, digits: int) -> str:
    return f"{x:.{digits}g}"


def format_text(result: Mapping[str, Any], digits: int = 6) -> str:
    def lines(r: Mapping[str, Any], prefix: str = "") -> list[str]:
        unit = f" {r['unit']}" if r.get("unit") else ""
        out = [f"{prefix}exact    {r['exact']}{unit}"]
        if r.get("numeric") is not None:
            out.append(f"{prefix}numeric  {_fmt(r['numeric'], max(digits, 10))}{unit}")
            out.append(f"{prefix}eng      {r['eng']}")
        if r.get("complex"):
            c = r["complex"]
            sign = "-" if c["im"] < 0 else "+"
            out.append(
                f"{prefix}rect     {_fmt(c['re'], digits)} {sign} "
                f"{_fmt(abs(c['im']), digits)}j{unit}"
            )
            out.append(
                f"{prefix}polar    {_fmt(c['abs'], digits)}{unit} ∠ {_fmt(c['deg'], digits)}°"
            )
        if r.get("free_symbols"):
            out.append(f"{prefix}symbols  {', '.join(r['free_symbols'])} (give them with --subs)")
        return out

    if "values" in result:
        text = [f"{len(result['values'])} result(s)"]
        for i, r in enumerate(result["values"], start=1):
            text.append(f"[{i}]")
            text.extend(lines(r, "  "))
        return "\n".join(text)
    return "\n".join(lines(result))
