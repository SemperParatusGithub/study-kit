"""`studykit validate`: the mini course is clean, and each bad fixture yields its code.

tests/fixtures/bad/<SK-CODE>/ mirrors a course layout with exactly one file that breaks
one rule. The test copies the mini course, lays that file over it, validates the whole
course and expects exactly that code, with a fix hint.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from conftest import BAD, REPO, overlay
from studykit import cli, content, findings, tools, validate

CASES = sorted(p.name for p in BAD.iterdir() if p.is_dir())
NEEDS_KATEX = {"SK-MATH-KATEX"}
# Rules only the pandoc filter checks (the Pandoc stage).
NEEDS_PANDOC = {"SK-BLOCK-MARKDOWN", "SK-BLOCK-RAW", "SK-MATH-TYPST", "SK-REF-LINK"}
# A duplicate is reported at every occurrence, the untouched original included.
ALSO_ON_THE_ORIGINAL = {"SK-STRUCT-DUP"}
KATEX_MISSING = validate.katex_available(tools.repo_root())
PANDOC_MISSING = not tools.bin_path(tools.repo_root(), "pandoc").exists()


def run(course: Path, denylist: Path, **kw) -> validate.Report:
    """Validate without KaTeX, figure builds and the site build unless asked for
    (tests/py/test_sitecheck.py covers the Site stage)."""
    config = validate.Config(
        denylist=denylist,
        katex=kw.pop("katex", False),
        figures=kw.pop("figures", False),
        site=kw.pop("site", False),
    )
    return validate.validate([course], config=config, **kw)


def codes(report: validate.Report) -> set[str]:
    return {f.code for f in report.findings}


def test_mini_course_is_clean(mini: Path, denylist: Path):
    report = run(mini, denylist)
    assert report.findings == []
    stages = {s.name: s.status for s in report.courses[0].stages}
    for name in ("Structure", "Schema", "Fences", "MC", "Math", "References", "Figures"):
        assert stages[name] == "ok", name
    assert stages["Pandoc"] == "skipped" or stages["Pandoc"] == "ok"


@pytest.mark.skipif(KATEX_MISSING is not None, reason=f"KaTeX unavailable: {KATEX_MISSING}")
def test_mini_course_passes_katex(mini: Path, denylist: Path):
    assert run(mini, denylist, katex=True).findings == []


@pytest.mark.parametrize("code", CASES)
def test_bad_fixture_yields_its_code(code: str, mini: Path, denylist: Path):
    if code in NEEDS_KATEX and KATEX_MISSING:
        pytest.skip(f"KaTeX unavailable: {KATEX_MISSING}")
    if code in NEEDS_PANDOC and PANDOC_MISSING:
        pytest.skip("pandoc is not installed in .tools/bin")
    written = overlay(mini, BAD / code)
    report = run(mini, denylist, katex=code in NEEDS_KATEX)
    found = report.findings
    assert {f.code for f in found} == {code}, "\n".join(f.format() for f in found)
    for f in found:
        assert f.fix, f.format()
        assert f.line >= 1 and f.col >= 1
    paths = {content.display_path(p) for p in written}
    if code in ALSO_ON_THE_ORIGINAL:
        assert {f.path for f in found} & paths
    else:
        assert {f.path for f in found} <= paths


@pytest.mark.skipif(KATEX_MISSING is not None, reason=f"KaTeX unavailable: {KATEX_MISSING}")
def test_bad_fixtures_only_fail_katex_where_intended(tmp_path: Path):
    """One KaTeX batch over every bad fixture: only SK-MATH-KATEX may fail it."""
    formulas = []
    for code in CASES:
        for path in (BAD / code).rglob("*.md"):
            split = content.split_frontmatter(path.read_text())
            body = content.Body(split.body, split.body_line, str(path), "summary")
            formulas += [(code, f) for f in body.formulas]
    errors = validate.katex_errors(tools.repo_root(), [(f.tex, f.display) for _, f in formulas])
    failing = {code for (code, _), err in zip(formulas, errors, strict=True) if err}
    assert failing <= {"SK-MATH-KATEX", "SK-YAML-ESCAPE", "SK-MATH-DENIED", "SK-MATH-ENV"}
    assert "SK-MATH-KATEX" in failing


def test_quick_skips_cross_file_stages(mini: Path, denylist: Path):
    overlay(mini, BAD / "SK-REF-MISSING")
    report = run(mini, denylist, quick=True)
    assert report.findings == []
    names = [s.name for s in report.courses[0].stages]
    assert names[:5] == ["Structure", "Schema", "Fences", "MC", "Math"]
    assert "References" not in names and "Coverage" not in names


@pytest.mark.skipif(PANDOC_MISSING, reason="pandoc is not installed in .tools/bin")
@pytest.mark.parametrize("quick", [False, True])
def test_the_filter_reports_what_the_python_stages_miss(quick: bool, mini: Path, denylist: Path):
    summary = mini / "summary" / "01-spannungsteiler.md"
    summary.write_text(summary.read_text() + "\nText mit <span>rohem HTML</span>.\n")
    report = run(mini, denylist, quick=quick)
    assert {(f.code, f.message.split("`")[1]) for f in report.findings} == {
        ("SK-BLOCK-RAW", "<span>"),
        ("SK-BLOCK-RAW", "</span>"),
    }
    assert all(f.path.endswith("summary/01-spannungsteiler.md") for f in report.findings)


@pytest.mark.skipif(PANDOC_MISSING, reason="pandoc is not installed in .tools/bin")
@pytest.mark.parametrize("quick", [False, True])
@pytest.mark.parametrize("code", ["SK-REF-FIGURE", "SK-REF-IMAGE"])
def test_a_figure_mistake_has_one_code_in_lint_and_validate(
    code: str, quick: bool, mini: Path, denylist: Path
):
    """--quick (the lint hook) leaves figures to the filter, a full run to References."""
    overlay(mini, BAD / code)
    report = run(mini, denylist, quick=quick)
    assert {f.code for f in report.findings} == {code}


def test_figures_are_built_and_failures_reported(mini: Path, denylist: Path):
    report = run(mini, denylist, figures=True)
    assert report.findings == []
    out = mini / "_build" / "figures"
    assert (out / "rc-bode.facts.json").is_file() and (out / "topic-map.web.svg").is_file()
    script = mini / "figures" / "rc-bode.py"
    script.write_text(script.read_text().replace("return c_.figure", "raise ValueError('kaputt')"))
    report = run(mini, denylist, figures=True)
    assert [(f.code, f.path.endswith("figures/rc-bode.py")) for f in report.findings] == [
        ("SK-FIG-BUILD", True)
    ]
    assert "ValueError: kaputt" in report.findings[0].message


def test_paths_limit_findings_to_those_files(mini: Path, denylist: Path):
    overlay(mini, BAD / "SK-MCQ-KEY")
    overlay(mini, BAD / "SK-BLOCK-UNKNOWN")
    only = mini / "mc" / "spannungsteiler.md"
    report = run(mini, denylist, paths=[only])
    assert codes(report) == {"SK-MCQ-KEY"}


def test_wrapped_titled_and_reference_links_are_checked(mini: Path, denylist: Path):
    overlay(mini, BAD / "SK-REF-MISSING")
    report = run(mini, denylist)
    found = [(f.line, f.col, f.message.split("'")[1]) for f in report.findings]
    assert found == [
        (8, 7, "ex:ex-gibt-es-nicht"),
        (10, 18, "ex:ex-umbruch-fehlt"),
        (11, 53, "ex:ex-titel-fehlt"),
        (12, 9, "ex:ex-referenz-fehlt"),
        (16, 1, "bild-fehlt"),
    ]


def test_release_adds_coverage(mini: Path, denylist: Path):
    # The mini overview wraps a topic link and an exercise wraps a figure caption.
    report = run(mini, denylist, release=True)
    assert codes(report) == {"SK-COV-EXERCISES", "SK-COV-MC"}
    assert all(f.path.endswith("course.yaml") for f in report.findings)


def test_coverage_reports_missing_parts(mini: Path, denylist: Path):
    (mini / "summary" / "01-spannungsteiler.md").unlink()
    (mini / "cheatsheet.md").unlink()
    (mini / "plan.yaml").unlink()
    shutil.rmtree(mini / "exams")
    overview = mini / "overview.md"
    overview.write_text(
        overview.read_text().replace("(topic:rc-tiefpass)", "(topic:spannungsteiler)")
    )
    report = run(mini, denylist, release=True)
    assert {"SK-COV-SUMMARY", "SK-COV-OVERVIEW", "SK-COV-EXAM"} <= codes(report)
    missing = [f for f in report.findings if f.code == "SK-STRUCT-MISSING"]
    assert sorted(f.path.split("/mini/")[1] for f in missing) == ["cheatsheet.md", "plan.yaml"]
    assert all(f.severity == "error" for f in missing)


def test_missing_course_files_warn_while_authoring(mini: Path, denylist: Path):
    (mini / "overview.md").unlink()
    (mini / "plan.yaml").unlink()
    report = run(mini, denylist, quick=True)
    assert report.ok
    assert [(f.code, f.severity, f.message) for f in report.findings] == [
        ("SK-STRUCT-MISSING", "warning", "overview.md is missing (required for --release)"),
        ("SK-STRUCT-MISSING", "warning", "plan.yaml is missing (required for --release)"),
    ]
    only = mini / "summary" / "01-spannungsteiler.md"
    assert run(mini, denylist, quick=True, paths=[only]).findings == []


def test_skipped_stages_explain_why(mini: Path, denylist: Path):
    report = run(mini, denylist)
    stages = {s.name: s for s in report.courses[0].stages}
    for name in ("Verification", "PDF", "Site"):
        assert stages[name].status == "skipped"
        assert stages[name].notes and stages[name].notes[0].startswith("skipped: ")


def test_registered_stage_runs_in_order(mini: Path, denylist: Path):
    seen = []

    @validate.stage("Probe", "SK-PROBE", 65)
    def probe(ctx: validate.Context) -> None:
        seen.append([s.name for s in validate.STAGES].index("Probe"))

    try:
        report = run(mini, denylist)
        names = [s.name for s in report.courses[0].stages]
        assert names.index("References") < names.index("Probe") < names.index("Figures")
        assert seen
    finally:
        validate.STAGES[:] = [s for s in validate.STAGES if s.name != "Probe"]


def test_missing_course_yaml(tmp_path: Path, denylist: Path):
    (tmp_path / "leer").mkdir()
    assert codes(run(tmp_path / "leer", denylist)) == {"SK-STRUCT-MISSING"}


def test_cli_validate_json(mini: Path, capsys, monkeypatch):
    monkeypatch.setenv("STUDYKIT_COURSES_DIR", str(mini.parent))
    overlay(mini, BAD / "SK-MCQ-COUNT")
    assert cli.main(["validate", "mini", "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["errors"] == 1
    assert out["findings"][0]["code"] == "SK-MCQ-COUNT"
    assert out["courses"][0]["course"] == "mini"


def test_cli_validate_text_format(mini: Path, capsys):
    overlay(mini, BAD / "SK-MCQ-COUNT")
    assert cli.main(["validate", str(mini)]) == 1
    line = capsys.readouterr().out.splitlines()[0]
    (parsed,) = findings.parse(line)
    assert parsed.path.endswith("mc/spannungsteiler.md")
    assert (parsed.line, parsed.col, parsed.code) == (6, 1, "SK-MCQ-COUNT")
    assert parsed.fix and parsed.format() == line


def test_denylist_matches_whole_control_words():
    entries = [
        validate.DenyEntry("\\R", "", "fails", ["\\R"], None),
        validate.DenyEntry("env:vmatrix", "", "fails", [], "vmatrix"),
    ]
    assert validate.denied("x \\in \\R", entries)
    assert not validate.denied("A \\Rightarrow B", entries)
    assert not validate.denied("a \\\\R", entries)  # a line break followed by the letter R
    assert validate.denied("\\begin{vmatrix} a \\end{vmatrix}", entries)


def test_wrapped_matrix_follows_the_denylist_pairs():
    wraps = {"matrix": [(["\\left", "|"], ["\\right", "|"])]}
    det = "\\left|\\begin{matrix} a \\end{matrix}\\right|"
    assert validate._environments(det, wraps) == [("matrix", True)]
    assert validate._environments(det, {}) == [("matrix", False)]
    bare = "\\begin{matrix} a \\end{matrix}"
    assert validate._environments(bare, wraps) == [("matrix", False)]
    mismatched = "\\left|\\begin{matrix} a \\end{matrix}\\right)"
    assert validate._environments(mismatched, wraps) == [("matrix", False)]


def test_real_denylist_entries_are_matchable():
    path = REPO / "pandoc" / "math-denylist.json"
    if not path.is_file():
        pytest.skip("pandoc/math-denylist.json not present on this branch")
    entries = validate.load_denylist(path)
    assert entries
    for entry in entries:
        assert entry.use, entry.token
        assert entry.kind in {"silent", "fails"}, entry.token
        sample = f"\\begin{{{entry.env}}} a \\end{{{entry.env}}}" if entry.env else entry.token
        assert entry in validate.denied(sample, entries), entry.token


def test_points_of_every_exam_are_checked(mini: Path, denylist: Path):
    """A broken task in one exam must not hide the points check of the next exam."""
    overlay(mini, BAD / "SK-STRUCT-MISSING")  # exams/probeklausur-2/01-pk2-t1.md, 10 points
    (mini / "exams" / "probeklausur-2" / "exam.yaml").write_text(
        "schema: 1\nid: probeklausur-2\ntitle: Probeklausur 2\nduration_min: 30\n"
        "points: 11\npass_points: 5\ntasks: [01-pk2-t1.md]\n"
    )
    task = mini / "exams" / "probeklausur-1" / "01-pk1-t1.md"
    task.write_text(task.read_text().replace("points: 10", "points: '10'"))
    found = {(f.code, Path(f.path).parent.name) for f in run(mini, denylist).findings}
    assert found == {("SK-SCHEMA-VALUE", "probeklausur-1"), ("SK-STRUCT-POINTS", "probeklausur-2")}


def test_paths_accept_directories(mini: Path, denylist: Path):
    overlay(mini, BAD / "SK-MCQ-KEY")
    overlay(mini, BAD / "SK-BLOCK-UNKNOWN")
    assert codes(run(mini, denylist, paths=[mini / "mc"])) == {"SK-MCQ-KEY"}
    assert codes(run(mini, denylist, paths=[mini])) == {"SK-MCQ-KEY", "SK-BLOCK-UNKNOWN"}


def test_exam_tasks_need_hints_like_exercises(mini: Path, denylist: Path):
    task = mini / "exams" / "probeklausur-1" / "01-pk1-t1.md"
    text = task.read_text()
    start = text.index("::: hint")
    task.write_text(text[:start] + text[text.index(":::\n\n", start) + 5 :])
    (finding,) = run(mini, denylist, quick=True).findings
    assert finding.code == "SK-BLOCK-HINTS" and "exam task has 1 to 3" in finding.message


@pytest.mark.parametrize(
    ("qid", "n", "pin_last", "lua"),
    [  # reference orders printed by `M.order` in pandoc/filters/lib/mcq.lua (1-based)
        ("mc-rc-tiefpass-001", 4, False, [2, 1, 3, 4]),
        ("mc-rc-tiefpass-001", 6, False, [3, 2, 6, 1, 4, 5]),
        ("mc-rc-tiefpass-001", 6, True, [2, 5, 1, 3, 4, 6]),
        ("mc-spannungsteiler-101", 3, False, [3, 1, 2]),
        ("mc-spannungsteiler-101", 5, False, [4, 5, 1, 2, 3]),
        ("mc-spannungsteiler-101", 5, True, [4, 1, 2, 3, 5]),
    ],
)
def test_pdf_order_mirrors_the_typst_shuffle(qid, n, pin_last, lua):
    assert [i + 1 for i in validate.pdf_order(qid, n, pin_last)] == lua


def test_skewed_answer_letters_after_the_pdf_shuffle_warn(mini: Path, denylist: Path):
    question = """:::: {{.mcq #mc-spannungsteiler-00{n} type="single" difficulty="1"}}
Frage {n}?

- [x] Antwort eins

  Richtig.

- [ ] Antwort zwei

  Falsch.

- [ ] Antwort drei

  Falsch.

::: explanation
Darum.
:::
::::
"""
    bank = "---\ntopic: spannungsteiler\ntitle: Spannungsteiler\n---\n\n"
    bank += "\n".join(question.format(n=n) for n in range(1, 5))
    (mini / "mc" / "spannungsteiler.md").write_text(bank)
    (finding,) = run(mini, denylist, quick=True).findings
    assert finding.code == "SK-MCQ-BIAS" and finding.severity == "warning"
    assert "correct answer is (A) in 3 of 4" in finding.message


def test_mock_exam_size_follows_the_real_exam(mini: Path, denylist: Path):
    course = mini / "course.yaml"
    text = course.read_text().replace("duration_min: 60", "duration_min: 90")
    course.write_text(text.replace("points: 30", "points: 33"))  # 30 is within 10% of 33
    found = [f for f in run(mini, denylist, release=True).findings if f.code == "SK-COV-EXAM"]
    assert [(f.path.split("/mini/")[1], f.line) for f in found] == [
        ("exams/probeklausur-1/exam.yaml", 5)
    ]
    assert "duration_min is 60 minutes, but the real exam has 90" in found[0].message
