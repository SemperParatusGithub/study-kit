"""`studykit calc`: exact and numeric results, complex phasors, units, and a safe parser."""

from __future__ import annotations

import json
import math

import pytest

from studykit import calc, cli


def test_exact_and_numeric_with_subs():
    r = calc.evaluate("1/(2*pi*R*C)", ["R=2.2e3", "C=47e-9"])
    assert r["exact"] == "2500000/(517*pi)"  # decimals are read as exact fractions
    assert r["numeric"] == pytest.approx(1 / (2 * math.pi * 2.2e3 * 47e-9))
    assert r["eng"] == "1.53922 k"
    assert r["free_symbols"] == [] and r["complex"] is None


def test_power_caret_implicit_product_and_free_symbols():
    assert calc.evaluate("2^10")["numeric"] == 1024
    assert calc.evaluate("2pi*50")["exact"] == "100*pi"
    r = calc.evaluate("R*C")
    assert r["free_symbols"] == ["C", "R"] and r["numeric"] is None
    assert "give them with --subs" in calc.format_text(r)


def test_complex_numbers_with_j_and_phasor_helpers():
    r = calc.evaluate("3+4j")
    assert r["exact"] == "3 + 4*j"
    assert r["complex"]["abs"] == pytest.approx(5)
    assert r["complex"]["deg"] == pytest.approx(math.degrees(math.atan2(4, 3)))
    z = calc.evaluate("par(100, 1/(j*2*pi*200*10e-6))")["complex"]
    expected = 1 / (1 / 100 + 1j * 2 * math.pi * 200 * 10e-6)
    assert complex(z["re"], z["im"]) == pytest.approx(expected)
    p = calc.evaluate("pol(10, -45)")["complex"]
    assert (p["abs"], p["deg"]) == (pytest.approx(10), pytest.approx(-45))
    assert calc.evaluate("angd(1 - j)")["numeric"] == pytest.approx(-45)
    assert calc.evaluate("mag(3 + 4*j)")["numeric"] == pytest.approx(5)
    assert calc.evaluate("db(1/sqrt(2))")["numeric"] == pytest.approx(-3.0103, abs=1e-4)
    text = calc.format_text(calc.evaluate("pol(10, -45)"))
    assert "rect     7.07107 - 7.07107j" in text and "∠ -45°" in text


def test_units():
    r = calc.evaluate("2.2*kohm*47*nF", units=True)
    assert (r["unit"], r["eng"]) == ("s", "103.4 µs")
    assert calc.evaluate("10*V/(2*kΩ)", units=True)["eng"] == "5 mA"
    assert calc.evaluate("U^2/R", ["U=10*V", "R=50*ohm"], units=True)["eng"] == "2 W"
    hz = calc.evaluate("1/(2*pi*2.2*kohm*47*nF)", units=True)
    assert hz["unit"] == "1/s" and hz["eng"] == "1.53922 k (1/s)"
    # without --units the names are plain symbols
    assert calc.evaluate("kohm")["free_symbols"] == ["kohm"]


def test_lists_from_solve():
    r = calc.evaluate("solve(x^2 - 4, x)")
    assert [v["numeric"] for v in r["values"]] == [-2, 2]


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os')",
        "x.real",
        "().__class__",
        "[1, 2]",
        "{1: 2}",
        "'text'",
        "lambda: 1",
        "open(1)",
        "eval(1)",
        "a = 1",
        "1; 2",
        "x if y else z",
        "_x + 1",
        "",
    ],
)
def test_parser_rejects_python(expr: str):
    with pytest.raises(calc.CalcError):
        calc.evaluate(expr)


def test_subs_must_be_name_value():
    with pytest.raises(calc.CalcError):
        calc.evaluate("x", ["x"])
    with pytest.raises(calc.CalcError):
        calc.evaluate("x", ["x.y=1"])


def test_cli(capsys):
    assert cli.main(["calc", "1/(2*pi*R*C)", "--subs", "R=1e3", "C=100e-9", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["numeric"] == pytest.approx(1591.549, rel=1e-6)
    assert out["subs"] == {"R": "1000", "C": "1/10000000"}
    # a repeated --subs adds to the earlier ones instead of replacing them
    assert (
        cli.main(["calc", "1/(2*pi*R*C)", "--subs", "R=1e3", "--subs", "C=100e-9", "--json"]) == 0
    )
    assert json.loads(capsys.readouterr().out)["numeric"] == pytest.approx(1591.549, rel=1e-6)
    assert cli.main(["calc", "2.2*kohm*47*nF", "--units"]) == 0
    assert "eng      103.4 µs" in capsys.readouterr().out
    assert cli.main(["calc", "x.real"]) == 2
    assert "not allowed" in capsys.readouterr().err
