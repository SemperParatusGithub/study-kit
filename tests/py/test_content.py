"""Discovery, frontmatter, the fence-line scanner, MC parsing, math and links, the index."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import MINI
from studykit import cli, content, index


def body(text: str, kind: str = "summary", first_line: int = 1) -> content.Body:
    return content.Body(text, first_line, "x.md", kind)


def codes(b: content.Body) -> list[str]:
    b.blocks, b.questions, b.formulas, b.links  # noqa: B018 - run every scanner
    return [f.code for f in b.findings]


@pytest.mark.parametrize(
    ("rel", "kind"),
    [
        ("course.yaml", "course"),
        ("summary/03-rc-filter.md", "summary"),
        ("summary/rc-filter.md", "unknown"),
        ("exercises/rc-filter/ex-rc-tp.md", "exercise"),
        ("exercises/ex-rc-tp.md", "unknown"),
        ("mc/rc-filter.md", "mc"),
        ("exams/probeklausur-1/exam.yaml", "exam"),
        ("exams/probeklausur-1/02-pk1-t2.md", "exam-task"),
        ("exams/probeklausur-1/mc.md", "exam-mc"),
        ("figures/rc-bode.py", "figure"),
        ("figures/rc_bode.py", "unknown"),
        ("analysis/exam-profile.yaml", "exam-profile"),
    ],
)
def test_classify(rel, kind):
    assert content.classify(rel)[0] == kind


def test_discovery_skips_generated_and_private_trees(mini: Path):
    for rel in ("_build/x.md", "state/verify/a.md", "sources/text/vl/p0001.md", ".hidden/a.md"):
        (mini / rel).parent.mkdir(parents=True, exist_ok=True)
        (mini / rel).write_text("x")
    tree = content.CourseTree(mini)
    assert not any(d.rel.startswith(("_build", "state", "sources/text", ".hidden")) for d in tree)
    assert {d.kind for d in tree} >= {"course", "overview", "summary", "exercise", "mc", "exam"}


def test_split_frontmatter():
    s = content.split_frontmatter("---\na: 1\n---\n\nText\n")
    assert (s.yaml, s.yaml_line, s.body_line, s.error) == ("a: 1\n", 2, 4, None)
    assert s.body.split("\n")[1] == "Text"
    assert "does not start" in content.split_frontmatter("Text\n").error
    assert "no closing" in content.split_frontmatter("---\na: 1\n").error


def test_fence_tree_and_positions():
    b = body(
        "Intro\n\n"
        ':::: {.mcq #mc-a-001 type="single" difficulty="1"}\n'
        "Stem\n\n"
        "- [x] A\n\n  why\n\n"
        "::: explanation\nE\n:::\n"
        "::::\n",
        kind="mc",
    )
    (mcq,) = b.blocks
    assert (mcq.name, mcq.ident, mcq.attrs["type"]) == ("mcq", "mc-a-001", "single")
    assert [c.name for c in mcq.children] == ["explanation"]
    assert b.lines[mcq.open_line].no == 3
    assert codes(b) == []


def test_fences_inside_code_are_ignored():
    b = body("```text\n::: tip\n```\n\n::: note\nx\n:::\n")
    assert [blk.name for blk in b.blocks] == ["note"]
    assert codes(b) == []


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("::: note\nx\n", "SK-BLOCK-FENCE"),  # never closed
        (":::\n", "SK-BLOCK-FENCE"),  # close without open
        (":::note\nx\n:::\n", "SK-BLOCK-FENCE"),  # no space
        ("::: note extra\nx\n:::\n", "SK-BLOCK-FENCE"),
        ("::: {.note}\nx\n:::\n", "SK-BLOCK-FENCE"),  # attributes on a plain block
        (":::: {.mcq #mc-a-001}\nx\n:::\n", "SK-BLOCK-FENCE"),  # close does not match
        ("::: mcq\nx\n:::\n", "SK-BLOCK-FENCE"),
        ("  ::: note\nx\n:::\n", "SK-BLOCK-FENCE"),
        ("::: explanation\nx\n:::\n", "SK-BLOCK-PLACEMENT"),
        ("::: note\nx\n:::\nText\n", "SK-BLOCK-BLANK"),
    ],
)
def test_fence_problems(text, code):
    assert code in codes(body(text))


def test_option_parsing_with_lazy_lines_and_display_math():
    b = body(
        ':::: {.mcq #mc-a-001 type="single" difficulty="1"}\n'
        "Stem line one\nline two\n\n"
        "- [X] Option A\ncontinued lazily\n\n"
        "  Why A with\n  $$\n  x = 1\n  $$\n\n"
        "- [ ] Option B\n\n  Why B\n\n"
        "::: explanation\nE\n:::\n::::\n",
        kind="mc",
    )
    (q,) = b.questions
    assert q.stem == ["Stem line one", "line two"]
    a, bb = q.options
    assert a.correct and not bb.correct
    assert a.text == "Option A continued lazily"
    assert len(a.paragraphs) == 2 and "x = 1" in a.why
    assert q.explanations == [(17, "E")]
    assert codes(b) == []


def test_inline_math_positions_and_rules():
    b = body("Ab $x$ und `$code$` und \\$5 und $y_2$.\n\nZweite $z$ Zeile\n", first_line=5)
    found = [(f.tex, f.line, f.col) for f in b.formulas]
    assert found == [("x", 5, 4), ("y_2", 5, 33), ("z", 7, 8)]
    assert set(codes(body("Preis $5 und $x$\n"))) == {"SK-MATH-INLINE"}
    assert codes(body("$x$5\n")) == ["SK-MATH-INLINE"]


def test_display_math_in_list_items_and_markers():
    b = body("- Punkt\n\n  $$\n  a =\n  b\n  $$\n")
    assert [(f.tex, f.display, f.line) for f in b.formulas] == [("a =\nb", True, 3)]
    assert codes(body("$$\na\n+ b\n$$\n")) == ["SK-MATH-BLOCKMARK"]
    assert codes(body("$$\na\n1. b\n$$\n")) == ["SK-MATH-BLOCKMARK"]
    assert codes(body("$$\na\n\nb\n$$\n")).count("SK-MATH-DISPLAY") >= 1
    assert codes(body("$$\na\n")) == ["SK-MATH-DISPLAY"]


def test_links_and_figures():
    b = body(
        "Text [a](ex:ex-a) und [$x$](topic:t).\n\n![Cap](fig:s)\n\n::: note\n![C](fig:t)\n:::\n"
    )
    assert [(lk.image, lk.target, lk.alone) for lk in b.links] == [
        (False, "ex:ex-a", False),
        (False, "topic:t", False),
        (True, "fig:s", True),
        (True, "fig:t", True),
    ]
    (attr,) = body("![Cap](fig:s){width=50%}\n").links
    assert attr.attrs and attr.alone


def test_shorten_never_cuts_math():
    text = (
        "Ein langer Satz über den Tiefpass mit "
        "$\\underline{H} = \\frac{1}{1 + \\mathrm{j}\\omega RC}$"
    )
    short = content.shorten(text, 50)
    assert short.endswith("…") and short.count("$") % 2 == 0


def test_items_and_ids():
    tree = content.CourseTree(MINI)
    assert set(tree.ids("exercise")) == {"ex-spannungsteiler-unbelastet", "ex-rc-tp-grenzfrequenz"}
    assert set(tree.ids("mc")) == {
        "mc-rc-tiefpass-001",
        "mc-rc-tiefpass-002",
        "mc-rc-tiefpass-003",
        "mc-spannungsteiler-101",
        "mc-rc-tiefpass-101",
        "mc-rc-tiefpass-102",
    }
    assert set(tree.ids("exam-task")) == {"pk1-t1", "pk1-t2"}
    assert tree.figure_slugs == ["rc-bode", "topic-map"]
    assert tree.archetypes == {"spannungsteiler-rechnung", "bode-diagramm"}


def test_index_contract(mini: Path, capsys):
    assert cli.main(["index", str(mini), "--json"]) == 0
    printed = json.loads(capsys.readouterr().out)
    written = json.loads((mini / "_build" / "index.json").read_text())
    assert printed == written
    assert list(written) == [
        "schema",
        "course",
        "lang",
        "title",
        "topics",
        "items",
        "exams",
        "figures",
        "sources",
    ]
    assert (written["schema"], written["course"], written["lang"]) == (1, "mini", "de")
    assert written["topics"]["rc-tiefpass"] == {"title": "RC-Tiefpass", "order": 2}
    for item in written["items"].values():
        assert set(item) == {"kind", "title", "topic", "path"}
        assert item["kind"] in index.ITEM_KINDS
        assert (mini / item["path"]).is_file()
    assert written["items"]["ex-rc-tp-grenzfrequenz"] == {
        "kind": "exercise",
        "title": "Grenzfrequenz eines RC-Tiefpasses",
        "topic": "rc-tiefpass",
        "path": "exercises/rc-tiefpass/ex-rc-tp-grenzfrequenz.md",
    }
    assert written["items"]["mc-rc-tiefpass-001"]["path"] == "mc/rc-tiefpass.md"
    assert written["items"]["overview"]["topic"] is None
    assert written["exams"] == {"probeklausur-1": {"title": "Probeklausur 1"}}
    assert "topic-map" in written["figures"]
    assert written["sources"]["vl-01"] == {"title": "Vorlesung 1", "pages": 20}


def test_index_survives_broken_files(mini: Path):
    (mini / "exercises" / "rc-tiefpass" / "ex-kaputt.md").write_text("---\nid: [\n---\n")
    data = index.build(content.CourseTree(mini))
    assert "ex-kaputt" not in data["items"] and "ex-rc-tp-grenzfrequenz" in data["items"]


def test_ls_json(mini: Path, capsys, monkeypatch):
    monkeypatch.setenv("STUDYKIT_COURSES_DIR", str(mini.parent))
    assert cli.main(["ls", "--json"]) == 0
    (course,) = json.loads(capsys.readouterr().out)
    assert course["id"] == "mini" and course["title"] == "Mini-Kurs Elektrotechnik"
    assert cli.main(["ls", "mini", "--json", "--kind", "exercise"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert {r["id"] for r in rows} == {"ex-spannungsteiler-unbelastet", "ex-rc-tp-grenzfrequenz"}
    assert all(r["kind"] == "exercise" and r["topic"] for r in rows)
