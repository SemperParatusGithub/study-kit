"""`studykit render`: the website's bridge to the pandoc filter set (docs/architecture.md §3.2)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from studykit import cli, render, tools

pytestmark = pytest.mark.skipif(
    not tools.bin_path(tools.repo_root(), "pandoc").exists(),
    reason="pandoc is not installed in .tools/bin",
)

RENDERED = {
    "cheatsheet.md": "cheatsheet",
    "overview.md": "overview",
    "exams/probeklausur-1/01-pk1-t1.md": "exam-task",
    "exams/probeklausur-1/02-pk1-t2.md": "exam-task",
    "exams/probeklausur-1/exam.yaml": "exam",
    "exams/probeklausur-1/mc.md": "exam-mc",
    "exercises/rc-tiefpass/ex-rc-tp-grenzfrequenz.md": "exercise",
    "exercises/spannungsteiler/ex-spannungsteiler-unbelastet.md": "exercise",
    "mc/rc-tiefpass.md": "mc",
    "summary/01-spannungsteiler.md": "summary",
    "summary/02-rc-tiefpass.md": "summary",
}


def by_rel(result: dict) -> dict[str, dict]:
    return {row["rel"]: row for row in result["files"]}


def test_renders_every_site_file_of_the_mini_course(mini: Path) -> None:
    result = render.render_course(mini)
    assert result["schema"] == 1
    assert result["course"] == "mini"
    assert result["lang"] == "de"
    assert result["pandoc"] == "3.13"
    rows = by_rel(result)
    assert {rel: row["kind"] for rel, row in rows.items()} == RENDERED
    assert (mini / "_build" / "index.json").is_file()
    for rel, row in rows.items():
        assert row["findings"] == [], rel
        assert row["cached"] is False
        assert len(row["digest"]) == 64
        if row["kind"] == "exam":
            assert row["html"] is None
        else:
            assert row["html"].rstrip().endswith("</script>"), rel
            assert 'id="sk-meta"' in row["html"]


def test_data_is_validated_frontmatter_as_json(mini: Path) -> None:
    rows = by_rel(render.render_course(mini))
    ex = rows["exercises/rc-tiefpass/ex-rc-tp-grenzfrequenz.md"]["data"]
    assert ex["id"] == "ex-rc-tp-grenzfrequenz"
    assert ex["difficulty"] == 2
    assert [a["key"] for a in ex["answers"]] == ["fg", "Hdb", "H"]
    assert ex["answers"][0]["label"] == "$f_\\mathrm{g}$"
    exam = rows["exams/probeklausur-1/exam.yaml"]["data"]
    assert exam["schema"] == 1  # by alias, as written in the file
    assert exam["tasks"] == ["01-pk1-t1.md", "02-pk1-t2.md"]
    json.dumps(rows)  # plain JSON throughout


def test_known_digests_come_back_cached(mini: Path) -> None:
    first = by_rel(render.render_course(mini))
    known = {rel: row["digest"] for rel, row in first.items()}
    second = by_rel(render.render_course(mini, known=known))
    assert all(row["cached"] and row["html"] is None for row in second.values())
    # an edit changes that file's digest only
    summary = mini / "summary" / "01-spannungsteiler.md"
    summary.write_text(summary.read_text(encoding="utf-8") + "\nNoch ein Satz.\n", "utf-8")
    third = by_rel(render.render_course(mini, known=known))
    assert [rel for rel, row in third.items() if not row["cached"]] == [
        "summary/01-spannungsteiler.md"
    ]
    assert "Noch ein Satz." in third["summary/01-spannungsteiler.md"]["html"]


def test_index_change_invalidates_every_digest(mini: Path) -> None:
    first = by_rel(render.render_course(mini))
    course = mini / "course.yaml"
    text = course.read_text(encoding="utf-8")
    course.write_text(text.replace("title: RC-Tiefpass,", "title: RC-Glied,"), "utf-8")
    second = by_rel(render.render_course(mini))
    assert all(second[rel]["digest"] != first[rel]["digest"] for rel in first)


def test_course_limits_are_part_of_the_digest(mini: Path) -> None:
    """cheatsheet.max_pages reaches the cheat sheet's schema check, not the index."""
    sheet = mini / "cheatsheet.md"
    sheet.write_text(sheet.read_text(encoding="utf-8").replace("max_pages: 1", "max_pages: 2"))
    first = by_rel(render.render_course(mini))
    assert first["cheatsheet.md"]["findings"] == []
    known = {rel: row["digest"] for rel, row in first.items()}
    course = mini / "course.yaml"
    text = course.read_text(encoding="utf-8")
    course.write_text(text.replace("max_pages: 2}", "max_pages: 1}"), "utf-8")
    row = by_rel(render.render_course(mini, known=known))["cheatsheet.md"]
    assert row["cached"] is False
    assert [f["code"] for f in row["findings"]] == ["SK-SCHEMA-VALUE"]


def test_every_module_the_bridge_loads_is_in_the_digest() -> None:
    """A studykit module that render imports, even indirectly, shapes what it returns."""
    script = (
        "import json, sys, studykit.render; print(json.dumps(sorted("
        "m.__file__ for n, m in sys.modules.items() if n.split('.')[0] == 'studykit')))"
    )
    proc = subprocess.run(
        [sys.executable, "-I", "-c", script], capture_output=True, text=True, check=True
    )
    loaded = {Path(p).resolve() for p in json.loads(proc.stdout)}
    hashed = {p.resolve() for p in render.shaping_modules()}
    assert loaded - hashed == set()
    assert {"yamlio.py", "model.py", "content.py", "render.py"} <= {p.name for p in hashed}


def test_filter_findings_are_returned_with_positions(mini: Path) -> None:
    summary = mini / "summary" / "01-spannungsteiler.md"
    summary.write_text(summary.read_text(encoding="utf-8") + "\n::: sidebar\nText.\n:::\n", "utf-8")
    row = by_rel(render.render_course(mini, paths=["summary/01-spannungsteiler.md"]))[
        "summary/01-spannungsteiler.md"
    ]
    assert row["html"] is None
    assert row["findings"], "an unknown block must be reported"
    first = row["findings"][0]
    assert first["code"].startswith("SK-")
    assert first["path"].endswith("summary/01-spannungsteiler.md")
    lines = summary.read_text(encoding="utf-8").splitlines()
    assert lines[first["line"] - 1].startswith("::: sidebar")


def test_schema_problems_keep_the_raw_frontmatter(mini: Path) -> None:
    ex = mini / "exercises" / "spannungsteiler" / "ex-spannungsteiler-unbelastet.md"
    ex.write_text(
        ex.read_text(encoding="utf-8").replace("minutes: 5\n", "minutes: fünf\n"), "utf-8"
    )
    row = by_rel(render.render_course(mini, paths=[ex]))[
        "exercises/spannungsteiler/ex-spannungsteiler-unbelastet.md"
    ]
    assert row["data"]["minutes"] == "fünf"
    assert row["data"]["title"] == "Unbelasteter Spannungsteiler"
    assert [f["code"] for f in row["findings"]] == ["SK-SCHEMA-VALUE"]
    assert row["html"] is not None  # the body still renders


def test_paths_select_files_and_report_the_rest(mini: Path) -> None:
    result = render.render_course(
        mini, paths=["mc/rc-tiefpass.md", "plan.yaml", "summary/99-nichts.md"]
    )
    assert [row["rel"] for row in result["files"]] == ["mc/rc-tiefpass.md"]
    assert result["skipped"] == [
        {"rel": "plan.yaml", "reason": "plan files are not rendered"},
        {"rel": "summary/99-nichts.md", "reason": "no such course file"},
    ]


def test_cli_prints_one_json_document(mini: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["render", str(mini), "--paths", "overview.md", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert [row["rel"] for row in result["files"]] == ["overview.md"]
    known = mini / "known.json"
    known.write_text(json.dumps({"overview.md": result["files"][0]["digest"]}))
    assert cli.main(["render", str(mini), "--paths", "overview.md", "--known", str(known)]) == 0
    assert "overview.md  cached" in capsys.readouterr().out
