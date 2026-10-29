"""Circuit schematics: value parsing, the drawing context, reference arrows and templates.

Assertions are on facts and on validate_svg(), never on SVG bytes.
"""

import math
import textwrap

import numpy as np
import pytest
from schemdraw import drawing_stack
from schemdraw.segments import SegmentText

from studykit.figures import circuit
from studykit.figures.validate import validate_svg

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(params=["de", "en"])
def locale(request, monkeypatch):
    monkeypatch.setenv("STUDYKIT_LOCALE", request.param)
    return request.param


@pytest.fixture
def de(monkeypatch):
    monkeypatch.setenv("STUDYKIT_LOCALE", "de")


@pytest.fixture
def en(monkeypatch):
    monkeypatch.setenv("STUDYKIT_LOCALE", "en")


def _assert_ok(fig):
    assert validate_svg(fig.svg) == []
    assert fig.png.startswith(PNG_MAGIC)
    assert fig.alt


def _component(fig, name):
    return next(c for c in fig.facts["components"] if c["name"] == name)


def _arrow(fig, name):
    return next(a for a in fig.facts["arrows"] if a["name"] == name)


# ---- values ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "kind", "si"),
    [
        ("4.7 kΩ", "resistor", 4700.0),
        ("4,7 kΩ", "resistor", 4700.0),
        ("2.2kOhm", "resistor", 2200.0),
        ("1 Ω", "resistor", 1.0),
        ("1 MΩ", "resistor", 1e6),
        ("100 nF", "capacitor", 1e-7),
        ("1 µF", "capacitor", 1e-6),
        ("1 uF", "capacitor", 1e-6),
        ("10 mH", "inductor", 1e-2),
        ("12 V", "voltage_source", 12.0),
        ("2 mA", "current_source", 2e-3),
        ("1e3", "resistor", 1000.0),
        ("1 kOhms", "resistor", 1000.0),
        ("1 k Ω", "resistor", 1000.0),
    ],
)
def test_quantity_reads_value_strings(text, kind, si):
    q = circuit.quantity(text, kind)
    assert q.si == pytest.approx(si, rel=1e-12)
    assert q.unit == circuit.KIND_UNIT[kind]


def test_quantity_formats_numbers_with_engineering_prefixes():
    assert circuit.quantity(4700, "resistor").text == "4.7 kΩ"
    assert circuit.quantity(1e-7, "capacitor").text == "100 nF"
    assert circuit.quantity(4.7e-7, "capacitor").text == "470 nF"
    assert circuit.quantity(999.9999, "resistor").text == "1 kΩ"


def test_quantity_tex_follows_locale(monkeypatch):
    monkeypatch.setenv("STUDYKIT_LOCALE", "de")
    assert circuit.quantity("4.7 kΩ", "resistor").tex == r"4{,}7\,\mathrm{k\Omega}"
    assert circuit.quantity(4.7e-7, "capacitor").tex == r"470\,\mathrm{nF}"
    assert circuit.quantity("1 µF", "capacitor").tex == r"1\,\mu\mathrm{F}"
    assert circuit.quantity("2,5 mA", "current_source").plain == "2,5 mA"
    monkeypatch.setenv("STUDYKIT_LOCALE", "en")
    assert circuit.quantity("4,7 kΩ", "resistor").tex == r"4.7\,\mathrm{k\Omega}"


def test_quantity_symbolic_and_invalid_values():
    for text in ("R", "2R", "R_0", "2 R_A", r"2\pi f L"):
        q = circuit.quantity(text, "resistor")
        assert q.si is None and q.tex == text
    assert circuit.quantity("2U", "voltage_source").si is None
    assert circuit.quantity(None, "resistor") is None
    with pytest.raises(ValueError, match="expected Ω"):
        circuit.quantity("100 nF", "resistor")
    with pytest.raises(ValueError, match="cannot read unit"):
        circuit.quantity("5 qΩ", "resistor")


@pytest.mark.parametrize(
    ("text", "kind", "hint"),
    [
        ("4.7k", "resistor", "4.7 kΩ"),
        ("2.2k", "resistor", "2.2 kΩ"),
        ("4k7", "resistor", "4.7 kΩ"),
        ("1 Meg", "resistor", "1 MΩ"),
        ("1 KΩ", "resistor", "1 kΩ"),
        ("100n", "capacitor", "100 nF"),
        ("10 nf", "capacitor", "10 nF"),
        ("5 v", "voltage_source", "5 V"),
        ("2 ma", "current_source", "2 mA"),
    ],
)
def test_quantity_rejects_spice_and_wrong_case_units(text, kind, hint):
    with pytest.raises(ValueError, match="cannot read unit") as error:
        circuit.quantity(text, kind)
    assert f"'{hint}'" in str(error.value)


def test_template_rejects_spice_values():
    with pytest.raises(ValueError, match=r"4\.7 kΩ"):
        circuit.voltage_divider("4.7k", "2.2k", "12V")


def test_value_label():
    q = circuit.quantity("1 kΩ", "resistor")
    assert circuit.value_label("R_1", q) == r"$R_1 = 1\,\mathrm{k\Omega}$"
    assert circuit.value_label("R_1", q, stacked=True) == "$R_1$\n" + r"$1\,\mathrm{k\Omega}$"
    assert circuit.value_label("R_1", None) == "$R_1$"
    assert circuit.value_label("R_1", circuit.quantity("R_1", "resistor")) == "$R_1$"
    assert circuit.value_label("R_1", circuit.quantity("2R", "resistor")) == "$R_1 = 2R$"
    assert circuit.plain_name(r"U_\mathrm{e}") == "Ue"


# ---- drawing context and reference arrows -----------------------------------------------


def test_drawing_records_components_and_arrows(de):
    with circuit.drawing(alt="Reihenschaltung") as c:
        src = c.source_v("U_0", "5 V", nodes=("1", "0")).at((0, 5)).down(5)
        c.wire((0, 5), (3, 5))
        r = c.resistor("R_1", "4.7 kΩ", nodes=("1", "2"), loc="left").at((3, 5)).down()
        cap = c.capacitor("C", "10 nF", nodes=("2", "0"), loc="left").down()
        c.wire((3, 0), (0, 0))
        circuit.zaehlpfeil_u(src, "U_0", side="left")
        circuit.zaehlpfeil_u(r, "U_R")
        circuit.zaehlpfeil_u(cap, "U_C", reverse=True)
        circuit.zaehlpfeil_i(r, "I")
        circuit.zaehlpfeil_i(src, "I_q", reverse=True, side="right")
    fig = c.figure
    _assert_ok(fig)
    assert fig.facts["template"] == "circuit.drawing"
    assert fig.facts["nodes"] == ["0", "1", "2"]
    r1 = _component(fig, "R1")
    assert r1["si"] == pytest.approx(4700.0)
    assert r1["nodes"] == ["1", "2"]
    assert r1["label"] == r"$R_1 = 4{,}7\,\mathrm{k\Omega}$"
    assert (_arrow(fig, "UR")["from"], _arrow(fig, "UR")["to"]) == ("1", "2")
    assert (_arrow(fig, "UC")["from"], _arrow(fig, "UC")["to"]) == ("0", "2")
    assert _arrow(fig, "I")["element"] == "R1"
    assert (_arrow(fig, "Iq")["from"], _arrow(fig, "Iq")["to"]) == ("0", "1")


def test_drawing_draws_every_symbol(en):
    with circuit.drawing(alt="All symbols", size="full") as c:
        circuit.Resistor().at((0, 0)).right()
        circuit.Inductor().right()
        circuit.Inductor(arcs=True).right()
        circuit.Capacitor().right()
        circuit.SourceV().right()
        circuit.SourceV(ac=True).right()
        circuit.SourceI().right()
        circuit.Opamp().at((0, 4))
        circuit.Opamp(plus_top=True).at((4, 4))
        circuit.OpampTriangle().at((8, 4))
        c.terminal((0, 0))
        c.dot((2.5, 0))
        c.ground((0, 0))
        c.text((12, 4), r"$\mathrm{A}$")
    _assert_ok(c.figure)


def test_drawing_needs_alt_text():
    with pytest.raises(ValueError, match="alt text"), circuit.drawing() as c:
        c.resistor("R", "1 kΩ").right()


def test_drawing_rejects_duplicate_names_and_bad_sides():
    with pytest.raises(ValueError, match="already"), circuit.drawing(alt="x") as c:
        c.resistor("R_1").right()
        c.resistor("R_1").right()
    with pytest.raises(ValueError, match="along the element"), circuit.drawing(alt="x"):
        r = circuit.Resistor().right()
        circuit.zaehlpfeil_u(r, "U", side="left")
    with pytest.raises(ValueError, match="unknown size"):
        circuit.drawing(alt="x", size="poster")


def test_module_docstring_example_renders(locale):
    block = circuit.__doc__.split("is `drawing`.")[1]
    code = textwrap.dedent(block[block.index("    with") :].split("return c.figure")[0])
    namespace = {"circuit": circuit}
    exec(code, namespace)
    fig = namespace["c"].figure
    _assert_ok(fig)
    assert _component(fig, "C")["nodes"] == ["2", "0"]
    u1 = _arrow(fig, "U1")
    assert (u1["element"], u1["from"], u1["to"]) == ("R1", "1", "2")


def _text_xy(overlay):
    return next(s.xy for s in overlay.segments if isinstance(s, SegmentText))


def test_default_label_and_arrow_sides_are_complementary(en):
    with circuit.drawing(alt="x", size="full") as c:
        r = c.resistor("R", "4.7 kΩ").at((0, 0)).right()
        r_left = c.resistor("R_b", "1 kΩ", loc="bottom").at((8, 0)).left()
        cap = c.capacitor("C", "10 nF", loc="right").at((10, 0)).down()
        ind = c.inductor("L", "1 mH").at((14, 0)).up()
        u_r = circuit.zaehlpfeil_u(r, "U_R")
        u_rb = circuit.zaehlpfeil_u(r_left, "U_b")
        u_c = circuit.zaehlpfeil_u(cap, "U_C")
        u_l = circuit.zaehlpfeil_u(ind, "U_L")
        i_r = circuit.zaehlpfeil_i(r, "I_R")
        i_c = circuit.zaehlpfeil_i(cap, "I_C")
        i_l = circuit.zaehlpfeil_i(ind, "I_L")
    _assert_ok(c.figure)
    assert (r.label_sides, r_left.label_sides) == ({"top"}, {"bottom"})
    assert (cap.label_sides, ind.label_sides) == ({"right"}, {"left"})
    # Voltage arrows take the side the label leaves free.
    assert all(p.y < 0 for p in u_r.segments[0].path)
    assert all(p.y > 0 for p in u_rb.segments[0].path)
    assert all(p.x < 10 for p in u_c.segments[0].path)
    assert all(p.x > 14 for p in u_l.segments[0].path)
    # Current labels: free side beside horizontal, label side beside vertical elements.
    assert _text_xy(i_r).y < 0
    assert _text_xy(i_c).x > 10
    assert _text_xy(i_l).x < 14


@pytest.mark.parametrize(
    ("loc", "direction", "message"),
    [("top", "down", "along the vertical"), ("left", "right", "along the horizontal")],
)
def test_label_side_along_the_element_is_an_error(loc, direction, message):
    with pytest.raises(ValueError, match=message), circuit.drawing(alt="x") as c:
        getattr(c.resistor("R", "1 kΩ", loc=loc), direction)()
    # The failed drawing leaves no state behind for the next one.
    assert drawing_stack.drawing_stack == {}
    assert circuit._ACTIVE == []


def test_current_arrow_needs_room_on_the_lead():
    with pytest.raises(ValueError, match="too short"), circuit.drawing(alt="x"):
        r = circuit.Resistor().right(1.2)
        circuit.zaehlpfeil_i(r, "I")


# ---- templates ----------------------------------------------------------------------------


def test_voltage_divider_facts(locale):
    fig = circuit.voltage_divider("4.7 kΩ", "2.2 kΩ", "12 V")
    _assert_ok(fig)
    assert fig.facts["template"] == "circuit.voltage_divider"
    assert _component(fig, "R1")["nodes"] == ["1", "2"]
    assert _component(fig, "R2")["nodes"] == ["2", "0"]
    assert _component(fig, "U0")["si"] == pytest.approx(12.0)
    u2 = _arrow(fig, "U2")
    assert (u2["element"], u2["from"], u2["to"]) == ("R2", "2", "0")
    ratio = 2.2 / (4.7 + 2.2)
    derived = fig.facts["derived"]
    assert derived["ratio_U2_U0"] == pytest.approx(ratio, rel=1e-5)
    assert derived["U2"] == pytest.approx(12 * ratio, rel=1e-5)
    assert derived["U1"] + derived["U2"] == pytest.approx(12.0, rel=1e-5)
    assert derived["I"] == pytest.approx(12 / 6900, rel=1e-5)
    comma = "4,7 kΩ" if locale == "de" else "4.7 kΩ"
    assert comma in fig.alt


def test_loaded_and_symbolic_voltage_divider(de):
    fig = circuit.voltage_divider("1 kΩ", "1 kΩ", "10 V", RL="2 kΩ")
    _assert_ok(fig)
    r_par = 1000 * 2000 / 3000
    assert fig.facts["loaded"] is True
    assert fig.facts["derived"]["U2"] == pytest.approx(10 * r_par / (1000 + r_par), rel=1e-5)
    assert _component(fig, "RL")["nodes"] == ["2", "0"]
    assert _arrow(fig, "IL")["element"] == "RL"
    sym = circuit.voltage_divider("R", "2R")
    _assert_ok(sym)
    assert sym.facts["derived"] == {}
    assert _component(sym, "R2")["label"] == "$R_2 = 2R$"


@pytest.mark.parametrize(
    ("build", "series", "shunt", "tau"),
    [
        (lambda: circuit.rc("lowpass", "1 kΩ", "100 nF"), "R", "C", 1e-4),
        (lambda: circuit.rc("highpass", 1000, 4.7e-7, phasors=True), "C", "R", 4.7e-4),
        (lambda: circuit.rl("lowpass", "100 Ω", "10 mH"), "L", "R", 1e-4),
        (lambda: circuit.rl("highpass", "100 Ω", "10 mH"), "R", "L", 1e-4),
    ],
)
def test_first_order_filters(de, build, series, shunt, tau):
    fig = build()
    _assert_ok(fig)
    assert _component(fig, series)["nodes"] == ["in", "out"]
    assert _component(fig, shunt)["nodes"] == ["out", "0"]
    assert (_arrow(fig, "Ua")["from"], _arrow(fig, "Ua")["to"]) == ("out", "0")
    assert fig.facts["derived"]["tau"] == pytest.approx(tau, rel=1e-5)
    assert fig.facts["derived"]["f_c"] == pytest.approx(1 / (2 * math.pi * tau), rel=1e-5)


def test_filter_kind_is_checked():
    with pytest.raises(ValueError, match="lowpass"):
        circuit.rc("bandpass", "1 kΩ", "1 nF")


def test_rlc_series_and_parallel(locale):
    w0 = 1 / math.sqrt(10e-3 * 1e-6)
    series = circuit.rlc("series", "10 Ω", "10 mH", "1 µF", U0="230 V")
    _assert_ok(series)
    assert series.facts["source"] == "voltage"
    assert [_component(series, n)["nodes"] for n in ("R", "L", "C")] == [
        ["1", "2"],
        ["2", "3"],
        ["3", "0"],
    ]
    assert series.facts["derived"]["f_0"] == pytest.approx(w0 / (2 * math.pi), rel=1e-5)
    assert series.facts["derived"]["Q"] == pytest.approx(math.sqrt(10e-3 / 1e-6) / 10, rel=1e-5)
    parallel = circuit.rlc("parallel", "1 kΩ", "10 mH", "1 µF", I0="2 mA")
    _assert_ok(parallel)
    assert parallel.facts["source"] == "current"
    assert _component(parallel, "I0")["si"] == pytest.approx(2e-3)
    assert parallel.facts["derived"]["Q"] == pytest.approx(1000 * math.sqrt(1e-6 / 10e-3))
    assert {a["name"] for a in parallel.facts["arrows"]} >= {"IR", "IL", "IC", "U", "I0"}


def test_rlc_source_checks():
    with pytest.raises(ValueError, match="I0 for a current source"):
        circuit.rlc("series", "1 Ω", "1 mH", "1 µF", I0="1 A")
    with pytest.raises(ValueError, match="topology"):
        circuit.rlc("bridged")


@pytest.mark.parametrize(
    ("kind", "kwargs", "derived", "pins"),
    [
        ("inverting", {"R1": "10 kΩ", "R2": "47 kΩ"}, {"gain": -4.7}, ("n", "0")),
        ("non_inverting", {"R1": "10 kΩ", "R2": "47 kΩ"}, {"gain": 5.7}, ("n", "in")),
        ("follower", {}, {"gain": 1.0}, ("out", "in")),
        ("integrator", {"R": "10 kΩ", "C": "100 nF"}, {"tau": 1e-3}, ("n", "0")),
        ("differentiator", {"R": "10 kΩ", "C": "100 nF"}, {"tau": 1e-3}, ("n", "0")),
    ],
)
def test_opamp_templates(de, kind, kwargs, derived, pins):
    fig = circuit.opamp(kind, **kwargs)
    _assert_ok(fig)
    assert fig.facts["kind"] == kind
    for key, value in derived.items():
        assert fig.facts["derived"][key] == pytest.approx(value, rel=1e-5)
    assert (fig.facts["opamp_pins"]["minus"], fig.facts["opamp_pins"]["plus"]) == pins
    assert {a["name"] for a in fig.facts["arrows"]} == {"Ue", "Ua"}


def test_opamp_component_nodes_and_symbols(en):
    fig = circuit.opamp("inverting", "10 kΩ", "47 kΩ", symbol="triangle")
    _assert_ok(fig)
    assert _component(fig, "R1")["nodes"] == ["in", "n"]
    assert _component(fig, "R2")["nodes"] == ["n", "out"]
    assert {a["name"] for a in fig.facts["arrows"]} == {"Uin", "Uout"}
    _assert_ok(circuit.opamp("non_inverting", "1 kΩ", "1 kΩ", symbol="triangle"))
    with pytest.raises(ValueError, match="integrator uses"):
        circuit.opamp("integrator", R1="1 kΩ")
    with pytest.raises(ValueError, match="symbol"):
        circuit.opamp("inverting", symbol="box")


def test_wheatstone_bridge(locale):
    fig = circuit.bridge("wheatstone", "1 kΩ", "2 kΩ", "1.5 kΩ", "3 kΩ", "10 V")
    _assert_ok(fig)
    assert fig.facts["derived"]["balanced"] is True
    assert fig.facts["derived"]["U_AB"] == pytest.approx(0.0, abs=1e-9)
    uab = _arrow(fig, "UAB")
    assert (uab["from"], uab["to"]) == ("A", "B")
    assert _component(fig, "R3")["nodes"] == ["T", "B"]


def test_wheatstone_bridge_with_detector_resistor(de):
    fig = circuit.bridge("wheatstone", "1 kΩ", "2 kΩ", "2 kΩ", "1 kΩ", "10 V", R5="500 Ω")
    _assert_ok(fig)
    g = [1 / r for r in (1e3, 2e3, 2e3, 1e3, 500.0)]
    a = np.array([[g[0] + g[1] + g[4], -g[4]], [-g[4], g[2] + g[3] + g[4]]])
    ua, ub = np.linalg.solve(a, np.array([g[0] * 10, g[2] * 10]))
    assert fig.facts["derived"]["balanced"] is False
    assert fig.facts["derived"]["U_AB"] == pytest.approx(ua - ub, rel=1e-5)
    assert _arrow(fig, "UAB")["element"] == "R5"
    with pytest.raises(ValueError, match="wheatstone"):
        circuit.bridge("maxwell")


def test_bridge_with_zero_ohm_resistors(de):
    # Shorted diagonal: A and B are one node fed by R1 || R3 from T and R2 || R4 to ground.
    fig = circuit.bridge("wheatstone", "1 kΩ", "1 kΩ", "1 kΩ", "2 kΩ", "5 V", R5="0 Ω")
    _assert_ok(fig)
    g1, g2, g3, g4 = (1 / r for r in (1e3, 1e3, 1e3, 2e3))
    u_node = 5 * (g1 + g3) / (g1 + g2 + g3 + g4)
    derived = fig.facts["derived"]
    assert derived["U_A"] == pytest.approx(u_node, rel=1e-5)
    assert derived["U_B"] == pytest.approx(u_node, rel=1e-5)
    assert derived["U_AB"] == 0.0
    # R1 = 0 ties A to the top node.
    tied = circuit.bridge("wheatstone", "0 Ω", "1 kΩ", "1 kΩ", "3 kΩ", "8 V").facts["derived"]
    assert tied["U_A"] == pytest.approx(8.0) and tied["U_B"] == pytest.approx(6.0)
    # R1 = R2 = 0 shorts the source: no node voltage is defined, nothing crashes.
    shorted = circuit.bridge("wheatstone", "0 Ω", "0 Ω", "1 kΩ", "1 kΩ", "5 V")
    _assert_ok(shorted)
    assert not {"U_A", "U_B", "U_AB"} & set(shorted.facts["derived"])


def test_zero_values_keep_the_defined_derived_numbers(de):
    rc = circuit.rc("lowpass", "0 Ω", "1 nF")
    _assert_ok(rc)
    assert rc.facts["derived"] == {"tau": 0.0}
    assert circuit.rl("lowpass", "0 Ω", "10 mH").facts["derived"] == {"omega_c": 0.0, "f_c": 0.0}
    assert set(circuit.rl("highpass", "100 Ω", "0 H").facts["derived"]) == {"tau"}
    w0 = 1 / math.sqrt(10e-3 * 1e-6)
    lc = circuit.rlc("series", "0 Ω", "10 mH", "1 µF")  # ideal LC circuit: no Q
    _assert_ok(lc)
    assert lc.facts["derived"]["omega_0"] == pytest.approx(w0, rel=1e-5)
    assert "Q" not in lc.facts["derived"]
    assert lc.facts["derived"]["bandwidth_Hz"] == 0.0
    parallel = circuit.rlc("parallel", "0 Ω", "10 mH", "1 µF").facts["derived"]
    assert parallel["Q"] == 0.0 and "bandwidth_Hz" not in parallel
    symbolic_r = circuit.rlc("series", "R", "10 mH", "1 µF").facts["derived"]
    assert symbolic_r == {
        "omega_0": pytest.approx(w0, rel=1e-5),
        "f_0": pytest.approx(w0 / 2 / math.pi, rel=1e-5),
    }
    series = circuit.rlc("series", "10 Ω", "10 mH", "1 µF").facts["derived"]
    assert series["bandwidth_Hz"] == pytest.approx(series["f_0"] / series["Q"], rel=1e-5)
    assert "gain" not in circuit.opamp("inverting", "0 Ω", "10 kΩ").facts["derived"]
    assert circuit.voltage_divider("0 Ω", "0 Ω", "5 V").facts["derived"] == {}
    upper_short = circuit.voltage_divider("0 Ω", "1 kΩ", "5 V").facts["derived"]
    assert upper_short["ratio_U2_U0"] == 1.0 and upper_short["I"] == pytest.approx(5e-3)
    load_short = circuit.voltage_divider("1 kΩ", "1 kΩ", "10 V", RL="0 Ω").facts["derived"]
    assert load_short["R2_parallel_RL"] == 0.0 and load_short["U2"] == 0.0
    assert load_short["I"] == pytest.approx(10e-3)


def test_quantity_rejects_negative_components_and_infinity():
    with pytest.raises(ValueError, match="negative"):
        circuit.quantity("-10 mH", "inductor")
    with pytest.raises(ValueError, match="negative"):
        circuit.quantity(-1.0, "resistor")
    with pytest.raises(ValueError, match="negative"):
        circuit.rlc("series", "1 Ω", "-10 mH", "1 µF")
    with pytest.raises(ValueError, match="finite"):
        circuit.quantity(math.inf, "capacitor")
    assert circuit.quantity("-5 V", "voltage_source").si == pytest.approx(-5.0)


@pytest.mark.parametrize("size", ["half", "cs", "full"])
def test_templates_fit_every_size(de, size):
    fig = circuit.rc("lowpass", "1 kΩ", "100 nF", size=size)
    _assert_ok(fig)
    assert fig.facts["scale_in_per_unit"] <= circuit.STYLE[size]["ipu"]
