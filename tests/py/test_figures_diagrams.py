"""Block diagrams, state machines, flowcharts and the topic map: facts and SVG validity."""

from __future__ import annotations

import pytest
import sympy as sp

from studykit.figures import block
from studykit.figures.validate import validate_svg


@pytest.fixture(params=["de", "en"])
def locale(request, monkeypatch):
    monkeypatch.setenv("STUDYKIT_LOCALE", request.param)
    return request.param


def _tf(fact: dict) -> sp.Expr:
    return sp.sympify(fact["expr"])


G1, G2, G3, H, Z = sp.symbols("G1 G2 G3 H Z")


def test_feedback_loop_negative_feedback(locale):
    fig = block.feedback_loop()
    assert validate_svg(fig.svg) == []
    f = fig.facts
    assert f["template"] == "block.feedback_loop"
    assert f["symbols"] == {"G1": "G_R(s)", "G2": "G_S(s)", "H": "H(s)"}
    assert sp.simplify(_tf(f["reference_tf"]) - G1 * G2 / (1 + G1 * G2 * H)) == 0
    assert sp.simplify(_tf(f["error_tf"]) - 1 / (1 + G1 * G2 * H)) == 0
    assert f["junctions"][0]["inputs"] == {"W": "+", "S": "-"}
    assert f["disturbance_tf"] is None
    assert 0.72 <= f["scale"] <= 1.0
    assert f["width_in"] <= 3.6 + 1e-6
    assert "G_R(s)" in fig.alt


def test_feedback_loop_unity_positive_and_disturbance(locale):
    fig = block.feedback_loop(
        forward=["G_R(s)", "G_A(s)", "G_S(s)"],
        feedback=None,
        signals={"u": ["U(s)", "V(s)"], "m": "Y_M(s)"},
        disturbance="D(s)",
        disturbance_at="output",
        sign="+",
        junction="sigma",
        size="full",
    )
    assert validate_svg(fig.svg) == []
    f = fig.facts
    assert f["feedback"] is None and f["sign"] == "+"
    loop = G1 * G2 * G3
    assert sp.simplify(_tf(f["reference_tf"]) - loop / (1 - loop)) == 0
    assert sp.simplify(_tf(f["disturbance_tf"]) - 1 / (1 - loop)) == 0
    assert f["junctions"][1] == {"at": "disturbance-output", "inputs": {"W": "+", "N": "+"}}


def test_feedback_loop_disturbance_at_plant_input():
    f = block.feedback_loop(disturbance="Z(s)").facts
    assert sp.simplify(_tf(f["disturbance_tf"]) - G2 / (1 + G1 * G2 * H)) == 0
    assert f["disturbance_at"] == "input"


def test_feedback_loop_rejects_bad_input():
    with pytest.raises(ValueError, match="sign"):
        block.feedback_loop(sign="*")
    with pytest.raises(ValueError, match="2 names"):
        block.feedback_loop(forward=["A", "B", "C"], signals={"u": ["U"]})
    with pytest.raises(ValueError, match="junction"):
        block.feedback_loop(junction="star")


def test_german_decimal_comma_in_labels(monkeypatch):
    monkeypatch.setenv("STUDYKIT_LOCALE", "de")
    f = block.feedback_loop(forward=["K", r"\frac{1}{s+0.5}"], feedback=None).facts
    assert "0{,}5" in f["symbols"]["G2"]


def test_chain_product(locale):
    fig = block.chain(["G_1(s)", "G_2(s)", r"\frac{1}{1+sT}"], ["U(s)", None, None, "Y(s)"])
    assert validate_svg(fig.svg) == []
    assert sp.simplify(_tf(fig.facts["transfer"]) - G1 * G2 * G3) == 0
    with pytest.raises(ValueError, match="needs 3 signals"):
        block.chain(["A", "B"], ["u", "y"])


def test_parallel_sum_with_signs(locale):
    fig = block.parallel(["G_1(s)", "G_2(s)"], ["U(s)", "Y(s)"], signs="+-")
    assert validate_svg(fig.svg) == []
    assert sp.simplify(_tf(fig.facts["transfer"]) - (G1 - G2)) == 0
    pid = block.parallel(["K_P", r"\frac{K_I}{s}", "K_D s"], ["E(s)", "U(s)"])
    assert validate_svg(pid.svg) == []
    assert sp.simplify(_tf(pid.facts["transfer"]) - (G1 + G2 + G3)) == 0
    with pytest.raises(ValueError, match="2 or 3"):
        block.parallel(["A"])


def test_wide_diagram_shrinks_to_column_width():
    fig = block.chain([f"G_{i}(s)" for i in range(1, 6)], size="col")
    assert fig.facts["scale"] < 1.0
    assert fig.facts["width_in"] <= 3.6 + 1e-6 or fig.facts["scale"] == block.MIN_SCALE
