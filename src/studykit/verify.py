"""`studykit verify`: run the verifier's checks and keep the per-item ledger (§2.10, §5.3).

Items are exercises, exam tasks and MC questions (practice banks and exam MC). A verifier
works from `studykit blind <course> <id>` and writes `checks/<id>.py` (a script that ends
with a `studykit.check` call) or `checks/<id>.json`. `verify` runs each check in a
subprocess with a timeout (no shell), compares what it computed with the item's key and
writes `state/verify/<id>.json`:

- an exercise or exam task: every `answers` key, numeric within the key's tolerance
  (in the key's unit; SI prefixes convert) or symbolic (SymPy, then sample points);
- an MC question: the set of correct options (single, multi), true or false per statement
  (Kprim), or for `mc_numeric` the four assertions of §2.6.

Ledger status:

| status | meaning |
|---|---|
| unverified | no check yet, the check failed to run, or two methods disagree |
| verified | the check agrees with the key (with disputes before it: fixed) |
| disputed | the check disagrees; goes to the author with the verifier's numbers |
| quarantined | still disputed after `MAX_ROUNDS` author fix rounds, or set by hand |

The ledger stores the item's content hash (`content_sha256`, over the exercise file or the
question's source lines), so an edit makes the entry stale: validate reports it and the
next run checks the new version. A dispute on a new version of the item counts one more
fix round; the dispute after the second fix round quarantines the item. Quarantined items
are hidden from the website and the PDFs (`quarantined_ids`, read through the course
index by the render bridge, the filters and the PDF assembler).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from studykit import model
from studykit.content import CourseTree, Doc, Question, display_path

LEDGER_DIR = "state/verify"
CHECKS_DIR = "checks"
REPORT = "state/verify/report.md"
MAX_ROUNDS = 2
DEFAULT_TIMEOUT = 120.0
LETTERS = "ABCDEF"
KINDS = ("exercise", "exam-task", "mc")
KEY_SEP = " | key: "  # what follows in a problem is the item's key; hidden from the verifier
CHECK_META = {"studykit-check", "kind", "method", "reason", "confidence", "note"}


class VerifyError(ValueError):
    """A usage problem (unknown id, missing ledger); the CLI exits with 2."""


# --- items ------------------------------------------------------------------------------------


@dataclass
class VItem:
    id: str
    kind: str  # exercise | exam-task | mc
    doc: Doc
    line: int
    topic: str | None
    exam: str | None = None
    question: Question | None = None

    @property
    def rel(self) -> str:
        return self.doc.rel

    @property
    def source(self) -> str:
        """The item's source text: the whole file, or the question's fenced block."""
        if self.question is None:
            return self.doc.text
        body = self.doc.body
        assert body is not None
        block = self.question.block
        end = block.close_line if block.close_line is not None else len(body.lines) - 1
        return "\n".join(body.lines[i].text for i in range(block.open_line, end + 1)) + "\n"

    @property
    def content_sha256(self) -> str:
        text = self.source.replace("\r\n", "\n")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @property
    def mc_type(self) -> str | None:
        return self.question.type if self.question else None

    def key_letters(self) -> list[str]:
        """Letters (source order) of the options marked [x]."""
        assert self.question is not None
        return [LETTERS[i] for i, o in enumerate(self.question.options) if o.correct]


def items(tree: CourseTree) -> list[VItem]:
    """Every verifiable item of the course, in discovery order."""
    out: list[VItem] = []
    for doc in tree:
        if doc.kind in ("exercise", "exam-task") and isinstance(doc.get("id"), str):
            line = doc.yaml.locate(["id"])[0] if doc.yaml else 1
            topic = doc.get("topic") if isinstance(doc.get("topic"), str) else None
            out.append(VItem(doc.get("id"), doc.kind, doc, line, topic, doc.parts.get("exam")))
        elif doc.kind in ("mc", "exam-mc") and doc.body is not None:
            for q in doc.body.questions:
                if q.id:
                    out.append(
                        VItem(
                            q.id,
                            "mc",
                            doc,
                            q.line,
                            model.mc_topic(q.id),
                            doc.parts.get("exam"),
                            q,
                        )
                    )
    return out


def select(tree: CourseTree, target: str | None) -> list[VItem]:
    """Items for `target`: an item id, a topic id, an exam id or `all` (the default)."""
    every = items(tree)
    if target in (None, "", "all"):
        return every
    by_id = [i for i in every if i.id == target]
    if by_id:
        return by_id[:1]
    if target in tree.topics:
        return [i for i in every if i.topic == target]
    exam = [i for i in every if i.exam == target]
    if exam:
        return exam
    raise VerifyError(
        f"'{target}' is not an exercise, exam task or MC question id, a topic or an exam of "
        f"{tree.id} (list them with `studykit ls {tree.id}`)"
    )


def find(tree: CourseTree, item_id: str) -> VItem:
    for item in items(tree):
        if item.id == item_id:
            return item
    raise VerifyError(f"{tree.id} has no exercise, exam task or MC question '{item_id}'")


# --- ledger -------------------------------------------------------------------------------------


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def ledger_path(root: Path, item_id: str) -> Path:
    return root / LEDGER_DIR / f"{item_id}.json"


def read_ledger(root: Path, item_id: str) -> model.VerifyEntry | None:
    """The ledger entry, None without one; ValueError for a file that does not validate."""
    path = ledger_path(root, item_id)
    if not path.is_file():
        return None
    try:
        return model.VerifyEntry.model_validate(json.loads(path.read_text("utf-8")))
    except (json.JSONDecodeError, ValidationError, UnicodeDecodeError) as exc:
        raise ValueError(f"{display_path(path)} is not a valid ledger entry: {exc}") from exc


def write_ledger(root: Path, entry: model.VerifyEntry) -> Path:
    path = ledger_path(root, entry.item)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = entry.model_dump(mode="json", by_alias=True, exclude_none=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def ledger_ids(root: Path) -> list[str]:
    folder = root / LEDGER_DIR
    return sorted(p.stem for p in folder.glob("*.json")) if folder.is_dir() else []


def quarantined_ids(root: Path) -> list[str]:
    """Ids whose ledger says quarantined; unreadable entries are skipped (validate reports
    them). This is what hides items on the site and in the PDFs."""
    out = []
    for item_id in ledger_ids(root):
        try:
            data = json.loads(ledger_path(root, item_id).read_text("utf-8"))
        except OSError, json.JSONDecodeError, UnicodeDecodeError:
            continue
        if isinstance(data, dict) and data.get("status") == "quarantined":
            out.append(str(data.get("item") or item_id))
    return sorted(set(out))


def hidden_file(doc: Doc, hidden: Iterable[str]) -> bool:
    """True for an exercise or exam-task file whose item is quarantined."""
    return doc.kind in ("exercise", "exam-task") and doc.get("id") in set(hidden)


def exam_without(
    tree: CourseTree, exam_doc: Doc, data: Mapping[str, Any], hidden: Iterable[str]
) -> dict[str, Any]:
    """exam.yaml data without its quarantined tasks and MC questions: the task list and
    the points shrink, and the pass mark keeps its share (rounded to half points). The
    website and the PDFs both show an exam this way."""
    hidden = set(hidden)
    out = dict(data)
    exam_id = exam_doc.parts.get("exam")
    tasks = data.get("tasks")
    points = data.get("points")
    if not hidden or not isinstance(tasks, list) or not isinstance(points, (int, float)):
        return out
    removed = 0.0
    kept = []
    for name in tasks:
        doc = tree.get(f"exams/{exam_id}/{name}")
        if doc is not None and hidden_file(doc, hidden):
            task_points = doc.get("points")
            removed += float(task_points) if isinstance(task_points, (int, float)) else 0.0
        else:
            kept.append(name)
    mc = data.get("mc")
    if isinstance(mc, Mapping) and isinstance(mc.get("points_each"), (int, float)):
        mc_doc = tree.get(f"exams/{exam_id}/{mc.get('file') or 'mc.md'}")
        questions = mc_doc.body.questions if mc_doc is not None and mc_doc.body else []
        removed += mc["points_each"] * sum(1 for q in questions if q.id in hidden)
    if not removed and len(kept) == len(tasks):
        return out
    total = max(0.0, float(points) - removed)
    out["tasks"] = kept
    out["points"] = total
    pass_points = data.get("pass_points")
    if isinstance(pass_points, (int, float)) and points:
        out["pass_points"] = round(float(pass_points) * total / float(points) * 2) / 2
    return out


def is_stale(entry: model.VerifyEntry, item: VItem) -> bool:
    return entry.content_sha256 != item.content_sha256


def check_file(root: Path, item_id: str) -> Path | None:
    """`checks/<id>.py`, else `checks/<id>.json`."""
    for suffix in (".py", ".json"):
        path = root / CHECKS_DIR / f"{item_id}{suffix}"
        if path.is_file():
            return path
    return None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- running a check --------------------------------------------------------------------------


def run_check(path: Path, root: Path, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """The JSON object a check produces; ValueError says why there is none."""
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"{path.name} is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"{path.name} must hold a JSON object")
        return data
    env = {**os.environ, "MPLBACKEND": "Agg", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{path.name} did not finish within {timeout:g} s") from exc
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()[-3:] or ["(no output)"]
        raise ValueError(f"{path.name} exited with {proc.returncode}: " + " | ".join(tail))
    for line in reversed(proc.stdout.strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            break
        if isinstance(data, dict):
            return data
        break
    raise ValueError(
        f"{path.name} printed no JSON object on its last line; end it with a studykit.check "
        "call such as answers(...) or mc_answer(...)"
    )


# --- units and numbers ------------------------------------------------------------------------

UNIT_ALIASES = {"Ohm": "Ω", "ohm": "Ω", "Ω": "Ω", "rad/s": "1/s", "1/s": "1/s", "s^-1": "1/s"}
PREFIXED = {"V", "A", "W", "Hz", "s", "F", "H", "Ω", "J", "C", "S", "VA", "var", "Wh", "1/s"}
PREFIX = {
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "µ": 1e-6,
    "μ": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
}
ANGLES = {"°": math.pi / 180, "deg": math.pi / 180, "rad": 1.0}


def parse_unit(unit: str) -> tuple[float, str] | None:
    """(scale to the base unit, base unit) for 'kΩ', 'µs', 'mA', 'Hz', '°' and a quotient
    of two such units ('V/s', 'mV/µs' -> 1e3, 'V/s'); None if unknown."""
    unit = unit.strip()
    if unit in ANGLES:
        return ANGLES[unit], "rad"
    if unit in UNIT_ALIASES:
        return 1.0, UNIT_ALIASES[unit]
    if unit.count("/") == 1:
        num, den = (parse_unit(part) for part in unit.split("/"))
        if num is None or den is None or "rad" in (num[1], den[1]) or "/" in num[1] + den[1]:
            return None
        return num[0] / den[0], f"{num[1]}/{den[1]}"
    if unit in PREFIXED:
        return 1.0, unit
    if unit == "Hz":
        return 1.0, "Hz"
    if len(unit) > 1 and unit[0] in PREFIX:
        rest = UNIT_ALIASES.get(unit[1:], unit[1:])
        if rest in PREFIXED:
            return PREFIX[unit[0]], rest
    return None


def convert(value: float, unit: str, to: str) -> float:
    """`value` in `unit` expressed in `to`; ValueError when they are not the same kind."""
    if unit.strip() == to.strip():
        return value
    a, b = parse_unit(unit), parse_unit(to)
    if a is None or b is None:
        raise ValueError(f"cannot convert {unit} to {to}")
    base_a = "1/s" if a[1] == "Hz" else a[1]
    base_b = "1/s" if b[1] == "Hz" else b[1]
    if base_a != base_b:
        raise ValueError(f"{unit} and {to} are different quantities")
    return value * a[0] / b[0]


TEX_REPLACEMENTS = [
    (r"\{,\}", "."),
    (r"\\[,;:! ]|~", " "),
    (r"\\(?:mathrm|text|mathit)\{([^{}]*)\}", r"\1"),
    (r"\\(?:mu|micro)\b\s*", "µ"),
    (r"\\Omega\b", "Ω"),
    (r"\^\{?\\circ\}?|\\circ|\\degree", "°"),
    (r"\\(?:cdot|times)\s*10\^\{?([+\-\u2212]?\d+)\}?", r"e\1"),
    (r"\\%", "%"),
]
NUMBER_RE = re.compile(
    r"^\s*([+\-\u2212]?\s*\d+(?:[.,]\d+)?)(?:\s*e\s*([+\-\u2212]?\d+))?\s*(.*?)\s*$"
)


def option_value(text: str) -> float | None:
    """The SI value an option's text states (`$4{,}82\\,\\mathrm{kHz}$` -> 4820.0), or None
    when the text is not a plain number with an optional unit."""
    s = text.strip()
    if s.count("$") == 2 and s.startswith("$") and s.endswith("$"):
        s = s[1:-1]
    elif "$" in s:
        return None
    for pattern, repl in TEX_REPLACEMENTS:
        s = re.sub(pattern, repl, s)
    s = s.replace("{", "").replace("}", "")
    m = NUMBER_RE.match(s)
    if not m:
        return None
    number = float(m[1].replace(" ", "").replace("\u2212", "-").replace(",", "."))
    if m[2]:
        number *= 10 ** int(m[2].replace("\u2212", "-"))
    unit = m[3].strip()
    if not unit:
        return number
    if unit == "°":
        return number
    if unit == "%":
        return number / 100
    if unit == "dB":
        return number
    parsed = parse_unit(unit)
    if parsed is None or parsed[1] == "rad":
        return None
    return number * parsed[0]


def numeric_question(question: Any) -> bool:
    """A single or multi question whose every option states a number (§2.6); its check
    is an `mc_numeric` script (SK-VER-CHECK)."""
    if question is None or question.type not in ("single", "multi") or not question.options:
        return False
    return all(option_value(o.text) is not None for o in question.options)


def close(a: float, b: float, rtol: float, atol: float = 0.0) -> bool:
    return abs(a - b) <= atol + rtol * abs(b)


# --- comparing ---------------------------------------------------------------------------------


@dataclass
class Outcome:
    result: str  # pass | mismatch | error
    method: str | None = None  # script | blind
    results: list[model.LedgerValue] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)  # content problems: a dispute
    errors: list[str] = field(default_factory=list)  # check problems: fix the check
    warnings: list[str] = field(default_factory=list)

    @property
    def problems(self) -> list[str]:
        return self.errors + self.mismatches


def _finish(out: Outcome) -> Outcome:
    out.result = "error" if out.errors else "mismatch" if out.mismatches else "pass"
    return out


def compare(item: VItem, data: Mapping[str, Any]) -> Outcome:
    out = Outcome("pass")
    if item.kind == "mc":
        _compare_mc(item, data, out)
    else:
        _compare_answers(item, data, out)
    return _finish(out)


def _answers_of(item: VItem) -> list[model.Answer] | None:
    m = item.doc.model
    return list(m.answers) if m is not None else None


def _computed_values(data: Mapping[str, Any]) -> dict[str, Any]:
    raw = data.get("answers")
    if isinstance(raw, Mapping):
        return dict(raw)
    return {k: v for k, v in data.items() if k not in CHECK_META and k not in {"agree"}}


def _compare_answers(item: VItem, data: Mapping[str, Any], out: Outcome) -> None:
    keys = _answers_of(item)
    if keys is None:
        out.errors.append(
            f"{item.rel}: the frontmatter does not validate; run `studykit validate` first"
        )
        return
    if data.get("kind") not in (None, "answers", "review"):
        out.errors.append(f"an exercise needs answers(...) or review(...), not {data['kind']}")
        return
    if data.get("kind") == "review" and keys:
        # review(...) is for an item without keys; agreeing must not stand in for computing
        out.errors.append(
            "the item has answer keys; end the check with answers(...), one value per key"
        )
        return
    if isinstance(data.get("agree"), bool):
        reason = str(data.get("reason") or "")
        out.results.append(
            model.LedgerValue(key="review", computed=data["agree"], ok=data["agree"])
        )
        if not data["agree"]:
            out.mismatches.append(
                "the verifier disagrees with the solution" + (f": {reason}" if reason else "")
            )
        if not keys:
            return
    elif not keys:
        out.errors.append(
            "the item has no answer keys; check it with review(agree, reason) or "
            '{"agree": true, "reason": "…"}'
        )
        return
    computed = _computed_values(data)
    for answer in keys:
        if answer.key not in computed:
            out.errors.append(f"the check computes no value for '{answer.key}'")
            continue
        value = computed[answer.key]
        if answer.expr is not None:
            out.results.append(_compare_symbolic(answer, value, out))
        else:
            out.results.append(_compare_numeric(answer, value, out))
    extra = sorted(set(computed) - {a.key for a in keys})
    if extra:
        out.warnings.append(f"values without an answer key: {', '.join(extra)}")


def _compare_numeric(answer: model.Answer, value: Any, out: Outcome) -> model.LedgerValue:
    unit = answer.unit or ""
    expected = float(answer.value or 0.0)
    row = model.LedgerValue(key=answer.key, expected=expected, unit=answer.unit, ok=False)
    try:
        if isinstance(value, Mapping):
            number = float(value["value"])
            given = str(value.get("unit") or "")
            number = convert(number, given, unit) if given and unit else number
        elif isinstance(value, bool):
            raise ValueError("a boolean is not a number")
        elif isinstance(value, (int, float)):
            number = float(value)
        elif isinstance(value, str):
            from studykit import calc

            number = float(complex(calc.parse(value).evalf()).real)
        else:
            raise ValueError(f"unreadable value {value!r}")
    except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
        out.errors.append(f"'{answer.key}': {exc}")
        return row
    if not math.isfinite(number):
        out.errors.append(f"'{answer.key}': the check computed {number}")
        return row
    tol = (answer.atol or 0.0) + (answer.rtol or 0.0) * abs(expected)
    abs_err = abs(number - expected)
    ok = abs_err <= tol
    row = model.LedgerValue(
        key=answer.key,
        expected=expected,
        computed=number,
        unit=answer.unit,
        abs_err=abs_err,
        rel_err=abs_err / abs(expected) if expected else None,
        tol=tol,
        ok=ok,
    )
    if not ok:
        out.mismatches.append(
            f"'{answer.key}': the check computes {number:.6g}{' ' + unit if unit else ''}, "
            f"which does not match the key{KEY_SEP}{expected:.6g}{' ' + unit if unit else ''} "
            f"± {tol:.3g}"
        )
    return row


def _compare_symbolic(answer: model.Answer, value: Any, out: Outcome) -> model.LedgerValue:
    import sympy

    from studykit import calc

    row = model.LedgerValue(key=answer.key, expected=answer.expr, computed=str(value), ok=False)
    try:
        expected = calc.parse(str(answer.expr), symbols=answer.symbols)
        computed = calc.parse(str(value), symbols=answer.symbols)
    except calc.CalcError as exc:
        out.errors.append(f"'{answer.key}': {exc}")
        return row
    ok = False
    try:
        ok = sympy.simplify(expected - computed) == 0
    except Exception:  # simplification can fail on odd input; sample points decide then
        ok = False
    if not ok:
        ok = _same_at_samples(expected, computed, answer.symbols)
    row = model.LedgerValue(key=answer.key, expected=answer.expr, computed=str(value), ok=ok)
    if not ok:
        out.mismatches.append(
            f"'{answer.key}': the check derives {value}, which does not match the key"
            f"{KEY_SEP}{answer.expr}"
        )
    return row


def _same_at_samples(a: Any, b: Any, names: list[str], n: int = 6) -> bool:
    import sympy

    symbols = [sympy.Symbol(s) for s in names]
    rng = random.Random(0)
    for _ in range(n):
        point = {s: sympy.Float(rng.uniform(0.5, 3.0)) for s in symbols}
        try:
            x = complex(sympy.N(a.subs(point)))
            y = complex(sympy.N(b.subs(point)))
        except TypeError, ValueError:
            return False
        if not abs(x - y) <= 1e-9 * max(1.0, abs(x), abs(y)):
            return False
    return True


def _compare_mc(item: VItem, data: Mapping[str, Any], out: Outcome) -> None:
    q = item.question
    assert q is not None
    n = len(q.options)
    letters = LETTERS[:n]
    expected = item.key_letters()
    if data.get("kind") == "mc-numeric" or "correct" in data:
        _compare_mc_numeric(item, data, out)
        return
    if "answer" not in data:
        out.errors.append('an MC check needs mc_answer(...), mc_numeric(...) or {"answer": [...]}')
        return
    if data.get("ambiguous") is True:
        reason = str(data.get("reason") or "")
        out.mismatches.append(
            "the verifier finds the question ambiguous" + (f": {reason}" if reason else "")
        )
    if str(data.get("confidence") or "high") not in ("high",):
        out.warnings.append(f"the verifier's confidence is {data.get('confidence')}")
    answer = data["answer"]
    if q.type == "kprim":
        if isinstance(answer, Mapping):
            given = {str(k).upper(): v for k, v in answer.items()}
            if not all(isinstance(v, bool) for v in given.values()):
                out.errors.append("a Kprim answer maps each letter to true or false")
                return
        elif isinstance(answer, list):
            given = {str(a).upper(): True for a in answer}
        else:
            out.errors.append("a Kprim answer is a list of the true statements or a mapping")
            return
        unknown = sorted(set(given) - set(letters))
        if unknown:
            out.errors.append(
                f"unknown statement(s) {', '.join(unknown)}; "
                f"the question has {letters[0]} to {letters[-1]}"
            )
            return
        if isinstance(answer, Mapping) and set(given) != set(letters):
            out.errors.append(f"judge every statement {', '.join(letters)}")
            return
        for i, letter in enumerate(letters):
            truth = q.options[i].correct
            mine = bool(given.get(letter, False))
            row = model.LedgerValue(key=letter, expected=truth, computed=mine, ok=truth == mine)
            out.results.append(row)
            if not row.ok:
                out.mismatches.append(
                    f"statement {letter}: the verifier judges it {'true' if mine else 'false'}, "
                    f"which does not match the key{KEY_SEP}{'true' if truth else 'false'}"
                )
        return
    if isinstance(answer, str):
        answer = [answer]
    if not isinstance(answer, list) or not all(isinstance(a, str) for a in answer):
        out.errors.append("an MC answer is a list of option letters")
        return
    chosen = sorted({a.strip().upper() for a in answer})
    unknown = [a for a in chosen if a not in letters]
    if unknown:
        out.errors.append(
            f"unknown option(s) {', '.join(unknown)}; "
            f"the question has {letters[0]} to {letters[-1]}"
        )
        return
    ok = chosen == expected
    out.results.append(model.LedgerValue(key="key", expected=expected, computed=chosen, ok=ok))
    if not ok:
        out.mismatches.append(
            f"the verifier's answer {', '.join(chosen) or '(none)'} does not match the key"
            f"{KEY_SEP}{', '.join(expected) or '(none)'}"
        )


def _compare_mc_numeric(item: VItem, data: Mapping[str, Any], out: Outcome) -> None:
    q = item.question
    assert q is not None
    letters = LETTERS[: len(q.options)]
    expected = item.key_letters()
    try:
        correct = float(data["correct"])
        options = {str(k).upper(): float(v) for k, v in dict(data.get("options") or {}).items()}
        mistakes = {str(k).upper(): float(v) for k, v in dict(data.get("mistakes") or {}).items()}
        rtol = float(data.get("rtol", 5e-3))
        separation = float(data.get("min_separation", 0.05))
    except (TypeError, ValueError, KeyError) as exc:
        out.errors.append(f"mc_numeric: unreadable values ({exc})")
        return
    if q.type == "kprim":
        out.errors.append(
            "mc_numeric is for single and multi questions; answer a Kprim with mc_answer"
        )
        return
    if sorted(options) != list(letters):
        out.errors.append(f"mc_numeric: give the stated value of every option {', '.join(letters)}")
        return
    unknown = sorted(set(mistakes) - set(letters))
    if unknown:
        out.errors.append(f"mc_numeric: mistakes for unknown option(s) {', '.join(unknown)}")
        return
    # 4. each option's text reads as its stated value
    for i, letter in enumerate(letters):
        stated = option_value(q.options[i].text)
        if stated is None:
            out.warnings.append(f"option {letter}: cannot read a value from '{q.options[i].text}'")
        elif not close(options[letter], stated, rtol):
            out.errors.append(
                f"option {letter} reads {stated:.6g} (SI), the check states {options[letter]:.6g}"
            )
    # 1. exactly the marked options match the correct value
    matching = [L for L in letters if close(options[L], correct, rtol)]
    out.results.append(
        model.LedgerValue(key="key", expected=expected, computed=matching, ok=matching == expected)
    )
    if matching != expected:
        out.mismatches.append(
            f"the correct value {correct:.6g} matches option(s) {', '.join(matching) or '(none)'}, "
            f"which does not match the key{KEY_SEP}{', '.join(expected) or '(none)'}"
        )
    for letter in letters:
        if letter in expected:
            continue
        value = options[letter]
        # 2. each distractor reproduces its named mistake
        if letter in mistakes:
            ok = close(value, mistakes[letter], rtol)
            out.results.append(
                model.LedgerValue(
                    key=f"mistake-{letter}", expected=value, computed=mistakes[letter], ok=ok
                )
            )
            if not ok:
                out.mismatches.append(
                    f"distractor {letter} ({value:.6g}) does not follow from its mistake "
                    f"(computed {mistakes[letter]:.6g}); its why is wrong"
                )
        else:
            out.warnings.append(f"distractor {letter} names no mistake in the check")
        # 3. every distractor is well away from the correct value
        if correct and abs(value - correct) <= separation * abs(correct):
            out.mismatches.append(
                f"distractor {letter} ({value:.6g}) lies within {separation:.0%} of the correct "
                f"value {correct:.6g}"
            )


# --- the ledger state machine -----------------------------------------------------------------


def _method(path: Path | None) -> str | None:
    if path is None:
        return None
    return "script" if path.suffix == ".py" else "blind"


def _rounds(disputes: list[model.Dispute]) -> int:
    versions = list(dict.fromkeys(d.content_sha256 for d in disputes))
    return max(0, len(versions) - 1)


def _base(prev: model.VerifyEntry | None, item: VItem, at: dt.datetime) -> dict[str, Any]:
    keep = prev.model_dump() if prev is not None else {}
    return {
        **keep,
        "item": item.id,
        "kind": item.kind,
        "path": item.rel,
        "content_sha256": item.content_sha256,
        "checked_at": at,
    }


def _add_dispute(fields: dict[str, Any], item: VItem, dispute: model.Dispute) -> dict[str, Any]:
    disputes = [model.Dispute.model_validate(d) for d in fields.get("disputes") or []]
    last = disputes[-1] if disputes else None
    if (
        last is not None
        and last.content_sha256 == dispute.content_sha256
        and last.source == dispute.source
    ):
        dispute = dispute.model_copy(update={"confirmed": last.confirmed or dispute.confirmed})
        disputes[-1] = dispute  # the same version disputed again: refresh, not a new round
    else:
        disputes.append(dispute)
    rounds = _rounds(disputes)
    disputes[-1] = disputes[-1].model_copy(update={"round": rounds})
    fields["disputes"] = disputes
    fields["rounds"] = rounds
    fields["verified_at"] = None
    if rounds >= MAX_ROUNDS or fields.get("status") == "quarantined":
        fields["status"] = "quarantined"
        fields["note"] = fields.get("note") or (
            f"still disputed after {rounds} author fix round(s)"
        )
    else:
        fields["status"] = "disputed"
    return fields


def apply(
    prev: model.VerifyEntry | None,
    item: VItem,
    outcome: Outcome,
    check: Path | None,
    root: Path,
    at: dt.datetime | None = None,
) -> model.VerifyEntry:
    """The new ledger entry after a check run."""
    at = at or now()
    fields = _base(prev, item, at)
    fields.update(
        method=_method(check),
        check=check.relative_to(root).as_posix() if check else None,
        check_sha256=sha256_file(check) if check else None,
        results=outcome.results,
        problems=outcome.problems,
        warnings=outcome.warnings,
    )
    if outcome.result == "error":
        if fields.get("status") != "quarantined":
            fields["status"] = "unverified"
        fields["verified_at"] = None
    elif outcome.result == "pass":
        if prev is not None and prev.status == "quarantined":
            fields["warnings"] = [*outcome.warnings, "was quarantined before this check passed"]
        fields["status"] = "verified"
        fields["verified_at"] = at
        fields["note"] = None
    else:
        dispute = model.Dispute(
            at=at,
            round=0,
            content_sha256=item.content_sha256,
            source="verify",
            results=outcome.results,
            problems=outcome.mismatches,
        )
        fields = _add_dispute(fields, item, dispute)
    return model.VerifyEntry.model_validate(fields)


# --- commands ------------------------------------------------------------------------------------


def _row(
    item: VItem, entry: model.VerifyEntry | None, outcome: str, show_key: bool
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": item.id,
        "kind": item.kind,
        "path": display_path(item.doc.path),
        "rel": item.rel,
        "line": item.line,
        "outcome": outcome,
        "status": entry.status if entry else "unverified",
        "stale": bool(entry and is_stale(entry, item)),
    }
    if entry is not None:
        row.update(
            check=entry.check,
            rounds=entry.rounds,
            results=[r.model_dump(mode="json") for r in entry.results],
            problems=entry.problems,
            warnings=entry.warnings,
            note=entry.note,
            # whether the last dispute of this version was confirmed by a second method
            confirmed=bool(
                entry.disputes
                and entry.disputes[-1].confirmed
                and entry.disputes[-1].content_sha256 == item.content_sha256
            ),
            confirmations=[
                {"check": c.check, "method": c.method, "result": c.result}
                for c in entry.confirmations
                if c.content_sha256 == item.content_sha256
            ],
        )
        if not show_key:
            for r in row["results"]:
                r.pop("expected", None)
            row["problems"] = [hide_key(p) for p in entry.problems]
    return row


def hide_key(problem: str) -> str:
    """A problem without the key's value, for the verifier's eyes."""
    return problem.split(KEY_SEP)[0]


def summary(tree: CourseTree) -> dict[str, Any]:
    """Counts per status over every item, plus the quarantined items."""
    counts = {s: 0 for s in model.VERIFY_STATUSES}
    counts.update(fixed=0, stale=0, no_check=0)
    quarantined = []
    for item in items(tree):
        try:
            entry = read_ledger(tree.root, item.id)
        except ValueError:
            entry = None
        status = entry.status if entry else "unverified"
        counts[status] += 1
        if entry and entry.status == "verified" and entry.disputes:
            counts["fixed"] += 1
        if entry and is_stale(entry, item):
            counts["stale"] += 1
        if check_file(tree.root, item.id) is None:
            counts["no_check"] += 1
        if status == "quarantined":
            quarantined.append(
                {
                    "id": item.id,
                    "kind": item.kind,
                    "path": display_path(item.doc.path),
                    "note": entry.note if entry else None,
                    "rounds": entry.rounds if entry else 0,
                    "problems": entry.problems if entry else [],
                }
            )
    return {"counts": {"items": len(items(tree)), **counts}, "quarantined": quarantined}


def run(
    tree: CourseTree,
    target: str | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    show_key: bool = False,
) -> dict[str, Any]:
    """Run the checks of the selected items and update their ledger entries."""
    selected = select(tree, target)
    rows = []
    for item in selected:
        try:
            prev = read_ledger(tree.root, item.id)
        except ValueError:
            prev = None  # a broken entry is replaced by this run
        check = check_file(tree.root, item.id)
        if check is None:
            rows.append(_row(item, prev, "no-check", show_key))
            continue
        try:
            data = run_check(check, tree.root, timeout)
        except ValueError as exc:
            outcome = Outcome("error", errors=[str(exc)])
        else:
            outcome = compare(item, data)
        entry = apply(prev, item, outcome, check, tree.root)
        write_ledger(tree.root, entry)
        rows.append(_row(item, entry, outcome.result, show_key))
    return {"course": tree.id, "target": target or "all", "items": rows, **summary(tree)}


def status(
    tree: CourseTree, target: str | None = None, *, show_key: bool = False
) -> dict[str, Any]:
    """The ledger state of the selected items, without running anything."""
    rows = []
    for item in select(tree, target):
        try:
            entry = read_ledger(tree.root, item.id)
        except ValueError as exc:
            rows.append({**_row(item, None, "invalid-ledger", show_key), "problems": [str(exc)]})
            continue
        outcome = (
            "no-ledger" if entry is None else "stale" if is_stale(entry, item) else entry.status
        )
        rows.append(_row(item, entry, outcome, show_key))
    return {"course": tree.id, "target": target or "all", "items": rows, **summary(tree)}


def _fresh_entry(tree: CourseTree, item: VItem) -> model.VerifyEntry:
    entry = read_ledger(tree.root, item.id)
    if entry is None:
        raise VerifyError(
            f"{item.id} has no ledger entry yet; run `studykit verify {tree.id} {item.id}` first"
        )
    if is_stale(entry, item):
        raise VerifyError(
            f"{item.id} changed since its last check; run "
            f"`studykit verify {tree.id} {item.id}` first"
        )
    return entry


def confirm(
    tree: CourseTree,
    item_id: str,
    file: Path,
    *,
    method: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    show_key: bool = False,
) -> dict[str, Any]:
    """Run a second method (`checks/<id>.<tag>.py|json`) and record it.

    A dispute that the second method reproduces becomes confirmed. When the second method
    agrees with the key instead (or, on a verified item, disagrees with it), the two
    methods disagree and the item goes back to unverified until the checks are fixed.
    The problems name the key only with `show_key` (the verifier runs this).
    """
    item = find(tree, item_id)
    entry = _fresh_entry(tree, item)
    path = file if file.is_absolute() else (Path.cwd() / file)
    if not path.is_file():
        alt = tree.root / file
        path = alt if alt.is_file() else path
    path = path.resolve()
    checks = (tree.root / CHECKS_DIR).resolve()
    if (
        path.parent != checks
        or not path.name.startswith(f"{item.id}.")
        or path.suffix not in (".py", ".json")
    ):
        raise VerifyError(f"the second method goes into {CHECKS_DIR}/{item.id}.<tag>.py or .json")
    if entry.check and path == (tree.root / entry.check).resolve():
        raise VerifyError("the second method must be a different check file than the first")
    if not path.is_file():
        raise VerifyError(f"no such file {display_path(path)}")
    try:
        outcome = compare(item, run_check(path, tree.root, timeout))
    except ValueError as exc:
        outcome = Outcome("error", errors=[str(exc)])
    at = now()
    record = model.Confirmation(
        at=at,
        content_sha256=item.content_sha256,
        check=path.relative_to(tree.root.resolve()).as_posix(),
        check_sha256=sha256_file(path),
        method=method,
        result=outcome.result,
        results=outcome.results,
        problems=outcome.problems,
    )
    fields = entry.model_dump()
    fields["confirmations"] = [*entry.confirmations, record]
    fields["checked_at"] = at
    if (
        outcome.result == "mismatch"
        and entry.status in ("disputed", "quarantined")
        and entry.disputes
    ):
        last = entry.disputes[-1].model_copy(update={"confirmed": True})
        fields["disputes"] = [*entry.disputes[:-1], last]
    elif outcome.result == "pass" and entry.status == "verified":
        pass  # two methods agree with the key
    elif outcome.result != "error" and entry.status in ("verified", "disputed"):
        fields["status"] = "unverified"
        fields["verified_at"] = None
        fields["problems"] = [
            *entry.problems,
            f"the two methods disagree ({entry.check}: "
            f"{'pass' if entry.status == 'verified' else 'mismatch'}, {record.check}: "
            f"{outcome.result}); fix the wrong check and run verify again",
        ]
    new = model.VerifyEntry.model_validate(fields)
    write_ledger(tree.root, new)
    return {
        "course": tree.id,
        "id": item.id,
        "confirmation": outcome.result,
        "status": new.status,
        "problems": outcome.problems if show_key else [hide_key(p) for p in outcome.problems],
        "warnings": outcome.warnings,
    }


def dispute(
    tree: CourseTree, item_id: str, *, note: str, computed: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Record a dispute by hand, with the verifier's numbers (`--computed key=value`)."""
    item = find(tree, item_id)
    try:
        prev = read_ledger(tree.root, item.id)
    except ValueError:
        prev = None
    keys = {a.key: a for a in (_answers_of(item) or [])}
    results = []
    for key, value in (computed or {}).items():
        expected = (
            keys[key].value
            if key in keys and keys[key].value is not None
            else (keys[key].expr if key in keys else None)
        )
        number: Any = value
        with contextlib.suppress(ValueError):
            number = float(value)
        results.append(
            model.LedgerValue(
                key=key,
                expected=expected,
                computed=number,
                unit=keys[key].unit if key in keys else None,
                ok=False,
            )
        )
    at = now()
    fields = _base(prev, item, at)
    fields.setdefault("status", "disputed")
    fields["method"] = fields.get("method") or "manual"
    fields["problems"] = [note]
    record = model.Dispute(
        at=at,
        round=0,
        content_sha256=item.content_sha256,
        source="manual",
        note=note,
        confirmed=True,
        results=results,
        problems=[note],
    )
    entry = model.VerifyEntry.model_validate(_add_dispute(fields, item, record))
    write_ledger(tree.root, entry)
    return {"course": tree.id, "id": item.id, "status": entry.status, "rounds": entry.rounds}


def quarantine(tree: CourseTree, item_id: str, *, note: str) -> dict[str, Any]:
    """Quarantine an item by hand: hidden from the site and the PDFs until a check passes."""
    item = find(tree, item_id)
    try:
        prev = read_ledger(tree.root, item.id)
    except ValueError:
        prev = None
    fields = _base(prev, item, now())
    fields.update(status="quarantined", note=note, verified_at=None)
    fields["method"] = fields.get("method") or "manual"
    entry = model.VerifyEntry.model_validate(fields)
    write_ledger(tree.root, entry)
    return {"course": tree.id, "id": item.id, "status": entry.status}


def clear(tree: CourseTree, target: str) -> dict[str, Any]:
    """Delete ledger entries: of an item, topic or exam, `all`, `stale` (content changed
    since the check) or `orphans` (items that no longer exist)."""
    known = {i.id: i for i in items(tree)}
    if target == "orphans":
        ids = [i for i in ledger_ids(tree.root) if i not in known]
    elif target == "stale":
        ids = []
        for item_id in ledger_ids(tree.root):
            try:
                entry = read_ledger(tree.root, item_id)
            except ValueError:
                continue
            if entry is not None and item_id in known and is_stale(entry, known[item_id]):
                ids.append(item_id)
    else:
        ids = [i.id for i in select(tree, target)]
    removed = []
    for item_id in ids:
        path = ledger_path(tree.root, item_id)
        if path.is_file():
            path.unlink()
            removed.append(item_id)
    return {"course": tree.id, "target": target, "removed": removed}


# --- output ----------------------------------------------------------------------------------


def format_text(result: Mapping[str, Any]) -> str:
    lines = []
    for row in result.get("items", []):
        extra = []
        if row.get("check"):
            extra.append(row["check"])
        if row.get("rounds"):
            extra.append(f"round {row['rounds']}")
        if row.get("stale"):
            extra.append("stale")
        shown = (
            row["status"]
            if row["outcome"] in (row["status"], "no-ledger")
            else f"{row['status']} ({row['outcome']})"
        )
        lines.append(f"{row['id']:<28} {shown}" + (f"  [{', '.join(extra)}]" if extra else ""))
        for p in row.get("problems") or []:
            lines.append(f"    {p}")
        for w in row.get("warnings") or []:
            lines.append(f"    warning: {w}")
        if row["outcome"] == "no-check":
            lines.append(f"    no check yet: write checks/{row['id']}.py or .json")
    counts = result.get("counts", {})
    if counts:
        lines.append(
            f"verify: {counts['items']} item(s): {counts['verified']} verified "
            f"({counts['fixed']} fixed), {counts['disputed']} disputed, "
            f"{counts['quarantined']} quarantined, {counts['unverified']} unverified, "
            f"{counts['stale']} stale"
        )
    for q in result.get("quarantined", []):
        lines.append(f"quarantined: {q['id']} ({q['path']}): {q['note'] or 'no reason given'}")
    return "\n".join(lines)


def format_action(result: Mapping[str, Any]) -> str:
    """Text for --confirm, --dispute, --quarantine and --clear: one item (or the removed ids)."""
    if "removed" in result:
        removed = result["removed"]
        return f"cleared {len(removed)} ledger entr{'y' if len(removed) == 1 else 'ies'}" + (
            f": {', '.join(removed)}" if removed else ""
        )
    head = f"{result['id']:<28} {result['status']}"
    if "confirmation" in result:
        head += f"  (second method: {result['confirmation']})"
    if result.get("rounds"):
        head += f"  [round {result['rounds']}]"
    lines = [head]
    lines += [f"    {p}" for p in result.get("problems") or []]
    lines += [f"    warning: {w}" for w in result.get("warnings") or []]
    return "\n".join(lines)


def report_md(tree: CourseTree) -> str:
    """`state/verify/report.md`: counts, then every item that is not verified."""
    data = status(tree, show_key=True)
    c = data["counts"]
    lines = [
        f"# Verification report: {tree.id}",
        "",
        f"Generated {now().isoformat().replace('+00:00', 'Z')} by `studykit verify --report`.",
        "",
        "| Items | Verified | Fixed | Disputed | Quarantined | Unverified | Stale | No check |",
        "|---|---|---|---|---|---|---|---|",
        f"| {c['items']} | {c['verified']} | {c['fixed']} | {c['disputed']} | "
        f"{c['quarantined']} | {c['unverified']} | {c['stale']} | {c['no_check']} |",
        "",
    ]
    sections = [
        ("Quarantined (hidden from the site and the PDFs)", lambda r: r["status"] == "quarantined"),
        ("Disputed", lambda r: r["status"] == "disputed"),
        ("Stale (changed since the check)", lambda r: r["stale"] and r["status"] != "quarantined"),
        ("Unverified", lambda r: r["status"] == "unverified" and not r["stale"]),
    ]
    for title, keep in sections:
        rows = [r for r in data["items"] if keep(r)]
        if not rows:
            continue
        lines += [f"## {title}", ""]
        for r in rows:
            why = (
                r.get("note")
                or "; ".join(r.get("problems") or [])
                or ("no check" if r["outcome"] == "no-ledger" else r["outcome"])
            )
            lines.append(f"- `{r['id']}` ({r['rel']}:{r['line']}): {why}")
        lines.append("")
    return "\n".join(lines)


def write_report(tree: CourseTree) -> Path:
    path = tree.root / REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_md(tree), encoding="utf-8")
    return path


def parse_pairs(pairs: Iterable[str]) -> dict[str, str]:
    out = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key.strip():
            raise VerifyError(f"--computed takes key=value, got '{pair}'")
        out[key.strip()] = value.strip()
    return out
