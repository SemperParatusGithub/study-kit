"""`studykit blind`: the verifier's view never shows a key, a solution or a hint."""

from __future__ import annotations

import hashlib
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
    # every option is a number: the view asks for an mc_numeric script, not a JSON answer
    assert "Every option is a number" in text and "mc_numeric(" in text
    assert '"answer"' not in text
    for leak in ("[x]", "[ ]", "Faktor $2\\pi$ vergessen", "explanation", "2\\pi f_\\mathrm{g} RC"):
        assert leak not in text, leak


def test_conceptual_mc_asks_for_an_answer(course: Path):
    text = view(course, "mc-rc-filter-006")  # options are sentences
    assert '"answer": ["…"]' in text and "mc_numeric" not in text


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


# --- a question about a course document -----------------------------------------------------

FORMELN = "formelsammlung"
QUESTION = """
:::: {{.mcq #mc-rc-filter-090 type="kprim" difficulty="1"{attrs}}}
{stem}

- [x] Die Grenzfrequenz steht dort.

  Geheimes Warum: Seite 4.

- [ ] Der Tiefpass steht dort.

  Geheimes Warum: nirgends.

- [x] Die Zeitkonstante steht dort.

  Geheimes Warum: Seite 3.

- [ ] Die Bandbreite steht dort.

  Geheimes Warum: nirgends.

Die Erklärung.
::::
"""


def manifest(course: Path, *docs: tuple[str, str, str]) -> None:
    """`sources/manifest.yaml` for (id, title, kind), each with a PDF and its page texts."""
    rows = []
    for doc, title, kind in docs:
        raw = course / "sources" / "raw" / f"{doc}.pdf"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"not really a pdf")
        pages = course / "sources" / "text" / doc
        pages.mkdir(parents=True, exist_ok=True)
        (pages / "index.json").write_text("{}")
        (pages / "p0001.txt").write_text(f"page 1 of {doc}")
        (pages / "p0002.txt").write_text(f"page 2 of {doc}")
        (pages / "p0002.vision.md").write_text(f"scanned page 2 of {doc}")
        rows.append(
            f"  - {{id: {doc}, title: '{title}', file: {doc}.pdf, origin: {doc}.pdf, "
            f"sha256: '{hashlib.sha256(doc.encode()).hexdigest()}', bytes: 16, pages: 2, "
            f"kind: {kind}, kind_from: user, "
            "text_share: 1.0, added: 2026-10-31}"
        )
    (course / "sources" / "manifest.yaml").write_text(
        f"schema: 1\ncourse: {course.name}\ndocuments:\n" + "\n".join(rows) + "\n"
    )


@pytest.fixture
def docs_course(tmp_path: Path) -> Path:
    target = tmp_path / "sample-course"
    shutil.copytree(SAMPLE, target, ignore=shutil.ignore_patterns("_build"))
    manifest(
        target,
        (FORMELN, "Formelsammlung", "other"),
        ("losung-3", "Lösung 3", "solutions"),
        ("klausur-loesung", "Klausur Lösung", "exam-solutions"),
    )
    return target


def add_question(course: Path, stem: str, attrs: str = "") -> str:
    bank = course / "mc" / "rc-filter.md"
    bank.write_text(bank.read_text() + QUESTION.format(attrs=attrs, stem=stem))
    return "mc-rc-filter-090"


def test_a_question_about_a_document_gets_it(docs_course: Path):
    item = add_question(
        docs_course,
        "Was steht in der offiziellen Formelsammlung?",
        f' source="{FORMELN}:4"',
    )
    text = view(docs_course, item)
    assert "## Course document" in text and "read every page (2 in all)" in text
    copies = docs_course / "_build" / "blind" / "docs" / FORMELN
    assert sorted(p.name for p in copies.iterdir()) == [
        "formelsammlung.pdf",
        "p0001.txt",
        "p0002.txt",
        "p0002.vision.md",
    ]  # no index.json
    assert (copies / "p0002.txt").read_text() == f"page 2 of {FORMELN}"
    assert f"docs/{FORMELN}/p0001.txt" in text and "`p0002.txt`" in text
    assert f"docs/{FORMELN}/{FORMELN}.pdf" in text and "vision.md" in text
    # the view hands over the document, not where the answer is, and no key
    for leak in (f"{FORMELN}:4", "Seite", "Geheimes", "[x]", "Die Erklärung"):
        assert leak not in text, leak


def test_an_option_can_name_the_document_and_case_and_inflection_do_not_matter(docs_course: Path):
    item = add_question(docs_course, "Was gilt für die FORMELSAMMLUNGEN?", f' source="{FORMELN}:1"')
    assert "## Course document" in view(docs_course, item)


@pytest.mark.parametrize(
    ("stem", "attrs"),
    [
        # cites it but is not about it: reasoning decides, the verifier stays independent
        ("Welche Aussagen gelten für den RC-Tiefpass?", f' source="{FORMELN}:4"'),
        # names it but cites something else: the author fixes the citation
        ("Was steht in der Formelsammlung?", ' source="unknown-doc:1"'),
        ("Was steht in der Formelsammlung?", ""),
        # a word inside a longer one is not its name
        ("Was steht in der Kurzformelsammlung?", f' source="{FORMELN}:4"'),
        # solutions never reach the verifier, however the question reads
        ("Was steht in Lösung 3?", ' source="losung-3:2"'),
        ("Was steht in der Klausur Lösung?", ' source="klausur-loesung:2"'),
    ],
)
def test_no_other_question_gets_a_document(docs_course: Path, stem: str, attrs: str):
    text = view(docs_course, add_question(docs_course, stem, attrs))
    assert "## Course document" not in text
    assert not (docs_course / "_build" / "blind" / "docs").exists()


def test_a_course_without_a_manifest_has_no_documents(course: Path):
    copy = course.parent / "no-manifest"
    shutil.copytree(course, copy, ignore=shutil.ignore_patterns("_build"), dirs_exist_ok=True)
    item = add_question(copy, "Was steht in der Formelsammlung?", f' source="{FORMELN}:4"')
    assert "## Course document" not in view(copy, item)


def test_a_document_is_copied_once_and_refreshed_when_it_changes(docs_course: Path):
    item = add_question(docs_course, "Was steht in der Formelsammlung?", f' source="{FORMELN}:4"')
    view(docs_course, item)
    copy = docs_course / "_build" / "blind" / "docs" / FORMELN / "p0001.txt"
    before = copy.stat().st_mtime_ns
    view(docs_course, item)
    assert copy.stat().st_mtime_ns == before
    source = docs_course / "sources" / "text" / FORMELN / "p0001.txt"
    source.write_text("a new first page")
    view(docs_course, item)
    assert copy.read_text() == "a new first page"


def test_cli_refuses_unknown_ids(course: Path, capsys):
    assert cli.main(["blind", str(course), "summary-rc-filter"]) == 2
    assert "has no exercise, exam task or MC question" in capsys.readouterr().err
    assert cli.main(["blind", str(course), "mc-rc-filter-002", "--stdout"]) == 0
    assert "## Options (source order)" in capsys.readouterr().out
