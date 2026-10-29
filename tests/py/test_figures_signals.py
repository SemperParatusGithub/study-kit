"""Control and signal templates: facts are checked against independent closed forms."""

import math

import control as ct
import numpy as np
import pytest
from scipy.optimize import brentq

from studykit.figures import signals
from studykit.figures.validate import validate_svg

G_LOOP = "10/(s*(s+1)*(s+10))"  # type-1 loop: GM = 11 at w = sqrt(10)


@pytest.fixture(params=["de", "en"])
def locale(request, monkeypatch):
    monkeypatch.setenv("STUDYKIT_LOCALE", request.param)
    return request.param


def test_transfer_function_inputs_agree():
    from_str = signals.plant("10/((s+1)*(s+10))")
    from_coeffs = signals.plant(([10], [1, 11, 10]))
    from_tf = signals.plant(ct.tf([20], [2, 22, 20]))
    for p in (from_coeffs, from_tf):
        np.testing.assert_allclose(p.num, from_str.num)
        np.testing.assert_allclose(p.den, from_str.den)
    assert not from_str.discrete
    assert signals.plant("(z-0.5)/(z**2-0.25)").discrete
    with pytest.raises(ValueError, match="dead time"):
        signals.plant("exp(-s)/(s+1)")
    with pytest.raises(ValueError, match="s or of z"):
        signals.plant("1/(s+a)")


def test_repeated_roots_are_merged():
    st = signals.structure(signals.plant("1/(s+1)**3"))
    assert list(st.poles) == [-1, -1, -1]


def test_bode_margins_cross_checked(locale):
    fig = signals.bode(G_LOOP, margins=True)
    assert validate_svg(fig.svg) == []
    mg = fig.facts["margins"]
    assert mg["agree"]
    assert mg["gm"] == pytest.approx(11, rel=1e-9)
    assert mg["gm_db"] == pytest.approx(20 * math.log10(11), rel=1e-9)
    assert mg["w_pc"] == pytest.approx(math.sqrt(10), rel=1e-9)
    # |G(jw)| = 1  <=>  w^2 (w^2 + 1)(w^2 + 100) = 100, solved here on its own.
    w_gc = math.sqrt(brentq(lambda x: x * (x + 1) * (x + 100) - 100, 0, 1))
    assert mg["w_gc"] == pytest.approx(w_gc, rel=1e-9)
    pm = 180 - 90 - math.degrees(math.atan(w_gc) + math.atan(w_gc / 10))
    assert mg["pm_deg"] == pytest.approx(pm, abs=1e-7)
    for key in ("gm", "w_pc", "pm_deg", "w_gc"):
        assert mg["control"][key] == pytest.approx(mg["check"][key], rel=1e-6)
    # Unwrapped phase -90 - atan(w) - atan(w/10) over the default range 0.01 .. 100 rad/s.
    assert fig.facts["omega_range"] == pytest.approx([0.01, 100])
    phase = [-90 - math.degrees(math.atan(w) + math.atan(w / 10)) for w in (100, 0.01)]
    assert fig.facts["phase_deg_range"] == pytest.approx(phase, abs=1e-9)
    assert "47.4 degrees" in fig.alt


def test_bode_without_crossings_has_no_margins():
    mg = signals.stability_margins("10/((s+1)*(s+10))")
    assert mg["gm"] is None and mg["pm_deg"] is None
    assert mg["check"]["gain_crossovers"] == [] and mg["check"]["phase_crossovers"] == []


def test_bode_asymptotes():
    fig = signals.bode("10/((s+1)*(s+10))", asymptotes=True)
    assert validate_svg(fig.svg) == []
    corners = fig.facts["corners"]
    assert [c["omega"] for c in corners] == pytest.approx([1, 10])
    assert [c["slope_change_db_per_decade"] for c in corners] == [-20, -20]
    assert fig.facts["k_bode"] == pytest.approx(1)
    p = signals.plant("10/((s+1)*(s+10))")
    mag, ph = signals.bode_asymptotes(p, np.array([0.01, 1.0, 10.0, 100.0]))
    np.testing.assert_allclose(mag, [0, 0, -20, -60], atol=1e-12)
    np.testing.assert_allclose(ph, [0, -45, -135, -180], atol=1e-12)


def test_bode_hz_complex_pair_and_negative_gain():
    fig = signals.bode(([1], [1, 0.4, 1]), unit="Hz", asymptotes=True, margins=True)
    assert validate_svg(fig.svg) == []
    (corner,) = fig.facts["corners"]
    assert corner["complex"] and corner["order"] == 2
    assert corner["zeta"] == pytest.approx(0.2)
    hz = fig.facts["crossovers_hz"]
    assert hz["f_gc"] == pytest.approx(fig.facts["margins"]["w_gc"] / (2 * math.pi))
    assert hz["f_pc"] is None
    # A negative gain starts at -180 degrees, not +180.
    ph = signals.phase_deg(signals.plant("-2/(s+1)"), np.array([1e-4, 1e4]))
    np.testing.assert_allclose(ph, [-180, -270], atol=0.1)
    # A right-half-plane zero: 0 -> -270, never shifted by a full turn.
    w = np.array([1e-4, 1.0, 1e4])
    ph = signals.phase_deg(signals.plant("(1-s)/((s+1)*(s+2))"), w)
    exact = -np.degrees(np.arctan(w) + np.arctan(w) + np.arctan(w / 2))
    np.testing.assert_allclose(ph, exact, atol=1e-9)


def test_bode_negative_margins():
    mg = signals.stability_margins("200/(s*(s+1)*(s+10))")
    assert mg["gm"] == pytest.approx(110 / 200, rel=1e-9)  # Routh: K_crit = 110
    assert mg["pm_deg"] < 0
    fig = signals.bode("200/(s*(s+1)*(s+10))", margins=True)
    assert validate_svg(fig.svg) == []


def test_nyquist_encirclements_match_closed_loop(locale):
    stable = signals.nyquist("2/((s+1)*(s+2)*(s+3))")
    unstable = signals.nyquist("100/((s+1)*(s+2)*(s+3))")
    for fig in (stable, unstable):
        assert validate_svg(fig.svg) == []
        assert fig.facts["nyquist_criterion_consistent"]
    assert stable.facts["encirclements_cw"] == 0 and stable.facts["closed_loop_stable"]
    assert unstable.facts["encirclements_cw"] == 2
    assert unstable.facts["closed_loop_rhp_poles"] == 2
    (cross,) = unstable.facts["real_axis_crossings"]
    assert cross["omega"] == pytest.approx(math.sqrt(11), rel=1e-9)
    assert cross["re"] == pytest.approx(-100 / 60, rel=1e-9)
    assert stable.facts["start"] == pytest.approx([2 / 6, 0])


def test_nyquist_with_integrators():
    one = signals.nyquist(G_LOOP)
    two = signals.nyquist("(s+0.5)/(s**2*(s+2))")
    unstable = signals.nyquist("200/(s*(s+1)*(s+10))")  # Routh: unstable for K > 110
    for fig in (one, two, unstable):
        assert validate_svg(fig.svg) == []
        assert fig.facts["unbounded"]
        assert fig.facts["nyquist_criterion_consistent"]
    assert one.facts["encirclements_cw"] == 0 and one.facts["closed_loop_stable"]
    assert two.facts["closed_loop_stable"]
    assert unstable.facts["encirclements_cw"] == 2 and not unstable.facts["closed_loop_stable"]
    # Undamped poles at +-j: s^3 + s^2 + s + 2 has two right-half-plane roots.
    undamped = signals.nyquist("1/((s**2+1)*(s+1))")
    assert undamped.facts["encirclements_cw"] == 2
    assert undamped.facts["nyquist_criterion_consistent"]
    assert undamped.facts["view_radius"] < 10
    # Open-loop unstable, closed loop stable: one counter-clockwise encirclement.
    rhp = signals.nyquist("2/(s-1)")
    assert rhp.facts["open_loop_rhp_poles"] == 1 and rhp.facts["encirclements_cw"] == -1
    assert rhp.facts["closed_loop_stable"]
