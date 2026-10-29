"""`studykit status`: the study status of /study-status."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from conftest import REPO
from studykit import cli, progress, status

SAMPLE = REPO / "examples" / "sample-course"


@pytest.fixture
def course(tmp_path: Path) -> Path:
    target = tmp_path / "courses" / "sample-course"
    shutil.copytree(SAMPLE, target, ignore=shutil.ignore_patterns("_build", "progress"))
    return target


def attempt(t: str, score: float, conf: str = "unsure") -> dict:
    return {"t": t, "chosen": ["A"], "score": score, "conf": conf, "ms": 1}


def seed(course: Path) -> None:
    items = {
        "plan:s-2026-11-02-a": {"done": True},
        "plan:s-2026-11-07-a": {"done": True},
        "mc:mc-spannungsteiler-001": {
            "h": "12345678",
            "box": 0,
            "due": "2026-11-10",
            "attempts": [attempt("2026-11-10T10:00:00.000Z", 0, "sure")],
        },
        "mc:mc-rc-filter-001": {
            "h": "12345678",
            "box": 2,
            "due": "2026-11-12",
            "attempts": [attempt("2026-11-09T10:00:00.000Z", 1)],
        },
        "ex:ex-rc-tp-bode": {
            "h": "12345678",
            "hints": 0,
            "answer_ok": True,
            "rating": "partial",
            "box": 1,
            "due": "2026-11-11",
        },
        "exam:probeklausur-1": {
            "attempts": [
                {
                    "started": "2026-11-08T09:00:00.000Z",
                    "duration_s": 7000,
                    "points": {"pk1-t1": 10},
                    "total": 42,
                },
                {
                    "started": "2026-11-09T09:00:00.000Z",
                    "duration_s": 7000,
                    "points": {"pk1-t1": 16},
                    "total": 64,
                },
            ]
        },
    }
    path = course.parent / "export.json"
    path.write_text(
        json.dumps(
            {
                "schema": "studykit-progress/1",
                "course": "sample-course",
                "exported_at": "2026-11-10T18:00:00.000Z",
                "items": items,
            }
        )
    )
    assert progress.import_file(course, path)[1] == []


def test_status_reports_days_adherence_and_reviews(course: Path, capsys):
    seed(course)
    assert cli.main(["status", str(course), "--today", "2026-11-12", "--json"]) == 0
    r = json.loads(capsys.readouterr().out)
    assert r["days_left"] == 95 and r["exam_date"] == "2027-02-15"
    # behind like the site: past sessions that are not done (11-04, 11-09, 11-11)
    assert r["plan"]["behind_ids"] == ["s-2026-11-04-a", "s-2026-11-09-a", "s-2026-11-11-a"]
    assert r["plan"]["done"] == 2 and r["plan"]["past"] == 5
    assert [s["id"] for s in r["plan"]["next"]] == [
        "s-2026-11-14-a",
        "s-2026-11-16-a",
        "s-2026-11-18-a",
    ]
    assert [t["id"] for t in r["weak_topics"]] == ["spannungsteiler", "rc-filter"]
    assert [t["id"] for t in r["unanswered_topics"]] == ["wechselstrom"]
    assert r["due"] == {"mc": 2, "exercises": 1}
    assert r["last_mock"]["total"] == 64 and r["last_mock"]["passed"] is True
    assert any("studykit plan" in h for h in r["hints"])
    # due reviews point to the examiner mode that asks them first
    assert any("`/examine sample-course mc`" in h for h in r["hints"])


def test_status_matches_the_report(course: Path):
    seed(course)
    r, found = status.study_status(course, "2026-11-12")
    assert found == []
    snap = progress.snapshot(course, "2026-11-12")
    report = progress.compute_report(snap)
    assert r["mastery"] == report["overall"]
    assert r["due"] == {"mc": report["due"]["mc"], "exercises": report["due"]["exercises"]}


def test_status_text_without_progress(course: Path, capsys):
    assert cli.main(["status", str(course), "--today", "2026-10-30"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("sample-course · ")
    assert "exam 2027-02-15 in 108 day(s)" in out
    assert "mastery - " in out
    assert "next 2026-11-02 learn (spannungsteiler) 120 min:" in out
    assert "/import-progress sample-course" in out
    assert "not practised yet" not in out  # no mastery yet: nothing to explain


def test_status_text_names_topics_not_practised(course: Path, capsys):
    seed(course)
    assert cli.main(["status", str(course), "--today", "2026-11-12"]) == 0
    out = capsys.readouterr().out
    assert "not practised yet (count 0 in the mastery): Komplexe Wechselstromrechnung" in out


def test_status_without_a_plan(course: Path, capsys):
    (course / "plan.yaml").unlink()
    assert cli.main(["status", str(course), "--today", "2026-10-30", "--json"]) == 0
    r = json.loads(capsys.readouterr().out)
    assert r["plan"]["sessions"] == 0
    assert "no study plan: `studykit plan sample-course` schedules one" in r["hints"]
