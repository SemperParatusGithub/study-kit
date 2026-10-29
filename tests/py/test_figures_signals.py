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


def test_phase_is_continuous_for_right_half_plane_pairs():
    w = np.logspace(-2, 2, 4001)
    # Unstable pair 0.1 +- j 0.995: Im 1/den(jw) > 0, so the phase runs 0 -> +180.
    ph = signals.phase_deg(signals.plant("1/(s**2-0.2*s+1)"), w)
    np.testing.assert_allclose(ph, np.degrees(np.arctan2(0.2 * w, 1 - w**2)), atol=1e-9)
    assert np.max(np.abs(np.diff(ph))) < 5  # no 360-degree jump at w = Im r
    fig = signals.bode("1/(s**2-0.2*s+1)", asymptotes=True)
    assert validate_svg(fig.svg) == []
    lo, hi = fig.facts["omega_range"]
    ends = [math.degrees(math.atan2(0.2 * x, 1 - x**2)) for x in (lo, hi)]
    assert fig.facts["phase_deg_range"] == pytest.approx(ends, abs=1e-9)  # 1.16 .. 179.9
    # Non-minimum-phase complex zeros 0.2 +- j 1.99: the numerator adds 0 -> -180.
    ph = signals.phase_deg(signals.plant("(s**2-0.4*s+4)/((s+1)*(s+2)*(s+3))"), w)
    exact = -np.arctan2(0.4 * w, 4 - w**2) - np.arctan(w) - np.arctan(w / 2) - np.arctan(w / 3)
    np.testing.assert_allclose(ph, np.degrees(exact), atol=1e-9)


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


def test_pole_zero(locale):
    fig = signals.pole_zero("(s+2)/((s+1)**2*(s**2+2*s+5))")
    assert validate_svg(fig.svg) == []
    poles = {tuple(p["value"]): p for p in fig.facts["poles"]}
    assert poles[(-1.0, 0.0)]["multiplicity"] == 2
    assert poles[(-1.0, 2.0)]["zeta"] == pytest.approx(1 / math.sqrt(5))
    assert poles[(-1.0, 2.0)]["omega_n"] == pytest.approx(math.sqrt(5))
    assert [z["value"] for z in fig.facts["zeros"]] == [[-2.0, 0.0]]
    assert fig.facts["stable"] and fig.facts["dc_gain"] == pytest.approx(2 / 5)

    disc = signals.pole_zero("(z-0.5)/((z-0.8)*(z**2-z+0.5))")
    assert validate_svg(disc.svg) == []
    assert disc.facts["discrete"] and disc.facts["stable"]
    assert max(p["magnitude"] for p in disc.facts["poles"]) == pytest.approx(0.8)
    assert not signals.pole_zero("1/((s-1)*(s+2))").facts["stable"]


def second_order_step(zeta, wn):
    wd = wn * math.sqrt(1 - zeta**2)

    def y(t):
        return 1 - math.exp(-zeta * wn * t) / math.sqrt(1 - zeta**2) * math.sin(
            wd * t + math.acos(zeta)
        )

    return y, wd


def test_step_response_second_order(locale):
    zeta, wn = 0.5, 2.0
    fig = signals.step_response(f"{wn**2}/(s**2+{2 * zeta * wn}*s+{wn**2})")
    assert validate_svg(fig.svg) == []
    m = fig.facts["metrics"]
    y, wd = second_order_step(zeta, wn)
    assert m["final"] == pytest.approx(1)
    assert m["overshoot_percent"] == pytest.approx(
        100 * math.exp(-math.pi * zeta / math.sqrt(1 - zeta**2)), abs=1e-4
    )
    assert m["peak_time"] == pytest.approx(math.pi / wd, abs=1e-4)
    t10 = brentq(lambda t: y(t) - 0.1, 1e-9, math.pi / wd)
    t90 = brentq(lambda t: y(t) - 0.9, 1e-9, math.pi / wd)
    assert m["rise_time"] == pytest.approx(t90 - t10, abs=1e-4)
    # Settling: last entry into the 2 % band, scanned backwards on the closed form.
    ts_grid = np.linspace(20, 0, 200001)
    out = np.array([abs(y(t) - 1) > 0.02 for t in ts_grid])
    k = int(np.argmax(out))
    t_s = brentq(lambda t: abs(y(t) - 1) - 0.02, ts_grid[k], ts_grid[k - 1])
    assert m["settling_time"] == pytest.approx(t_s, abs=1e-3)
    assert fig.facts["scipy_max_abs_diff"] < 1e-6
    assert fig.facts["step_info"]["Overshoot"] == pytest.approx(m["overshoot_percent"], abs=0.05)
    assert fig.facts["t_range"][1] > m["settling_time"]


def test_step_response_first_order_in_ms():
    tau = 1e-3
    fig = signals.step_response("1/(1e-3*s+1)", annotate=("final", "rise", "settling"))
    assert validate_svg(fig.svg) == []
    m = fig.facts["metrics"]
    assert fig.facts["time_axis"] == {"unit": "ms", "scale": 1000.0}
    assert m["rise_time"] == pytest.approx(tau * math.log(9), rel=1e-4)
    assert m["settling_time"] == pytest.approx(tau * math.log(50), rel=1e-4)
    assert m["overshoot_percent"] == 0 and m["peak_time"] is None
    assert "ms" in fig.alt


def test_step_response_negative_gain():
    fig = signals.step_response("-3/(s**2+2*s+4)")
    assert validate_svg(fig.svg) == []
    m = fig.facts["metrics"]
    assert m["final"] == pytest.approx(-0.75)
    assert m["peak"] == pytest.approx(-0.75 * (1 + m["overshoot_percent"] / 100))
    assert m["overshoot_percent"] == pytest.approx(
        100 * math.exp(-math.pi / math.sqrt(3)), abs=1e-4
    )


def test_step_response_unstable_and_bad_input():
    fig = signals.step_response("1/(s-1)", t=(0, 2))
    assert validate_svg(fig.svg) == []
    assert not fig.facts["stable"] and fig.facts["metrics"] is None
    with pytest.raises(ValueError, match="unknown annotation"):
        signals.step_response("1/(s+1)", annotate=("delay",))
    with pytest.raises(ValueError, match="proper"):
        signals.step_response("s**2/(s+1)")


def test_root_locus(locale):
    fig = signals.root_locus("1/(s*(s+1)*(s+2))")
    assert validate_svg(fig.svg) == []
    f = fig.facts
    assert f["k_crit"] == pytest.approx(6, rel=1e-9)
    (cross,) = f["imag_axis_crossings"]
    assert cross["omega"] == pytest.approx(math.sqrt(2), rel=1e-9)
    assert f["k_crit_check_gm"] == pytest.approx(6, rel=1e-6)
    assert max(f["imag_axis_crossing_residuals"]) < 1e-6
    assert f["asymptotes"]["centroid"] == pytest.approx(-1)
    assert f["asymptotes"]["angles_deg"] == pytest.approx([60, 180, 300])
    (brk,) = f["breakaway"]
    assert brk["s"] == pytest.approx(-1 + 1 / math.sqrt(3))
    assert brk["k"] == pytest.approx(2 / (3 * math.sqrt(3)))

    circle = signals.root_locus("(s+2)/(s**2+2*s+5)")
    assert validate_svg(circle.svg) == []
    assert circle.facts["k_crit"] is None
    assert [b["s"] for b in circle.facts["breakaway"]] == pytest.approx([-2 - math.sqrt(5)])
    disc = signals.root_locus("(z+0.5)/((z-1)*(z-0.5))")
    assert validate_svg(disc.svg) == [] and disc.facts["discrete"]


def test_phasor(locale):
    fig = signals.phasor({"U_R": (5, 0), "U_L": (3, 90)}, chain=True)
    assert validate_svg(fig.svg) == []
    res = fig.facts["resultant"]
    assert res["name"] == "U"
    assert res["magnitude"] == pytest.approx(math.sqrt(34))
    assert res["angle_deg"] == pytest.approx(math.degrees(math.atan2(3, 5)))
    assert fig.facts["vectors"][1]["start"] == pytest.approx([5, 0])
    star = signals.phasor({"U_1": (230, 0), "U_2": (230, -120), "U_3": (230, 120)})
    assert validate_svg(star.svg) == []
    assert star.facts["resultant"]["magnitude"] == pytest.approx(0, abs=1e-9)
    assert signals._phasor_tex("U_R") == r"$\underline{U}_{R}$"
    assert signals._phasor_tex("I") == r"$\underline{I}$"
    with pytest.raises(ValueError):
        signals.phasor({"U": (-1, 0)})


def test_signals(locale):
    t = np.linspace(0, 2e-3, 2001)
    fig = signals.signals(t, {"u": lambda t: np.sin(2 * np.pi * 1e3 * t)}, y_unit="V")
    assert validate_svg(fig.svg) == []
    s = fig.facts["series"]["u"]
    assert s["mean"] == pytest.approx(0, abs=1e-9)
    assert s["rms"] == pytest.approx(1 / math.sqrt(2), rel=1e-5)
    assert fig.facts["time_axis"]["unit"] == "ms"

    n = np.arange(0, 8)
    seq = signals.signals(n, {"x": 0.5**n, "y": np.ones(8)}, stem=True)
    assert validate_svg(seq.svg) == []
    assert seq.facts["series"]["x"]["values"] == pytest.approx(list(0.5**n))
    assert seq.facts["series"]["y"]["mean"] == pytest.approx(1)
    with pytest.raises(ValueError):
        signals.signals([0.0], {"x": [1.0]})
