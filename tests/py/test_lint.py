"""`studykit lint` and its Claude Code hook mode, plus the error-code documentation."""

from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

import pytest

from conftest import BAD, MINI, REPO, overlay
from studykit import cli, lint, tools, validate

ERRORS_DOC = REPO / "docs" / "content-format" / "errors.md"


def config(denylist: Path) -> validate.Config:
    return validate.Config(denylist=denylist, katex=False)


def test_lint_clean_file(denylist: Path):
    report = lint.lint_files([MINI / "mc" / "rc-tiefpass.md"], config(denylist))
    assert report.ok and report.findings == []


def test_lint_reports_only_the_given_file(mini: Path, denylist: Path):
    overlay(mini, BAD / "SK-MCQ-WHY")
    overlay(mini, BAD / "SK-BLOCK-UNKNOWN")
    report = lint.lint_files([mini / "mc" / "spannungsteiler.md"], config(denylist))
    assert {f.code for f in report.findings} == {"SK-MCQ-WHY"}


def test_lint_reports_a_duplicate_in_the_edited_file(mini: Path, denylist: Path):
    # The edited exam bank reuses a practice-bank id; exams/ is discovered before mc/.
    edited = mini / "exams" / "probeklausur-1" / "mc.md"
    edited.write_text(edited.read_text().replace("#mc-rc-tiefpass-101", "#mc-rc-tiefpass-001"))
    report = lint.lint_files([edited], config(denylist))
    (dup,) = report.findings
    assert dup.code == "SK-STRUCT-DUP" and dup.line == 25
    assert "mc/rc-tiefpass.md:6" in dup.message
    assert "existing ids are never renamed" in dup.fix
    full = validate.validate([mini], config=config(denylist), quick=True)
    assert sorted((f.path.split("/mini/")[1], f.line) for f in full.findings) == [
        ("exams/probeklausur-1/mc.md", 25),
        ("mc/rc-tiefpass.md", 6),
    ]


def test_lint_is_quick(mini: Path, denylist: Path):
    """Lint stops after Math: a broken reference is a validate (References) finding."""
    (written,) = overlay(mini, BAD / "SK-REF-MISSING")
    start = time.perf_counter()
    report = lint.lint_files([written], config(denylist))
    assert time.perf_counter() - start < 1.0
    assert report.findings == []


PANDOC_MISSING = not tools.bin_path(tools.repo_root(), "pandoc").exists()


@pytest.mark.skipif(PANDOC_MISSING, reason="pandoc is not installed in .tools/bin")
@pytest.mark.parametrize(
    ("rel", "replaced", "snippet", "message"),
    [
        (
            "summary/01-spannungsteiler.md",
            None,
            'Der Widerstand `R1`{onmouseover="alert(1)"} teilt die Spannung.',
            "inline code takes no attributes",
        ),
        (
            "summary/01-spannungsteiler.md",
            None,
            '| Größe | Wert |\n|---|---|\n| `x`{onfocus="x()" autofocus=""} | 1 |',
            "inline code takes no attributes",
        ),
        (
            "summary/01-spannungsteiler.md",
            None,
            '{onclick="alert(1)"}\n| Größe | Wert |\n|---|---|\n| R | 1 |',
            "tables take no attributes",
        ),
        (
            "mc/rc-tiefpass.md",
            "  $f_\\mathrm{g} = 1/(2\\pi RC)$.",
            '  $f_\\mathrm{g} = 1/(2\\pi RC)$ mit `RC`{onclick="alert(1)"}.',
            "inline code takes no attributes",
        ),
    ],
)
def test_lint_rejects_attributes_that_would_reach_the_page(
    rel: str, replaced: str | None, snippet: str, message: str, mini: Path, denylist: Path
):
    """An attribute the filter does not reject is copied onto the page (an onclick runs)."""
    path = mini / rel
    text = path.read_text()
    if replaced is None:
        path.write_text(text + "\n" + snippet + "\n")
    else:
        assert replaced in text
        path.write_text(text.replace(replaced, snippet, 1))
    report = lint.lint_files([path], config(denylist))
    assert [(f.code, f.message) for f in report.findings] == [("SK-BLOCK-MARKDOWN", message)]


def test_lint_outside_a_course(tmp_path: Path, denylist: Path):
    stray = tmp_path / "notiz.md"
    stray.write_text("---\ntitle: x\n---\n")
    report = lint.lint_files([stray, tmp_path / "fehlt.md"], config(denylist))
    assert sorted(f.code for f in report.findings) == ["SK-STRUCT-MISSING", "SK-STRUCT-PATH"]


def test_lint_cli_exit_codes(mini: Path, capsys):
    assert cli.main(["lint", str(MINI / "overview.md")]) == 0
    capsys.readouterr()
    (written,) = overlay(mini, BAD / "SK-MCQ-KEY")
    assert cli.main(["lint", str(written), "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert [f["code"] for f in out["findings"]] == ["SK-MCQ-KEY"]
    assert cli.main(["lint"]) == 2


def hook(monkeypatch, payload: object) -> tuple[int, str]:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    err = io.StringIO()
    monkeypatch.setattr("sys.stderr", err)
    return cli.main(["lint", "--hook"]), err.getvalue()


@pytest.fixture
def course_dir(mini: Path, monkeypatch) -> Path:
    monkeypatch.setenv("STUDYKIT_COURSES_DIR", str(mini.parent))
    return mini


def test_hook_blocks_on_findings(course_dir: Path, monkeypatch):
    (written,) = overlay(course_dir, BAD / "SK-MCQ-COUNT")
    code, err = hook(monkeypatch, {"tool_name": "Write", "tool_input": {"file_path": str(written)}})
    assert code == 2
    first = err.splitlines()[0]
    assert re.match(r"^\S+:\d+:\d+ SK-MCQ-COUNT .+ \(fix: .+\)$", first)


def test_hook_passes_clean_files(course_dir: Path, monkeypatch):
    target = course_dir / "summary" / "02-rc-tiefpass.md"
    assert hook(monkeypatch, {"tool_input": {"file_path": str(target)}}) == (0, "")


def test_hook_resolves_relative_paths(course_dir: Path, monkeypatch):
    overlay(course_dir, BAD / "SK-MCQ-COUNT")
    payload = {"cwd": str(course_dir), "tool_input": {"file_path": "mc/spannungsteiler.md"}}
    assert hook(monkeypatch, payload)[0] == 2


@pytest.mark.parametrize(
    "payload",
    [
        {"tool_input": {"file_path": str(MINI / "overview.md")}},  # tests/ is not a hook root
        {"tool_input": {"file_path": str(tools.repo_root() / "README.md")}},
        {"tool_input": {}},
        {"something": "else"},
        "not an object",
    ],
)
def test_hook_ignores_everything_else(payload, monkeypatch, tmp_path: Path):
    monkeypatch.setenv("STUDYKIT_COURSES_DIR", str(tmp_path))
    assert hook(monkeypatch, payload) == (0, "")


def test_hook_ignores_non_content_files(course_dir: Path, monkeypatch):
    script = course_dir / "figures" / "rc-bode.py"
    assert hook(monkeypatch, {"tool_input": {"file_path": str(script)}}) == (0, "")


def test_hook_ignores_bad_json(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
    assert cli.main(["lint", "--hook"]) == 0


FILTERS = REPO / "pandoc" / "filters"


def documented_codes() -> set[str]:
    return set(re.findall(r"^### `(SK-[A-Z0-9-]+)`", ERRORS_DOC.read_text(), re.MULTILINE))


def filter_codes() -> set[str]:
    """Every code the Lua filters can report (each is written out as a string literal)."""
    return {
        code
        for path in sorted(FILTERS.rglob("*.lua"))
        for code in re.findall(r"'(SK-[A-Z0-9-]+)'", path.read_text())
    }


def test_filter_codes_name_a_rule():
    """A filter finding names its rule like every other check (docs/architecture.md §4.3)."""
    codes = filter_codes()
    assert {"SK-BLOCK-RAW", "SK-REF-FIGURE", "SK-MATH-THINSPACE"} <= codes
    assert not {c for c in codes if not re.fullmatch(r"SK-[A-Z]+-[A-Z0-9-]+", c)}


def test_every_code_is_documented():
    sources = [
        REPO / "src" / "studykit" / f"{name}.py"
        for name in ("yamlio", "model", "content", "validate", "lint", "sitecheck", "checklinks")
    ]
    used = set()
    for path in sources:
        used |= set(re.findall(r'"(SK-[A-Z]+-[A-Z0-9-]+)"', path.read_text()))
    used |= {p.name for p in BAD.iterdir() if p.is_dir()}
    used |= filter_codes()
    missing = used - documented_codes()
    assert not missing, f"document these in docs/content-format/errors.md: {sorted(missing)}"


def test_documented_codes_exist():
    sources = "".join(
        (REPO / "src" / "studykit" / f"{n}.py").read_text()
        for n in ("yamlio", "model", "content", "validate", "lint", "sitecheck", "checklinks")
    )
    emitted = filter_codes()
    stale = {c for c in documented_codes() if f'"{c}"' not in sources and c not in emitted}
    assert not stale, f"errors.md documents codes nothing emits: {sorted(stale)}"
