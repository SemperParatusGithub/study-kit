"""`studykit progress import|log|report` and the parity of progress.py with the site.

The parity tests run the site's own TypeScript (site/src/lib/store.ts and stats.ts) on
the shared cases in tests/fixtures/progress/cases.json through
tests/fixtures/progress/parity.mjs, in the same time zone, and compare every value.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from conftest import FIXTURES, REPO
from studykit import cli, model, progress

PARITY = FIXTURES / "progress" / "parity.mjs"
CASES = FIXTURES / "progress" / "cases.json"
SAMPLE = REPO / "examples" / "sample-course"
TZ_NAME = "Europe/Berlin"
TZ = ZoneInfo(TZ_NAME)
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")


def run_node(cases: dict) -> dict:
    out = subprocess.run(
        [NODE, str(PARITY)],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "TZ": TZ_NAME},
        cwd=REPO,
    )
    return json.loads(out.stdout)


def topic_infos(raw: list[dict]) -> list[progress.TopicInfo]:
    return [
        progress.TopicInfo(
            id=t["id"],
            title=t.get("title", ""),
            weight=t.get("weight"),
            skip=t.get("skip", False),
            mc=t.get("mc", []),
        )
        for t in raw
    ]


def normalized(doc: dict) -> dict:
    return {**doc, "items": {k: progress.normalize_entry(k, v) for k, v in doc["items"].items()}}


def python_stats(case: dict) -> dict:
    items, today, exam = case["items"], case["today"], case["examDate"]
    items = {k: progress.normalize_entry(k, v) for k, v in items.items()}
    topics = topic_infos(case["topics"])
    st = progress.topic_stats(items, topics, today, exam, TZ)
    sessions = case.get("sessions") or []
    nxt = progress.next_session(sessions, items, today)
    return {
        "topics": [
            {
                "id": s["id"],
                "answered": s["answered"],
                "accuracy": s["accuracy"],
                "due": s["due"],
                "misconceptions": s["misconceptions"],
                "recent": len(s["recent"]),
            }
            for s in st
        ],
        "mastery": progress.mastery(st, topics),
        "due": progress.due_count(items, topics, today, exam, tz=TZ),
        "exercisesDue": progress.exercises_due(items, today, exam),
        "weakest": [s["id"] for s in progress.weakest_topics(st, topics)],
        "exercises": {
            k[3:]: progress.exercise_status(e) for k, e in items.items() if k.startswith("ex:")
        },
        "exams": {
            k[5:]: progress.exam_summary(e) for k, e in items.items() if k.startswith("exam:")
        },
        "next": nxt["id"] if nxt else None,
        "behind": progress.behind_count(sessions, items, today),
    }


@needs_node
def test_merge_matches_the_site_store():
    cases = json.loads(CASES.read_text())
    expected = run_node(cases)["merge"]
    assert len(expected) == len(cases["merge"]) >= 8
    for case, want in zip(cases["merge"], expected, strict=True):
        doc, added, merged = progress.merge(normalized(case["local"]), normalized(case["incoming"]))
        assert {"items": doc["items"], "added": added, "merged": merged} == want
        # same key order as the site writes it
        assert list(doc["items"]) == list(want["items"])


@needs_node
def test_stats_match_the_site_figures():
    cases = json.loads(CASES.read_text())
    expected = run_node(cases)["stats"]
    for case, want in zip(cases["stats"], expected, strict=True):
        got = python_stats(case)
        # exact float equality: the sums run in the same order as in JavaScript
        assert got == want, case["today"]
    # the cases reach the interesting branches
    assert {w["mastery"] for w in expected} - {None}
    assert any(w["exercisesDue"] for w in expected) and any(w["due"] for w in expected)
    assert any(t["recent"] == progress.RECENT for w in expected for t in w["topics"])


def test_local_day_follows_the_browser():
    berlin = ZoneInfo("Europe/Berlin")
    assert progress.local_day("2026-11-09T23:30:00.000Z", berlin) == "2026-11-10"
    assert progress.local_day("2026-11-10T12:00:00", berlin) == "2026-11-10"
    assert progress.local_day("2026-11-10", ZoneInfo("America/New_York")) == "2026-11-09"
    assert progress.utc_stamp(progress._parse("2026-11-10T10:00:00+01:00")) == (
        "2026-11-10T09:00:00.000Z"
    )


def test_leitner_mirrors_the_site():
    exam = "2027-02-15"
    assert progress.review(None, 1, "unsure", "2026-11-10", exam)["box"] == 2
    assert progress.review(3, 0, "sure", "2026-11-10", exam) == {
        "box": 0,
        "due": "2026-11-10",
        "misconception": True,
    }
    # an interval past the limit ends at the window start (or the limit inside the window)
    assert progress.schedule(5, "2027-01-20", exam) == "2027-02-05"
    assert progress.schedule(5, "2027-02-08", exam) == "2027-02-13"
    assert progress.schedule(1, "2027-02-13", exam) == "2027-02-16"
    assert not progress.is_due("2027-02-10", "2027-02-01", "2027-02-14", exam)


# --- import ------------------------------------------------------------------------------


@pytest.fixture
def course(tmp_path: Path) -> Path:
    """A writable copy of the sample course (without built files)."""
    target = tmp_path / "courses" / "sample-course"
    shutil.copytree(SAMPLE, target, ignore=shutil.ignore_patterns("_build", "progress"))
    return target


def export(items: dict, course: str = "sample-course", **kw) -> dict:
    return {
        "schema": kw.get("schema", "studykit-progress/1"),
        "course": course,
        "exported_at": kw.get("exported_at", "2026-11-20T18:03:00.000Z"),
        "items": items,
    }


def write(tmp_path: Path, name: str, data: dict | str) -> Path:
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=2))
    return path


MC = {
    "h": "9c01aa12",
    "box": 2,
    "due": "2026-11-22",
    "attempts": [
        {"t": "2026-11-19T08:00:00.000Z", "chosen": ["A"], "score": 1, "conf": "sure", "ms": 900}
    ],
}


def test_import_merges_and_reports_changes(course: Path, tmp_path: Path, capsys):
    first = write(
        tmp_path,
        "studykit-progress-sample-course-2026-11-20.json",
        export(
            {
                "mc:mc-rc-filter-001": MC,
                "ex:ex-rc-tp-bode": {
                    "h": "12345678",
                    "hints": 1,
                    "rating": "partial",
                    "box": 1,
                    "due": "2026-11-21",
                },
                "plan:s-2026-11-02-a": {"done": True},
            }
        ),
    )
    assert cli.main(["progress", "import", str(course), str(first), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["changes"]["added"] == 3 and out["changes"]["sessions_done"] == ["s-2026-11-02-a"]
    state = json.loads((course / "progress" / "state.json").read_text())
    model.Progress.model_validate(state)
    assert (course / "progress" / "browser" / first.name).read_bytes() == first.read_bytes()

    second_mc = {
        **MC,
        "attempts": [
            *MC["attempts"],
            {"t": "2026-11-21T08:00:00.000Z", "chosen": ["B"], "score": 0, "conf": "sure", "ms": 1},
        ],
        "box": 0,
        "due": "2026-11-21",
    }
    second = write(
        tmp_path,
        "studykit-progress-sample-course-2026-11-21.json",
        export(
            {"mc:mc-rc-filter-001": second_mc, "plan:s-2026-11-02-a": {"done": False}},
            exported_at="2026-11-21T09:00:00.000Z",
        ),
    )
    assert cli.main(["progress", "import", str(course), str(second)]) == 0
    text = capsys.readouterr().out
    assert "MC: 1 new attempt(s) on 1 question(s)" in text
    state = json.loads((course / "progress" / "state.json").read_text())
    entry = state["items"]["mc:mc-rc-filter-001"]
    assert len(entry["attempts"]) == 2 and entry["box"] == 0
    assert state["items"]["plan:s-2026-11-02-a"] == {"done": True}  # a done session stays done
    assert state["exported_at"] == "2026-11-21T09:00:00.000Z"

    # the same file again changes nothing and is not copied twice
    assert cli.main(["progress", "import", str(course), str(second), "--json"]) == 0
    again = json.loads(capsys.readouterr().out)
    assert again["changes"]["unchanged"] == 2 and not again["copied"]
    assert len(list((course / "progress" / "browser").iterdir())) == 2


def test_import_dry_run_writes_nothing(course: Path, tmp_path: Path, capsys):
    path = write(tmp_path, "export.json", export({"mc:mc-rc-filter-001": MC}))
    assert cli.main(["progress", "import", str(course), str(path), "--dry-run"]) == 0
    assert "nothing written" in capsys.readouterr().out
    assert not (course / "progress").exists()


@pytest.mark.parametrize(
    ("data", "code", "text"),
    [
        (export({}, course="get2"), "SK-PROGRESS-COURSE", "belongs to the course 'get2'"),
        ({**export({}), "course": ""}, "SK-PROGRESS-COURSE", "names no course"),
        (export({}, schema="studykit-progress/2"), "SK-PROGRESS-SCHEMA", "newer"),
        ({"items": {}, "course": "sample-course"}, "SK-PROGRESS-SCHEMA", "None"),
        ("{not json", "SK-PROGRESS-FILE", "not JSON"),
        ({"schema": "x"}, "SK-PROGRESS-FILE", "no `items`"),
        (
            export({"mc:mc-rc-filter-001": {**MC, "box": 9}}),
            "SK-PROGRESS-ENTRY",
            "items.mc:mc-rc-filter-001.box",
        ),
        (
            export(
                {"mc:mc-rc-filter-001": {**MC, "attempts": [{**MC["attempts"][0], "t": "2026"}]}}
            ),
            "SK-PROGRESS-ENTRY",
            "",
        ),
    ],
)
def test_import_refuses_what_the_site_would_not_write(
    data, code: str, text: str, course: Path, tmp_path: Path, capsys
):
    path = write(tmp_path, "bad.json", data)
    assert cli.main(["progress", "import", str(course), str(path)]) == 1
    err = capsys.readouterr().err
    assert f" {code} " in err and text in err and "(fix: " in err
    assert not (course / "progress").exists()


def test_import_points_at_the_entry_line(course: Path, tmp_path: Path):
    data = export({"plan:s-2026-11-02-a": {"done": True}, "mc:mc-rc-filter-001": {**MC, "h": "X"}})
    path = write(tmp_path, "bad.json", data)
    _, found = progress.import_file(course, path)
    line = path.read_text().splitlines().index('    "mc:mc-rc-filter-001": {') + 1
    assert [(f.code, f.line) for f in found] == [("SK-PROGRESS-ENTRY", line)]


# --- examiner log ------------------------------------------------------------------------

RESULT = {
    "t": "2026-11-20T10:00:00Z",
    "mode": "mc",
    "kind": "mc",
    "topic": "rc-filter",
    "item": "mc-rc-filter-003",
    "chosen": ["B"],
    "conf": "sure",
    "score": 0,
    "finding": "Faktor 2π vergessen",
}


def test_log_appends_valid_results(course: Path, capsys, monkeypatch):
    task = {
        "mode": "exam",
        "kind": "exam-task",
        "topic": "spannungsteiler",
        "item": "pk1-t1",
        "score": 0.75,
        "points": 15,
        "max_points": 20,
    }
    args = ["--json-line", json.dumps(RESULT), "--json-line", json.dumps(task)]
    assert cli.main(["progress", "log", str(course), *args]) == 0
    assert "logged 2 result(s)" in capsys.readouterr().out
    lines = (course / "progress" / "examiner.jsonl").read_text().splitlines()
    first, second = (json.loads(x) for x in lines)
    assert first["t"] == "2026-11-20T10:00:00.000Z"
    assert second["t"].endswith("Z")  # filled in with the time of logging
    for line in lines:
        model.ExaminerResult.model_validate_json(line)

    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({**RESULT, "score": 1}) + "\n\n"))
    assert cli.main(["progress", "log", str(course)]) == 0
    assert len((course / "progress" / "examiner.jsonl").read_text().splitlines()) == 3


@pytest.mark.parametrize(
    ("change", "text"),
    [
        ({"item": "mc-rc-filter-999"}, "does not exist"),
        ({"topic": "wechselstrom"}, "belongs to the topic 'rc-filter'"),
        ({"topic": "unknown"}, "unknown topic"),
        ({"conf": None}, "needs `conf`"),
        ({"score": 2}, "score"),
        ({"kind": "oral", "chosen": ["A"]}, "MC results only"),
        ({"points": 3}, "come together"),
    ],
)
def test_log_refuses_invalid_results(course: Path, change: dict, text: str, capsys):
    bad = {k: v for k, v in {**RESULT, **change}.items() if v is not None}
    assert cli.main(["progress", "log", str(course), "--json-line", json.dumps(bad)]) == 1
    err = capsys.readouterr().err
    assert "--json-line:1:" in err and "SK-PROGRESS-EXAMINER" in err and text in err
    assert not (course / "progress" / "examiner.jsonl").exists()


def test_log_is_all_or_nothing(course: Path, capsys):
    args = ["--json-line", json.dumps(RESULT), "--json-line", "{oops"]
    assert cli.main(["progress", "log", str(course), *args]) == 1
    assert "--json-line:2:2 SK-PROGRESS-EXAMINER" in capsys.readouterr().err
    assert not (course / "progress").exists()


# --- report --------------------------------------------------------------------------------


def seed(course: Path, tmp_path: Path) -> None:
    items = {
        "mc:mc-rc-filter-001": MC,
        "mc:mc-spannungsteiler-001": {
            **MC,
            "attempts": [{**MC["attempts"][0], "score": 0, "chosen": ["C"]}],
            "box": 0,
            "due": "2026-11-19",
        },
        "ex:ex-rc-tp-bode": {
            "h": "12345678",
            "hints": 1,
            "rating": "solved",
            "box": 2,
            "due": "2026-11-20",
        },
        "ex:ex-st-belastet": {"h": "12345678", "hints": 2},
        "exam:probeklausur-1": {
            "attempts": [
                {
                    "started": "2026-11-15T09:00:00.000Z",
                    "duration_s": 6900,
                    "points": {"pk1-t1": 15, "pk1-t3": 10, "mc": 14},
                    "total": 61,
                }
            ]
        },
        "plan:s-2026-11-02-a": {"done": True},
    }
    path = write(tmp_path, "export.json", export(items))
    assert progress.import_file(course, path)[1] == []
    results, found = progress.parse_examiner(
        [("test", 1, json.dumps(RESULT))], progress.content.CourseTree(course)
    )
    assert found == []
    progress.append_examiner(course, results)


def test_report_writes_mastery_and_markdown(course: Path, tmp_path: Path, capsys):
    seed(course, tmp_path)
    args = ["progress", "report", str(course), "--today", "2026-11-20"]
    assert cli.main(args) == 0
    assert "wrote" in capsys.readouterr().out
    data = json.loads((course / "progress" / "mastery.json").read_text())
    model.Mastery.model_validate(data)
    assert data["generated"] == "2026-11-20"
    # the examiner's wrong sure answer is an attempt, and a misconception
    rc = data["topics"]["rc-filter"]
    assert rc["answered"] == 2 and rc["misconceptions"] == 1
    wrong = [m["id"] for m in data["misconceptions"]]
    assert wrong == ["mc-rc-filter-003", "mc-spannungsteiler-001"]
    assert data["exercises"]["ex-rc-tp-bode"]["status"] == "solved"
    assert data["exercises"]["ex-st-belastet"]["status"] == "started"
    assert data["exams"]["probeklausur-1"]["last"]["passed"] is True
    assert data["topics"]["spannungsteiler"]["exam_tasks"]["max_points"] == 20
    assert data["examiner"]["findings"][0]["finding"] == "Faktor 2π vergessen"
    report = (course / "progress" / "report.md").read_text()
    assert report.startswith("# Progress report: ") and "## Misconceptions" in report

    # deterministic: the same inputs give the same bytes
    first = (course / "progress" / "mastery.json").read_bytes()
    assert cli.main(args) == 0
    assert (course / "progress" / "mastery.json").read_bytes() == first


def test_report_without_progress_has_no_mastery(course: Path, capsys):
    assert cli.main(["progress", "report", str(course), "--today", "2026-11-20", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["overall"] is None
    assert all(t["mastery"] is None for t in data["topics"].values())


@needs_node
def test_mastery_json_is_what_the_browser_computes(course: Path, tmp_path: Path):
    """The site contract: `overall` is lib/stats.ts mastery() over the same answers, and
    `topics.<id>.mastery` its topic accuracy (lib/courses.ts reads either)."""
    seed(course, tmp_path)
    snap = progress.snapshot(course, "2026-11-20", TZ)
    report = progress.compute_report(snap, TZ)
    topics = [
        {"id": t.id, "title": t.title, "weight": t.weight, "skip": t.skip, "mc": t.mc}
        for t in snap.info.topics
    ]
    case = {
        "items": snap.items,
        "topics": topics,
        "today": "2026-11-20",
        "examDate": snap.info.exam_date,
        "sessions": [],
    }
    (want,) = run_node({"stats": [case]})["stats"]
    assert report["overall"] == want["mastery"] and report["overall"] is not None
    for t in want["topics"]:
        assert report["topics"][t["id"]]["mastery"] == t["accuracy"]
        assert report["topics"][t["id"]]["due"] == t["due"]
    assert report["due"]["mc"] == want["due"]
    assert report["due"]["exercises"] == want["exercisesDue"]


def test_report_refuses_a_broken_state(course: Path, capsys):
    (course / "progress").mkdir()
    (course / "progress" / "state.json").write_text('{"schema": "studykit-progress/1"}')
    assert cli.main(["progress", "report", str(course)]) == 1
    assert "SK-PROGRESS-FILE" in capsys.readouterr().err
