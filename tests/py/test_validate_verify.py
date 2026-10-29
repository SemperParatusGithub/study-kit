"""validate's Verification stage (SK-VER): what the ledger says, reported at the item."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from studykit import content, validate, verify

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "examples" / "sample-course"
GRENZ = "exercises/rc-filter/ex-rc-tp-grenzfrequenz.md"
CHECK = """\
from math import pi
from studykit.check import answers
R, C = 2.2e3, 47e-9
answers(tau=R * C * 1e6, fg=1 / (2 * pi * R * C), Hdb=-3.0103, phi=-45.0)
"""


@pytest.fixture
def course(tmp_path: Path) -> Path:
    target = tmp_path / "sample-course"
    shutil.copytree(SAMPLE, target, ignore=shutil.ignore_patterns("_build"))
    (target / "checks").mkdir()
    (target / "checks" / "ex-rc-tp-grenzfrequenz.py").write_text(CHECK)
    return target


def stage(course: Path, release: bool = False, paths=None) -> tuple[list, list[str]]:
    """Findings and notes of the Verification stage alone."""
    config = validate.Config(katex=False, figures=False, pdf=False, site=False)
    tree = content.CourseTree(course)
    ctx = validate.Context(tree, config, paths, quick=False, release=release)
    validate.check_verification(ctx)
    return sorted(ctx.findings), ctx.notes


def by_code(findings) -> dict[str, list]:
    out: dict[str, list] = {}
    for f in findings:
        out.setdefault(f.code, []).append(f)
    return out


def edit(course: Path, old: str, new: str) -> None:
    path = course / GRENZ
    path.write_text(path.read_text().replace(old, new, 1))


def test_a_fresh_course_is_quiet_until_release(course: Path):
    findings, notes = stage(course)
    assert findings == []
    assert notes == ["0 of 60 items verified, 0 disputed, 0 quarantined, 0 stale"]
    findings, _ = stage(course, release=True)
    codes = by_code(findings)
    assert set(codes) == {"SK-VER-UNVERIFIED", "SK-VER-CHECK"}
    assert len(codes["SK-VER-UNVERIFIED"]) == 60
    assert all(f.severity == "warning" for f in findings)
    first = next(f for f in codes["SK-VER-UNVERIFIED"] if "ex-rc-tp-grenzfrequenz" in f.message)
    assert (first.path.endswith(GRENZ), first.line) == (True, 2)
    numeric = {f.message.split()[2] for f in codes["SK-VER-CHECK"]}
    assert "mc-rc-filter-001" in numeric and "mc-rc-filter-002" not in numeric  # 1/sqrt(2)
    assert "mc-rc-filter-009" not in numeric  # Kprim


def test_verified_items_drop_out_and_edits_go_stale(course: Path):
    verify.run(content.CourseTree(course), "ex-rc-tp-grenzfrequenz")
    findings, notes = stage(course, release=True)
    assert not [f for f in findings if "ex-rc-tp-grenzfrequenz" in f.message]
    assert notes[0].startswith("1 of 60 items verified")
    edit(course, "**b)**", "**b)** Nun:")
    (stale,) = by_code(stage(course)[0])["SK-VER-STALE"]
    assert stale.severity == "warning" and stale.path.endswith(GRENZ)
    assert "changed since it was checked (verified)" in stale.message


def test_disputes_fail_a_release_and_quarantine_is_listed(course: Path):
    edit(course, "value: 1539.2, unit: Hz", "value: 1608.0, unit: Hz")
    verify.run(content.CourseTree(course), "ex-rc-tp-grenzfrequenz")
    (f,) = by_code(stage(course)[0])["SK-VER-DISPUTED"]
    assert f.severity == "warning" and "'fg'" in f.message
    (f,) = by_code(stage(course, release=True)[0])["SK-VER-DISPUTED"]
    assert f.severity == "error"
    verify.quarantine(content.CourseTree(course), "mc-rc-filter-003", note="ambiguous stem")
    (q,) = by_code(stage(course)[0])["SK-VER-QUARANTINED"]
    assert q.severity == "warning" and "hidden from the site and the PDFs" in q.message
    assert q.path.endswith("mc/rc-filter.md") and q.line > 1


def test_broken_and_orphaned_entries(course: Path):
    ledgers = course / "state" / "verify"
    ledgers.mkdir(parents=True)
    (ledgers / "mc-rc-filter-002.json").write_text("{not json")
    (ledgers / "ex-weg.json").write_text("{}")
    (course / "checks" / "mc-weg-001.json").write_text("{}")
    (course / "checks" / "ex-rc-tp-grenzfrequenz.alt.py").write_text(CHECK)  # second method
    (course / "checks" / "sum-rc-filter.py").write_text("")  # formula audit
    codes = by_code(stage(course)[0])
    (ledger,) = codes["SK-VER-LEDGER"]
    assert ledger.severity == "error" and ledger.path.endswith("mc-rc-filter-002.json")
    assert sorted(Path(f.path).name for f in codes["SK-VER-ORPHAN"]) == [
        "ex-weg.json",
        "mc-weg-001.json",
    ]
    # --paths reports only the selected files, and no orphans
    findings, _ = stage(course, paths={GRENZ})
    assert findings == []


def test_full_validate_runs_the_stage(course: Path):
    config = validate.Config(katex=False, figures=False, pdf=False, site=False)
    report = validate.validate([course], config=config)
    stages = {s.name: s for s in report.courses[0].stages}
    assert stages["Verification"].status == "ok"
    assert stages["Verification"].notes[0].endswith("0 stale")
