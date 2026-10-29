"""`studykit verify`: check runner, comparison with the key, ledger and dispute protocol.

Every test works on a copy of the sample course and writes the checks a blind verifier
would write, computed from the statement (never copied from the key).
"""

from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path

import pytest

from studykit import cli, content, model, verify

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "examples" / "sample-course"

GRENZ = "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md"
# R = 2.2 kΩ, C = 47 nF; computed from the statement, never from the key
CHECK_GRENZ = """\
from math import atan, degrees, log10, pi, sqrt

from studykit.check import answers

R, C = 2.2e3, 47e-9
tau = R * C
answers(
    tau=tau * 1e6,
    fg=1 / (2 * pi * tau),
    Hdb=20 * log10(1 / sqrt(2)),
    phi=-degrees(atan(1)),
    method="tau = RC, fg = 1/(2 pi tau)",
)
"""
# mc-rc-filter-001: R = 3.3 kΩ, C = 10 nF; options A 30,3 kHz, B 482 Hz, C 4,82 kHz, D 190 kHz
CHECK_MC001 = """\
from math import pi

from studykit.check import mc_numeric

R, C = 3.3e3, 10e-9
mc_numeric(
    correct=1 / (2 * pi * R * C),
    options={"A": 30.3e3, "B": 482.0, "C": 4.82e3, "D": 190e3},
    mistakes={"A": 1 / (R * C), "B": 1 / (2 * pi * R * 100e-9), "D": 2 * pi / (R * C)},
)
"""


@pytest.fixture
def course(tmp_path: Path) -> Path:
    target = tmp_path / "sample-course"
    shutil.copytree(SAMPLE, target, ignore=shutil.ignore_patterns("_build"))
    return target


def tree(course: Path) -> content.CourseTree:
    return content.CourseTree(course)


def write_check(course: Path, name: str, text: str) -> Path:
    path = course / "checks" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text) if name.endswith(".py") else text)
    return path


def edit(course: Path, rel: str, old: str, new: str) -> None:
    path = course / rel
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new, 1))


def ledger(course: Path, item_id: str) -> dict:
    return json.loads((course / "state" / "verify" / f"{item_id}.json").read_text())


def run_one(course: Path, item_id: str, **kw) -> dict:
    result = verify.run(tree(course), item_id, **kw)
    (row,) = result["items"]
    return row


# --- the happy path -------------------------------------------------------------------------


def test_correct_exercise_becomes_verified(course: Path):
    write_check(course, "ex-rc-tp-grenzfrequenz.py", CHECK_GRENZ)
    row = run_one(course, "ex-rc-tp-grenzfrequenz")
    assert (row["outcome"], row["status"]) == ("pass", "verified")
    entry = model.VerifyEntry.model_validate(ledger(course, "ex-rc-tp-grenzfrequenz"))
    item = verify.find(tree(course), "ex-rc-tp-grenzfrequenz")
    assert entry.content_sha256 == item.content_sha256
    assert entry.check == "checks/ex-rc-tp-grenzfrequenz.py"
    assert entry.check_sha256 == verify.sha256_file(course / entry.check)
    assert (entry.method, entry.rounds, entry.disputes) == ("script", 0, [])
    assert [r.key for r in entry.results] == ["tau", "fg", "Hdb", "phi"]
    assert all(r.ok for r in entry.results)
    fg = entry.results[1]
    assert (fg.expected, fg.unit) == (1539.2, "Hz")
    assert fg.computed == pytest.approx(1539.216, rel=1e-6)
    assert entry.verified_at == entry.checked_at
    # the ledger file is what schemas/verify.schema.json describes
    assert ledger(course, "ex-rc-tp-grenzfrequenz")["schema"] == 1


def test_mc_checks_by_letters_numeric_and_kprim(course: Path):
    write_check(course, "mc-rc-filter-001.py", CHECK_MC001)
    write_check(course, "mc-rc-filter-002.json", '{"answer": ["D"], "reason": "1/sqrt(2)"}')
    # multi: options B and D are true (source order)
    write_check(
        course,
        "mc-rc-filter-007.py",
        'from studykit.check import mc_answer\nmc_answer(["B", "D"], reason="first order")\n',
    )
    # Kprim as a mapping and as the list of true statements
    write_check(
        course,
        "mc-rc-filter-009.json",
        '{"answer": {"A": false, "B": true, "C": true, "D": false}, "confidence": "high"}',
    )
    result = verify.run(tree(course), "rc-filter")
    rows = {r["id"]: r for r in result["items"]}
    for item_id in ("mc-rc-filter-001", "mc-rc-filter-002", "mc-rc-filter-007", "mc-rc-filter-009"):
        assert rows[item_id]["status"] == "verified", rows[item_id]
    assert ledger(course, "mc-rc-filter-002")["method"] == "blind"
    assert rows["mc-rc-filter-003"]["outcome"] == "no-check"
    # every option's text was read as its stated value; each mistake reproduced
    keys = {r["key"]: r["ok"] for r in ledger(course, "mc-rc-filter-001")["results"]}
    assert keys == {"key": True, "mistake-A": True, "mistake-B": True, "mistake-D": True}
    write_check(course, "mc-rc-filter-009.json", '{"answer": ["B", "C"]}')
    assert run_one(course, "mc-rc-filter-009")["status"] == "verified"


def test_units_convert_and_symbolic_answers_compare(course: Path):
    write_check(
        course,
        "ex-rc-tp-grenzfrequenz.py",
        """\
        from math import pi
        from studykit.check import answers, quantity
        R, C = 2.2e3, 47e-9
        answers(tau=quantity(R * C, "s"), fg=quantity(1 / (2 * pi * R * C) / 1e3, "kHz"),
                Hdb=-3.0103, phi=quantity(-pi / 4, "rad"))
        """,
    )
    assert run_one(course, "ex-rc-tp-grenzfrequenz")["status"] == "verified"
    # H = RL / (R + RL + s R RL C), written another way; H0 = 20 lg(1/2); fg = 2/(2 pi R C)
    write_check(
        course,
        "ex-rc-tp-belastet.py",
        """\
        import sympy as sp
        from math import log10, pi
        from studykit.check import answers
        s, R, RL, C = sp.symbols("s R RL C")
        Zp = 1 / (1 / RL + s * C)
        H = sp.simplify(Zp / (R + Zp))
        answers(H=H, H0db=20 * log10(0.5), fg=(1e4 + 1e4) / (2 * pi * 1e4 * 1e4 * 10e-9))
        """,
    )
    row = run_one(course, "ex-rc-tp-belastet")
    assert row["status"] == "verified", row
    write_check(
        course,
        "ex-rc-tp-belastet.json",
        '{"answers": {"H": "1/(1 + s*R*C)", "H0db": -6.02, "fg": 3183.1}}',
    )
    (course / "checks" / "ex-rc-tp-belastet.py").unlink()
    row = run_one(course, "ex-rc-tp-belastet")
    assert row["status"] == "disputed"
    assert any("'H'" in p for p in row["problems"])


# --- seeded errors are caught ---------------------------------------------------------------


def test_seeded_wrong_number_is_disputed(course: Path, capsys):
    # the classic slip: the key says 1/(2 pi R C) with C = 45 nF instead of 47 nF
    edit(course, GRENZ, "value: 1539.2, unit: Hz", "value: 1608.0, unit: Hz")
    write_check(course, "ex-rc-tp-grenzfrequenz.py", CHECK_GRENZ)
    assert cli.main(["verify", str(course), "ex-rc-tp-grenzfrequenz"]) == 1
    out = capsys.readouterr().out
    assert "disputed" in out and "'fg': the check computes 1539.22 Hz" in out
    assert "1608" not in out  # the text output hides the key from the verifier
    entry = ledger(course, "ex-rc-tp-grenzfrequenz")
    assert entry["status"] == "disputed" and entry["rounds"] == 0
    (dispute,) = entry["disputes"]
    assert dispute["source"] == "verify" and not dispute["confirmed"]
    fg = next(r for r in dispute["results"] if r["key"] == "fg")
    assert (fg["expected"], fg["ok"]) == (1608.0, False)
    assert fg["computed"] == pytest.approx(1539.216, rel=1e-6)
    assert "1608" in dispute["problems"][0]  # the author gets the key and the numbers
    assert cli.main(["verify", str(course), "ex-rc-tp-grenzfrequenz", "--show-key"]) == 1
    assert "| key: 1608 Hz" in capsys.readouterr().out


def test_seeded_wrong_mc_key_is_caught(course: Path):
    # move the [x] of mc-rc-filter-001 from C (4,82 kHz) to A (30,3 kHz, the forgotten 2 pi)
    edit(course, "mc/rc-filter.md", "- [ ] $30{,}3\\,", "- [x] $30{,}3\\,")
    edit(course, "mc/rc-filter.md", "- [x] $4{,}82\\,", "- [ ] $4{,}82\\,")
    write_check(course, "mc-rc-filter-001.py", CHECK_MC001)
    row = run_one(course, "mc-rc-filter-001", show_key=True)
    assert row["status"] == "disputed"
    assert any("matches option(s) C" in p and "key: A" in p for p in row["problems"])
    # a blind answer to a conceptual question that does not match the key
    write_check(course, "mc-rc-filter-002.json", '{"answer": ["A"], "reason": "-6 dB"}')
    row = run_one(course, "mc-rc-filter-002", show_key=True)
    assert row["status"] == "disputed"
    assert row["problems"] == ["the verifier's answer A does not match the key | key: D"]


@pytest.mark.parametrize(
    "check",
    [
        ("mc-rc-filter-001.json", '{"answer": ["C"], "reason": "1/(2 pi RC)"}'),
        ("mc-rc-filter-001.py", "from studykit.check import mc_answer\nmc_answer(['C'])\n"),
    ],
)
def test_a_numeric_question_needs_mc_numeric(course: Path, check: tuple[str, str]):
    # a letter alone would skip the distractor, separation and option-value checks
    write_check(course, *check)
    row = run_one(course, "mc-rc-filter-001")
    assert (row["outcome"], row["status"]) == ("error", "unverified")
    assert any("mc_numeric(...)" in p for p in row["problems"]), row["problems"]


def test_mc_numeric_catches_bad_distractors_and_misread_options(course: Path):
    write_check(
        course,
        "mc-rc-filter-001.py",
        CHECK_MC001.replace('"B": 1 / (2 * pi * R * 100e-9)', '"B": 1 / (2 * pi * R * 1e-6)'),
    )
    row = run_one(course, "mc-rc-filter-001")
    assert row["status"] == "disputed"
    assert any("distractor B" in p and "why is wrong" in p for p in row["problems"])
    # a distractor too close to the correct value
    write_check(
        course,
        "mc-rc-filter-001.py",
        CHECK_MC001.replace("\n)\n", "\n    min_separation=10.0,\n)\n"),
    )
    row = run_one(course, "mc-rc-filter-001")
    assert any("lies within" in p for p in row["problems"])
    # the check states a value the option text does not say: the check is wrong
    write_check(course, "mc-rc-filter-001.py", CHECK_MC001.replace('"B": 482.0', '"B": 4820.0'))
    row = run_one(course, "mc-rc-filter-001")
    assert (row["outcome"], row["status"]) == ("error", "unverified")
    assert any("option B reads 482" in p for p in row["problems"])


def test_an_ambiguous_question_is_disputed(course: Path):
    write_check(
        course,
        "mc-rc-filter-002.json",
        '{"answer": ["D"], "ambiguous": true, "reason": "B is right too for f -> 0"}',
    )
    row = run_one(course, "mc-rc-filter-002")
    assert row["status"] == "disputed"
    assert row["problems"] == [
        "the verifier finds the question ambiguous: B is right too for f -> 0"
    ]


# --- content hash, rounds and quarantine ----------------------------------------------------------


def test_editing_the_item_makes_the_ledger_stale(course: Path):
    write_check(course, "ex-rc-tp-grenzfrequenz.py", CHECK_GRENZ)
    write_check(course, "mc-rc-filter-002.json", '{"answer": ["D"]}')
    verify.run(tree(course), "ex-rc-tp-grenzfrequenz")
    verify.run(tree(course), "mc-rc-filter-002")
    edit(course, GRENZ, "**c)** Wie groß", "**c)** Wie groß genau")
    # an edit to another question of the same bank leaves mc-rc-filter-002 fresh
    edit(
        course,
        "mc/rc-filter.md",
        "Wie groß ist\nseine Grenzfrequenz",
        "Wie groß ist\ndie Grenzfrequenz",
    )
    rows = {r["id"]: r for r in verify.status(tree(course))["items"]}
    assert rows["ex-rc-tp-grenzfrequenz"]["outcome"] == "stale"
    assert rows["ex-rc-tp-grenzfrequenz"]["stale"] is True
    assert rows["mc-rc-filter-002"]["outcome"] == "verified"
    edit(
        course,
        "mc/rc-filter.md",
        "Übertragungsfunktion eines RC-Tiefpasses bei",
        "Übertragungsfunktion eines RC-Tiefpasses genau bei",
    )
    assert verify.status(tree(course), "mc-rc-filter-002")["items"][0]["stale"] is True
    row = run_one(course, "ex-rc-tp-grenzfrequenz")
    assert (row["status"], row["stale"]) == ("verified", False)


def test_two_failed_fix_rounds_quarantine(course: Path):
    write_check(course, "ex-rc-tp-grenzfrequenz.py", CHECK_GRENZ)
    edit(course, GRENZ, "value: 1539.2, unit: Hz", "value: 1608.0, unit: Hz")
    assert run_one(course, "ex-rc-tp-grenzfrequenz")["status"] == "disputed"
    # running again on the same version is not a new round
    assert run_one(course, "ex-rc-tp-grenzfrequenz")["rounds"] == 0
    edit(course, GRENZ, "value: 1608.0, unit: Hz", "value: 1590.0, unit: Hz")  # fix round 1
    row = run_one(course, "ex-rc-tp-grenzfrequenz")
    assert (row["status"], row["rounds"]) == ("disputed", 1)
    edit(course, GRENZ, "value: 1590.0, unit: Hz", "value: 1500.0, unit: Hz")  # fix round 2
    row = run_one(course, "ex-rc-tp-grenzfrequenz")
    assert (row["status"], row["rounds"]) == ("quarantined", 2)
    entry = ledger(course, "ex-rc-tp-grenzfrequenz")
    assert [d["round"] for d in entry["disputes"]] == [0, 1, 2]
    assert entry["note"] == "still disputed after 2 author fix round(s)"
    assert verify.quarantined_ids(course) == ["ex-rc-tp-grenzfrequenz"]
    summary = verify.summary(tree(course))
    assert summary["counts"]["quarantined"] == 1
    assert summary["quarantined"][0]["id"] == "ex-rc-tp-grenzfrequenz"
    # a rewrite that passes brings it back, and the ledger remembers it was fixed
    edit(course, GRENZ, "value: 1500.0, unit: Hz", "value: 1539.2, unit: Hz")
    row = run_one(course, "ex-rc-tp-grenzfrequenz")
    assert row["status"] == "verified"
    assert verify.quarantined_ids(course) == []
    assert verify.summary(tree(course))["counts"]["fixed"] == 1


def test_second_method_confirms_or_contradicts(course: Path, capsys):
    write_check(course, "ex-rc-tp-grenzfrequenz.py", CHECK_GRENZ)
    edit(course, GRENZ, "value: 1539.2, unit: Hz", "value: 1608.0, unit: Hz")
    run_one(course, "ex-rc-tp-grenzfrequenz")
    # second method: the cutoff from |H(j w)| = 1/sqrt(2), solved numerically
    alt = write_check(
        course,
        "ex-rc-tp-grenzfrequenz.numeric.py",
        """\
        from math import pi
        from scipy.optimize import brentq
        from studykit.check import answers
        R, C = 2.2e3, 47e-9
        H = lambda f: abs(1 / (1 + 2j * pi * f * R * C))
        fg = brentq(lambda f: H(f) - 2 ** -0.5, 1.0, 1e6)
        answers(tau=R * C * 1e6, fg=fg, Hdb=-3.0103, phi=-45.0)
        """,
    )
    args = ["verify", str(course), "ex-rc-tp-grenzfrequenz", "--confirm", str(alt)]
    assert cli.main([*args, "--method", "brentq on |H|", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert (out["confirmation"], out["status"]) == ("mismatch", "disputed")
    entry = ledger(course, "ex-rc-tp-grenzfrequenz")
    assert entry["disputes"][-1]["confirmed"] is True
    assert entry["confirmations"][0]["method"] == "brentq on |H|"
    # /verify reads whether a dispute is confirmed from the status rows
    row = verify.status(tree(course), "ex-rc-tp-grenzfrequenz")["items"][0]
    assert row["confirmed"] is True
    assert row["confirmations"] == [
        {
            "check": "checks/ex-rc-tp-grenzfrequenz.numeric.py",
            "method": "brentq on |H|",
            "result": "mismatch",
        }
    ]
    # a second method that sides with the key: the first check is suspect
    alt.write_text(
        "from studykit.check import answers\nanswers(tau=103.4, fg=1608.0, Hdb=-3.01, phi=-45)\n"
    )
    result = verify.confirm(tree(course), "ex-rc-tp-grenzfrequenz", alt)
    assert (result["confirmation"], result["status"]) == ("pass", "unverified")
    assert "the two methods disagree" in ledger(course, "ex-rc-tp-grenzfrequenz")["problems"][-1]
    # the second method must be a sibling file of the first, not the first itself
    with pytest.raises(verify.VerifyError):
        verify.confirm(
            tree(course), "ex-rc-tp-grenzfrequenz", course / "checks" / "ex-rc-tp-grenzfrequenz.py"
        )
    with pytest.raises(verify.VerifyError):
        verify.confirm(tree(course), "ex-rc-tp-grenzfrequenz", course / "checks" / "other.py")


def test_confirm_text_never_shows_the_key(course: Path, capsys):
    # the verifier runs --confirm without --json; its output must not name the key
    write_check(course, "ex-rc-tp-grenzfrequenz.py", CHECK_GRENZ)
    edit(course, GRENZ, "value: 1539.2, unit: Hz", "value: 1608.0, unit: Hz")
    run_one(course, "ex-rc-tp-grenzfrequenz")
    alt = write_check(
        course,
        "ex-rc-tp-grenzfrequenz.sympy.py",
        """\
        import sympy as sp
        from studykit.check import answers
        R, C = sp.Integer(2200), sp.Rational(47, 10**9)
        answers(tau=sp.N(R * C * 10**6), fg=sp.N(1 / (2 * sp.pi * R * C)), Hdb=-3.0103, phi=-45)
        """,
    )
    capsys.readouterr()
    args = ["verify", str(course), "ex-rc-tp-grenzfrequenz", "--confirm", str(alt)]
    assert cli.main(args) == 0
    out = capsys.readouterr().out
    assert "ex-rc-tp-grenzfrequenz" in out and "disputed" in out
    assert "second method: mismatch" in out
    assert "1608" not in out and "key:" not in out
    assert cli.main([*args, "--show-key"]) == 0
    assert "1608" in capsys.readouterr().out


def test_manual_dispute_quarantine_and_clear(course: Path, capsys):
    c = str(course)
    assert cli.main(["verify", c, "ex-rc-tp-bode", "--dispute"]) == 2  # needs --note
    capsys.readouterr()
    args = ["verify", c, "ex-rc-tp-bode", "--dispute", "--note", "slope is wrong"]
    assert cli.main([*args, "--computed", "slope=-20", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "disputed"
    entry = ledger(course, "ex-rc-tp-bode")
    assert entry["method"] == "manual"
    assert entry["disputes"][0]["results"][0] == {"key": "slope", "computed": -20.0, "ok": False}
    assert cli.main(["verify", c, "mc-rc-filter-003", "--quarantine", "--note", "unclear"]) == 0
    assert verify.quarantined_ids(course) == ["mc-rc-filter-003"]
    assert cli.main(["verify", c, "all", "--quarantine", "--note", "x"]) == 2
    capsys.readouterr()
    assert cli.main(["verify", c, "--status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["counts"]["disputed"] == 1 and status["counts"]["quarantined"] == 1
    # orphans: a ledger whose item is gone
    (course / "state" / "verify" / "ex-gone.json").write_text("{}")
    assert verify.clear(tree(course), "orphans")["removed"] == ["ex-gone"]
    assert verify.clear(tree(course), "rc-filter")["removed"] == [
        "ex-rc-tp-bode",
        "mc-rc-filter-003",
    ]
    assert verify.ledger_ids(course) == []


def test_check_problems_leave_the_item_unverified(course: Path):
    cases = {
        "raise SystemExit(3)": "exited with 3",
        "print('hello')": "printed no JSON object",
        "import time; time.sleep(5)": "did not finish within 0.5 s",
        "from studykit.check import answers\nanswers(tau=103.4)": "computes no value for 'fg'",
        "from studykit.check import mc_answer\nmc_answer(['A'])": "needs answers(...) or",
        # agreeing is no check of an item with keys: every key needs a computed value
        "from studykit.check import review\nreview(True, 'looks fine')": "has answer keys",
    }
    for code, message in cases.items():
        write_check(course, "ex-rc-tp-grenzfrequenz.py", code + "\n")
        row = run_one(course, "ex-rc-tp-grenzfrequenz", timeout=0.5)
        assert (row["outcome"], row["status"]) == ("error", "unverified"), code
        assert any(message in p for p in row["problems"]), (code, row["problems"])
    write_check(course, "mc-rc-filter-002.json", '{"answer": ["G"]}')
    assert "unknown option(s) G" in run_one(course, "mc-rc-filter-002")["problems"][0]
    write_check(course, "mc-rc-filter-002.json", "[1, 2]")
    assert "must hold a JSON object" in run_one(course, "mc-rc-filter-002")["problems"][0]


def test_targets_and_cli_usage(course: Path, capsys):
    t = tree(course)
    every = verify.select(t, "all")
    assert {i.kind for i in every} == {"exercise", "exam-task", "mc"}
    assert len(every) == 16 + 4 + len([i for i in every if i.kind == "mc"])
    assert {i.topic for i in verify.select(t, "wechselstrom")} == {"wechselstrom"}
    exam = verify.select(t, "probeklausur-1")
    assert {i.exam for i in exam} == {"probeklausur-1"} and len(exam) > 4
    with pytest.raises(verify.VerifyError):
        verify.select(t, "nope")
    assert cli.main(["verify", str(course), "nope"]) == 2
    assert "is not an exercise" in capsys.readouterr().err
    # an exercise and an MC question in a bank and in an exam: one hash each
    hashes = {i.id: i.content_sha256 for i in every}
    assert len(set(hashes.values())) == len(hashes)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("$4{,}82\\,\\mathrm{kHz}$", 4820.0),
        ("$482\\,\\mathrm{Hz}$", 482.0),
        ("$0{,}314\\,\\mathrm{m\\Omega}$", 0.314e-3),
        ("$3{,}18\\,\\mathrm{k\\Omega}$", 3180.0),
        ("$-45^\\circ$", -45.0),
        ("$+20\\,\\mathrm{dB}$", 20.0),
        ("$10\\,\\mathrm{\\mu F}$", 10e-6),
        ("$2{,}2 \\cdot 10^{3}\\,\\Omega$", 2200.0),
        ("$63\\,\\%$", 0.63),
        ("$-425{,}5\\,\\mathrm{V/s}$", -425.5),
        ("$2\\,\\mathrm{V/\\mu s}$", 2e6),
        ("$0{,}5$", 0.5),
        ("$1/\\sqrt{2}$", None),
        ("Der Strom eilt vor", None),
    ],
)
def test_option_values(text: str, value: float | None):
    got = verify.option_value(text)
    assert got == (pytest.approx(value) if value is not None else None)


def test_units():
    assert verify.convert(1.5, "kHz", "Hz") == pytest.approx(1500)
    assert verify.convert(2.0, "kΩ", "Ω") == pytest.approx(2000)
    assert verify.convert(100, "rad/s", "1/s") == 100
    assert verify.convert(-45, "°", "rad") == pytest.approx(-0.7853981634)
    assert verify.convert(103.4, "µs", "s") == pytest.approx(103.4e-6)
    assert verify.convert(0.5, "V/ms", "V/s") == pytest.approx(500)
    assert verify.convert(3, "mA/V", "A/V") == pytest.approx(3e-3)
    with pytest.raises(ValueError):
        verify.convert(1, "V", "A")
