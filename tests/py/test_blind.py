"""`studykit blind`: the verifier's view never shows a key, a solution or a hint."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from studykit import blind, cli, content, verify

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "examples" / "sample-course"


@pytest.fixture(scope="module")
def course(tmp_path_factory: pytest.TempPathFactory) -> Path:
    target = tmp_path_factory.mktemp("blind") / "sample-course"
    shutil.copytree(SAMPLE, target, ignore=shutil.ignore_patterns("_build"))
    return target


def view(course: Path, item_id: str) -> str:
    path, text = blind.write(content.CourseTree(course), item_id)
    assert path == course / "_build" / "blind" / f"{item_id}.md"
    assert path.read_text() == text
    return text


def test_exercise_view_has_the_statement_and_the_keys_to_compute(course: Path):
    text = view(course, "ex-rc-tp-grenzfrequenz")
    assert "Gegeben ist ein unbelasteter RC-Tiefpass" in text
    assert "**c)** Wie groß sind Betrag (in dB) und Phase" in text
    assert "- `fg`: Grenzfrequenz $f_\\mathrm{g}$ (a number in Hz)" in text
    assert "answers(tau=…, fg=…, Hdb=…, phi=…)" in text
    assert "![RC-Tiefpass mit R = 2,2 kΩ und C = 47 nF](../figures/rc-tp-2k2.png)" in text
    for leak in (
        "1539",
        "103,4",
        "103.4",
        "-3,01",
        "::: hint",
        "::: solution",
        "Lösung",
        "Blindwiderstand des Kondensators so groß",
        "value:",
        "rtol",
    ):
        assert leak not in text, leak


def test_symbolic_keys_name_their_symbols(course: Path):
    text = view(course, "ex-rc-tp-belastet")
    assert "- `H`: Übertragungsfunktion" in text and "(an expression in s, R, RL, C)" in text
    assert "RL/(R + RL" not in text


def test_exam_task_view_has_no_rubric(course: Path):
    text = view(course, "pk1-t1")
    assert "20 points" in text and "Leerlaufspannung" in text
    assert "rubric" not in text.lower()
    assert "Teilerregel" not in text  # a rubric criterion
    assert "18" not in re.sub(r"pk1-t1", "", text.split("## Results to compute")[1])


def test_mc_view_lists_options_in_source_order_without_marks(course: Path):
    text = view(course, "mc-rc-filter-001")
    options = re.findall(r"^- \*\*([A-F])\*\* (.*)$", text, re.MULTILINE)
    assert options == [
        ("A", "$30{,}3\\,\\mathrm{kHz}$"),
        ("B", "$482\\,\\mathrm{Hz}$"),
        ("C", "$4{,}82\\,\\mathrm{kHz}$"),
        ("D", "$190\\,\\mathrm{kHz}$"),
    ]
    assert "single choice" in text
    for leak in ("[x]", "[ ]", "Faktor $2\\pi$ vergessen", "explanation", "2\\pi f_\\mathrm{g} RC"):
        assert leak not in text, leak


def test_kprim_and_exam_mc(course: Path):
    text = view(course, "mc-rc-filter-009")
    assert "Kprim: judge every statement" in text and '"answer": {"A": true' in text
    tree = content.CourseTree(course)
    exam_mc = next(i for i in verify.items(tree) if i.kind == "mc" and i.exam)
    text = view(course, exam_mc.id)
    assert len(re.findall(r"^- \*\*[A-F]\*\* ", text, re.MULTILINE)) == len(
        exam_mc.question.options
    )
    whys = [o.why for o in exam_mc.question.options if o.why]
    assert whys and not any(w in text for w in whys)


def test_links_keep_their_text(course: Path):
    text = view(course, "ex-st-belastet")
    assert "Der Spannungsteiler aus der Übung Unbelasteter Spannungsteiler" in text
    assert "ex:ex-st-unbelastet" not in text


def test_cli_refuses_unknown_ids(course: Path, capsys):
    assert cli.main(["blind", str(course), "summary-rc-filter"]) == 2
    assert "has no exercise, exam task or MC question" in capsys.readouterr().err
    assert cli.main(["blind", str(course), "mc-rc-filter-002", "--stdout"]) == 0
    assert "## Options (source order)" in capsys.readouterr().out
