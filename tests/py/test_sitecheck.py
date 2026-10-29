"""The Site stage of `validate --release`: strict build, astro check, link check (SK-SITE)."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import BAD, REPO, overlay
from studykit import sitecheck, validate
from studykit.figures import runner
from studykit.findings import Finding
from studykit.sitecheck import Run

SITE_MISSING = sitecheck.missing(REPO)

STRICT_OUTPUT = """\
\x1b[2m08:11:59\x1b[22m \x1b[31m[ERROR]\x1b[39m [build] Caught error rendering /c/mini/: \
StrictError: 1 content error(s) (STUDYKIT_STRICT=1):
  courses/mini/_build/figures/rc-bode.web.svg:1:1 SK-FIG-BUILD figure 'rc-bode' is not \
available: its SVG is missing (fix: run `studykit fig build mini`)
1 content error(s) (STUDYKIT_STRICT=1):
  courses/mini/_build/figures/rc-bode.web.svg:1:1 SK-FIG-BUILD figure 'rc-bode' is not \
available: its SVG is missing (fix: run `studykit fig build mini`)
    at inlineFigures (file:///site/.astro/chunks/figures.mjs:76:41)
"""

CHECK_OUTPUT = """\
$ astro check
08:49:03 [check] Getting diagnostics for Astro files in /repo/site...
src/elements/sk-exam.ts:85:7 - warning ts(6385): 'returnValue' is deprecated.
src/pages/c/[course]/index.astro:12:5 - error ts(2322): Type 'number' is not assignable \
to type 'string'.

Result (57 files):
- 1 error
"""


def test_a_failed_strict_build_reports_the_content_findings_it_printed():
    found = sitecheck.build_findings(Run(1, sitecheck.ANSI_RE.sub("", STRICT_OUTPUT)), "c.yaml")
    assert [(f.path, f.code) for f in found] == [
        ("courses/mini/_build/figures/rc-bode.web.svg", "SK-FIG-BUILD")
    ]
    assert found[0].fix == "run `studykit fig build mini`"
    assert sitecheck.build_findings(Run(0, STRICT_OUTPUT), "c.yaml") == []


def test_a_failed_build_without_content_findings_is_sk_site_build():
    out = (
        "08:00:00 [build] Building\n[vite] error: Cannot find module 'x'\n    at foo (bar.js:1:1)\n"
    )
    (f,) = sitecheck.build_findings(Run(1, out), "examples/c/course.yaml")
    assert (f.path, f.line, f.code) == ("examples/c/course.yaml", 1, "SK-SITE-BUILD")
    assert "Cannot find module 'x'" in f.message and "at foo" not in f.message


def test_astro_check_errors_become_sk_site_check():
    (f,) = sitecheck.check_findings(Run(1, CHECK_OUTPUT))
    assert (f.path, f.line, f.col, f.code) == (
        "site/src/pages/c/[course]/index.astro",
        12,
        5,
        "SK-SITE-CHECK",
    )
    assert "ts(2322)" in f.message
    assert sitecheck.check_findings(Run(0, CHECK_OUTPUT)) == []  # warnings never fail
    (generic,) = sitecheck.check_findings(Run(1, "something broke\n"))
    assert generic.code == "SK-SITE-CHECK" and "something broke" in generic.message


def test_links_on_other_courses_pages_are_left_to_their_own_run(tmp_path: Path):
    out = tmp_path / "dist"

    def at(rel: str) -> Finding:
        return Finding(str(out / rel), 3, 4, "SK-SITE-LINK", "href='/x/': /x/ is missing", "fix")

    found = sitecheck.link_findings(
        [at("c/mini/index.html"), at("c/other/index.html"), at("search/index.html")], out, "mini"
    )
    assert [f.path for f in found] == ["dist/c/mini/index.html", "dist/search/index.html"]
    assert {(f.line, f.col, f.code) for f in found} == {(3, 4, "SK-SITE-LINK")}


def test_check_builds_into_a_temporary_directory_and_checks_it(tmp_path: Path):
    """The order, arguments and environment of the three steps, with a fake runner."""
    course = tmp_path / "courses" / "mini"
    course.mkdir(parents=True)
    calls: list[tuple[list[str], dict[str, str], Path]] = []
    outs: list[Path] = []

    def fake(argv: list[str], env: dict[str, str], cwd: Path) -> Run:
        calls.append((argv, env, cwd))
        if "build" in argv:
            out = Path(argv[argv.index("--outDir") + 1])
            outs.append(out)
            for rel, html in {
                "c/mini/index.html": '<a href="/c/mini/fehlt/">x</a><a href="#oben">y</a>',
                "c/other/index.html": '<a href="/nirgends/">z</a>',
                "index.html": '<a href="/c/mini/">mini</a>',
            }.items():
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                (out / rel).write_text(f"<html><body>{html}</body></html>")
        return Run(0, "")

    notes: list[str] = []
    found = sitecheck.check(
        REPO, course, "mini", "de", course_doc="mini/course.yaml", run=fake, notes=notes
    )
    build, pagefind, check = (argv for argv, _, _ in calls)
    assert build[1:] == [
        "-C",
        str(REPO / "site"),
        "exec",
        "astro",
        "build",
        "--outDir",
        str(outs[0]),
    ]
    assert outs[0] != REPO / "site" / "dist" and not outs[0].exists()  # removed afterwards
    assert pagefind[1:] == ["--site", str(outs[0]), "--force-language", "de"]
    assert check[1:] == ["-C", str(REPO / "site"), "check"]
    for _, env, _ in calls:
        assert env["STUDYKIT_STRICT"] == "1"
        assert env["STUDYKIT_COURSES_DIR"] == str(course.parent.resolve())
    assert sorted((f.path, f.code, f.message.split(":")[0]) for f in found) == [
        ("dist/c/mini/index.html", "SK-SITE-LINK", "href='#oben'"),
        ("dist/c/mini/index.html", "SK-SITE-LINK", "href='/c/mini/fehlt/'"),
    ]
    assert notes == ["built 3 page(s) into a temporary directory; links checked"]


def test_a_failed_build_skips_pagefind_and_links_but_still_runs_astro_check(tmp_path: Path):
    argvs: list[list[str]] = []

    def fake(argv: list[str], env: dict[str, str], cwd: Path) -> Run:
        argvs.append(argv)
        return Run(1, STRICT_OUTPUT) if "build" in argv else Run(0, "")

    found = sitecheck.check(REPO, tmp_path / "c", "c", "en", course_doc="c/course.yaml", run=fake)
    assert [a[-1] for a in argvs] == [argvs[0][-1], "check"]
    assert [f.code for f in found] == ["SK-FIG-BUILD"]


def test_missing_tools_skip_the_stage(tmp_path: Path, monkeypatch):
    assert sitecheck.missing(tmp_path) == "site/astro.config.mjs not found"
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "astro.config.mjs").write_text("export default {};\n")
    monkeypatch.setattr(sitecheck.shutil, "which", lambda tool, path=None: f"/bin/{tool}")
    assert sitecheck.missing(tmp_path) == "site/node_modules is not installed (run `just setup`)"
    monkeypatch.setattr(
        sitecheck.shutil, "which", lambda tool, path=None: None if tool == "pnpm" else "/bin/x"
    )
    assert sitecheck.missing(tmp_path) == "pnpm is not on PATH (run `just setup`)"


def site_stage(report: validate.Report) -> validate.StageResult:
    (stage,) = [s for s in report.courses[0].stages if s.name == "Site"]
    return stage


def test_the_site_stage_runs_only_with_release(mini: Path, denylist: Path, monkeypatch):
    calls = []
    monkeypatch.setattr(sitecheck, "missing", lambda root: None)
    monkeypatch.setattr(sitecheck, "check", lambda *a, **kw: calls.append(a) or [])
    config = validate.Config(denylist=denylist, katex=False, figures=False)
    stage = site_stage(validate.validate([mini], config=config))
    assert stage.status == "skipped" and "--release" in stage.notes[0]
    # The mini course misses its coverage targets, but Coverage runs after Site.
    report = validate.validate([mini], config=config, release=True)
    assert site_stage(report).status == "ok"
    assert [a[1:4] for a in calls] == [(mini.resolve(), "mini", "de")]
    overlay(mini, BAD / "SK-MCQ-KEY")
    stage = site_stage(validate.validate([mini], config=config, release=True))
    assert stage.status == "skipped" and "fix the errors above first" in stage.notes[0]
    off = validate.Config(denylist=denylist, katex=False, figures=False, site=False)
    assert site_stage(validate.validate([mini], config=off, release=True)).status == "skipped"
    assert len(calls) == 1


@pytest.mark.skipif(SITE_MISSING is not None, reason=f"site unavailable: {SITE_MISSING}")
def test_the_mini_course_builds_strictly_and_a_missing_figure_fails(mini: Path):
    """The real pnpm, astro and pagefind on a copy of the mini course."""
    assert all(o.status != "failed" for o in runner.build_course(mini))
    notes: list[str] = []
    found = sitecheck.check(REPO, mini, "mini", "de", course_doc="mini/course.yaml", notes=notes)
    # the fixture has no lecture PDFs, so source links are warnings
    assert [f for f in found if f.is_error] == [], [f.format() for f in found]
    assert {f.code for f in found} <= {"SK-SITE-LINK"}
    assert notes[0].startswith("built ") and notes[0].endswith("links checked")

    (mini / "_build" / "figures" / "rc-bode.web.svg").unlink()

    def without_astro_check(argv, env, cwd):
        return Run(0, "") if argv[-1] == "check" else sitecheck._run(argv, env, cwd)

    found = sitecheck.check(
        REPO, mini, "mini", "de", course_doc="mini/course.yaml", run=without_astro_check
    )
    assert [(f.code, Path(f.path).name) for f in found] == [("SK-FIG-BUILD", "rc-bode.web.svg")]
