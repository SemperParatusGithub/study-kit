"""`studykit plan <course>`: the deterministic study-plan scheduler (docs/architecture.md §2.9).

The same inputs (course.yaml, the course's exercises, MC banks and mock exams, the progress
in `progress/`, the old `plan.yaml` and the first day) always give the same `plan.yaml`,
byte for byte. Claude writes only the `goal` and `note` text afterwards.

How sessions are placed:

1. **Days.** From the first day (`--from`, else today; never before `study.start`) to the
   day before the exam. `study.hours_per_week` gives the weekly budget; it is split into
   n = round(budget / 120 min) sessions (1 to 6) on fixed weekdays (1: Sat; 2: Mon, Thu;
   3: Mon, Wed, Sat; 4: Mon, Tue, Thu, Sat; 5: Mon to Fri; 6: Mon to Sat) of
   budget / n minutes, rounded down to 15. Blocked periods have no sessions. The day
   before the exam always has one.
2. **The last 14 days.** The day before the exam is for the cheat sheet (a review of every
   topic when the exam allows none). Mock exams (`targets.mock_exams`, at most the mock
   exams the course has and that were not taken yet) take exam duration + 30 minutes and are
   spread over the last 14 days, the last one at least 4 days before the exam; the session
   after each one reviews it. The session before the cheat-sheet day is a final MC round
   over every topic. The last session before these 14 days is a buffer.
3. **Budget.** No calendar week (Monday to Sunday) has more minutes than the weekly budget:
   in a week with a mock exam, a done session or the extra cheat-sheet day the other
   sessions get shorter, down to 45 minutes; below that the least important one is dropped
   (buffer, then practice, from the latest).
4. **Learning.** Topics that are not skipped are learned one after the other in
   prerequisite order (teaching order among those that are free). The learning sessions
   take 60 % of the sessions before the last 14 days (at least one per topic), shared out in
   proportion to weight * mean exercise difficulty (times 1.5 for focus topics), and never
   more than the topic has exercises left to learn. A topic's
   first session reads its summary; its exercises are spread over its sessions from easy to
   hard; each session ends with MC practice of the topic.
5. **Spaced repeats.** A topic is reviewed 1, 3 and 7 days after its last learning session
   (in the first session on or after that day): a review task joins a learning session, or a
   free session becomes a review (review plus MC practice).
6. **Practice.** The remaining sessions practise learned topics in a smooth weighted round
   robin by the same shares, multiplied by 1 + 3 * (1 - accuracy) where `progress/` has
   answers (lib/stats.ts accuracy), so weak topics come up first and most often: two
   exercises (unsolved and harder first) and MC practice of one topic, and a review of a
   second.

**Replanning** keeps every session that `progress/` marks done, wherever it lies, and
plans the rest anew from the first day. A topic all of whose learning sessions are done is
not learned again; one with some done is continued without reading the summary again, and
exercises already solved or in a done session are left out of its learning sessions. A new
session keeps the `goal` and `note` of the old session with the same id when its kind,
topics and tasks are unchanged; the others need a new goal (listed in the output).
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from datetime import date, tzinfo
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from studykit import content, model, progress, tools, yamlio
from studykit.findings import Finding

TARGET_MINUTES = 120
MIN_MINUTES = 45
MOCK_EXTRA = 30
LEARN_SHARE = 0.6
FINAL_DAYS = 14
MOCK_LAST = 4  # the last mock exam is at least this many days before the exam
REVIEW_OFFSETS = (1, 3, 7)
FOCUS_FACTOR = 1.5
MC_COUNT = 10
PLACEHOLDER_DAYS = 84
DEFAULT_DIFFICULTY = 2.0
WEAK_FACTOR = 4.0
WEEKDAYS = {
    1: (5,),
    2: (0, 3),
    3: (0, 2, 5),
    4: (0, 1, 3, 5),
    5: (0, 1, 2, 3, 4),
    6: (0, 1, 2, 3, 4, 5),
}
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
# dropped first when a week is over budget
DROP_ORDER = ("buffer", "regular", "final-mc", "mock-review")


def weakness(accuracy: float | None) -> float:
    """How much more a topic is practised: 1 without answers or at full accuracy, up to
    WEAK_FACTOR at none."""
    return 1.0 if accuracy is None else 1 + (WEAK_FACTOR - 1) * (1 - accuracy)


def half_up(x: float) -> int:
    return math.floor(x + 0.5)


@dataclass
class Slot:
    date: str
    role: str = "regular"  # regular | mock | mock-review | final-mc | cheatsheet | buffer
    minutes: int = 0
    exam: str | None = None
    learn: str | None = None
    learn_index: int = 0
    reviews: list[str] = field(default_factory=list)
    session: dict | None = None


@dataclass
class Inputs:
    course: model.Course
    info: progress.CourseInfo
    items: dict
    start: str
    generated: str
    old: list[dict]
    kept: list[dict]
    course_loc: tuple[str, int, int] = ("course.yaml", 1, 1)


def _ranges(blocked: list[str]) -> set[str]:
    days: set[str] = set()
    for spec in blocked:
        first, _, last = spec.partition("..")
        d, end = date.fromisoformat(first), date.fromisoformat(last or first)
        while d <= end:
            days.add(d.isoformat())
            d = date.fromordinal(d.toordinal() + 1)
    return days


def _week(day: str) -> str:
    d = date.fromisoformat(day)
    return date.fromordinal(d.toordinal() - d.weekday()).isoformat()


def topo_order(topics: list[progress.TopicInfo]) -> list[progress.TopicInfo]:
    """Prerequisites first; among the topics that are free, teaching order."""
    ids = {t.id for t in topics}
    done: set[str] = set()
    out: list[progress.TopicInfo] = []
    rest = list(topics)
    while rest:
        for t in rest:
            if all(p in done or p not in ids for p in t.prereq):
                out.append(t)
                done.add(t.id)
                rest.remove(t)
                break
        else:  # a cycle (validate reports it): keep teaching order
            out.extend(rest)
            break
    return out


def _share(t: progress.TopicInfo, info: progress.CourseInfo) -> float:
    diffs = [
        e["difficulty"] for e in info.exercises.values() if e["topic"] == t.id and e["difficulty"]
    ]
    mean_diff = progress.mean([float(d) for d in diffs]) or DEFAULT_DIFFICULTY
    return (t.weight or 0) * mean_diff * (FOCUS_FACTOR if t.focus else 1)


def allocate(total: int, shares: list[float]) -> list[int]:
    """`total` sessions over topics in proportion to `shares`, at least one each
    (largest remainder; ties go to the earlier topic)."""
    n = len(shares)
    if n == 0:
        return []
    if total <= n:
        return [1 if i < total else 0 for i in range(n)]
    whole = sum(shares) or 1.0
    quota = [s / whole * total for s in shares]
    alloc = [max(1, math.floor(q)) for q in quota]
    while sum(alloc) < total:
        i = max(range(n), key=lambda k: (quota[k] - alloc[k], -k))
        alloc[i] += 1
    while sum(alloc) > total:
        candidates = [k for k in range(n) if alloc[k] > 1]
        i = min(candidates, key=lambda k: (quota[k] - alloc[k], -k))
        alloc[i] -= 1
    return alloc


def _chunks(items: list[str], n: int) -> list[list[str]]:
    q, r = divmod(len(items), n)
    out, i = [], 0
    for k in range(n):
        size = q + (1 if k < r else 0)
        out.append(items[i : i + size])
        i += size
    return out


class RoundRobin:
    """Smooth weighted round robin: deterministic, each topic in proportion to its weight."""

    def __init__(self, weights: dict[str, float], order: list[str]):
        self.weights = weights
        self.order = order
        self.current = dict.fromkeys(order, 0.0)

    def pick(self, eligible: list[str], exclude: str | None = None) -> str | None:
        pool = [t for t in self.order if t in eligible and t != exclude]
        if not pool:
            return None
        total = 0.0
        for t in pool:
            self.current[t] += self.weights[t]
            total += self.weights[t]
        best = max(pool, key=lambda t: (self.current[t], -self.order.index(t)))
        self.current[best] -= total
        return best


def _session_dict(s: model.Session) -> dict:
    tasks = []
    for t in s.tasks:
        task: dict[str, Any] = {"do": t.do}
        if t.ref is not None:
            task["ref"] = t.ref
        if t.refs:
            task["refs"] = list(t.refs)
        if t.topic is not None:
            task["topic"] = t.topic
        if t.count is not None:
            task["count"] = t.count
        tasks.append(task)
    out: dict[str, Any] = {
        "id": s.id,
        "date": s.date.isoformat(),
        "minutes": s.minutes,
        "kind": s.kind,
        "topics": list(s.topics),
    }
    if s.goal is not None:
        out["goal"] = s.goal
    if s.note is not None:
        out["note"] = s.note
    out["tasks"] = tasks
    return out


def schedule(inp: Inputs) -> tuple[list[dict], dict, list[Finding]]:
    """The sessions of the new plan (kept ones included), facts for the output, warnings."""
    course, info = inp.course, inp.info
    warn: list[tuple[list[str | int], str, str]] = []  # (yaml loc, message, fix)
    study = course.study
    assert study is not None
    budget = half_up(study.hours_per_week * 60)
    n_week = min(6, max(1, half_up(budget / TARGET_MINUTES)))
    base = budget // n_week // 15 * 15 or budget // n_week
    weekdays = WEEKDAYS[n_week]
    start = max(inp.start, study.start.isoformat()) if study.start else inp.start
    placeholder = info.exam_date is None
    end = info.exam_date or progress.add_days(start, PLACEHOLDER_DAYS)
    last_day = progress.add_days(end, -1)
    final_start = progress.add_days(end, -FINAL_DAYS)
    blocked = _ranges(study.blocked)
    occupied = {s["date"] for s in inp.kept}
    skipped = {t.id for t in info.topics if t.skip}
    topics = [t for t in info.topics if not t.skip]
    banks = {t.id: len(t.mc) for t in info.topics}

    days = []
    d = start
    while d <= last_day:
        wd = date.fromisoformat(d).weekday()
        if d not in blocked and d not in occupied and (wd in weekdays or d == last_day):
            days.append(d)
        d = progress.add_days(d, 1)
    slots = [Slot(day, minutes=base) for day in days]
    facts: dict[str, Any] = {
        "start": start,
        "end": last_day,
        "budget": budget,
        "per_week": n_week,
        "minutes": base,
        "weekdays": [DAY_NAMES[w] for w in weekdays],
        "placeholder": placeholder,
    }
    if not slots:
        return list(inp.kept), facts, []
    slots[-1].role = "cheatsheet"

    # mock exams
    taken = {
        t["ref"][5:]
        for s in inp.kept
        for t in s["tasks"]
        if t["do"] == "exam" and t.get("ref", "").startswith("exam:")
    }
    taken |= {
        e.id for e in info.exams if progress.exam_summary(inp.items.get(f"exam:{e.id}"))["count"]
    }
    available = [e for e in info.exams if e.id not in taken]
    wanted = course.targets.mock_exams
    if len(info.exams) < wanted:
        warn.append(
            (
                ["targets", "mock_exams"],
                f"targets.mock_exams is {wanted}, but the course has {len(info.exams)} mock "
                "exam(s); the plan schedules those",
                "write the missing mock exams (`/regenerate <course> exams`) and plan again",
            )
        )
    k = min(max(0, wanted - len(taken)), len(available))
    last_mock = progress.add_days(end, -MOCK_LAST)
    span = max(0, progress.days_between(final_start, last_mock))
    mocks: list[dict] = []
    for i in range(k):
        exam = available[i]
        target = progress.add_days(final_start, (i + 1) * span // (k + 1))
        free = [s for s in slots if s.role == "regular" and s.date <= last_mock]
        after = [s for s in free if s.date >= target]
        slot = after[0] if after else (free[-1] if free else None)
        if slot is None:
            warn.append(
                (
                    ["exam", "date"],
                    f"no session is left for mock exam {exam.id} before the exam",
                    "start earlier (--from) or raise study.hours_per_week",
                )
            )
            continue
        slot.role, slot.exam = "mock", exam.id
        minutes = exam.duration_min + MOCK_EXTRA
        if minutes > budget:
            warn.append(
                (
                    ["study", "hours_per_week"],
                    f"mock exam {exam.id} needs {minutes} min, more than the weekly budget of "
                    f"{budget} min; it gets {budget} min",
                    "raise study.hours_per_week",
                )
            )
            minutes = budget
        slot.minutes = minutes
        mocks.append({"exam": exam.id, "date": slot.date})
        later = [s for s in slots if s.date > slot.date and s.role == "regular"]
        if later:
            later[0].role, later[0].exam = "mock-review", exam.id
    if len(slots) > 1 and slots[-2].role == "regular" and slots[-2].date >= final_start:
        slots[-2].role = "final-mc"
    before_final = [s for s in slots if s.role == "regular" and s.date < final_start]
    if len(before_final) >= 4:
        before_final[-1].role = "buffer"

    # weekly budget
    kept_minutes: dict[str, int] = {}
    for s in inp.kept:
        kept_minutes[_week(s["date"])] = kept_minutes.get(_week(s["date"]), 0) + s["minutes"]
    weeks: dict[str, list[Slot]] = {}
    for s in slots:
        weeks.setdefault(_week(s.date), []).append(s)
    dropped: set[int] = set()
    for week, group in weeks.items():
        fixed = kept_minutes.get(week, 0) + sum(s.minutes for s in group if s.role == "mock")
        flex = [s for s in group if s.role != "mock"]
        while flex:
            remaining = budget - fixed
            per = min(base, max(0, remaining) // len(flex) // 15 * 15)
            if per >= MIN_MINUTES or (len(flex) == 1 and flex[0].role == "cheatsheet"):
                for s in flex:
                    s.minutes = per if per > 0 else max(0, remaining)
                break
            victim = None
            for role in DROP_ORDER:
                pool = [s for s in flex if s.role == role]
                if pool:
                    victim = pool[-1]
                    break
            if victim is None:
                victim = flex[-1]
            flex.remove(victim)
            dropped.add(id(victim))
    slots = [s for s in slots if id(s) not in dropped and s.minutes > 0]
    if fixed_over := [w for w in weeks if kept_minutes.get(w, 0) > budget]:
        warn.append(
            (
                ["study", "hours_per_week"],
                f"done sessions already exceed the weekly budget in the week(s) of "
                f"{', '.join(fixed_over)}",
                "nothing to do; the plan adds no session in those weeks",
            )
        )

    # learning
    done_ex = {
        r[3:]
        for s in inp.kept
        for t in s["tasks"]
        for r in t.get("refs", [])
        if r.startswith("ex:")
    }
    done_ex |= {
        k[3:] for k, e in inp.items.items() if k.startswith("ex:") and e.get("rating") == "solved"
    }
    old_learn: dict[str, int] = {}
    done_learn: dict[str, int] = {}
    for s in inp.old:
        if s["kind"] == "learn" and s["topics"]:
            old_learn[s["topics"][0]] = old_learn.get(s["topics"][0], 0) + 1
    for s in inp.kept:
        if s["kind"] == "learn" and s["topics"]:
            done_learn[s["topics"][0]] = done_learn.get(s["topics"][0], 0) + 1
    learned = {t for t, n in done_learn.items() if n >= old_learn.get(t, 0)}
    to_learn = [t for t in topo_order(topics) if t.id not in learned]
    regular = [s for s in slots if s.role == "regular"]
    pre = [s for s in regular if s.date < final_start]
    total = min(len(regular), max(len(to_learn), half_up(LEARN_SHARE * len(pre))))
    if len(regular) < len(to_learn):
        missing = [t.id for t in to_learn[len(regular) :]]
        warn.append(
            (
                ["study", "hours_per_week"],
                f"too few sessions to learn every topic: {', '.join(missing)} get no learning "
                "session",
                "start earlier (--from), raise study.hours_per_week or skip topics",
            )
        )
    todo = {
        t.id: sorted(
            (e for e in t.ex if e not in done_ex),
            key=lambda e: (info.exercises[e]["difficulty"] or 0, e),
        )
        for t in to_learn
    }
    # a topic never gets more learning sessions than exercises left to learn with
    alloc = [
        min(n, max(1, len(todo[t.id])))
        for t, n in zip(to_learn, allocate(total, [_share(t, info) for t in to_learn]), strict=True)
    ]
    learn_count: dict[str, int] = {}
    idx = 0
    last_learn: dict[str, str] = {}
    for t, n in zip(to_learn, alloc, strict=True):
        learn_count[t.id] = n
        for j in range(n):
            if idx >= len(regular):
                break
            slot = regular[idx]
            slot.learn, slot.learn_index = t.id, j
            last_learn[t.id] = slot.date
            idx += 1

    # spaced repeats
    cheatsheet_day = next((s.date for s in slots if s.role == "cheatsheet"), end)
    for t in to_learn:
        if t.id not in last_learn:
            continue
        for off in REVIEW_OFFSETS:
            target = progress.add_days(last_learn[t.id], off)
            for s in regular:
                if (
                    s.date >= target
                    and s.date < cheatsheet_day
                    and s.learn != t.id
                    and t.id not in s.reviews
                    and len(s.reviews) < 2
                ):
                    s.reviews.append(t.id)
                    break

    # sessions
    accuracy = {
        st["id"]: st["accuracy"]
        for st in progress.topic_stats(inp.items, info.topics, start, info.exam_date)
    }
    weights = {t.id: max(_share(t, info), 1e-9) * weakness(accuracy[t.id]) for t in topics}
    rr = RoundRobin(weights, [t.id for t in topics])
    rotation = {
        t.id: sorted(
            t.ex,
            key=lambda e: (
                e in done_ex,
                -(info.exercises[e]["difficulty"] or 0),
                e,
            ),
        )
        for t in topics
    }
    cursor = dict.fromkeys(rotation, 0)

    def mc(topic: str, count: int = MC_COUNT) -> list[dict]:
        n = min(count, banks.get(topic, 0))
        return [{"do": "mc", "topic": topic, "count": n}] if n else []

    def review_of(topic: str) -> dict:
        return {"do": "review", "topic": topic}

    def next_exercises(topic: str, n: int = 2) -> list[str]:
        pool = rotation.get(topic, [])
        if not pool:
            return []
        out = []
        for _ in range(min(n, len(pool))):
            out.append(pool[cursor[topic] % len(pool)])
            cursor[topic] += 1
        return out

    partial = {t for t in done_learn if t not in learned}
    to_learn_ids = {t.id for t in to_learn}
    chunks: dict[str, list[list[str]]] = {}
    for t in to_learn:
        if learn_count.get(t.id):
            chunks[t.id] = _chunks(todo[t.id], learn_count[t.id])

    topic_order = [t.id for t in info.topics]
    all_topics = [t.id for t in topics]
    exam_topics = {
        e.id: [t for t in topic_order if any(task.topic == t for task in e.tasks)]
        for e in info.exams
    }
    sessions = []
    for s in slots:
        topics_: list[str] = []
        tasks: list[dict] = []
        if s.role == "mock":
            kind = "mock-exam"
            tasks = [{"do": "exam", "ref": f"exam:{s.exam}"}]
        elif s.role == "mock-review":
            kind = "review"
            topics_ = [t for t in exam_topics.get(s.exam or "", []) if t not in skipped]
            topics_ = topics_ or all_topics
            tasks = [{"do": "review", "refs": [f"exam:{s.exam}"]}]
            tasks += [review_of(t) for t in topics_]
        elif s.role == "final-mc":
            kind = "review"
            topics_ = all_topics
            tasks = [task for t in topics_ for task in mc(t)] or [review_of(t) for t in topics_]
        elif s.role == "cheatsheet":
            if course.cheatsheet.allowed:
                kind, tasks = "cheatsheet", [{"do": "cheatsheet"}]
            else:
                kind, topics_ = "review", all_topics
                tasks = [review_of(t) for t in topics_]
        elif s.role == "buffer":
            kind = "buffer"
        elif s.learn:
            kind = "learn"
            t = s.learn
            topics_ = [t]
            if s.learn_index == 0 and t not in partial and t in info.summaries:
                tasks.append({"do": "read", "ref": f"topic:{t}"})
            chunk = chunks[t][s.learn_index]
            if chunk:
                tasks.append({"do": "exercises", "refs": [f"ex:{e}" for e in chunk]})
            tasks += mc(t, 5 if tasks and tasks[0]["do"] == "read" else MC_COUNT)
            if not tasks:
                tasks.append(review_of(t))
            for r in s.reviews:
                topics_.append(r)
                tasks.append(review_of(r))
        elif s.reviews:
            kind = "review"
            topics_ = list(s.reviews)
            for r in s.reviews:
                tasks.append(review_of(r))
                tasks += mc(r)
        else:
            eligible = [
                t
                for t in all_topics
                if t not in to_learn_ids or (t in last_learn and last_learn[t] < s.date)
            ]
            p = rr.pick(eligible)
            if p is None:
                kind = "buffer"
            else:
                kind = "mixed"
                topics_ = [p]
                ex = next_exercises(p)
                if ex:
                    tasks.append({"do": "exercises", "refs": [f"ex:{e}" for e in ex]})
                tasks += mc(p)
                if not tasks:
                    tasks.append(review_of(p))
                q = rr.pick(eligible, exclude=p)
                if q is not None:
                    topics_.append(q)
                    tasks.append(review_of(q))
        sessions.append(
            {
                "date": s.date,
                "minutes": s.minutes,
                "kind": kind,
                "topics": topics_,
                "tasks": tasks,
            }
        )

    # ids, goals and notes
    used = {s["id"] for s in inp.kept}
    old = {s["id"]: s for s in inp.old}
    goals_kept = 0
    out = []
    for s in sessions:
        letter = "a"
        while f"s-{s['date']}-{letter}" in used:
            letter = chr(ord(letter) + 1)
        sid = f"s-{s['date']}-{letter}"
        used.add(sid)
        session: dict[str, Any] = {"id": sid, **s}
        prev = old.get(sid)
        if prev and all(prev[k] == s[k] for k in ("kind", "topics", "tasks")):
            for key in ("goal", "note"):
                if prev.get(key) is not None:
                    session[key] = prev[key]
            goals_kept += "goal" in session
        out.append(session)
    out.extend(inp.kept)
    out.sort(key=lambda s: (s["date"], s["id"]))
    facts.update(
        {
            "mock_exams": mocks,
            "learn": {t: learn_count[t] for t in learn_count if learn_count[t]},
            "learned_before": sorted(learned, key=topic_order.index),
            "goals_kept": goals_kept,
            "dropped": len(dropped),
        }
    )
    path, line, col = inp.course_loc
    findings = [
        Finding(path, line, col, "SK-PLAN-BUDGET", message, fix, "warning")
        for _loc, message, fix in warn
    ]
    return out, facts, findings


# --- YAML ----------------------------------------------------------------------------------


def _q(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _task_yaml(task: dict) -> str:
    parts = [f"do: {task['do']}"]
    if "ref" in task:
        parts.append(f"ref: {_q(task['ref'])}")
    if "refs" in task:
        parts.append("refs: [" + ", ".join(_q(r) for r in task["refs"]) + "]")
    if "topic" in task:
        parts.append(f"topic: {task['topic']}")
    if "count" in task:
        parts.append(f"count: {task['count']}")
    return "{" + ", ".join(parts) + "}"


def render(plan: dict, schema_ref: str | None) -> str:
    lines = []
    if schema_ref:
        lines.append(f"# yaml-language-server: $schema={schema_ref}")
    lines += [
        "schema: 1",
        f"generated: {plan['generated']}",
        f"exam_date: {plan['exam_date'] or 'null'}",
    ]
    if not plan["sessions"]:
        lines.append("sessions: []")
        return "\n".join(lines) + "\n"
    lines.append("sessions:")
    for s in plan["sessions"]:
        lines += [
            f"  - id: {s['id']}",
            f"    date: {s['date']}",
            f"    minutes: {s['minutes']}",
            f"    kind: {s['kind']}",
        ]
        if s["topics"]:
            lines.append(f"    topics: [{', '.join(s['topics'])}]")
        for key in ("goal", "note"):
            if s.get(key) is not None:
                lines.append(f"    {key}: {_q(s[key])}")
        if s["tasks"]:
            lines.append("    tasks:")
            lines += [f"      - {_task_yaml(t)}" for t in s["tasks"]]
        else:
            lines.append("    tasks: []")
    return "\n".join(lines) + "\n"


def check(text: str, path: str, tree: content.CourseTree) -> list[Finding]:
    """The written plan reads back, validates and refers only to what exists."""
    doc = yamlio.load(text, path=path)
    found = list(doc.findings)
    if not doc.ok:
        return found
    try:
        plan = model.Plan.model_validate(doc.data, context=tree.context)
    except ValidationError as exc:
        return found + content.schema_findings(doc, exc)
    targets = {
        "ex": set(tree.ids("exercise")),
        "topic": set(tree.topics),
        "exam": set(tree.ids("exam")),
    }
    for i, s in enumerate(plan.sessions):
        for j, t in enumerate(s.tasks):
            for ref in [t.ref, *t.refs]:
                if ref is None:
                    continue
                scheme, _, ident = ref.partition(":")
                if scheme in targets and ident not in targets[scheme]:
                    line, col = doc.locate(["sessions", i, "tasks", j])
                    found.append(
                        Finding(
                            path,
                            line,
                            col,
                            "SK-REF-MISSING",
                            f"plan reference '{ref}' does not exist",
                            "a done session refers to a removed item; edit or delete it",
                        )
                    )
    return found


# --- command ---------------------------------------------------------------------------------


def _schema_ref(root: Path) -> str | None:
    repo = tools.repo_root().resolve()
    try:
        root.resolve().relative_to(repo)
    except ValueError:
        return None
    rel = os.path.relpath(repo / "schemas" / "plan.schema.json", root.resolve())
    return Path(rel).as_posix()


def run(
    root: Path,
    *,
    start: str | None = None,
    write: bool = True,
    tz: tzinfo | None = None,
) -> tuple[dict, list[Finding]]:
    tree = content.CourseTree(root)
    course_doc = tree.course_doc
    cpath = course_doc.display if course_doc else content.display_path(root / "course.yaml")

    def at(loc: list[str | int]) -> tuple[int, int]:
        return course_doc.yaml.locate(loc) if course_doc and course_doc.yaml else (1, 1)

    course = tree.model
    if course is None:
        found = course_doc.validated[1] if course_doc else []
        found = found or [
            Finding(cpath, 1, 1, "SK-PLAN-STUDY", "course.yaml does not validate", "run validate")
        ]
        return {}, found
    if course.study is None:
        return {}, [
            Finding(
                cpath,
                1,
                1,
                "SK-PLAN-STUDY",
                "course.yaml has no study settings, so the plan has no time budget",
                "add study: {start: YYYY-MM-DD, hours_per_week: 6, blocked: []}",
            )
        ]
    if half_up(course.study.hours_per_week * 60) < 15:
        return {}, [
            Finding(
                cpath,
                *at(["study", "hours_per_week"]),
                "SK-PLAN-STUDY",
                "study.hours_per_week gives less than 15 minutes a week",
                "set study.hours_per_week to the hours you can really study each week",
            )
        ]
    plan_doc = tree.get("plan.yaml")
    old: list[dict] = []
    if plan_doc is not None:
        yaml_found = plan_doc.yaml.findings if plan_doc.yaml else []
        if plan_doc.model is None:
            return {}, [f for f in yaml_found if f.is_error] + plan_doc.validated[1]
        old = [_session_dict(s) for s in plan_doc.model.sessions]
    generated = start or progress.today_local(tz)
    snap = progress.snapshot(root, generated, tz)
    if snap.findings:
        return {}, snap.findings
    kept = [s for s in old if progress.session_done(snap.items, s["id"])]
    info = snap.info
    # the plan follows course.yaml alone (the site falls back to the old plan's date)
    info.exam_date = course.exam.date.isoformat() if course.exam.date else None
    found: list[Finding] = []
    if info.exam_date is None:
        found.append(
            Finding(
                cpath,
                *at(["exam", "date"]),
                "SK-PLAN-DATE",
                "the exam date is unknown; the plan runs "
                f"{PLACEHOLDER_DAYS // 7} weeks and writes exam_date: null",
                "set exam.date in course.yaml as soon as it is known and plan again",
                "warning",
            )
        )
    elif generated >= info.exam_date:
        return {}, [
            Finding(
                cpath,
                *at(["exam", "date"]),
                "SK-PLAN-DATE",
                f"the plan would start on {generated}, but the exam is on {info.exam_date}",
                "plan from an earlier day (--from), or set the new exam date",
            )
        ]
    inp = Inputs(course, info, snap.items, generated, generated, old, kept, (cpath, *at(["study"])))
    sessions, facts, warns = schedule(inp)
    found += warns
    new = [s for s in sessions if s not in kept]
    if not new:
        found.append(
            Finding(
                cpath,
                *at(["study"]),
                "SK-PLAN-DATE",
                f"no free study day between {facts['start']} and the exam",
                "plan from an earlier day (--from), or shorten study.blocked",
            )
        )
        return {}, found
    plan = {
        "schema": 1,
        "generated": generated,
        "exam_date": info.exam_date,
        "sessions": sessions,
    }
    path = root / "plan.yaml"
    text = render(plan, _schema_ref(root))
    problems = check(text, content.display_path(path), tree)
    if problems:
        return {}, found + problems
    if write:
        path.write_text(text, "utf-8")
    kinds: dict[str, int] = {}
    for s in sessions:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    week_minutes: dict[str, int] = {}
    for s in sessions:
        week_minutes[_week(s["date"])] = week_minutes.get(_week(s["date"]), 0) + s["minutes"]
    result = {
        "course": tree.id,
        "file": content.display_path(path),
        "written": write,
        "generated": generated,
        "exam_date": info.exam_date,
        **facts,
        "sessions": len(sessions),
        "kept": [s["id"] for s in kept],
        "kinds": kinds,
        "max_week_minutes": max(week_minutes.values()),
        "goals_missing": [s["id"] for s in sessions if s not in kept and "goal" not in s],
        "plan": sessions,
    }
    return result, found


def format_text(r: dict, *, dry_run: bool = False) -> str:
    verb = "planned" if dry_run else "wrote"
    exam = f"exam {r['exam_date']}" if r["exam_date"] else "exam date unknown"
    lines = [
        f"{verb} {r['file']}: {r['sessions']} session(s) from {r['start']} to {r['end']} ({exam})",
        f"  {r['per_week']} session(s) of {r['minutes']} min a week ({', '.join(r['weekdays'])}), "
        f"at most {r['budget']} min a week (the busiest week has {r['max_week_minutes']})",
    ]
    learn = ", ".join(f"{t} {n}" for t, n in r["learn"].items())
    kinds = ", ".join(f"{n} {k}" for k, n in sorted(r["kinds"].items()))
    lines.append(f"  learning sessions: {learn or 'none'}; kinds: {kinds}")
    for m in r["mock_exams"]:
        lines.append(f"  mock exam {m['exam']} on {m['date']}")
    if r["kept"]:
        lines.append(f"  kept {len(r['kept'])} done session(s)")
    if r["goals_missing"]:
        lines.append(
            f"  {len(r['goals_missing'])} session(s) have no goal yet; write a one-line goal "
            "in the course language for each (studykit plan keeps it while the session "
            "stays the same)"
        )
    return "\n".join(lines)
