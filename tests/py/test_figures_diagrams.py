"""Block diagrams, state machines, flowcharts and the topic map: facts and SVG validity."""

from __future__ import annotations

import itertools
import json
import math

import pytest
import sympy as sp

from studykit.figures import block, graph
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
    f = block.chain([r"$K = 0.5$", "T = 0.5"]).facts
    assert f["symbols"] == {"G1": "K = 0{,}5", "G2": "T = 0{,}5"}
    # The drawing goes through the same rule: math, text and mixed labels.
    assert block.label(r"$K = 0.5$") == (r"$K = 0{,}5$", True)
    assert block.label("T = 0.5") == (r"$T = 0{,}5$", True)
    assert block.label("Warte 0.5 s", math=False) == ("Warte 0,5 s", False)
    assert block.label("x > 0.5", math=False) == ("x > 0,5", False)
    assert block.label("x_k > 0.5?", math=False) == (r"$x_k > 0{,}5?$", True)
    assert block.label("Ausgabe 1.5 $s_{0.5}$") == (r"Ausgabe 1,5 $s_{0{,}5}$", True)


def test_english_labels_keep_the_decimal_point(monkeypatch):
    monkeypatch.setenv("STUDYKIT_LOCALE", "en")
    assert block.label("x > 0.5", math=False) == ("x > 0.5", False)
    assert block.label("T = 0.5") == ("$T = 0.5$", True)


def test_sum_labels_keep_their_parentheses(locale):
    fig = block.feedback_loop(forward=["K_P", "1 + sT_V", r"\frac{1}{s}"], feedback=None)
    assert validate_svg(fig.svg) == []
    ref = fig.facts["reference_tf"]
    product = r"K_P \left(1 + sT_V\right) \frac{1}{s}"
    assert ref["latex"] == rf"\frac{{{product}}}{{{product} + 1}}"
    assert ref["text"] == r"K_P*(1 + sT_V)*\frac{1}{s}/(K_P*(1 + sT_V)*\frac{1}{s} + 1)"
    assert ref["text"] in fig.alt
    ch = block.chain(["K", "1+sT"])
    assert ch.facts["transfer"]["latex"] == r"K \left(1+sT\right)"
    assert "K*(1+sT)" in ch.alt
    par = block.parallel(["K", "a + b"], signs="+-")
    assert par.facts["transfer"]["text"] == "K - (a + b)"
    assert par.facts["transfer"]["latex"] == r"K - \left(a + b\right)"
    assert "K - (a + b)" in par.alt


def test_word_labels_are_upright_text_and_never_corrupt_the_formula(locale):
    fig = block.feedback_loop(forward=["Regler", "Heizung"], feedback="Thermometer")
    assert validate_svg(fig.svg) == []
    ref = fig.facts["reference_tf"]
    assert ref["text"] == "Regler*Heizung/(Regler*Heizung*Thermometer + 1)"
    assert ref["latex"] == (
        r"\frac{\text{Regler} \cdot \text{Heizung}}"
        r"{\text{Regler} \cdot \text{Heizung} \cdot \text{Thermometer} + 1}"
    )
    assert ref["text"] in fig.alt
    assert block.label("Regelstrecke") == ("Regelstrecke", False)
    assert block.label("Störgröße") == ("Störgröße", False)
    assert block.label("K_P") == ("$K_P$", True)
    assert block.label("1 + sT") == ("$1 + sT$", True)
    # A label that contains another symbol's name or a capital H stays intact.
    fig = block.feedback_loop(forward=["K_H", "G_H(s)"], feedback="H_M(s)")
    assert fig.facts["reference_tf"]["text"] == "K_H*G_H(s)/(K_H*G_H(s)*H_M(s) + 1)"
    assert fig.facts["reference_tf"]["text"] in fig.alt


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


# --- state machines ----------------------------------------------------------------------

MOORE = {"Z0": "0", "Z1": "0", "Z2": "0", "Z3": "1"}
MOORE_T = [
    ("Z0", "Z1", "1"),
    ("Z0", "Z0", "0"),
    ("Z1", "Z2", "1"),
    ("Z1", "Z0", "0"),
    ("Z2", "Z3", "1"),
    ("Z2", "Z0", "0"),
    ("Z3", "Z3", "1"),
    ("Z3", "Z0", "0"),
]


def _edge(facts: dict, src: str, dst: str) -> dict:
    return next(e for e in facts["edges"] if e["src"] == src and e["dst"] == dst)


def test_moore_machine_facts(locale):
    fig = graph.state_machine(MOORE, MOORE_T, initial="Z0")
    assert validate_svg(fig.svg) == []
    f = fig.facts
    assert f["template"] == "graph.state_machine" and f["kind"] == "moore"
    assert [(s["name"], s["output"]) for s in f["states"]] == list(MOORE.items())
    assert len(f["transitions"]) == 8
    assert _edge(f, "Z0", "Z0")["route"] == "loop"
    there, back = _edge(f, "Z0", "Z1"), _edge(f, "Z1", "Z0")
    assert there["route"] == back["route"] == "arc"
    assert there["k"] > 0 and back["k"] > 0  # each bends to its own left: opposite sides
    assert f["reachable"] == ["Z0", "Z1", "Z2", "Z3"] and f["unreachable"] == []
    assert f["label_overlaps"] == 0 and f["label_state_gap"] > 0
    assert "Z0" in fig.alt


def test_mealy_machine_labels_and_validation():
    t = [("S_0", "S_1", "a", "0"), ("S_1", "S_0", "b", "1"), ("S_1", "S_1", "a", "1")]
    f = graph.state_machine(["S_0", "S_1", "S_2"], t, initial="S_0", kind="mealy").facts
    assert [e["label"] for e in f["transitions"]] == ["a/0", "b/1", "a/1"]
    assert f["unreachable"] == ["S_2"]
    with pytest.raises(ValueError, match="Mealy"):
        graph.state_machine({"A": "1"}, [], kind="mealy")
    with pytest.raises(ValueError, match="unknown state"):
        graph.state_machine(["A"], [("A", "B", "x")])
    with pytest.raises(ValueError, match="layout"):
        graph.state_machine(["A"], [], layout="spiral")


def test_eight_states_stay_legible():
    names = [f"q{i}" for i in range(8)]
    t = [(f"q{i}", f"q{(i + 1) % 8}", "1") for i in range(8)]
    t += [(n, n, "0") for n in names] + [("q0", "q4", "r"), ("q6", "q2", "r"), ("q3", "q0", "x/y")]
    fig = graph.state_machine(names, t, initial="q0", accepting=["q7"], size="full")
    assert validate_svg(fig.svg) == []
    f = fig.facts
    xy = {s["name"]: s["xy"] for s in f["states"]}
    closest = min(math.dist(xy[a], xy[b]) for a, b in itertools.combinations(names, 2))
    assert closest >= 2 * f["radius"] + 1.5
    assert f["label_overlaps"] == 0 and f["label_state_gap"] > 0
    assert f["scale"] == 1.0
    assert [s["name"] for s in f["states"] if s["accepting"]] == ["q7"]


def test_row_layout_bends_edges_around_states():
    t = [("q0", "q1", "a"), ("q1", "q2", "b"), ("q0", "q2", "c"), ("q1", "q1", "a")]
    f = graph.state_machine(["q0", "q1", "q2"], t, initial="q0", layout="row").facts
    assert _edge(f, "q0", "q1")["route"] == "line"
    assert _edge(f, "q0", "q2")["route"] == "arc"
    assert [s["xy"][1] for s in f["states"]] == [0.0, 0.0, 0.0]
    grid = graph.state_machine(
        ["a", "b", "c", "d"],
        [("a", "d", "x")],
        layout={"a": (0, 0), "b": (1, 0), "c": (0, -1), "d": (1, -1)},
    )
    assert validate_svg(grid.svg) == []
    assert grid.facts["layout"] == "coords"


# --- flowcharts --------------------------------------------------------------------------

LOOP_NODES = [
    ("s", "start", "Start"),
    ("i", "process", "$i = 0$"),
    ("d", "decision", "$i < n$?"),
    ("b", "process", "$s = s + a_i$"),
    ("inc", "process", "$i = i + 1$"),
    ("o", "io", "Ausgabe $s$"),
    ("e", "end", "Ende"),
]
LOOP_EDGES = [
    ("s", "i"),
    ("i", "d"),
    ("d", "b", "ja"),
    ("b", "inc"),
    ("inc", "d"),
    ("d", "o", "nein"),
    ("o", "e"),
]


def test_flowchart_loop_layout(locale):
    fig = graph.flowchart(LOOP_NODES, LOOP_EDGES)
    assert validate_svg(fig.svg) == []
    f = fig.facts
    nodes = {n["id"]: n for n in f["nodes"]}
    assert {k: nodes[k]["layer"] for k in nodes} == {
        "s": 0, "i": 1, "d": 2, "b": 3, "inc": 4, "o": 3, "e": 4
    }  # fmt: skip
    assert [nodes[k]["column"] for k in ("s", "i", "d", "b", "inc")] == [0] * 5
    assert nodes["o"]["column"] == 1
    edges = {(e["src"], e["dst"]): e for e in f["edges"]}
    assert edges[("inc", "d")]["back"] is True
    assert edges[("d", "b")]["port"] == "S" and edges[("d", "o")]["port"] == "E"
    # The loop returns on the left of the main column and enters the decision from above.
    back = edges[("inc", "d")]["points"]
    assert min(p[0] for p in back) < nodes["d"]["xy"][0] - 1.0
    assert back[-1][1] > nodes["d"]["xy"][1]


def test_flowchart_rejects_bad_input():
    with pytest.raises(ValueError, match="kind"):
        graph.flowchart([("a", "cloud", "x")], [])
    with pytest.raises(ValueError, match="unknown node"):
        graph.flowchart([("a", "start", "A")], [("a", "b")])


# --- topic map ---------------------------------------------------------------------------

SMALL_COURSE = """\
schema: 1
id: get2
lang: de
topics:
  - {id: gleichstrom,  title: Gleichstromnetzwerke,          weight: 0.15, prereq: []}
  - {id: wechselstrom, title: Komplexe Wechselstromrechnung, weight: 0.30, prereq: [gleichstrom]}
  - {id: rc-filter,    title: RC-Filter und Bode-Diagramm,   weight: 0.25, prereq: [wechselstrom]}
focus: [wechselstrom]
skip: []
"""

BIG_COURSE = """\
schema: 1
id: rt
lang: de
topics:
  - {id: gleichstrom, title: Gleichstromnetzwerke und Kirchhoffsche Regeln, weight: 0.04, prereq: []}
  - {id: netzwerk, title: Netzwerkanalyse mit Knoten- und Maschenverfahren, weight: 0.05, prereq: [gleichstrom]}
  - {id: wechselstrom, title: Komplexe Wechselstromrechnung, weight: 0.08, prereq: [gleichstrom]}
  - {id: zeiger, title: Zeigerdiagramme und Leistungsberechnung, weight: 0.05, prereq: [wechselstrom]}
  - {id: rc-filter, title: RC-Filter und Bode-Diagramm, weight: 0.07, prereq: [wechselstrom, netzwerk]}
  - {id: schwingkreis, title: Reihen- und Parallelschwingkreise, weight: 0.05, prereq: [wechselstrom]}
  - {id: laplace, title: Laplace-Transformation, weight: 0.08, prereq: []}
  - {id: uebertragung, title: Übertragungsfunktionen und Pol-Nullstellen-Diagramme, weight: 0.1, prereq: [laplace, rc-filter]}
  - {id: sprung, title: Sprungantwort und Zeitverhalten, weight: 0.07, prereq: [uebertragung]}
  - {id: stabil, title: Stabilitätskriterien nach Hurwitz und Nyquist, weight: 0.1, prereq: [uebertragung]}
  - {id: regelkreis, title: Standardregelkreis und Störverhalten, weight: 0.09, prereq: [sprung, stabil]}
  - {id: pid, title: PID-Reglerentwurf und Einstellregeln, weight: 0.08, prereq: [regelkreis]}
  - {id: frequenz, title: Frequenzkennlinienverfahren, weight: 0.06, prereq: [regelkreis, rc-filter]}
  - {id: zustandsraum, title: Zustandsraumdarstellung, weight: 0.05, prereq: [laplace]}
  - {id: digital, title: Zeitdiskrete Regelung und z-Transformation, weight: 0.03, prereq: [pid, zustandsraum]}
focus: [stabil, pid]
skip: [schwingkreis]
"""  # noqa: E501


def _course(tmp_path, text: str):
    (tmp_path / "course.yaml").write_text(text, encoding="utf-8")
    return tmp_path


def test_topic_map_small_course(tmp_path, locale):
    fig = graph.topic_map(_course(tmp_path, SMALL_COURSE))
    assert validate_svg(fig.svg) == []
    f = fig.facts
    assert f["template"] == "graph.topic_map" and f["direction"] == "lr"
    assert f["layers"] == [["gleichstrom"], ["wechselstrom"], ["rc-filter"]]
    assert f["order"] == ["gleichstrom", "wechselstrom", "rc-filter"]
    assert f["edges"] == [["gleichstrom", "wechselstrom"], ["wechselstrom", "rc-filter"]]
    nodes = f["nodes"]
    heights = [nodes[k]["box"][1] for k in ("gleichstrom", "rc-filter", "wechselstrom")]
    assert heights == sorted(heights) and heights[0] < heights[-1]  # height grows with weight
    assert nodes["wechselstrom"]["status"] == "focus"
    xs = [nodes[k]["xy"][0] for k in f["order"]]
    assert xs == sorted(xs)  # left to right by prerequisite depth
    assert "Gleichstromnetzwerke" in fig.alt


def test_topic_map_fifteen_long_german_titles(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYKIT_LOCALE", "de")
    fig = graph.topic_map(_course(tmp_path, BIG_COURSE))
    assert validate_svg(fig.svg) == []
    f = fig.facts
    assert len(f["order"]) == 15 and sorted(f["order"]) == sorted(f["nodes"])
    assert f["node_overlaps"] == 0
    assert f["crossings"] == 0
    assert all(1 <= len(n["lines"]) <= 2 for n in f["nodes"].values())
    assert len(f["nodes"]["uebertragung"]["lines"]) == 2
    level = {k: i for i, layer in enumerate(f["layers"]) for k in layer}
    assert level == f["depth"]
    assert all(level[p] < level[t] for p, t in f["edges"])
    assert f["depth"]["digital"] == 7
    assert f["nodes"]["schwingkreis"]["status"] == "skip"
    assert f["width_in"] <= 6.2 + 1e-6 and f["scale"] >= block.MIN_SCALE


def test_topic_map_rejects_broken_course(tmp_path):
    cyclic = (
        "topics:\n"
        "  - {id: a, title: A, weight: 1, prereq: [b]}\n"
        "  - {id: b, title: B, weight: 1, prereq: [a]}\n"
    )
    with pytest.raises(ValueError, match="cycle"):
        graph.topic_map(_course(tmp_path, cyclic))
    unknown = "topics:\n  - {id: a, title: A, weight: 1, prereq: [x]}\n"
    with pytest.raises(ValueError, match="unknown topics: x"):
        graph.topic_map(_course(tmp_path, unknown))


def test_topic_map_is_a_builtin_figure(tmp_path, monkeypatch):
    from studykit.figures import builtins, runner

    monkeypatch.setitem(runner.BUILTINS, "topic-map", builtins.topic_map)
    monkeypatch.setenv("STUDYKIT_LOCALE", "en")
    course = tmp_path / "get2"
    course.mkdir()
    _course(course, SMALL_COURSE)
    outcomes = runner.build_course(course, only={"topic-map"})
    assert [(o.slug, o.status) for o in outcomes] == [("topic-map", "built")]
    out = course / "_build" / "figures"
    facts = json.loads((out / "topic-map.facts.json").read_text())
    assert facts["template"] == "graph.topic_map" and facts["alt"]
    assert (out / "topic-map.web.svg").is_file()
