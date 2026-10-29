"""`studykit plan`: the deterministic scheduler (docs/architecture.md §2.9)."""

from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path

import pytest

from conftest import REPO
from studykit import cli, model, plan, progress, validate, yamlio

SAMPLE = REPO / "examples" / "sample-course"


@pytest.fixture
def course(tmp_path: Path) -> Path:
    target = tmp_path / "courses" / "sample-course"
    shutil.copytree(SAMPLE, target, ignore=shutil.ignore_patterns("_build", "progress"))
    return target


def set_study(course: Path, text: str) -> None:
    path = course / "course.yaml"
    path.write_text(re.sub(r"^study: .*$", text, path.read_text(), flags=re.MULTILINE))


def make(course: Path, start: str = "2026-10-29", **kw) -> dict:
    result, found = plan.run(course, start=start, **kw)
    errors = [f.format() for f in found if f.is_error]
    assert not errors, errors
    return result


def load(course: Path) -> model.Plan:
    doc = yamlio.load((course / "plan.yaml").read_text(), path="plan.yaml")
    assert doc.ok, doc.findings
    return model.Plan.model_validate(doc.data)


def week(day: date) -> date:
    return date.fromordinal(day.toordinal() - day.weekday())


def check_constraints(course: Path, start: str) -> model.Plan:
    """The rules every plan keeps (§2.9)."""
    c = model.validate_course(yamlio.safe_load((course / "course.yaml").read_text()))
    p = load(course)
    exam = c.exam.date
    budget = round(c.study.hours_per_week * 60)
    sessions = p.sessions
    assert sessions
    assert all(s.date < exam for s in sessions), "no session on or after the exam"
    assert all(s.date.isoformat() >= max(start, c.study.start.isoformat()) for s in sessions)
    blocked = set()
    for spec in c.study.blocked:
        first, _, last = spec.partition("..")
        d = date.fromisoformat(first)
        while d <= date.fromisoformat(last or first):
            blocked.add(d)
            d = date.fromordinal(d.toordinal() + 1)
    assert not {s.date for s in sessions} & blocked
    per_week: dict[date, int] = {}
    for s in sessions:
        per_week[week(s.date)] = per_week.get(week(s.date), 0) + s.minutes
    assert max(per_week.values()) <= budget, per_week
    # prerequisites are learned first
    learn: dict[str, list[date]] = {}
    for s in sessions:
        if s.kind == "learn":
            learn.setdefault(s.topics[0], []).append(s.date)
    for t in c.topics:
        for pre in t.prereq:
            if t.id in learn and pre in learn:
                assert max(learn[pre]) < min(learn[t.id]), (pre, t.id)
    # mock exams in the last 14 days, at least 4 days before the exam, then reviewed
    for i, s in enumerate(sessions):
        if s.kind == "mock-exam":
            assert (exam - s.date).days <= 14 and (exam - s.date).days >= 4
            assert sessions[i + 1].kind == "review"
            assert sessions[i + 1].tasks[0].refs == [s.tasks[0].ref]
    # the last day is for the cheat sheet
    assert sessions[-1].kind == ("cheatsheet" if c.cheatsheet.allowed else "review")
    assert (exam - sessions[-1].date).days >= 1
    return p


def test_sample_course_plan(course: Path, capsys):
    assert cli.main(["plan", str(course), "--from", "2026-10-29"]) == 0
    out = capsys.readouterr().out
    assert "wrote " in out and "mock exam probeklausur-1 on 2027-02-" in out
    p = check_constraints(course, "2026-10-29")
    kinds = {s.kind for s in p.sessions}
    assert {"learn", "review", "mixed", "mock-exam", "cheatsheet", "buffer"} <= kinds
    assert [s.kind for s in p.sessions].count("mock-exam") == 1
    assert p.generated.isoformat() == "2026-10-29" and p.exam_date.isoformat() == "2027-02-15"
    # every topic is read first, its exercises come from easy to hard
    first = [s for s in p.sessions if s.kind == "learn"]
    reads = [t.ref for s in first for t in s.tasks if t.do == "read"]
    assert reads == ["topic:spannungsteiler", "topic:wechselstrom", "topic:rc-filter"]
    text = (course / "plan.yaml").read_text()
    assert text.startswith("# yaml-language-server: $schema=") or "schema: 1" in text


def test_spaced_repeats_follow_learning(course: Path):
    make(course)
    p = load(course)
    last = {}
    for s in p.sessions:
        if s.kind == "learn":
            last[s.topics[0]] = s.date
    for topic, day in last.items():
        reviews = [
            s.date
            for s in p.sessions
            if s.date > day and any(t.do == "review" and t.topic == topic for t in s.tasks)
        ]
        assert reviews, topic
        # the first review comes the day after or at the next session
        nxt = min(s.date for s in p.sessions if s.date > day)
        assert reviews[0] == nxt


def test_regenerating_is_stable(course: Path, tmp_path: Path):
    make(course)
    first = (course / "plan.yaml").read_bytes()
    make(course)
    assert (course / "plan.yaml").read_bytes() == first
    # the same inputs in another copy give the same bytes
    other = tmp_path / "other" / "sample-course"
    shutil.copytree(course, other)
    (other / "plan.yaml").write_bytes((SAMPLE / "plan.yaml").read_bytes())
    make(other)
    assert (other / "plan.yaml").read_bytes() == first


def test_goals_are_kept_for_unchanged_sessions(course: Path):
    (course / "plan.yaml").unlink()
    make(course)
    text = (course / "plan.yaml").read_text()
    text = text.replace(
        "    kind: buffer\n", "    kind: buffer\n    goal: 'Puffer'\n    note: 'frei'\n"
    )
    (course / "plan.yaml").write_text(text)
    result = make(course)
    p = load(course)
    buffer = next(s for s in p.sessions if s.kind == "buffer")
    assert (buffer.goal, buffer.note) == ("Puffer", "frei")
    assert buffer.id not in result["goals_missing"]
    assert len(result["goals_missing"]) == len(p.sessions) - 1


@pytest.mark.parametrize("hours", [1, 2, 4, 6, 9, 15, 30])
@pytest.mark.parametrize("start", ["2026-10-29", "2026-12-28", "2027-01-20", "2027-02-08"])
def test_constraints_hold_for_any_budget(course: Path, hours: int, start: str):
    set_study(
        course,
        f"study: {{start: 2026-11-02, hours_per_week: {hours}, "
        "blocked: ['2026-12-21..2027-01-06']}",
    )
    _, found = plan.run(course, start=start)
    assert not [f for f in found if f.is_error]
    assert {f.code for f in found} <= {"SK-PLAN-BUDGET"}
    p = load(course)
    exam = date(2027, 2, 15)
    budget = hours * 60
    per_week: dict[date, int] = {}
    for s in p.sessions:
        per_week[week(s.date)] = per_week.get(week(s.date), 0) + s.minutes
        assert s.date < exam and s.date.isoformat() >= start
    assert max(per_week.values()) <= budget
    assert p.sessions[-1].kind == "cheatsheet"


def test_weekly_split_follows_hours(course: Path):
    set_study(course, "study: {start: 2026-11-02, hours_per_week: 8, blocked: []}")
    result = make(course)
    assert result["per_week"] == 4 and result["minutes"] == 120
    assert result["weekdays"] == ["Mon", "Tue", "Thu", "Sat"]
    assert result["max_week_minutes"] <= 480


def test_mock_exam_longer_than_budget_warns(course: Path):
    set_study(course, "study: {start: 2026-11-02, hours_per_week: 2, blocked: []}")
    result, found = plan.run(course, start="2026-10-29")
    assert any(f.code == "SK-PLAN-BUDGET" and "mock exam" in f.message for f in found)
    mock = next(s for s in result["plan"] if s["kind"] == "mock-exam")
    assert mock["minutes"] == 120


def test_focus_and_weight_share_the_learning(course: Path):
    result = make(course)
    learn = result["learn"]
    # rc-filter has the largest weight and is the focus topic; never more sessions than
    # exercises
    assert learn["rc-filter"] >= max(learn["wechselstrom"], learn["spannungsteiler"])
    assert learn["rc-filter"] <= 6


def test_skipped_topics_get_no_sessions(course: Path):
    path = course / "course.yaml"
    path.write_text(path.read_text().replace("skip: []", "skip: [wechselstrom]"))
    make(course)
    p = load(course)
    assert not any("wechselstrom" in s.topics for s in p.sessions)


def test_unknown_exam_date_plans_twelve_weeks(course: Path):
    path = course / "course.yaml"
    path.write_text(path.read_text().replace("date: 2027-02-15", "date: null"))
    result, found = plan.run(course, start="2026-11-02")
    assert [(f.code, f.severity) for f in found] == [("SK-PLAN-DATE", "warning")]
    p = load(course)
    assert p.exam_date is None
    assert result["end"] == "2027-01-24"


def test_refuses_to_plan_after_the_exam(course: Path, capsys):
    assert cli.main(["plan", str(course), "--from", "2027-02-15"]) == 1
    assert "SK-PLAN-DATE" in capsys.readouterr().err
    assert (course / "plan.yaml").read_bytes() == (SAMPLE / "plan.yaml").read_bytes()


def test_needs_study_settings(course: Path, capsys):
    path = course / "course.yaml"
    path.write_text(re.sub(r"^study: .*\n", "", path.read_text(), flags=re.MULTILINE))
    assert cli.main(["plan", str(course)]) == 1
    assert "SK-PLAN-STUDY" in capsys.readouterr().err


def test_dry_run_and_json(course: Path, capsys):
    before = (course / "plan.yaml").read_bytes()
    assert cli.main(["plan", str(course), "--from", "2026-10-29", "--dry-run", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and not out["written"] and out["sessions"] == len(out["plan"])
    assert (course / "plan.yaml").read_bytes() == before


def test_the_written_plan_passes_validate(course: Path, denylist: Path):
    make(course)
    config = validate.Config(denylist=denylist, katex=False, figures=False, pdf=False, site=False)
    report = validate.validate([course], config=config)
    assert report.findings == [], [f.format() for f in report.findings]


# --- replanning -------------------------------------------------------------------------------


def done(course: Path, ids: list[str], extra: dict | None = None) -> None:
    items = {f"plan:{i}": {"done": True} for i in ids}
    items.update(extra or {})
    path = course.parent / "export.json"
    path.write_text(
        json.dumps(
            {
                "schema": "studykit-progress/1",
                "course": "sample-course",
                "exported_at": "2026-12-01T10:00:00.000Z",
                "items": items,
            }
        )
    )
    assert progress.import_file(course, path)[1] == []


def test_replanning_keeps_done_sessions(course: Path):
    make(course)
    before = {s.id: s for s in load(course).sessions}
    learn_st = [
        i for i, s in before.items() if s.kind == "learn" and s.topics[0] == "spannungsteiler"
    ]
    finished = [*learn_st, "s-2026-11-11-a"]
    done(course, finished)
    result = make(course, start="2026-12-01")
    after = {s.id: s for s in load(course).sessions}
    for sid in finished:
        assert after[sid] == before[sid]
    assert sorted(result["kept"]) == sorted(finished)
    # nothing new before the first day; undone past sessions are gone
    assert all(s.date.isoformat() >= "2026-12-01" for i, s in after.items() if i not in finished)
    # spannungsteiler was learned completely: no new learning session, no new reading
    new = [s for i, s in after.items() if i not in finished]
    assert not any(s.kind == "learn" and s.topics[0] == "spannungsteiler" for s in new)
    assert "spannungsteiler" in result["learned_before"]
    # replanning again with the same progress is stable
    text = (course / "plan.yaml").read_bytes()
    make(course, start="2026-12-01")
    assert (course / "plan.yaml").read_bytes() == text


def test_replanning_skips_solved_exercises(course: Path):
    make(course)
    done(
        course,
        [],
        {
            "ex:ex-rc-tp-grenzfrequenz": {
                "h": "12345678",
                "hints": 0,
                "answer_ok": True,
                "rating": "solved",
                "box": 2,
                "due": "2026-12-04",
            }
        },
    )
    make(course, start="2026-11-20")
    learn_refs = [
        r for s in load(course).sessions if s.kind == "learn" for t in s.tasks for r in t.refs
    ]
    assert "ex:ex-rc-tp-grenzfrequenz" not in learn_refs
    assert "ex:ex-rc-tp-bode" in learn_refs


def test_weak_topics_come_first_in_practice(course: Path):
    def mc(topic: str, n: int, score: float) -> dict:
        return {
            f"mc:mc-{topic}-{i:03d}": {
                "h": "12345678",
                "box": 1,
                "due": "2027-01-10",
                "attempts": [
                    {
                        "t": f"2026-12-0{i}T10:00:00.000Z",
                        "chosen": ["A"],
                        "score": score,
                        "conf": "unsure",
                        "ms": 1,
                    }
                ],
            }
            for i in range(1, n + 1)
        }

    make(course)
    all_learn = [s.id for s in load(course).sessions if s.kind == "learn"]
    done(
        course,
        all_learn,
        {**mc("spannungsteiler", 5, 0), **mc("rc-filter", 5, 1), **mc("wechselstrom", 5, 1)},
    )
    make(course, start="2027-01-07")
    practice = [s for s in load(course).sessions if s.kind == "mixed"]
    assert practice[0].topics[0] == "spannungsteiler"
    firsts = [s.topics[0] for s in practice]
    assert firsts.count("spannungsteiler") >= max(firsts.count("wechselstrom"), 1)
