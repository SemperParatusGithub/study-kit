"""`studykit cheatsheet fit`: densities 0 to 4, the page limit and the measured overflow.

Courses are copied into the repository's .cache (Typst reads only files below --root). The
fixtures in tests/py/fixtures/cheatsheet/ replace the mini course's cheat sheet (limit 1
page): long.md needs a denser setting than 0 to fit one page, too-long.md does not fit even
at density 4.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import MINI
from studykit import cheatsheet, cli, pdf, tools

ROOT = tools.repo_root()
SAMPLE = ROOT / "examples" / "sample-course"
FIXTURES = Path(__file__).parent / "fixtures" / "cheatsheet"


@pytest.fixture
def scratch() -> Iterator[Path]:
    base = ROOT / ".cache"
    base.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="test-cheatsheet-", dir=base))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def mini(scratch: Path) -> Path:
    course = scratch / "mini"
    shutil.copytree(MINI, course, ignore=shutil.ignore_patterns("_build"))
    return course


def use(course: Path, fixture: str) -> None:
    (course / "cheatsheet.md").write_text((FIXTURES / fixture).read_text())


def fit(course: Path, capsys, *flags: str) -> tuple[int, dict]:
    code = cli.main(["cheatsheet", "fit", str(course), "--json", "--no-figures", *flags])
    return code, json.loads(capsys.readouterr().out)


def manifest_entry(course: Path) -> dict | None:
    manifest = json.loads((course / "_build" / "pdf" / "manifest.json").read_text())
    entries = [d for d in manifest["docs"] if d["id"] == "cheatsheet"]
    return entries[0] if entries else None


# --- the limit and the loop --------------------------------------------------------------


def course_with(max_pages: int) -> SimpleNamespace:
    return SimpleNamespace(cheatsheet=SimpleNamespace(max_pages=max_pages))


@pytest.mark.parametrize(
    ("course", "own", "expected"),
    [
        (2, {"max_pages": 2}, 2),
        (2, {"max_pages": 1}, 1),
        (1, {"max_pages": 3}, 1),
        (3, {}, 3),
        (5, {"max_pages": 4}, 4),
        (10, {"max_pages": 10}, 10),
        (12, {"max_pages": 11}, 10),  # never more than 10, whatever the files say
        (3, {"max_pages": True}, 3),  # not a number
        (3, {"max_pages": 0}, 3),  # out of range: the schema reports it
    ],
)
def test_the_limit_is_the_smallest_of_ten_the_course_and_the_sheet(course, own, expected):
    assert cheatsheet.limit(course_with(course), own) == expected


def test_the_fit_stops_at_the_first_density_within_the_limit():
    pages = {0: 3, 1: 3, 2: 2, 3: 2, 4: 1}
    compiled: list[int] = []

    def compile(density: int) -> list:
        compiled.append(density)
        return []

    result = cheatsheet.fit(compile, lambda: pages[compiled[-1]], 2)
    assert (result.fits, result.density, result.pages) == (True, 2, 2)
    assert compiled == [0, 1, 2] and result.tried == [(0, 3), (1, 3), (2, 2)]

    compiled.clear()
    result = cheatsheet.fit(compile, lambda: 4, 3)
    assert (result.fits, result.density, result.pages) == (False, 4, 4)
    assert compiled == [0, 1, 2, 3, 4]

    result = cheatsheet.fit(lambda d: ["broken"], lambda: 1, 2)
    assert (result.fits, result.density, result.problems) == (False, 0, ["broken"])


PAGE = {
    "density": 4,
    "width": "600pt",
    "height": "840pt",
    "margin": "20pt",
    "columns": 2,
    "gutter": "20pt",
}  # content 800pt high; columns start at x 20pt and 310pt


def at(page: int, column: int, down: float) -> dict:
    return {"page": page, "x": f"{20 + 290 * column}pt", "y": f"{20 + 800 * down}pt"}


def test_positions_run_through_the_columns_in_pages():
    assert cheatsheet.position(at(1, 0, 0), PAGE) == 0
    assert cheatsheet.position(at(1, 0, 0.5), PAGE) == 0.25
    assert cheatsheet.position(at(1, 1, 0), PAGE) == 0.5
    assert cheatsheet.position(at(2, 1, 0.5), PAGE) == 1.75
    assert cheatsheet.position({"page": 1, "x": "309.4pt", "y": "900pt"}, PAGE) == 1.0


def test_the_overflow_names_the_largest_sections_by_their_source_lines():
    layout = {
        "page": PAGE,
        "end": at(2, 0, 0.84),  # 1.42 pages
        "sections": [  # starting at 0.05, 0.25, 0.6 and 1.0 pages
            {"title": "A", "at": at(1, 0, 0.1)},
            {"title": "B", "at": at(1, 0, 0.5)},
            {"title": "C", "at": at(1, 1, 0.2)},
            {"title": "D", "at": at(2, 0, 0.0)},
        ],
    }
    lines = [(7, "Alpha $x$"), (20, "Beta"), (31, "Gamma"), (40, "Delta")]
    over = cheatsheet.overflow(layout, 1, 2, lines)
    assert over["overflow_pages"] == 0.42 and over["used_pages"] == 1.42
    assert (over["pages"], over["max_pages"], over["density"]) == (2, 1, 4)
    assert over["largest_sections"] == [
        {"title": "Delta", "line": 40, "height_pages": 0.42},
        {"title": "Gamma", "line": 31, "height_pages": 0.4},
        {"title": "Beta", "line": 20, "height_pages": 0.35},
        {"title": "Alpha $x$", "line": 7, "height_pages": 0.2},
    ]
    # headings the source does not match one to one keep the titles Typst read
    titles = [s["title"] for s in cheatsheet.overflow(layout, 1, 2, lines[:2])["largest_sections"]]
    assert titles == ["D", "C", "B", "A"]
    assert "more than 10 pages" in cheatsheet.overflow_message({**over, "pages": 11})


# --- real builds --------------------------------------------------------------------------


def test_the_sample_cheat_sheet_fits_within_two_pages(scratch: Path, capsys):
    course = scratch / "sample-course"
    shutil.copytree(SAMPLE, course, ignore=shutil.ignore_patterns("_build"))
    figures = SAMPLE / "_build" / "figures"
    if figures.is_dir():  # reuse built figures; the runner's cache decides what is fresh
        shutil.copytree(figures, course / "_build" / "figures")
    code = cli.main(["cheatsheet", "fit", str(course), "--json"])
    result = json.loads(capsys.readouterr().out)
    assert code == 0, result
    assert result["fits"] is True and result["max_pages"] == 2
    assert 1 <= result["pages"] <= 2 and result["density"] in cheatsheet.DENSITIES
    path = course / "_build" / "pdf" / "cheatsheet.pdf"
    assert pdf.page_count(path) == result["pages"]
    entry = manifest_entry(course)
    assert entry is not None
    assert (entry["pages"], entry["max_pages"], entry["density"]) == (
        result["pages"],
        2,
        result["density"],
    )


def test_a_longer_sheet_fits_at_a_denser_setting(mini: Path, capsys):
    use(mini, "long.md")
    code, result = fit(mini, capsys)
    assert code == 0, result
    assert result["fits"] is True and result["pages"] == result["max_pages"] == 1
    assert result["density"] in (1, 2, 3)
    assert manifest_entry(mini)["density"] == result["density"]
    # a second run reuses the PDF and remembers its density
    code, again = fit(mini, capsys)
    assert code == 0 and again["status"] == "cached" and again["density"] == result["density"]


def test_a_too_long_sheet_exits_3_with_the_overflow_and_keeps_the_previous_pdf(mini: Path, capsys):
    assert fit(mini, capsys)[0] == 0
    path = mini / "_build" / "pdf" / "cheatsheet.pdf"
    before = path.read_bytes()

    use(mini, "too-long.md")
    code, result = fit(mini, capsys)
    assert code == cheatsheet.EXIT_OVERFLOW == 3
    assert result["fits"] is False and result["status"] == "failed"
    assert (result["max_pages"], result["density"]) == (1, 4) and result["pages"] >= 2
    assert 0 < result["overflow_pages"] < 1
    assert result["overflow_pages"] == pytest.approx(result["used_pages"] - 1, abs=0.011)
    sections = result["largest_sections"]
    assert len(sections) == cheatsheet.SHOWN_SECTIONS
    heights = [s["height_pages"] for s in sections]
    assert heights == sorted(heights, reverse=True) and all(h > 0 for h in heights)
    source = (mini / "cheatsheet.md").read_text().split("\n")
    for s in sections:  # each names its heading in cheatsheet.md
        assert source[s["line"] - 1] == f"## {s['title']}"
    assert result["kept"].endswith("mini/_build/pdf/cheatsheet.pdf")
    assert path.read_bytes() == before
    assert manifest_entry(mini) is None

    # the same as text
    assert cli.main(["cheatsheet", "fit", str(mini), "--no-figures"]) == 3
    text = capsys.readouterr().out
    assert "does not fit" in text and "kept the previous" in text
    assert f"(cheatsheet.md:{sections[0]['line']})" in text

    # `studykit pdf` fails the document the same way
    result = pdf.build(mini, ["cheatsheet"], figures=False)
    (row,) = result["docs"]
    assert row["status"] == "failed" and row["overflow"]["overflow_pages"] > 0
    assert row["errors"][0].startswith("the cheat sheet has ")


@pytest.mark.parametrize("max_pages", [3, 10])
def test_long_sheet_respects_the_course_limit(mini: Path, capsys, max_pages: int):
    course_yaml = mini / "course.yaml"
    text = course_yaml.read_text()
    assert "max_pages: 2" in text
    course_yaml.write_text(text.replace("max_pages: 2", f"max_pages: {max_pages}"))
    head, body = (FIXTURES / "too-long.md").read_text().split("---\n", 2)[1:]
    head = head.replace("max_pages: 1", f"max_pages: {max_pages}")
    parts = [body.replace("\n## ", f"\n## Teil {n}: ") for n in (1, 2, 3)]
    (mini / "cheatsheet.md").write_text(f"---\n{head}---\n" + "\n".join(parts))
    code, result = fit(mini, capsys)
    assert result["max_pages"] == max_pages
    if max_pages == 10:
        assert code == 0 and result["fits"] is True
        assert 3 < result["pages"] <= 10
        assert manifest_entry(mini)["max_pages"] == 10
        return
    assert code == 3
    assert result["pages"] > 3 and result["overflow_pages"] > 0
    assert result["kept"] is None and not (mini / "_build" / "pdf" / "cheatsheet.pdf").exists()
    row = pdf.build(mini, ["cheatsheet"], figures=False)["docs"][0]
    assert "over its limit of 3" in row["errors"][0]


def test_a_course_without_a_cheat_sheet_has_nothing_to_fit(mini: Path, capsys):
    (mini / "cheatsheet.md").unlink()
    assert cli.main(["cheatsheet", "fit", str(mini), "--no-figures"]) == 2
    assert "no document cheatsheet" in capsys.readouterr().err
