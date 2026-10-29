"""The PDF stage of `studykit validate` (SK-PDF): builds the PDFs, reports what fails.

The mini course is copied into the repository's .cache, because Typst reads only files
below --root; a copy in a temporary directory outside it is skipped with a note.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from conftest import BAD, MINI, overlay
from studykit import content, pdf, tools, validate

ROOT = tools.repo_root()
FIXTURES = Path(__file__).parent / "fixtures" / "cheatsheet"


@pytest.fixture
def course() -> Iterator[Path]:
    base = ROOT / ".cache"
    base.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="test-validate-pdf-", dir=base))
    target = tmp / "mini"
    shutil.copytree(MINI, target, ignore=shutil.ignore_patterns("_build"))
    yield target
    shutil.rmtree(tmp, ignore_errors=True)


def run(course: Path, denylist: Path, **kw) -> validate.Report:
    config = validate.Config(
        denylist=denylist,
        katex=False,
        figures=kw.pop("figures", True),
        pdf=kw.pop("pdf", True),
        site=False,
    )
    return validate.validate([course], config=config, **kw)


def pdf_stage(report: validate.Report) -> validate.StageResult | None:
    stages = [s for s in report.courses[0].stages if s.name == "PDF"]
    return stages[0] if stages else None


def manifest_ids(course: Path) -> list[str]:
    manifest = json.loads((course / "_build" / "pdf" / "manifest.json").read_text())
    return [d["id"] for d in manifest["docs"]]


ALL = [
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


def test_a_full_validate_builds_the_pdfs_and_reuses_them(course: Path, denylist: Path):
    report = run(course, denylist)
    assert report.findings == []
    stage = pdf_stage(report)
    assert stage is not None and stage.status == "ok"
    assert stage.notes == [
        f"9 of 9 PDFs in {content.display_path(course / '_build' / 'pdf')} (9 built, 0 up to "
        "date); cheat sheet 1 of 1 pages at density 0"
    ]
    assert manifest_ids(course) == ALL

    again = pdf_stage(run(course, denylist))
    assert "(0 built, 9 up to date)" in again.notes[0]
    # quick runs (and lint) never build PDFs
    assert pdf_stage(run(course, denylist, quick=True)) is None


def test_paths_build_only_the_documents_made_from_them(course: Path, denylist: Path):
    sheet = course / "cheatsheet.md"
    stage = pdf_stage(run(course, denylist, paths=[sheet]))
    assert stage.status == "ok" and stage.notes[0].startswith("1 of 1 PDFs")
    assert manifest_ids(course) == ["cheatsheet"]
    task = course / "exams" / "probeklausur-1" / "01-pk1-t1.md"
    stage = pdf_stage(run(course, denylist, paths=[task]))
    assert stage.notes[0].startswith("2 of 2 PDFs")
    assert manifest_ids(course) == ["probeklausur-1", "probeklausur-1-solutions", "cheatsheet"]


def test_a_cheat_sheet_over_its_limit_is_reported_at_its_max_pages(course: Path, denylist: Path):
    assert run(course, denylist, paths=[course / "cheatsheet.md"]).findings == []
    before = (course / "_build" / "pdf" / "cheatsheet.pdf").read_bytes()
    (course / "cheatsheet.md").write_text((FIXTURES / "too-long.md").read_text())
    report = run(course, denylist)
    (finding,) = report.findings
    assert finding.code == "SK-PDF-CHEATSHEET" and finding.is_error
    assert finding.path.endswith("mini/cheatsheet.md")
    assert (finding.line, finding.col) == (3, 1)  # max_pages: 1
    assert "even at density 4 (7 pt)" in finding.message and "limit of 1" in finding.message
    assert "studykit cheatsheet fit mini --json" in finding.fix
    assert pdf_stage(report).status == "failed"
    assert (course / "_build" / "pdf" / "cheatsheet.pdf").read_bytes() == before
    assert manifest_ids(course) == [d for d in ALL if d != "cheatsheet"]


def test_a_missing_figure_is_a_compile_error_at_the_file_that_shows_it(
    course: Path, denylist: Path
):
    # without the Figures stage nothing builds the SVGs the documents embed
    report = run(course, denylist, figures=False)
    found = {(f.code, f.path.split("/mini/")[-1], f.line) for f in report.findings}
    assert {code for code, _, _ in found} == {"SK-PDF-COMPILE"}
    exercise = "exercises/rc-tiefpass/ex-rc-tp-grenzfrequenz.md"
    assert ("SK-PDF-COMPILE", "overview.md", 1) in found
    assert ("SK-PDF-COMPILE", exercise, 2) in found  # the line of its id
    by_file = {f.path.split("/mini/")[-1]: f for f in report.findings}
    message = by_file[exercise].message
    assert message.startswith("exercises") and "Typst error: file not found" in message
    assert "/_build/typ/exercises" in message
    assert set(manifest_ids(course)) == {
        "mc",
        "probeklausur-1",
        "probeklausur-1-solutions",
        "cheatsheet",
        "plan",
    }


def test_the_stage_is_skipped_with_a_reason(
    course: Path, denylist: Path, tmp_path: Path, monkeypatch
):
    def note(report: validate.Report) -> str:
        stage = pdf_stage(report)
        assert stage is not None and stage.status == "skipped"
        return stage.notes[0]

    assert note(run(course, denylist, pdf=False)) == "skipped: PDF build is off (Config.pdf)"
    outside = tmp_path / "mini"
    shutil.copytree(MINI, outside, ignore=shutil.ignore_patterns("_build"))
    assert "outside the repository" in note(run(outside, denylist))
    overlay(course, BAD / "SK-MCQ-KEY")
    assert "fix the errors above first" in note(run(course, denylist))

    real = tools.bin_path
    monkeypatch.setattr(
        validate.tools,
        "bin_path",
        lambda root, name: root / "nowhere" if name == "typst" else real(root, name),
    )
    assert note(run(course, denylist)) == (
        "skipped: typst is not installed in .tools/bin (run `just setup`)"
    )
    assert not (course / "_build" / "pdf").exists()


# --- how problems become findings -----------------------------------------------------------


def outcome(doc_id: str, primary: str | None, *problems: pdf.Problem) -> pdf.Outcome:
    return pdf.Outcome(
        doc_id, doc_id, f"{doc_id}.pdf", "", "failed", problems=list(problems), primary=primary
    )


def test_problems_are_reported_where_they_come_from(course: Path):
    tree = content.CourseTree(course)
    typ = course / "_build" / "typ" / "exercises.typ"
    typ.parent.mkdir(parents=True)
    typ.write_text(
        "#sk-info(…)\n"
        '#metadata("ex-spannungsteiler-unbelastet") <ex-spannungsteiler-unbelastet>\n'
        "$ x $\n"
        "#sk-appendix-entry(title: [1.1], back: <ex-rc-tp-grenzfrequenz>)[\n"
        "$ y $\n"
    )
    rel = content.display_path(typ)
    head = pdf.Problem("typst-error", "unknown variable: z", rel, 1, 2)
    body = pdf.Problem("typst-error", "unknown variable: x", rel, 3, 3)
    appendix = pdf.Problem("typst-warning", "unknown font family: nope", rel, 5, 3)
    library = pdf.Problem("typst-error", "oops", "typst/studykit.typ", 12, 1)
    pandoc_warning = pdf.Problem("pandoc-warning", "Could not convert TeX math")
    assembly = pdf.Problem("assembly", "task file 03-x.md does not exist")
    filtered = pdf.Problem(
        "finding", f"{content.display_path(course / 'overview.md')}:4:1 SK-BLOCK-FENCE bad (fix: x)"
    )
    out = outcome("exercises", None, head, body, appendix, library, pandoc_warning, assembly)
    found = [validate._pdf_finding(tree, out, p) for p in out.problems]
    where = [(f.code, f.path.split("/mini/")[-1], f.line) for f in found]
    assert where == [
        ("SK-PDF-COMPILE", "course.yaml", 1),
        ("SK-PDF-COMPILE", "exercises/spannungsteiler/ex-spannungsteiler-unbelastet.md", 2),
        ("SK-PDF-WARNING", "exercises/rc-tiefpass/ex-rc-tp-grenzfrequenz.md", 2),
        ("SK-PDF-COMPILE", "course.yaml", 1),
        ("SK-PDF-WARNING", "course.yaml", 1),
        ("SK-PDF-BUILD", "course.yaml", 1),
    ]
    assert found[1].message == f"exercises.pdf: Typst error: unknown variable: x (at {rel}:3:3)"
    assert found[2].message.startswith("exercises.pdf: Typst warning: unknown font family")
    assert found[4].message == "exercises.pdf: pandoc warning: Could not convert TeX math"
    assert "studykit pdf mini exercises" in found[5].fix
    # a document with a file of its own reports there; a filter finding stays as it is
    plan = outcome("plan", "plan.yaml", assembly, filtered)
    found = [validate._pdf_finding(tree, plan, p) for p in plan.problems]
    assert [(f.code, f.path.split("/mini/")[-1], f.line) for f in found] == [
        ("SK-PDF-BUILD", "plan.yaml", 1),
        ("SK-BLOCK-FENCE", "overview.md", 4),
    ]
