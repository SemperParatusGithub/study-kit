"""Circuit schematics: value parsing, the drawing context, reference arrows and templates.

Assertions are on facts and on validate_svg(), never on SVG bytes.
"""

import pytest

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
    for text in ("R", "2R", "R_0"):
        q = circuit.quantity(text, "resistor")
        assert q.si is None and q.tex == text
    assert circuit.quantity(None, "resistor") is None
    with pytest.raises(ValueError, match="expected Ω"):
        circuit.quantity("100 nF", "resistor")
    with pytest.raises(ValueError, match="cannot read unit"):
        circuit.quantity("5 qΩ", "resistor")


def test_value_label():
    q = circuit.quantity("1 kΩ", "resistor")
    assert circuit.value_label("R_1", q) == r"$R_1 = 1\,\mathrm{k\Omega}$"
    assert circuit.value_label("R_1", q, stacked=True) == "$R_1$\n" + r"$1\,\mathrm{k\Omega}$"
    assert circuit.value_label("R_1", None) == "$R_1$"
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


def test_current_arrow_needs_room_on_the_lead():
    with pytest.raises(ValueError, match="too short"), circuit.drawing(alt="x"):
        r = circuit.Resistor().right(1.2)
        circuit.zaehlpfeil_i(r, "I")
