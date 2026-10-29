"""`studykit status <course>`: the study status `/study-status` prints (docs/architecture.md
§5.2).

Days left, plan adherence (missed sessions counted as the site's "behind schedule" banner
counts them: past sessions not ticked done), the next sessions, the weakest topics, reviews
due today and the last mock exam. It reads the same snapshot as `studykit progress report`
(`progress/state.json` plus the examiner's results, lib/stats.ts figures), so the numbers
match the report and, for the same answers, the site.

This is the student's status. The output-derived pipeline status of
`/register-new-subject` (§5.4, Phase 6) is a different thing.
"""

from __future__ import annotations

from datetime import tzinfo
from pathlib import Path

from studykit import progress
from studykit.findings import Finding

NEXT = 3


def _session(s: dict) -> dict:
    return {
        "id": s["id"],
        "date": s["date"],
        "kind": s["kind"],
        "minutes": s["minutes"],
        "topics": s["topics"],
        "goal": s["goal"],
    }


def study_status(
    root: Path, today: str | None = None, tz: tzinfo | None = None
) -> tuple[dict, list[Finding]]:
    snap = progress.snapshot(root, today, tz)
    if snap.findings:
        return {}, snap.findings
    info, items, today = snap.info, snap.items, snap.today
    exam = info.exam_date
    stats = progress.topic_stats(items, info.topics, today, exam, tz)
    by_id = {t.id: t for t in info.topics}
    sessions = info.sessions
    past = [s for s in sessions if s["date"] < today]
    behind = [s for s in past if not progress.session_done(items, s["id"])]
    done = [s for s in sessions if progress.session_done(items, s["id"])]

    last_mock = None
    for e in info.exams:
        last = progress.exam_summary(items.get(f"exam:{e.id}"))["last"]
        if last and (last_mock is None or last["started"] > last_mock["started"]):
            last_mock = {
                "exam": e.id,
                "title": e.title,
                "started": last["started"],
                "total": last["total"],
                "points": e.points,
                "pass_points": e.pass_points,
                "passed": last["total"] >= e.pass_points,
            }

    weak = [
        {"id": s["id"], "title": by_id[s["id"]].title, "accuracy": s["accuracy"]}
        for s in progress.weakest_topics(stats, info.topics)
    ]
    due_mc = progress.due_count(items, info.topics, today, exam, tz=tz)
    due_ex = progress.exercises_due(items, today, exam)
    state_at = snap.state["exported_at"]
    days_left = progress.days_between(today, exam) if exam else None

    c = info.id
    hints = []
    if not sessions:
        hints.append(f"no study plan: `studykit plan {c}` schedules one")
    elif behind:
        hints.append(
            f"{len(behind)} past session(s) not done: `studykit plan {c}` replans from today "
            "(done sessions and session goals are kept)"
        )
    if state_at == progress.EPOCH:
        hints.append(f"no browser progress imported yet: `/import-progress {c}`")
    if due_mc or due_ex:
        hints.append("reviews are due: the site's MC hub (mode Due) or `/examine " + c + " weak`")
    if exam and last_mock is None and info.exams and days_left is not None and days_left <= 14:
        hints.append(f"no mock exam taken yet, {days_left} day(s) before the exam")
    if exam is None:
        hints.append("the exam date is unknown: set exam.date in course.yaml")

    result = {
        "course": c,
        "title": info.title,
        "today": today,
        "exam_date": exam,
        "days_left": days_left,
        "mastery": progress.mastery(stats, info.topics),
        "plan": {
            "sessions": len(sessions),
            "done": len(done),
            "past": len(past),
            "behind": len(behind),
            "behind_ids": [s["id"] for s in behind],
            "next": [_session(s) for s in progress.upcoming_sessions(sessions, items, today, NEXT)],
        },
        "weak_topics": weak,
        "due": {"mc": due_mc, "exercises": due_ex},
        "last_mock": last_mock,
        "progress": {
            "state": None if state_at == progress.EPOCH else state_at,
            "examiner": len(snap.examiner),
        },
        "hints": hints,
    }
    return result, []


def format_text(r: dict) -> str:
    exam = (
        f"exam {r['exam_date']} in {r['days_left']} day(s)"
        if r["exam_date"]
        else "exam date unknown"
    )
    lines = [f"{r['course']} · {r['title']}: {exam}"]
    lines.append(
        f"mastery {progress.pct(r['mastery'])} · reviews due: {r['due']['mc']} MC, "
        f"{r['due']['exercises']} exercise(s)"
    )
    p = r["plan"]
    if p["sessions"]:
        behind = f", {p['behind']} behind ({', '.join(p['behind_ids'])})" if p["behind"] else ""
        lines.append(f"plan: {p['done']} of {p['sessions']} session(s) done{behind}")
    for s in p["next"]:
        topics = ", ".join(s["topics"]) or "-"
        goal = f": {s['goal']}" if s["goal"] else ""
        lines.append(f"  next {s['date']} {s['kind']} ({topics}) {s['minutes']} min{goal}")
    if r["weak_topics"]:
        weak = ", ".join(f"{t['title']} {progress.pct(t['accuracy'])}" for t in r["weak_topics"])
        lines.append(f"weakest topics: {weak}")
    m = r["last_mock"]
    if m:
        verdict = "passed" if m["passed"] else "not passed"
        lines.append(
            f"last mock exam: {m['title']} on {m['started'][:10]}, "
            f"{m['total']:g}/{m['points']:g} ({verdict})"
        )
    src = r["progress"]
    lines.append(
        f"progress as of {src['state'][:10] if src['state'] else 'never'} (browser export), "
        f"{src['examiner']} examiner result(s)"
    )
    lines.extend(f"hint: {h}" for h in r["hints"])
    return "\n".join(lines)
