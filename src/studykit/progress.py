"""Progress on the repository side (docs/architecture.md §2.11).

`studykit progress import|log|report`:

- **import** validates a browser export (`studykit-progress/1`, the document
  `site/src/lib/store.ts` writes), merges it into `progress/state.json` with the site's own
  union merge, and keeps a copy in `progress/browser/`.
- **log** appends examiner results to `progress/examiner.jsonl` (`model.ExaminerResult`).
- **report** writes `progress/mastery.json` and `progress/report.md`.

This module mirrors three site libraries line by line, and `tests/py/test_progress.py`
runs both on shared fixtures (`tests/fixtures/progress/`):

- `lib/leitner.ts`: boxes, intervals and the exam clamp;
- `lib/store.ts`: `merge` (attempts combined without duplicates, the schedule of the side
  with the later attempt, hint counts at their maximum, a correct answer check or a done
  session stays done);
- `lib/stats.ts`: accuracy (mean score of a topic's last 10 MC attempts), mastery (topic
  accuracies weighted by topic weight over the topics not skipped, unanswered topics count
  0), due reviews, misconceptions, exercise status, the plan's next and missed sessions.

Floating-point sums are plain left-to-right loops, as JavaScript's `reduce` adds them
(Python's `sum()` compensates rounding errors and would differ in the last bit). Days are
local calendar days, as the browser has them: an attempt's day is its timestamp in the
local time zone (`tz`, the system's by default).

Examiner MC results count as MC attempts in the report (and in `studykit status` and the
replanning of `studykit plan`): they are folded into the browser items as attempts with the
same Leitner step, so the build-time mastery on the site includes them until the browser
has answers of its own.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from studykit import content, model
from studykit.findings import Finding

SCHEMA = "studykit-progress/1"
MASTERY_SCHEMA = "studykit-mastery/1"
UNKNOWN_HASH = "00000000"
MAX_ATTEMPTS = 100
HINT_CAP = 1
RECENT = 10
EPOCH = "1970-01-01T00:00:00.000Z"

STATE = "state.json"
EXAMINER = "examiner.jsonl"
MASTERY = "mastery.json"
REPORT = "report.md"
BROWSER = "browser"

# --- lib/leitner.ts ---------------------------------------------------------------------

INTERVALS = (0, 1, 3, 7, 14, 30)
MAX_BOX = 5
ENTRY_BOX = 1
CLAMP_LIMIT_DAYS = 2
CLAMP_WINDOW_DAYS = 10
LONG_AGO = "0001-01-01"
DAY_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def is_day(value: Any) -> bool:
    if not isinstance(value, str) or not DAY_RE.match(value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def add_days(day: str, days: int) -> str:
    if not DAY_RE.match(day):
        raise ValueError(f"not a YYYY-MM-DD day: {day}")
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def days_between(a: str, b: str) -> int:
    """Whole days from `a` to `b` (positive when b is later)."""
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value


def clamp_box(box: Any) -> int | None:
    if not _is_num(box) or box in (float("inf"), float("-inf")):
        return None
    return min(MAX_BOX, max(0, int(box)))


def next_box(box: Any, score: float, conf: str) -> int:
    if score >= 1 - 1e-9:
        current = clamp_box(box)
        return min(MAX_BOX, (ENTRY_BOX if current is None else current) + 1)
    return 0 if conf == "sure" else ENTRY_BOX


def clamp_due(due: str, reviewed_on: str, exam_date: str | None) -> str:
    if not exam_date or not is_day(exam_date) or reviewed_on > exam_date:
        return due
    limit = add_days(exam_date, -CLAMP_LIMIT_DAYS)
    window_start = add_days(exam_date, -CLAMP_WINDOW_DAYS)
    if reviewed_on >= limit:
        return due if due > exam_date else add_days(exam_date, 1)
    if due <= limit:
        return due
    return window_start if reviewed_on < window_start else limit


def schedule(box: int, today: str, exam_date: str | None) -> str:
    b = clamp_box(box)
    interval = INTERVALS[ENTRY_BOX if b is None else b]
    return clamp_due(add_days(today, interval), today, exam_date)


def review(box: Any, score: float, conf: str, today: str, exam_date: str | None) -> dict:
    nxt = next_box(box, score, conf)
    return {"box": nxt, "due": schedule(nxt, today, exam_date), "misconception": nxt == 0}


def in_rest_days(today: str, exam_date: str | None) -> bool:
    if not exam_date or not is_day(exam_date):
        return False
    return add_days(exam_date, -CLAMP_LIMIT_DAYS) < today <= exam_date


def review_day_of(due: Any, box: Any) -> str | None:
    b = clamp_box(box)
    if not is_day(due) or b is None:
        return None
    return add_days(due, -INTERVALS[b])


def effective_due(due: Any, reviewed_on: Any, exam_date: str | None) -> str | None:
    if not is_day(due):
        return None
    return clamp_due(due, reviewed_on if is_day(reviewed_on) else LONG_AGO, exam_date)


def is_due(due: Any, reviewed_on: Any, today: str, exam_date: str | None) -> bool:
    if in_rest_days(today, exam_date):
        return False
    eff = effective_due(due, reviewed_on, exam_date)
    return eff is not None and eff <= today


# --- timestamps -------------------------------------------------------------------------

# lib/store.ts `time()`: what both `Date.parse` and `datetime.fromisoformat` read.
ISO_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$"
)


def site_time(value: Any) -> bool:
    """True for a timestamp the site keeps (lib/store.ts `time()`)."""
    if not isinstance(value, str) or not ISO_TIME_RE.match(value) or not is_day(value[:10]):
        return False
    try:
        _parse(value)
    except ValueError:
        return False
    return True


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace(" ", "T").replace("Z", "+00:00"))


def local_day(timestamp: str, tz: tzinfo | None = None) -> str:
    """The local calendar day of a timestamp, as `dayOf(new Date(t))` gives it in the
    browser: a date alone is UTC midnight, a date-time without offset is local time."""
    dt = _parse(timestamp)
    if len(timestamp) == 10:
        dt = dt.replace(tzinfo=UTC)
    if dt.tzinfo is None:
        return dt.date().isoformat()
    return dt.astimezone(tz).date().isoformat()


def utc_stamp(dt: datetime) -> str:
    """`Date.toISOString()`: UTC with milliseconds."""
    if dt.tzinfo is None:
        dt = dt.astimezone()
    dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def today_local(tz: tzinfo | None = None) -> str:
    return datetime.now(tz).date().isoformat() if tz else date.today().isoformat()


# --- lib/store.ts: entries and merge ------------------------------------------------------

KEY_RE = re.compile(r"^(mc|ex|exam|plan):[a-z0-9][a-z0-9-]*$")


def kind_of(key: str) -> str | None:
    m = KEY_RE.match(key)
    return m[1] if m else None


def normalize_entry(key: str, value: dict) -> dict:
    """An entry in the site's full shape (lib/store.ts `sanitizeEntry` on valid input)."""
    kind = kind_of(key)
    if kind == "mc":
        attempts = [
            {
                "t": a["t"],
                "chosen": list(a["chosen"]),
                "score": a["score"],
                "conf": a["conf"],
                "ms": a.get("ms", 0),
            }
            for a in value.get("attempts", [])
        ]
        return {
            "h": value["h"],
            "box": value.get("box"),
            "due": value.get("due"),
            "attempts": attempts[-MAX_ATTEMPTS:],
        }
    if kind == "ex":
        return {
            "h": value["h"],
            "hints": value.get("hints", 0),
            "answer_ok": value.get("answer_ok"),
            "rating": value.get("rating"),
            "box": value.get("box"),
            "due": value.get("due"),
        }
    if kind == "exam":
        return {
            "attempts": [
                {
                    "started": a["started"],
                    "duration_s": a["duration_s"],
                    "points": dict(a["points"]),
                    "total": a["total"],
                }
                for a in value.get("attempts", [])
            ]
        }
    if kind == "plan":
        return {"done": value["done"]}
    raise ValueError(f"invalid progress key: {key}")


def empty_doc(course: str) -> dict:
    return {"schema": SCHEMA, "course": course, "exported_at": EPOCH, "items": {}}


def _last_time(entry: dict) -> str:
    t = ""
    for a in entry["attempts"]:
        if a["t"] > t:
            t = a["t"]
    return t


def _merge_mc(a: dict, b: dict) -> dict:
    seen: dict[str, dict] = {}
    for at in [*a["attempts"], *b["attempts"]]:
        seen[f"{at['t']}|{''.join(at['chosen'])}"] = at
    attempts = sorted(seen.values(), key=lambda x: x["t"])
    newer = b if _last_time(b) > _last_time(a) else a
    return {
        "h": newer["h"],
        "box": newer["box"],
        "due": newer["due"],
        "attempts": attempts[-MAX_ATTEMPTS:],
    }


def capped_rating(rating: str, hints: int) -> str:
    return "partial" if rating == "solved" and hints > HINT_CAP else rating


def _merge_ex(a: dict, b: dict) -> dict:
    later = b if (b["due"] or "") > (a["due"] or "") else a
    hints = max(a["hints"], b["hints"])
    if a["answer_ok"] is True or b["answer_ok"] is True:
        answer_ok = True
    else:
        answer_ok = a["answer_ok"] if a["answer_ok"] is not None else b["answer_ok"]
    merged = {
        "h": a["h"] if a["h"] != UNKNOWN_HASH else b["h"],
        "hints": hints,
        "answer_ok": answer_ok,
        "rating": later["rating"],
        "box": later["box"],
        "due": later["due"],
    }
    if merged["rating"] and capped_rating(merged["rating"], hints) != merged["rating"]:
        dues = sorted(d for d in (a["due"], b["due"]) if d is not None)
        merged["rating"] = capped_rating(merged["rating"], hints)
        merged["box"] = ENTRY_BOX
        merged["due"] = dues[0] if dues else None
    return merged


def _merge_exam(a: dict, b: dict) -> dict:
    seen: dict[str, dict] = {}
    for at in [*a["attempts"], *b["attempts"]]:
        seen[at["started"]] = at
    return {"attempts": sorted(seen.values(), key=lambda x: x["started"])}


def merge(local: dict, incoming: dict) -> tuple[dict, int, int]:
    """lib/store.ts `merge`: (merged document, entries added, entries merged)."""
    doc = copy.deepcopy(local)
    added = merged = 0
    for key, entry in incoming["items"].items():
        mine = doc["items"].get(key)
        if mine is None:
            doc["items"][key] = copy.deepcopy(entry)
            added += 1
            continue
        merged += 1
        kind = kind_of(key)
        if kind == "mc":
            doc["items"][key] = copy.deepcopy(_merge_mc(mine, entry))
        elif kind == "ex":
            doc["items"][key] = _merge_ex(mine, entry)
        elif kind == "exam":
            doc["items"][key] = copy.deepcopy(_merge_exam(mine, entry))
        elif kind == "plan":
            doc["items"][key] = {"done": mine["done"] or entry["done"]}
    return doc, added, merged


# --- reading progress documents ------------------------------------------------------------


def _key_line(text: str, key: str) -> int:
    """Line of `"key"` in a JSON text, else 1."""
    needle = json.dumps(key)
    pos = text.find(needle)
    return text.count("\n", 0, pos) + 1 if pos >= 0 else 1


def read_document(
    text: str, path: str, course: str, *, what: str = "progress file"
) -> tuple[dict | None, list[Finding]]:
    """Validate a progress document for `course`; the normalized document or findings."""

    def fail(code: str, message: str, fix: str, line: int = 1) -> tuple[None, list[Finding]]:
        return None, [Finding(path, line, 1, code, message, fix)]

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        return fail(
            "SK-PROGRESS-FILE",
            f"{what} is not JSON: {exc.msg}",
            "export the progress again on the site's progress page",
            exc.lineno,
        )
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), dict):
        return fail(
            "SK-PROGRESS-FILE",
            f"this is not a study-kit {what} (no `items` object)",
            "use the file the site's Export button downloads, "
            "studykit-progress-<course>-<date>.json",
        )
    schema = raw.get("schema")
    m = re.fullmatch(r"studykit-progress/(\d+)", schema) if isinstance(schema, str) else None
    if m is None or int(m[1]) != 1:
        newer = m is not None and int(m[1]) > 1
        return fail(
            "SK-PROGRESS-SCHEMA",
            f"{what} has schema {schema!r}; this studykit reads {SCHEMA} only"
            + (" (the file is newer)" if newer else ""),
            "update study-kit (git pull, uv sync) and import again"
            if newer
            else "import the file on the site once and export it again",
            _key_line(text, "schema"),
        )
    if not isinstance(raw.get("course"), str) or not raw["course"]:
        return fail(
            "SK-PROGRESS-COURSE",
            f"{what} names no course",
            "export the progress from the course's own progress page",
        )
    if raw["course"] != course:
        return fail(
            "SK-PROGRESS-COURSE",
            f"{what} belongs to the course '{raw['course']}', not '{course}'",
            f"import it into {raw['course']}, or export the progress of {course}",
            _key_line(text, "course"),
        )
    found: list[Finding] = []
    try:
        model.Progress.model_validate(raw)
    except ValidationError as exc:
        for err in exc.errors():
            loc = [str(p) for p in err["loc"]]
            key = loc[1] if len(loc) > 1 and loc[0] == "items" else (loc[0] if loc else "")
            where = ".".join(loc)
            found.append(
                Finding(
                    path,
                    _key_line(text, key) if key else 1,
                    1,
                    "SK-PROGRESS-ENTRY",
                    f"{where}: {err['msg']}",
                    "export the progress again on the site; the site never writes such an entry",
                )
            )
        return None, found
    for key, entry in raw["items"].items():
        stamps = [("t", a.get("t")) for a in entry.get("attempts", []) if kind_of(key) == "mc"]
        stamps += [
            ("started", a.get("started"))
            for a in entry.get("attempts", [])
            if kind_of(key) == "exam"
        ]
        for name, value in stamps:
            if not site_time(value):
                found.append(
                    Finding(
                        path,
                        _key_line(text, key),
                        1,
                        "SK-PROGRESS-ENTRY",
                        f"{key}: timestamp {name}={value!r} is not ISO 8601 as the site writes it",
                        "use YYYY-MM-DDTHH:MM:SS(.mmm)Z, as Date.toISOString() gives it",
                    )
                )
    if found:
        return None, found
    doc = {
        "schema": SCHEMA,
        "course": course,
        "exported_at": raw["exported_at"],
        "items": {k: normalize_entry(k, v) for k, v in raw["items"].items()},
    }
    return doc, []


# --- import --------------------------------------------------------------------------------


@dataclass
class Changes:
    added: int = 0
    merged: int = 0
    unchanged: int = 0
    mc_attempts: int = 0
    mc_items: list[str] = field(default_factory=list)
    exercises: list[dict] = field(default_factory=list)
    exams: list[dict] = field(default_factory=list)
    sessions_done: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "added": self.added,
            "merged": self.merged,
            "unchanged": self.unchanged,
            "mc": {"attempts": self.mc_attempts, "questions": self.mc_items},
            "exercises": self.exercises,
            "exams": self.exams,
            "sessions_done": self.sessions_done,
        }


def diff(before: dict, after: dict, keys: list[str]) -> Changes:
    """What a merge changed for the incoming `keys`."""
    ch = Changes()
    for key in keys:
        old, new = before["items"].get(key), after["items"][key]
        if old == new:
            ch.unchanged += 1
            continue
        kind, ident = key.split(":", 1)
        if kind == "mc":
            n = len(new["attempts"]) - (len(old["attempts"]) if old else 0)
            ch.mc_attempts += max(0, n)
            ch.mc_items.append(ident)
        elif kind == "ex":
            ch.exercises.append(
                {
                    "id": ident,
                    "rating": [old["rating"] if old else None, new["rating"]],
                    "answer_ok": [old["answer_ok"] if old else None, new["answer_ok"]],
                    "hints": [old["hints"] if old else 0, new["hints"]],
                }
            )
        elif kind == "exam":
            known = {a["started"] for a in old["attempts"]} if old else set()
            fresh = [a for a in new["attempts"] if a["started"] not in known]
            ch.exams.append(
                {"id": ident, "new_attempts": len(fresh), "totals": [a["total"] for a in fresh]}
            )
        elif kind == "plan" and new["done"] and not (old and old["done"]):
            ch.sessions_done.append(ident)
    return ch


def progress_dir(root: Path) -> Path:
    return root / "progress"


def load_state(root: Path, course: str) -> tuple[dict, list[Finding]]:
    """`progress/state.json` (the merged browser progress), or an empty document."""
    path = progress_dir(root) / STATE
    if not path.is_file():
        return empty_doc(course), []
    doc, found = read_document(
        path.read_text("utf-8"), content.display_path(path), course, what="progress state"
    )
    return (doc or empty_doc(course)), found


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _copy_name(browser: Path, src: Path, doc: dict, text: str) -> tuple[Path, bool]:
    """Where the imported file is kept, and whether it is there already."""
    day = doc["exported_at"][:10] if is_day(doc["exported_at"][:10]) else "undated"
    stem = f"studykit-progress-{doc['course']}-{day}"
    own = rf"studykit-progress-{re.escape(doc['course'])}-[0-9-]+(?: ?\(\d+\))?"
    if re.fullmatch(own, src.stem):
        stem = src.stem.replace(" ", "")
    n = 1
    while True:
        target = browser / (f"{stem}.json" if n == 1 else f"{stem}-{n}.json")
        if not target.exists():
            return target, False
        if target.read_text("utf-8", errors="replace") == text:
            return target, True
        n += 1


def import_file(root: Path, file: Path, *, dry_run: bool = False) -> tuple[dict, list[Finding]]:
    """Validate and merge one browser export into `progress/`."""
    course = root.name
    path = content.display_path(file) if file.is_absolute() else str(file)
    try:
        text = file.read_text("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {}, [
            Finding(path, 1, 1, "SK-PROGRESS-FILE", f"cannot read the file: {exc}", "check it")
        ]
    incoming, found = read_document(text, path, course)
    if incoming is None:
        return {}, found
    state, found = load_state(root, course)
    if found:
        return {}, found
    merged, added, n_merged = merge(state, incoming)
    if incoming["exported_at"] > merged["exported_at"]:
        merged["exported_at"] = incoming["exported_at"]
    ch = diff(state, merged, list(incoming["items"]))
    ch.added, ch.merged = added, n_merged
    pdir = progress_dir(root)
    target, already = _copy_name(pdir / BROWSER, file, incoming, text)
    if not dry_run:
        (pdir / BROWSER).mkdir(parents=True, exist_ok=True)
        if not already:
            shutil.copyfile(file, target)
        (pdir / STATE).write_text(dumps(merged), "utf-8")
    result = {
        "course": course,
        "file": path,
        "exported_at": incoming["exported_at"],
        "items": len(incoming["items"]),
        "copy": content.display_path(target),
        "copied": not already and not dry_run,
        "state": content.display_path(pdir / STATE),
        "dry_run": dry_run,
        "changes": ch.to_json(),
    }
    return result, []


def format_import(result: dict) -> str:
    ch = result["changes"]
    verb = "would import" if result["dry_run"] else "imported"
    lines = [
        f"{verb} {result['file']} ({result['items']} items, exported {result['exported_at']})",
        f"  {ch['added']} new, {ch['merged']} merged, {ch['unchanged']} unchanged",
    ]
    if ch["mc"]["attempts"] or ch["mc"]["questions"]:
        lines.append(
            f"  MC: {ch['mc']['attempts']} new attempt(s) on {len(ch['mc']['questions'])} "
            "question(s)"
        )
    for ex in ch["exercises"]:
        parts = []
        if ex["rating"][0] != ex["rating"][1]:
            parts.append(f"rated {ex['rating'][0] or 'unrated'} -> {ex['rating'][1]}")
        if ex["answer_ok"][0] != ex["answer_ok"][1]:
            parts.append(f"answer check {ex['answer_ok'][1]}")
        if ex["hints"][0] != ex["hints"][1]:
            parts.append(f"hints {ex['hints'][0]} -> {ex['hints'][1]}")
        lines.append(f"  exercise {ex['id']}: {', '.join(parts) or 'schedule changed'}")
    for ex in ch["exams"]:
        totals = ", ".join(f"{t:g}" for t in ex["totals"])
        lines.append(f"  mock exam {ex['id']}: {ex['new_attempts']} new attempt(s) ({totals})")
    if ch["sessions_done"]:
        lines.append(f"  plan: {len(ch['sessions_done'])} session(s) newly done")
    if result["dry_run"]:
        lines.append("  nothing written (--dry-run)")
    else:
        kept = "copied to" if result["copied"] else "already kept as"
        lines.append(f"  {kept} {result['copy']}; merged state in {result['state']}")
    return "\n".join(lines)


# --- examiner log ---------------------------------------------------------------------------


def _course_items(tree: content.CourseTree) -> dict[str, dict[str, str | None]]:
    """kind -> {id: topic} for the items an examiner result can name."""
    out: dict[str, dict[str, str | None]] = {"mc": {}, "exercise": {}, "exam-task": {}}
    for item in tree.items:
        if item.kind in out:
            out[item.kind].setdefault(item.id, item.topic)
    return out


def parse_examiner(
    lines: list[tuple[str, int, str]], tree: content.CourseTree, now: datetime | None = None
) -> tuple[list[dict], list[Finding]]:
    """Validate examiner results given as (source, line, json text); `t` defaults to now."""
    course = tree.model
    ctx = model.course_context(course)
    items = _course_items(tree)
    stamp = utc_stamp(now or datetime.now(UTC))
    out: list[dict] = []
    found: list[Finding] = []
    fix = (
        'write one JSON object per result, e.g. {"mode": "mc", "kind": "mc", "topic": "rc-filter", '
        '"item": "mc-rc-filter-003", "chosen": ["A"], "conf": "sure", "score": 1}'
    )
    for source, line, text in lines:
        if not text.strip():
            continue
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            found.append(
                Finding(
                    source, line, exc.colno, "SK-PROGRESS-EXAMINER", f"not JSON: {exc.msg}", fix
                )
            )
            continue
        if not isinstance(raw, dict):
            found.append(Finding(source, line, 1, "SK-PROGRESS-EXAMINER", "not a JSON object", fix))
            continue
        raw = {"t": stamp, **raw}
        try:
            result = model.ExaminerResult.model_validate(raw, context=ctx)
        except ValidationError as exc:
            for err in exc.errors():
                where = ".".join(str(p) for p in err["loc"]) or "result"
                found.append(
                    Finding(
                        source,
                        line,
                        1,
                        "SK-PROGRESS-EXAMINER",
                        f"{where}: {err['msg']}",
                        err.get("ctx", {}).get("fix") or fix,
                    )
                )
            continue
        if result.item is not None and result.kind in items:
            topics = items[result.kind]
            if result.item not in topics:
                found.append(
                    Finding(
                        source,
                        line,
                        1,
                        "SK-PROGRESS-EXAMINER",
                        f"{result.kind} '{result.item}' does not exist in this course",
                        f"use an id from `studykit ls {tree.id} --json`",
                    )
                )
                continue
            if topics[result.item] not in (None, result.topic):
                found.append(
                    Finding(
                        source,
                        line,
                        1,
                        "SK-PROGRESS-EXAMINER",
                        f"'{result.item}' belongs to the topic '{topics[result.item]}', "
                        f"not '{result.topic}'",
                        f"set topic to {topics[result.item]}",
                    )
                )
                continue
        raw["t"] = utc_stamp(result.t)
        out.append(raw)
    return out, found


def append_examiner(root: Path, results: list[dict]) -> Path:
    path = progress_dir(root) / EXAMINER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path


def load_examiner(root: Path, tree: content.CourseTree) -> tuple[list[dict], list[Finding]]:
    path = progress_dir(root) / EXAMINER
    if not path.is_file():
        return [], []
    display = content.display_path(path)
    lines = [(display, i, t) for i, t in enumerate(path.read_text("utf-8").splitlines(), 1)]
    return parse_examiner(lines, tree)


def fold_examiner(
    items: dict, results: list[dict], exam_date: str | None, tz: tzinfo | None = None
) -> dict:
    """Browser items plus the examiner's MC answers as attempts (Leitner applied in order)."""
    out = copy.deepcopy(items)
    for r in sorted((r for r in results if r["kind"] == "mc"), key=lambda r: r["t"]):
        key = f"mc:{r['item']}"
        entry = out.get(key) or {"h": UNKNOWN_HASH, "box": None, "due": None, "attempts": []}
        attempt = {
            "t": r["t"],
            "chosen": sorted(r.get("chosen", [])),
            "score": r["score"],
            "conf": r["conf"],
            "ms": 0,
        }
        sig = f"{attempt['t']}|{''.join(attempt['chosen'])}"
        if any(f"{a['t']}|{''.join(a['chosen'])}" == sig for a in entry["attempts"]):
            continue
        later = attempt["t"] >= _last_time(entry)
        entry["attempts"] = sorted([*entry["attempts"], attempt], key=lambda a: a["t"])[
            -MAX_ATTEMPTS:
        ]
        if later:
            step = review(
                entry["box"], attempt["score"], attempt["conf"], local_day(r["t"], tz), exam_date
            )
            entry["box"], entry["due"] = step["box"], step["due"]
        out[key] = entry
    return out


# --- lib/stats.ts ----------------------------------------------------------------------------

MC_ID_RE = re.compile(r"^mc-(.+)-\d{3}$")


@dataclass
class TopicInfo:
    id: str
    title: str
    weight: float | None = None
    skip: bool = False
    focus: bool = False
    prereq: list[str] = field(default_factory=list)
    mc: list[str] = field(default_factory=list)
    ex: list[str] = field(default_factory=list)


@dataclass
class TaskInfo:
    id: str
    topic: str | None
    points: float


@dataclass
class ExamInfo:
    id: str
    title: str
    points: float
    pass_points: float
    duration_min: int
    tasks: list[TaskInfo] = field(default_factory=list)


@dataclass
class CourseInfo:
    id: str
    title: str
    exam_date: str | None
    topics: list[TopicInfo]
    exams: list[ExamInfo]
    sessions: list[dict]  # plan.yaml sessions as {id, date, kind, minutes, topics, goal}
    exercises: dict[str, dict] = field(default_factory=dict)  # id -> {topic, difficulty}
    summaries: set[str] = field(default_factory=set)
    cheatsheet: bool = False


def topic_resolver(topics: list[TopicInfo]):
    if any(t.mc for t in topics):
        by_id: dict[str, str] = {}
        for t in topics:
            for q in t.mc:
                by_id[q] = t.id
        return lambda ident: by_id.get(ident)
    ids = {t.id for t in topics}

    def by_name(ident: str) -> str | None:
        m = MC_ID_RE.match(ident)
        return m[1] if m and m[1] in ids else None

    return by_name


def last_attempt_day(entry: dict, tz: tzinfo | None = None) -> str | None:
    return local_day(entry["attempts"][-1]["t"], tz) if entry["attempts"] else None


def mc_is_due(entry: dict, today: str, exam_date: str | None, tz: tzinfo | None = None) -> bool:
    return is_due(entry["due"], last_attempt_day(entry, tz), today, exam_date)


def is_correct(score: float) -> bool:
    return score >= 1 - 1e-9


def is_misconceived(entry: dict) -> bool:
    if not entry["attempts"]:
        return False
    last = entry["attempts"][-1]
    return last["conf"] == "sure" and not is_correct(last["score"])


def mean(xs: list[float]) -> float | None:
    if not xs:
        return None
    total = 0
    for x in xs:
        total += x
    return total / len(xs)


def _mc_entries(items: dict) -> list[tuple[str, dict]]:
    return [(k[3:], e) for k, e in items.items() if k.startswith("mc:")]


def topic_stats(
    items: dict,
    topics: list[TopicInfo],
    today: str,
    exam_date: str | None,
    tz: tzinfo | None = None,
) -> list[dict]:
    topic_of = topic_resolver(topics)
    stats = {
        t.id: {
            "id": t.id,
            "title": t.title or t.id,
            "answered": 0,
            "recent": [],
            "accuracy": None,
            "due": 0,
            "misconceptions": 0,
            "all": [],
        }
        for t in topics
    }
    for ident, e in _mc_entries(items):
        topic = topic_of(ident)
        st = stats.get(topic) if topic else None
        if st is None:
            continue
        if e["attempts"]:
            st["answered"] += 1
        st["all"].extend(e["attempts"])
        if mc_is_due(e, today, exam_date, tz):
            st["due"] += 1
        if is_misconceived(e):
            st["misconceptions"] += 1
    out = []
    for st in stats.values():
        every = st.pop("all")
        recent = sorted(every, key=lambda a: a["t"])[-RECENT:]
        st["recent"] = recent
        st["accuracy"] = mean([a["score"] for a in recent])
        out.append(st)
    return out


def due_count(
    items: dict,
    topics: list[TopicInfo],
    today: str,
    exam_date: str | None,
    topic: str | None = None,
    tz: tzinfo | None = None,
) -> int:
    topic_of = topic_resolver(topics)
    n = 0
    for ident, e in _mc_entries(items):
        t = topic_of(ident)
        if t is None or (topic and t != topic):
            continue
        if mc_is_due(e, today, exam_date, tz):
            n += 1
    return n


def ex_is_due(entry: dict, today: str, exam_date: str | None) -> bool:
    return is_due(entry["due"], review_day_of(entry["due"], entry["box"]), today, exam_date)


def exercises_due(items: dict, today: str, exam_date: str | None) -> int:
    return sum(
        1 for k, e in items.items() if k.startswith("ex:") and ex_is_due(e, today, exam_date)
    )


def weakest_topics(stats: list[dict], topics: list[TopicInfo], n: int = 3) -> list[dict]:
    skipped = {t.id for t in topics if t.skip}
    order = {t.id: i for i, t in enumerate(topics)}
    answered = [s for s in stats if s["accuracy"] is not None and s["id"] not in skipped]
    return sorted(answered, key=lambda s: (s["accuracy"], order.get(s["id"], 0)))[:n]


def mastery(stats: list[dict], topics: list[TopicInfo]) -> float | None:
    if not any(s["accuracy"] is not None for s in stats):
        return None
    by_id = {s["id"]: s for s in stats}
    counted = [t for t in topics if not t.skip]
    weights = [
        t.weight if _is_num(t.weight) and t.weight > 0 else 0  # type: ignore[operator]
        for t in counted
    ]
    total = 0
    for w in weights:
        total += w
    acc = 0
    for i, t in enumerate(counted):
        w = weights[i] / total if total > 0 else 1 / len(counted)
        s = by_id.get(t.id)
        acc += w * (s["accuracy"] if s and s["accuracy"] is not None else 0)
    return min(1, max(0, acc))


def exercise_status(entry: dict | None) -> str:
    rating = entry.get("rating") if entry else None
    if rating in ("solved", "partial", "not-yet"):
        return rating
    if entry and ((entry.get("hints") or 0) > 0 or isinstance(entry.get("answer_ok"), bool)):
        return "started"
    return "new"


def exam_summary(entry: dict | None) -> dict:
    attempts = sorted((entry or {}).get("attempts", []), key=lambda a: a["started"])
    best = None
    for a in attempts:
        if best is None or a["total"] > best["total"]:
            best = a
    return {"count": len(attempts), "best": best, "last": attempts[-1] if attempts else None}


def session_done(items: dict, ident: str) -> bool:
    return (items.get(f"plan:{ident}") or {}).get("done") is True


def next_session(sessions: list[dict], items: dict, today: str) -> dict | None:
    for s in sorted(sessions, key=lambda s: s["date"]):
        if s["date"] >= today and not session_done(items, s["id"]):
            return s
    return None


def upcoming_sessions(sessions: list[dict], items: dict, today: str, n: int = 3) -> list[dict]:
    ordered = sorted(sessions, key=lambda s: s["date"])
    return [s for s in ordered if s["date"] >= today and not session_done(items, s["id"])][:n]


def behind_count(sessions: list[dict], items: dict, today: str) -> int:
    return sum(1 for s in sessions if s["date"] < today and not session_done(items, s["id"]))


# --- the course as the site's clientInfo() sees it -----------------------------------------


def course_info(tree: content.CourseTree) -> CourseInfo:
    """Topics with their questions and exercises, exams and plan sessions (lib/courses.ts
    `clientInfo`, plus what the report and the scheduler need)."""
    course = tree.model
    if course is None:
        raise ValueError(f"{tree.id}: course.yaml does not validate; run studykit validate")
    banks: dict[str, list[str]] = {}
    for doc in tree.of_kind("mc"):
        topic = doc.get("topic")
        if isinstance(topic, str) and doc.body is not None:
            banks.setdefault(topic, []).extend(q.id for q in doc.body.questions if q.id)
    exercises: dict[str, dict] = {}
    for doc in tree.of_kind("exercise"):
        ident, topic = doc.get("id"), doc.get("topic")
        if isinstance(ident, str):
            diff_ = doc.get("difficulty")
            minutes = doc.get("minutes")
            exercises[ident] = {
                "topic": topic if isinstance(topic, str) else None,
                "difficulty": diff_ if isinstance(diff_, int) else None,
                "minutes": minutes if isinstance(minutes, int) else None,
            }
    topics = [
        TopicInfo(
            id=t.id,
            title=t.title,
            weight=t.weight,
            skip=t.id in course.skip,
            focus=t.id in course.focus,
            prereq=list(t.prereq),
            mc=banks.get(t.id, []),
            ex=sorted(i for i, e in exercises.items() if e["topic"] == t.id),
        )
        for t in course.topics
    ]
    exams = []
    for doc in tree.of_kind("exam"):
        exam = doc.model
        if exam is None:
            continue
        folder = doc.rel.rsplit("/", 1)[0]
        tasks = []
        for name in exam.tasks:
            task = tree.get(f"{folder}/{name}")
            if task is not None and isinstance(task.get("id"), str):
                pts = task.get("points")
                tasks.append(
                    TaskInfo(
                        task.get("id"),
                        task.get("topic") if isinstance(task.get("topic"), str) else None,
                        float(pts) if _is_num(pts) else 0.0,
                    )
                )
        exams.append(
            ExamInfo(
                exam.id,
                exam.title,
                exam.points,
                exam.pass_points,
                exam.duration_min,
                tasks,
            )
        )
    exams.sort(key=lambda e: e.id)
    plan_doc = tree.get("plan.yaml")
    plan = plan_doc.model if plan_doc is not None else None
    sessions = [
        {
            "id": s.id,
            "date": s.date.isoformat(),
            "kind": s.kind,
            "minutes": s.minutes,
            "topics": list(s.topics),
            "goal": s.goal,
        }
        for s in (plan.sessions if plan else [])
    ]
    exam_date = course.exam.date or (plan.exam_date if plan else None)
    return CourseInfo(
        id=tree.id,
        title=course.title,
        exam_date=exam_date.isoformat() if exam_date else None,
        topics=topics,
        exams=exams,
        sessions=sessions,
        exercises=exercises,
        summaries={d.parts.get("topic") for d in tree.of_kind("summary")} - {None},
        cheatsheet=tree.get("cheatsheet.md") is not None,
    )


# --- the report ------------------------------------------------------------------------------


@dataclass
class Snapshot:
    """Everything the report, the study status and the scheduler read about progress."""

    info: CourseInfo
    state: dict
    examiner: list[dict]
    items: dict  # browser items with the examiner's MC answers folded in
    today: str
    imports: int
    findings: list[Finding]


def snapshot(root: Path, today: str | None = None, tz: tzinfo | None = None) -> Snapshot:
    tree = content.CourseTree(root)
    info = course_info(tree)
    state, found = load_state(root, tree.id)
    examiner, found2 = load_examiner(root, tree)
    items = fold_examiner(state["items"], examiner, info.exam_date, tz)
    browser = progress_dir(root) / BROWSER
    imports = len(list(browser.glob("*.json"))) if browser.is_dir() else 0
    return Snapshot(info, state, examiner, items, today or today_local(tz), imports, found + found2)


def _passed(total: float, exam: ExamInfo | None) -> bool | None:
    return None if exam is None else total >= exam.pass_points


def compute_report(snap: Snapshot, tz: tzinfo | None = None) -> dict:
    """The content of `progress/mastery.json` (model.Mastery)."""
    info, items, today = snap.info, snap.items, snap.today
    stats = topic_stats(items, info.topics, today, info.exam_date, tz)
    by_id = {s["id"]: s for s in stats}
    topic_of = topic_resolver(info.topics)

    # exam tasks: the latest attempt of each exam, per topic
    task_score: dict[str, list[float]] = {}
    exams_out: dict[str, dict] = {}
    for exam in info.exams:
        summary = exam_summary(items.get(f"exam:{exam.id}"))

        def brief(a: dict | None, exam: ExamInfo = exam) -> dict | None:
            if a is None:
                return None
            passed = _passed(a["total"], exam)
            return {"started": a["started"], "total": a["total"], "passed": passed}

        exams_out[exam.id] = {
            "title": exam.title,
            "points": exam.points,
            "pass_points": exam.pass_points,
            "attempts": summary["count"],
            "best": brief(summary["best"]),
            "last": brief(summary["last"]),
        }
        last = summary["last"]
        if last is None:
            continue
        for task in exam.tasks:
            if task.topic and task.id in last["points"] and task.points > 0:
                acc = task_score.setdefault(task.topic, [0, 0])
                acc[0] += last["points"][task.id]
                acc[1] += task.points

    # examiner: per topic, the mean score of the last RECENT results
    by_topic: dict[str, list[dict]] = {}
    for r in sorted(snap.examiner, key=lambda r: r["t"]):
        by_topic.setdefault(r["topic"], []).append(r)

    exercises: dict[str, dict] = {}
    ex_counts = {
        t.id: {"new": 0, "started": 0, "not-yet": 0, "partial": 0, "solved": 0} for t in info.topics
    }
    for ident in sorted(info.exercises):
        entry = items.get(f"ex:{ident}")
        status = exercise_status(entry)
        topic = info.exercises[ident]["topic"]
        if topic in ex_counts:
            ex_counts[topic][status] += 1
        exercises[ident] = {
            "topic": topic,
            "status": status,
            "hints": entry["hints"] if entry else 0,
            "answer_ok": entry["answer_ok"] if entry else None,
            "box": entry["box"] if entry else None,
            "due": entry["due"] if entry else None,
            "due_now": bool(entry) and ex_is_due(entry, today, info.exam_date),
        }

    topics_out = {}
    for t in info.topics:
        st = by_id[t.id]
        ts = task_score.get(t.id)
        recent = by_topic.get(t.id, [])[-RECENT:]
        topics_out[t.id] = {
            "title": t.title,
            "weight": t.weight,
            "focus": t.focus,
            "skip": t.skip,
            "mastery": st["accuracy"],
            "answered": st["answered"],
            "questions": len(t.mc),
            "attempts": len(st["recent"]),
            "due": st["due"],
            "misconceptions": st["misconceptions"],
            "exercises": ex_counts[t.id],
            "exam_tasks": None
            if ts is None
            else {"points": ts[0], "max_points": ts[1], "fraction": min(1, ts[0] / ts[1])},
            "examiner": None
            if not recent
            else {"results": len(recent), "score": mean([r["score"] for r in recent])},
        }

    mc_due = sorted(
        ident
        for ident, e in _mc_entries(items)
        if topic_of(ident) is not None and mc_is_due(e, today, info.exam_date, tz)
    )
    ex_due = sorted(
        k[3:]
        for k, e in items.items()
        if k.startswith("ex:") and ex_is_due(e, today, info.exam_date)
    )
    misconceptions = [
        {
            "id": ident,
            "topic": topic_of(ident),
            "t": e["attempts"][-1]["t"],
            "chosen": e["attempts"][-1]["chosen"],
        }
        for ident, e in sorted(_mc_entries(items))
        if topic_of(ident) is not None and is_misconceived(e)
    ]
    findings = [
        {
            "t": r["t"],
            "topic": r["topic"],
            "kind": r["kind"],
            "item": r.get("item"),
            "score": r["score"],
            "finding": r["finding"],
        }
        for r in sorted(snap.examiner, key=lambda r: r["t"])
        if r.get("finding")
    ][-20:]
    return {
        "schema": MASTERY_SCHEMA,
        "course": info.id,
        "generated": today,
        "exam_date": info.exam_date,
        "overall": mastery(stats, info.topics),
        "topics": topics_out,
        "due": {
            "mc": len(mc_due),
            "exercises": len(ex_due),
            "mc_ids": mc_due,
            "exercise_ids": ex_due,
        },
        "misconceptions": misconceptions,
        "exercises": exercises,
        "exams": exams_out,
        "examiner": {
            "results": len(snap.examiner),
            "last": max((r["t"] for r in snap.examiner), default=None),
            "findings": findings,
        },
        "sources": {
            "state": None if snap.state["exported_at"] == EPOCH else snap.state["exported_at"],
            "imports": snap.imports,
            "examiner": len(snap.examiner),
        },
    }


def pct(value: float | None) -> str:
    return "-" if value is None else f"{round(value * 100)} %"


def format_markdown(report: dict, info: CourseInfo) -> str:
    """`progress/report.md`: the report for the student, in English."""
    today, exam = report["generated"], report["exam_date"]
    left = f", {days_between(today, exam)} days left" if exam else ""
    out = [
        f"# Progress report: {info.title}",
        "",
        f"As of {today} · exam {exam or 'date unknown'}{left}.",
        "",
        f"**Mastery: {pct(report['overall'])}** (topic accuracy over the last {RECENT} MC "
        "answers, weighted by topic weight; unanswered topics count 0).",
        "",
        "## Topics",
        "",
        "| Topic | Weight | Mastery | Answered | Due | Misconceptions | Exercises solved "
        "| Exam tasks | Examiner |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t in report["topics"].values():
        ex = t["exercises"]
        total_ex = sum(ex.values())
        tasks = t["exam_tasks"]
        exr = t["examiner"]
        flags = " (focus)" if t["focus"] else (" (skipped)" if t["skip"] else "")
        out.append(
            f"| {t['title']}{flags} | {t['weight']:g} | {pct(t['mastery'])} "
            f"| {t['answered']}/{t['questions']} | {t['due']} | {t['misconceptions']} "
            f"| {ex['solved']}/{total_ex} "
            f"| {pct(tasks['fraction']) if tasks else '-'} "
            f"| {pct(exr['score']) + ' (' + str(exr['results']) + ')' if exr else '-'} |"
        )
    due = report["due"]
    out += ["", "## Due reviews", ""]
    out.append(f"{due['mc']} MC question(s) and {due['exercises']} exercise(s) are due today.")
    if due["mc_ids"]:
        out.append("")
        out.append("MC: " + ", ".join(f"`{i}`" for i in due["mc_ids"]))
    if due["exercise_ids"]:
        out.append("")
        out.append("Exercises: " + ", ".join(f"`{i}`" for i in due["exercise_ids"]))
    out += ["", "## Misconceptions", ""]
    if report["misconceptions"]:
        out.append("Answered sure, but not fully right the last time:")
        out.append("")
        for m in report["misconceptions"]:
            chosen = ", ".join(m["chosen"]) or "nothing"
            out.append(f"- `{m['id']}` ({m['topic']}): chose {chosen} on {m['t'][:10]}")
    else:
        out.append("None.")
    out += ["", "## Exercises", ""]
    by_status: dict[str, list[str]] = {}
    for ident, e in report["exercises"].items():
        by_status.setdefault(e["status"], []).append(ident)
    for status in ("solved", "partial", "not-yet", "started", "new"):
        ids = by_status.get(status, [])
        if ids:
            out.append(f"- {status}: " + ", ".join(f"`{i}`" for i in ids))
    if not report["exercises"]:
        out.append("The course has no exercises.")
    out += ["", "## Mock exams", ""]
    if not report["exams"]:
        out.append("The course has no mock exams.")
    for eid, e in report["exams"].items():
        if not e["attempts"]:
            out.append(f"- {e['title']} (`{eid}`): not taken yet")
            continue
        best, last = e["best"], e["last"]
        out.append(
            f"- {e['title']} (`{eid}`): {e['attempts']} attempt(s); last {last['total']:g}/"
            f"{e['points']:g} ({'passed' if last['passed'] else 'not passed'}), best "
            f"{best['total']:g}/{e['points']:g}; pass mark {e['pass_points']:g}"
        )
    out += ["", "## Examiner", ""]
    ex = report["examiner"]
    if not ex["results"]:
        out.append("No examiner results yet (`/examine`).")
    else:
        out.append(f"{ex['results']} result(s), the last on {ex['last'][:10]}.")
        if ex["findings"]:
            out.append("")
            for f in ex["findings"]:
                item = f" `{f['item']}`" if f["item"] else ""
                score = pct(f["score"])
                out.append(f"- {f['t'][:10]} {f['topic']}{item} ({score}): {f['finding']}")
    return "\n".join(out) + "\n"


def write_report(root: Path, report: dict, info: CourseInfo) -> tuple[Path, Path]:
    model.Mastery.model_validate(report)
    pdir = progress_dir(root)
    pdir.mkdir(parents=True, exist_ok=True)
    mastery_path = pdir / MASTERY
    report_path = pdir / REPORT
    mastery_path.write_text(dumps(report), "utf-8")
    report_path.write_text(format_markdown(report, info), "utf-8")
    return mastery_path, report_path
