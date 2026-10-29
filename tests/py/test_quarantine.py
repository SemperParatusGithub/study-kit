"""Quarantined items (§2.10) are hidden from the website and the PDFs alike.

The course index carries the quarantined ids; the render bridge (which the site's loader
reads), the filters (HTML and Typst) and the PDF assembler all act on it, so one ledger
entry hides an item everywhere. The site only sees what the bridge returns: a skipped
file has no page and no list entry, and a question the filter drops is in no bank, pool
JSON or exam.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from studykit import content, index, pdf, render, tools, verify

ROOT = tools.repo_root()
SAMPLE = ROOT / "examples" / "sample-course"
HIDDEN = {
    "ex-rc-tp-grenzfrequenz": "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md",
    "mc-rc-filter-001": "mc/rc-filter.md",
    "pk1-t1": "exams/probeklausur-1/01-pk1-t1.md",
    "mc-spannungsteiler-101": "exams/probeklausur-1/mc.md",
}

pytestmark = pytest.mark.skipif(
    not tools.bin_path(ROOT, "pandoc").exists(), reason="pandoc is not installed"
)


@pytest.fixture(scope="module")
def course() -> Iterator[Path]:
    base = ROOT / ".cache"  # Typst reads only files below the repository
    base.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="test-quarantine-", dir=base))
    target = tmp / "sample-course"
    shutil.copytree(SAMPLE, target, ignore=shutil.ignore_patterns("_build"))
    figures = SAMPLE / "_build" / "figures"
    if figures.is_dir():
        shutil.copytree(figures, target / "_build" / "figures")
    tree = content.CourseTree(target)
    for item_id in HIDDEN:
        verify.quarantine(tree, item_id, note="seeded for the test")
    yield target
    shutil.rmtree(tmp, ignore_errors=True)


def test_the_index_lists_quarantined_items(course: Path):
    _, data = index.write(content.CourseTree(course))
    assert data["quarantined"] == sorted(HIDDEN)
    assert "ex-rc-tp-grenzfrequenz" in data["items"]  # links still resolve


def test_the_render_bridge_hides_them_from_the_site(course: Path):
    result = render.render_course(course)
    files = {f["rel"]: f for f in result["files"]}
    skipped = {s["rel"]: s["reason"] for s in result["skipped"]}
    for rel in (HIDDEN["ex-rc-tp-grenzfrequenz"], HIDDEN["pk1-t1"]):
        assert rel not in files and skipped[rel] == render.QUARANTINED
    bank = files["mc/rc-filter.md"]["html"]
    assert 'data-id="mc-rc-filter-001"' not in bank and 'data-id="mc-rc-filter-002"' in bank
    meta = json.loads(bank.split('id="sk-meta">')[1].split("</script>")[0])
    assert "mc-rc-filter-001" not in {i["id"] for i in meta["items"]}
    exam_mc = files["exams/probeklausur-1/mc.md"]["html"]
    assert 'data-id="mc-spannungsteiler-101"' not in exam_mc
    assert 'data-id="mc-spannungsteiler-102"' in exam_mc
    # the exam loses the task and the question with their points; the pass mark keeps its share
    exam = files["exams/probeklausur-1/exam.yaml"]["data"]
    assert exam["tasks"] == ["02-pk1-t2.md", "03-pk1-t3.md", "04-pk1-t4.md"]
    assert (exam["points"], exam["pass_points"]) == (78.0, 39.0)
    # a link to a quarantined exercise is plain text; the others stay links
    summary = files["summary/03-rc-filter.md"]["html"]
    assert 'href="/c/sample-course/exercises/ex-rc-tp-grenzfrequenz/"' not in summary
    assert "Grenzfrequenz eines RC-Tiefpasses" in summary
    assert 'href="/c/sample-course/exercises/ex-rc-tp-messung/"' in summary
    assert all(not f["findings"] for f in result["files"]), [
        f["findings"] for f in result["files"] if f["findings"]
    ]


def test_quarantine_changes_every_digest(course: Path):
    before = {f["rel"]: f["digest"] for f in render.render_course(course)["files"]}
    known = dict(before)
    tree = content.CourseTree(course)
    verify.quarantine(tree, "mc-rc-filter-002", note="second")
    try:
        after = render.render_course(course, known=known)
        assert not any(f["cached"] for f in after["files"])
        bank = next(f for f in after["files"] if f["rel"] == "mc/rc-filter.md")["html"]
        assert 'data-id="mc-rc-filter-002"' not in bank
    finally:
        verify.clear(tree, "mc-rc-filter-002")


def test_the_pdfs_leave_them_out(course: Path):
    result = pdf.build(course, ["exercises", "mc", "probeklausur-1"])
    assert all(d["status"] != "failed" for d in result["docs"]), result
    out = course / "_build" / "pdf"

    def text(name: str) -> str:
        return " ".join(pdf.pdf_text(out / name))

    exercises = text("exercises.pdf")
    assert "Grenzfrequenz eines RC-Tiefpasses" not in exercises
    assert "Tiefpass aus einer Messung bestimmen" in exercises
    mc = text("mc.pdf")
    assert "mc-rc-filter-001" not in mc and "mc-rc-filter-002" in mc
    tree = content.CourseTree(course)
    bank = tree.get("mc/rc-filter.md")
    assert f"{len(bank.body.questions) - 1} Fragen" in mc
    exam = text("probeklausur-1.pdf")
    assert "Ersatzspannungsquelle eines Netzwerks" not in exam
    assert "Punkte 78, bestanden ab 39" in exam
    assert "MC-Teil (9 Fragen) 18" in exam and "Summe 78" in exam
