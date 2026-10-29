"""`studykit pdf`: every document of the sample course, built once for this module.

The course is copied into the repository's .cache (Typst reads only files below --root)
and built with the real toolchain, so these tests look at the PDFs themselves: page counts
against pypdfium2, the MC answer key and option order against validate.pdf_order and the
site's shuffle.ts, the exam's footer and points table, solutions present or absent, and a
failed build keeping the previous PDF.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from conftest import MINI
from studykit import cli, content, pdf, tools, validate

ROOT = tools.repo_root()
SAMPLE = ROOT / "examples" / "sample-course"
SHUFFLE_TS = ROOT / "site" / "src" / "lib" / "shuffle.ts"
EXPECTED = [
    "overview",
    "summary",
    "exercises",
    "exercises-blank",
    "mc",
    "probeklausur-1",
    "probeklausur-1-solutions",
    "cheatsheet",
    "plan",
]


@pytest.fixture(scope="module")
def built() -> Iterator[tuple[Path, dict]]:
    base = ROOT / ".cache"
    base.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="test-pdf-", dir=base))
    course = tmp / "sample-course"
    shutil.copytree(SAMPLE, course, ignore=shutil.ignore_patterns("_build"))
    figures = SAMPLE / "_build" / "figures"
    if figures.is_dir():  # reuse built figures; the runner's cache decides what is fresh
        shutil.copytree(figures, course / "_build" / "figures")
    result = pdf.build(course)
    yield course, result
    shutil.rmtree(tmp, ignore_errors=True)


def text_of(path: Path) -> list[str]:
    """Page texts, normalised: math letters as ASCII, no hyphenation marks, one space."""
    out = []
    for page in pdf.pdf_text(path):
        page = unicodedata.normalize("NFKC", page).replace("￾", "").replace("\x02", "")
        out.append(" ".join(page.split()))
    return out


def words(markdown: str) -> list[str]:
    """Runs of plain words in Markdown (math, emphasis and markers left out)."""
    plain = re.sub(r"\$\$.*?\$\$", " | ", markdown, flags=re.S)
    plain = re.sub(r"\$[^$]*\$", " | ", plain)
    plain = re.sub(r"\*\*[a-z]\)\*\*", " | ", plain)
    plain = plain.replace("*", "").replace("\n", " ")
    runs = re.findall(r"(?:[A-Za-zÄÖÜäöüß]+ ){3,}[A-Za-zÄÖÜäöüß]+", plain)
    return sorted(runs, key=len, reverse=True)


# --- the build ---------------------------------------------------------------------------


def test_every_sample_document_builds_without_warnings(built):
    course, result = built
    rows = {r["id"]: r for r in result["docs"]}
    assert list(rows) == EXPECTED
    for row in rows.values():
        assert row["status"] == "built", (row["id"], row["errors"])
        assert row["errors"] == []
        log = json.loads((course / "_build" / "logs" / f"{row['id']}.json").read_text())
        assert [e for e in log if e.get("verbosity") == "WARNING"] == []
    assert result["notes"] == []


def test_manifest_follows_the_contract_and_counts_pages_with_pypdfium2(built):
    course, _ = built
    manifest = json.loads((course / "_build" / "pdf" / "manifest.json").read_text())
    assert manifest["schema"] == "studykit-pdf/1"
    assert manifest["course"] == "sample-course"
    assert [d["id"] for d in manifest["docs"]] == EXPECTED
    for doc in manifest["docs"]:
        keys = {"id", "kind", "file", "title", "pages", "bytes"}
        if doc["kind"] in ("exam", "exam-solutions"):
            keys.add("exam")
            assert doc["exam"] == "probeklausur-1"
        if doc["kind"] == "cheatsheet":
            keys |= {"max_pages", "density"}
            assert (doc["max_pages"], doc["density"]) == (2, 0)
        assert set(doc) == keys
        path = course / "_build" / "pdf" / doc["file"]
        assert doc["file"] == f"{doc['id']}.pdf"
        assert doc["pages"] == pdf.page_count(path) > 0
        assert doc["bytes"] == path.stat().st_size
    kinds = {d["id"]: d["kind"] for d in manifest["docs"]}
    assert kinds["probeklausur-1"] == "exam"
    assert kinds["probeklausur-1-solutions"] == "exam-solutions"


def test_a_second_run_finds_every_document_up_to_date(built):
    course, _ = built
    again = pdf.build(course, figures=False)
    assert {r["status"] for r in again["docs"]} == {"cached"}


def test_the_assembled_markdown_escapes_generated_text():
    assert pdf.esc("1. Woche #2 *a* [b](c) $x$ <i> & ü") == (
        r"1\. Woche \#2 \*a\* \[b\]\(c\) \$x\$ \<i\> \& ü"
    )
    assert pdf.label_md("Phase $\\varphi$ bei $f_\\mathrm{g}$ in [°]") == (
        r"Phase $\varphi$ bei $f_\mathrm{g}$ in \[°\]"
    )
    assert pdf.label_md("$|\\underline{H}|$ in dB") == r"$|\underline{H}|$ in dB"


# --- multiple choice ---------------------------------------------------------------------


def bank_questions(course: Path) -> list[tuple[content.Question, str]]:
    """Practice questions in mc.pdf order (topics in course order), each with its bank."""
    tree = content.CourseTree(course)
    order = {t: i for i, t in enumerate(tree.topics)}
    banks = sorted(tree.of_kind("mc"), key=lambda d: order.get(d.parts["topic"], 99))
    return [(q, d.rel) for d in banks for q in d.body.questions]


def display_order(q: content.Question) -> list[int]:
    return validate.pdf_order(q.id, len(q.options), q.block.attrs.get("pin-last") == "true")


def shown_keys(q: content.Question) -> list[str]:
    order = display_order(q)
    return [pdf_key(k) for k, src in enumerate(order) if q.options[src].correct]


def pdf_key(position: int) -> str:
    return validate.PDF_KEYS[position]


def key_entries(text: str) -> dict[str, str]:
    """The detailed answer-key entries of mc.pdf: question id -> its text."""
    key = text[text.index("Lösungsschlüssel") :]
    marks = list(re.finditer(r"Frage (\d+) (mc-[a-z0-9-]+)", key))
    return {
        m[2]: key[m.end() : marks[i + 1].start() if i + 1 < len(marks) else len(key)]
        for i, m in enumerate(marks)
    }


def test_mc_pdf_has_an_answer_key_for_every_question(built):
    course, _ = built
    text = " ".join(text_of(course / "_build" / "pdf" / "mc.pdf"))
    questions = bank_questions(course)
    assert len(questions) == 30
    table = text[text.index("Lösungsschlüssel") :]
    entries = key_entries(text)
    for number, (q, _) in enumerate(questions, start=1):
        keys = ", ".join(shown_keys(q))
        answer = f"richtig: {keys}" if q.type == "kprim" else keys
        assert f" {number} {answer} {q.id} " in f" {table} ", (number, q.id, answer)
        assert f"Frage {number} {q.id}" in text
        entry = entries[q.id]
        if q.type == "kprim":
            wrong = [pdf_key(k) for k in range(len(q.options)) if pdf_key(k) not in keys]
            assert f"Lösung: richtig: {keys} · falsch: {', '.join(wrong)}" in entry
        else:
            assert f"Lösung: {keys} " in entry
        assert "Erklärung:" in entry


def test_mc_pdf_order_matches_validate_and_the_site(built):
    """Every option is shown under the letter validate.pdf_order and shuffle.ts give it."""
    course, _ = built
    questions = bank_questions(course)
    script = (
        f"import {{ optionOrder }} from {json.dumps(SHUFFLE_TS.as_uri())};"
        "let s = ''; process.stdin.on('data', (d) => (s += d));"
        "process.stdin.on('end', () => console.log(JSON.stringify("
        "JSON.parse(s).map(([id, n, p]) => optionOrder(id, n, p)))));"
    )
    args = [[q.id, len(q.options), q.block.attrs.get("pin-last") == "true"] for q, _ in questions]
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=json.dumps(args),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    site = json.loads(proc.stdout)
    entries = key_entries(" ".join(text_of(course / "_build" / "pdf" / "mc.pdf")))
    identified = total = 0
    for (q, _), site_order in zip(questions, site, strict=True):
        order = display_order(q)
        assert site_order == order, q.id
        # the key entry repeats each option with its why: "(B) <mark> 9 V — Das ist U1 über …"
        parts = dict(re.findall(r"\(([A-F])\) (.*?)(?= \([A-F]\) | Erklärung:|$)", entries[q.id]))
        assert sorted(parts) == [pdf_key(k) for k in range(len(q.options))], q.id
        # the option text sits between the mark and the dash: "(B) <mark> 9 V — …"
        heads = {
            k: re.sub(r"\s", "", MARK.sub("", seg.split(" — ")[0])) for k, seg in parts.items()
        }
        for src, option in enumerate(q.options):
            total += 1
            runs = words(option.text + "\n" + option.why)
            letters = [k for k, seg in parts.items() if runs and all(r in seg for r in runs)]
            if len(letters) != 1:  # all math, or worded like another option: try the value
                letters = [k for k, head in heads.items() if head == tex_plain(option.text)]
            if len(letters) != 1:
                continue  # nothing to tell it by
            assert letters == [pdf_key(order.index(src))], (q.id, src, runs, parts)
            identified += 1
    assert identified >= 0.9 * total, (identified, total)


# the mark before an option in the key: check, cross, or the Kprim verdict
MARK = re.compile("^(?:\\u2713|\\u00d7|richtig|falsch) ")

TEX_CHARS = {
    "\\Omega": "Ω",
    "\\omega": "ω",
    "\\tau": "τ",
    "\\pi": "π",
    "\\mu": "μ",
    "\\varphi": "φ",
    "\\infty": "∞",
    "\\to": "→",
    "\\cdot": "⋅",
    "\\circ": "∘",
    "\\%": "%",
    "\\sqrt": "√",
    "-": "\u2212",
}


def tex_plain(text: str) -> str:
    """Option text as the PDF's text layer has it, without spaces: math read as plain text
    (`$1{,}59\\,\\mathrm{kHz}$` → 1,59kHz), so a value option can be recognised."""

    def math(m: re.Match[str]) -> str:
        t = m[1].replace("{,}", ",")
        t = re.sub(r"\\(?:mathrm|underline|text)\{([^{}]*)\}", r"\1", t)
        for tex, char in TEX_CHARS.items():
            t = t.replace(tex, char)
        return re.sub(r"\\[,;: ]|[{}_^]", "", t)

    plain = re.sub(r"\$([^$]*)\$", math, text)
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", plain))


# --- exams ------------------------------------------------------------------------------


def test_exam_pdf_has_page_x_of_y_and_the_points_table(built):
    course, _ = built
    path = course / "_build" / "pdf" / "probeklausur-1.pdf"
    pages = text_of(path)
    n = len(pages)
    for i, page in enumerate(pages, start=1):
        assert page.endswith(f"Seite {i} von {n}"), (i, page[-60:])
    exam = yaml.safe_load((course / "exams" / "probeklausur-1" / "exam.yaml").read_text())
    cover = pages[0]
    table = cover[cover.index("Aufgabe Thema Punkte erreicht") :]
    rows = re.findall(r"(?:^| )(\d|MC) (.+?) (\d+(?:,\d+)?)(?= \d |  ?MC | Summe)", table)
    points = [float(p.replace(",", ".")) for _, _, p in rows]
    assert [r[0] for r in rows] == ["1", "2", "3", "4", "MC"]
    total = float(re.search(r"Summe (\d+(?:,\d+)?)", table)[1].replace(",", "."))
    assert sum(points) == total == exam["points"]
    tasks = [
        yaml.safe_load((course / "exams" / "probeklausur-1" / t).read_text().split("---")[1])
        for t in exam["tasks"]
    ]
    assert points[:-1] == [t["points"] for t in tasks]
    assert "Lösung" not in " ".join(pages[1:]) and "Bewertung" not in " ".join(pages)


def test_exam_solutions_pdf_has_every_rubric(built):
    course, _ = built
    text = " ".join(text_of(course / "_build" / "pdf" / "probeklausur-1-solutions.pdf"))
    exam_dir = course / "exams" / "probeklausur-1"
    for name in yaml.safe_load((exam_dir / "exam.yaml").read_text())["tasks"]:
        fm = yaml.safe_load((exam_dir / name).read_text().split("---")[1])
        assert f"Summe {fm['points']}" in text
        for row in fm["rubric"]:
            first = words(row["criterion"]) or [row["criterion"].split("$")[0].strip()]
            assert first[0] in text, (name, row["criterion"])
    assert text.count("Bewertung Kriterium Punkte") == 4


# --- exercises ----------------------------------------------------------------------------


def solution_runs(course: Path) -> dict[str, str]:
    """Per exercise: the longest plain sentence fragment of its solution."""
    out = {}
    for doc in content.CourseTree(course).of_kind("exercise"):
        body = doc.split.body
        start = body.index("::: solution")
        runs = words(body[start + len("::: solution") : body.rindex(":::")])
        if runs:
            out[doc.rel] = runs[0]
    return out


def test_exercises_pdf_has_every_solution_and_the_blank_one_none(built):
    course, _ = built
    runs = solution_runs(course)
    assert len(runs) >= 12  # most solutions have prose to recognise them by
    full = " ".join(text_of(course / "_build" / "pdf" / "exercises.pdf"))
    blank = " ".join(text_of(course / "_build" / "pdf" / "exercises-blank.pdf"))
    for rel, run in runs.items():
        assert run in full, (rel, run)
        assert run not in blank, (rel, run)
    appendix = re.compile(r"(Hinweise|Lösungen) [ .]*\d+ ")  # the outline's appendix lines
    assert len(appendix.findall(full)) == 2 and "Ergebnisse" in full
    assert appendix.findall(blank) == []
    for word in ("Hinweis 1", "Ergebnisse", "zur Aufgabe"):
        assert word not in blank


# --- failures --------------------------------------------------------------------------------


def test_a_failed_compile_keeps_the_previous_pdf(built):
    course, _ = built
    pdf_dir = course / "_build" / "pdf"
    before = (pdf_dir / "overview.pdf").read_bytes()
    svg = course / "_build" / "figures" / "topic-map.svg"
    saved = svg.read_bytes()
    svg.unlink()
    try:
        result = pdf.build(course, ["overview"], figures=False)
    finally:
        svg.write_bytes(saved)
    (row,) = result["docs"]
    assert row["status"] == "failed" and row["errors"][0].startswith("typst: ")
    assert (pdf_dir / "overview.pdf").read_bytes() == before
    manifest = json.loads((pdf_dir / "manifest.json").read_text())
    assert [d["id"] for d in manifest["docs"]] == [d for d in EXPECTED if d != "overview"]

    again = pdf.build(course, ["overview"], figures=False)
    assert again["docs"][0]["status"] in ("built", "cached")
    manifest = json.loads((pdf_dir / "manifest.json").read_text())
    assert [d["id"] for d in manifest["docs"]] == EXPECTED


def test_a_filter_finding_names_the_course_file_and_line(built):
    course, _ = built
    overview = course / "overview.md"
    text = overview.read_text()
    lines = text.split("\n")
    at = lines.index("## Voraussetzungen")
    bad = [*lines[:at], ":::: note", "Kein Block.", "::::", "", *lines[at:]]
    overview.write_text("\n".join(bad))
    try:
        result = pdf.build(course, ["overview", "summary"], figures=False)
    finally:
        overview.write_text(text)
    for row in result["docs"]:
        assert row["status"] == "failed"
        assert any(
            f"sample-course/overview.md:{at + 1}:1 SK-BLOCK-FENCE" in e for e in row["errors"]
        ), row["errors"]
    assert pdf.build(course, ["overview", "summary"], figures=False)["docs"][0]["status"] in (
        "built",
        "cached",
    )


def test_unknown_documents_are_refused(built):
    course, _ = built
    with pytest.raises(ValueError, match="no document nope"):
        pdf.build(course, ["nope"], figures=False)


def test_without_a_course_every_course_is_built(monkeypatch, capsys):
    base = ROOT / ".cache"
    base.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="test-pdf-all-", dir=base))
    try:
        shutil.copytree(MINI, tmp / "mini", ignore=shutil.ignore_patterns("_build"))
        monkeypatch.setenv("STUDYKIT_COURSES_DIR", str(tmp))
        assert cli.main(["pdf", "--json"]) == 0
        (result,) = json.loads(capsys.readouterr().out)
        assert result["course"] == "mini"
        assert {d["status"] for d in result["docs"]} == {"built"}
        assert cli.main(["pdf"]) == 0
        assert capsys.readouterr().out.startswith("pdf mini: 0 built, 9 cached, 0 failed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
