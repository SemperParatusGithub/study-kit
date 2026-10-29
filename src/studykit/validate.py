"""`studykit validate`: every content check as an ordered list of stages (§4.3).

A stage is a function over one course that adds findings. Stages are registered with
`@stage(...)` in pipeline order; `--quick` runs only quick stages (up to and including
Math, used by the lint hook), `--release` adds release-only ones (Coverage). A stage whose
tools or inputs are not there yet (pandoc filters, figure builds, PDFs, the site) declares
`requires=` and is reported as skipped with an info note instead of failing, so later
phases plug in by registering a stage or by providing what `requires` looks for.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from studykit import findings as findings_mod
from studykit import model, tools
from studykit.content import (
    CODE_LANGUAGES,
    CourseTree,
    Doc,
    Formula,
    Item,
    Line,
    display_path,
)
from studykit.findings import Finding

# --- configuration and results ----------------------------------------------------------


@dataclass
class Config:
    root: Path = field(default_factory=tools.repo_root)
    denylist: Path | None = None  # default: <root>/pandoc/math-denylist.json
    katex: bool = True

    @property
    def denylist_path(self) -> Path:
        return self.denylist or self.root / "pandoc" / "math-denylist.json"


@dataclass
class StageResult:
    name: str
    status: str  # ok | warnings | failed | skipped
    notes: list[str] = field(default_factory=list)


@dataclass
class CourseReport:
    course: str
    path: str
    stages: list[StageResult] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


@dataclass
class Report:
    courses: list[CourseReport] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def findings(self) -> list[Finding]:
        return [f for c in self.courses for f in c.findings]

    @property
    def errors(self) -> int:
        return sum(f.is_error for f in self.findings)

    @property
    def warnings(self) -> int:
        return sum(f.severity == "warning" for f in self.findings)

    @property
    def ok(self) -> bool:
        return self.errors == 0

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "notes": self.notes,
            "courses": [
                {
                    "course": c.course,
                    "path": c.path,
                    "stages": [s.__dict__ for s in c.stages],
                }
                for c in self.courses
            ],
            "findings": [f.to_dict() for f in self.findings],
        }

    def format_text(self, label: str = "validate") -> str:
        lines = [f.format() for f in self.findings]
        for c in self.courses:
            for s in c.stages:
                for note in s.notes:
                    lines.append(f"info: {c.course}: {s.name}: {note}")
        lines.extend(f"info: {note}" for note in self.notes)
        lines.append(
            f"{label}: {self.errors} error(s), {self.warnings} warning(s) in "
            f"{len(self.courses)} course(s)"
        )
        return "\n".join(lines)


class Context:
    """One course under validation plus the stage's output channel."""

    def __init__(
        self,
        tree: CourseTree,
        config: Config,
        selected: set[str] | None,
        quick: bool,
        release: bool,
    ):
        self.tree = tree
        self.config = config
        self.selected = selected  # course-relative paths, None = whole course
        self.quick = quick
        self.release = release
        self.findings: list[Finding] = []
        self.notes: list[str] = []

    def docs(self, *kinds: str) -> list[Doc]:
        """Selected documents of the given kinds (all kinds when none are given)."""
        return [
            d
            for d in self.tree
            if (not kinds or d.kind in kinds) and (self.selected is None or d.rel in self.selected)
        ]

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def extend(self, items: Iterable[Finding]) -> None:
        self.findings.extend(items)

    def at(
        self,
        doc: Doc,
        line: int,
        col: int,
        code: str,
        message: str,
        fix: str,
        severity: str = "error",
    ) -> None:
        self.add(Finding(doc.display, line, col, code, message, fix, severity))  # type: ignore[arg-type]

    def at_yaml(self, doc: Doc, loc: list, code: str, message: str, fix: str, severity="error"):
        line, col = doc.yaml.locate(loc) if doc.yaml else (1, 1)
        self.at(doc, line, col, code, message, fix, severity)

    def note(self, text: str) -> None:
        self.notes.append(text)


@dataclass
class Stage:
    name: str
    code: str
    order: int
    run: Callable[[Context], None]
    quick: bool = False
    release_only: bool = False
    requires: Callable[[Context], str | None] | None = None


STAGES: list[Stage] = []


def stage(
    name: str,
    code: str,
    order: int,
    *,
    quick: bool = False,
    release_only: bool = False,
    requires: Callable[[Context], str | None] | None = None,
):
    """Register a validation stage; `requires(ctx)` returns why it cannot run, or None."""

    def register(fn: Callable[[Context], None]) -> Callable[[Context], None]:
        STAGES[:] = [s for s in STAGES if s.name != name]
        STAGES.append(Stage(name, code, order, fn, quick, release_only, requires))
        STAGES.sort(key=lambda s: s.order)
        return fn

    return register


# --- Structure (SK-STRUCT) ------------------------------------------------------------------

LAYOUT_HINT = {
    "summary": "summary/NN-<topic>.md",
    "exercises": "exercises/<topic>/<ex-id>.md",
    "mc": "mc/<topic>.md",
    "exams": "exams/<exam-id>/{exam.yaml, NN-<task-id>.md, mc.md}",
    "figures": "figures/<slug>.py",
    "analysis": "analysis/{exam-profile.yaml, notation.yaml}",
    "sources": "sources/{manifest.yaml, outline.md}",
}


@stage("Structure", "SK-STRUCT", 10, quick=True)
def check_structure(ctx: Context) -> None:
    tree = ctx.tree
    for doc in ctx.docs():
        if doc.kind == "unknown":
            top = doc.rel.split("/", 1)[0] if "/" in doc.rel else ""
            ctx.at(
                doc,
                1,
                1,
                "SK-STRUCT-PATH",
                f"'{doc.rel}' is not a known course file",
                "move or rename it to "
                + LAYOUT_HINT.get(top, "the layout in docs/architecture.md §2.1"),
            )
            continue
        _check_names(ctx, doc)
    overview = tree.get("overview.md")
    if overview and overview in ctx.docs("overview") and overview.body and not overview.split.error:
        h2 = overview.body.headings(2)
        if len(h2) != 6:
            ctx.at(
                overview,
                h2[6][0] if len(h2) > 6 else (h2[-1][0] if h2 else 1),
                1,
                "SK-STRUCT-SECTIONS",
                f"overview.md has {len(h2)} '##' sections, expected 6",
                "use the six sections of docs/architecture.md §2.12 in their order",
            )
    _check_required_files(ctx)
    _check_ids(ctx)
    _check_exams(ctx)


def _check_required_files(ctx: Context) -> None:
    """overview.md, plan.yaml and (if allowed) cheatsheet.md; course.yaml is checked first.

    A course is authored step by step (§5.4), so a missing file is a warning until
    `--release`, where it is an error.
    """
    tree = ctx.tree
    course = tree.model
    required = [
        ("overview.md", "author it with the six sections of docs/architecture.md §2.12"),
        ("plan.yaml", "run `studykit plan <course>`"),
    ]
    if course is not None and course.cheatsheet.allowed:
        required.append(("cheatsheet.md", "`/regenerate <course> cheatsheet`, then fit it"))
    for rel, fix in required:
        if tree.get(rel) is None:
            ctx.add(
                Finding(
                    display_path(tree.root / rel),
                    1,
                    1,
                    "SK-STRUCT-MISSING",
                    f"{rel} is missing" + ("" if ctx.release else " (required for --release)"),
                    fix,
                    "error" if ctx.release else "warning",
                )
            )


def _check_names(ctx: Context, doc: Doc) -> None:
    """File names and directories must agree with the ids and topics inside."""
    ident, topic = doc.get("id"), doc.get("topic")
    expected_id = {
        "exercise": doc.parts.get("id"),
        "exam-task": doc.parts.get("id"),
        "exam": doc.parts.get("exam"),
        "course": ctx.tree.id,
    }.get(doc.kind)
    if expected_id and isinstance(ident, str) and ident != expected_id:
        where = "directory" if doc.kind in {"exam", "course"} else "file name"
        ctx.at_yaml(
            doc,
            ["id"],
            "SK-STRUCT-ID",
            f"id '{ident}' does not match the {where} '{expected_id}'",
            f"rename the {where} or set id: {expected_id} (ids are never renamed once used)",
        )
    if doc.kind in {"summary", "exercise", "mc"} and isinstance(topic, str):
        expected = doc.parts.get("topic")
        if topic != expected:
            layout = {
                "summary": f"summary/NN-{topic}.md",
                "exercise": f"exercises/{topic}/{doc.path.name}",
                "mc": f"mc/{topic}.md",
            }[doc.kind]
            ctx.at_yaml(
                doc,
                ["topic"],
                "SK-STRUCT-PATH",
                f"topic '{topic}' does not match the path '{doc.rel}'",
                f"move the file to {layout} or fix the topic",
            )


def _check_ids(ctx: Context) -> None:
    tree = ctx.tree
    data = tree.course_doc.data if tree.course_doc else None
    retired = data.get("retired_ids") if isinstance(data, dict) else None
    retired = set(retired) if isinstance(retired, list) else set()
    by_id: dict[str, list[Item]] = {}
    summaries: dict[str, list[Item]] = {}
    for item in tree.items:
        if tree.get(item.rel) is None:
            continue
        if item.kind == "summary" and item.topic:
            summaries.setdefault(item.topic, []).append(item)
            continue
        if item.kind not in {"exercise", "mc", "exam-task", "exam"}:
            continue
        by_id.setdefault(item.id, []).append(item)
        if item.id in retired:
            ctx.at(
                tree.get(item.rel),
                item.line,
                1,
                "SK-STRUCT-RETIRED",
                f"id '{item.id}' is listed in course.yaml retired_ids",
                "retired ids are never reused; choose a new id",
            )
    # Every occurrence gets the finding, so `lint` on the file that introduced the duplicate
    # reports it, whichever file discovery happens to visit first.
    for item_id, items in by_id.items():
        for item, others in _with_others(items):
            ctx.at(
                tree.get(item.rel),
                item.line,
                1,
                "SK-STRUCT-DUP",
                f"id '{item_id}' is also used in {others}",
                "choose a new id for the newer item; existing ids are never renamed",
            )
    for topic, items in summaries.items():
        for item, others in _with_others(items):
            ctx.at(
                tree.get(item.rel),
                1,
                1,
                "SK-STRUCT-DUP",
                f"topic '{topic}' has another summary chapter: {others}",
                "keep one chapter per topic; merge the newer chapter into the existing one",
            )


def _with_others(items: list[Item]) -> Iterator[tuple[Item, str]]:
    """Each item of a duplicate group with the locations of the others."""
    if len(items) < 2:
        return
    for item in items:
        others = ", ".join(f"{o.rel}:{o.line}" for o in items if o is not item)
        yield item, others


def _check_exams(ctx: Context) -> None:
    tree = ctx.tree
    exam_dirs: dict[str, list[Doc]] = {}
    for doc in tree:
        if doc.kind in {"exam", "exam-task", "exam-mc"}:
            exam_dirs.setdefault(doc.parts["exam"], []).append(doc)
    for exam_id, docs in exam_dirs.items():
        exam_doc = tree.get(f"exams/{exam_id}/exam.yaml")
        if exam_doc is None:
            ctx.at(
                docs[0],
                1,
                1,
                "SK-STRUCT-MISSING",
                f"exams/{exam_id}/ has no exam.yaml",
                "add exam.yaml with id, title, duration_min, points, pass_points and tasks",
            )
            continue
        exam = exam_doc.model
        if exam is None:
            continue
        listed = set(exam.tasks)
        for doc in docs:
            if doc.kind == "exam-task" and doc.path.name not in listed:
                ctx.at(
                    doc,
                    1,
                    1,
                    "SK-STRUCT-PATH",
                    f"{doc.path.name} is not listed in exam.yaml tasks",
                    "add it to tasks: or delete the file",
                )
            if doc.kind == "exam-mc" and exam.mc is None:
                ctx.at(
                    doc,
                    1,
                    1,
                    "SK-STRUCT-PATH",
                    "mc.md exists but exam.yaml has no mc part",
                    "add mc: {file: mc.md, points_each: …} to exam.yaml or delete mc.md",
                )
        _check_exam_points(ctx, exam_doc, exam)


def _check_exam_points(ctx: Context, exam_doc: Doc, exam: model.Exam) -> None:
    folder = exam_doc.rel.rsplit("/", 1)[0]
    task_points: list[float] = []
    for name in exam.tasks:
        task = ctx.tree.get(f"{folder}/{name}")
        if task is None or task.model is None:
            return  # reported elsewhere; the sum would be meaningless
        task_points.append(task.model.points)
    mc_points = 0.0
    if exam.mc is not None:
        mc_doc = ctx.tree.get(f"{folder}/{exam.mc.file}")
        if mc_doc is None or mc_doc.body is None or mc_doc.split.error:
            return
        mc_points = len(mc_doc.body.questions) * exam.mc.points_each
    total = sum(task_points) + mc_points
    if abs(total - exam.points) > 1e-9:
        ctx.at_yaml(
            exam_doc,
            ["points"],
            "SK-STRUCT-POINTS",
            f"tasks ({sum(task_points):g}) and MC ({mc_points:g}) add up to {total:g}, "
            f"but the exam has {exam.points:g} points",
            "adjust task points, the number of MC questions, points_each or points",
        )


# --- Schema (SK-SCHEMA, SK-YAML) --------------------------------------------------------


@stage("Schema", "SK-SCHEMA", 20, quick=True)
def check_schema(ctx: Context) -> None:
    for doc in ctx.docs():
        if doc.is_markdown and doc.split.error:
            ctx.at(
                doc,
                1,
                1,
                "SK-SCHEMA-FRONTMATTER",
                doc.split.error,
                "start the file with a '---' line, the YAML fields, and a closing '---' line",
            )
            continue
        if doc.yaml is not None:
            ctx.extend(doc.yaml.findings)
            ctx.extend(doc.validated[1])


# --- Fences (SK-BLOCK) --------------------------------------------------------------------


@stage("Fences", "SK-BLOCK", 30, quick=True)
def check_fences(ctx: Context) -> None:
    for doc in ctx.docs():
        body = doc.body
        if body is None or doc.split.error:
            continue
        body.blocks  # noqa: B018 - runs the fence scanner
        ctx.extend(f for f in body.findings if f.code.startswith("SK-BLOCK"))
        for line, info in body.code_blocks:
            lang = info.split()[0].lstrip("{.") if info else ""
            if lang not in CODE_LANGUAGES:
                ctx.at(
                    doc,
                    line,
                    1,
                    "SK-BLOCK-CODE",
                    f"code block language '{lang}' is not allowed"
                    if lang
                    else "code block without a language",
                    f"write ```<language> with one of: {' '.join(CODE_LANGUAGES)}",
                )
        if doc.kind in {"exercise", "exam-task"}:
            _check_block_order(ctx, doc)


def _check_block_order(ctx: Context, doc: Doc) -> None:
    body = doc.body
    assert body is not None
    blocks = [b for b in body.blocks if b.known]
    hints = [b for b in blocks if b.name == "hint"]
    solutions = [b for b in blocks if b.name == "solution"]
    if not 1 <= len(hints) <= 3:
        line = body.lines[hints[3].open_line].no if len(hints) > 3 else body.lines[-1].no
        what = "an exercise" if doc.kind == "exercise" else "an exam task"
        ctx.at(
            doc,
            line if hints else 1,
            1,
            "SK-BLOCK-HINTS",
            f"{len(hints)} hint blocks; {what} has 1 to 3",
            "order hints principle -> set-up -> key intermediate result",
        )
    if len(solutions) != 1:
        line = body.lines[solutions[1].open_line].no if len(solutions) > 1 else 1
        ctx.at(
            doc,
            line,
            1,
            "SK-BLOCK-SOLUTION",
            f"{len(solutions)} solution blocks, expected exactly one",
            "end the file with one ::: solution block",
        )
        return
    solution = solutions[0]
    end = solution.close_line if solution.close_line is not None else len(body.lines)
    trailing = [ln for ln in body.lines[end + 1 :] if ln.text.strip()]
    later = [b for b in blocks if b.open_line > solution.open_line]
    if trailing or later:
        line = trailing[0].no if trailing else body.lines[later[0].open_line].no
        ctx.at(
            doc,
            line,
            1,
            "SK-BLOCK-SOLUTION",
            "content after the solution block",
            "the solution is the last block; move hints and text above it",
        )


# --- MC (SK-MCQ) --------------------------------------------------------------------------

OPTION_COUNTS = {"single": (3, 5), "multi": (4, 6), "kprim": (4, 4)}
MCQ_ATTRS = {"type", "difficulty", "tags", "source", "pin-last"}
ALL_OF_THE_ABOVE_RE = re.compile(
    r"\b(?:all(?:\s+of)?\s+(?:the\s+)?(?:above|these|listed)"
    r"|alle\s+(?:der\s+)?(?:oben\s+|vorher\s+|zuvor\s+)?(?:genannten\s+|obigen\s+)?"
    r"(?:aussagen|antworten|optionen|möglichkeiten)\b(?!\s+(?:außer|bis))"
    r"|alle\s+(?:oben\s+)?genannten\b)",
    re.IGNORECASE,
)
NONE_OF_THE_ABOVE_RE = re.compile(
    r"\b(?:none\s+of\s+(?:the\s+)?(?:above|these|them)"
    r"|keine\s+(?:der|dieser)\s+(?:oben\s+)?(?:genannten\s+)?"
    r"(?:aussagen|antworten|optionen|möglichkeiten)"
    r"|keine\s+davon)\b",
    re.IGNORECASE,
)
LETTER_REF_RE = re.compile(
    r"\b(?:option|optionen|antwort|antworten|antwortmöglichkeit|aussage|aussagen|"
    r"answer|answers|choice|choices|statement|statements)\s+\(?[A-F]\)?(?![\w])",
    re.IGNORECASE,
)
SOURCE_ATTR_RE = re.compile(rf"^{model.KEBAB}:[0-9]+$")


def _plain(text: str) -> str:
    """Text with inline math removed, for wording checks."""
    return model.INLINE_MATH_RE.sub(" ", text)


@stage("MC", "SK-MCQ", 40, quick=True)
def check_mc(ctx: Context) -> None:
    for doc in ctx.docs("mc", "exam-mc"):
        body = doc.body
        if body is None or doc.split.error:
            continue
        body.questions  # noqa: B018 - runs the question parser
        ctx.extend(f for f in body.findings if f.code.startswith("SK-MCQ"))
        for ln in body.outside_blocks():
            if ln.text.strip():
                ctx.at(
                    doc,
                    ln.no,
                    1,
                    "SK-MCQ-FORMAT",
                    "text outside an mcq block",
                    "an MC bank contains only :::: {.mcq …} blocks",
                )
                break
        for q in body.questions:
            _check_question(ctx, doc, q)
        _check_bias(ctx, doc)


def _check_question(ctx: Context, doc: Doc, q) -> None:
    attrs = q.block.attrs
    fix_attrs = 'write :::: {.mcq #mc-<topic>-NNN type="single" difficulty="2"}'
    problems = []
    if not q.id or not model.MC_ID_RE.match(q.id):
        problems.append(f"id '{q.id or ''}' does not match mc-<topic>-NNN")
    extra_classes = [c for c in q.block.classes[1:]]
    if extra_classes:
        problems.append(f"extra classes {extra_classes}")
    if attrs.get("type") not in OPTION_COUNTS:
        problems.append(f"type must be single, multi or kprim (got {attrs.get('type')!r})")
    if attrs.get("difficulty") not in {"1", "2", "3", "4"}:
        problems.append(f"difficulty must be 1 to 4 (got {attrs.get('difficulty')!r})")
    if attrs.get("pin-last", "false") not in {"true", "false"}:
        problems.append("pin-last must be true or false")
    if "source" in attrs and not SOURCE_ATTR_RE.match(attrs["source"]):
        problems.append(f"source must be doc:page (got {attrs['source']!r})")
    unknown = sorted(set(attrs) - MCQ_ATTRS)
    if unknown:
        problems.append(f"unknown attributes {unknown}")
    for problem in problems:
        ctx.at(doc, q.line, 1, "SK-MCQ-ATTR", problem, fix_attrs)
    topic = model.mc_topic(q.id or "")
    if topic is not None:
        bank_topic = doc.parts.get("topic")
        if doc.kind == "mc" and topic != bank_topic:
            ctx.at(
                doc,
                q.line,
                1,
                "SK-STRUCT-TOPIC",
                f"question id '{q.id}' names topic '{topic}', but the bank is '{bank_topic}'",
                f"number it mc-{bank_topic}-NNN",
            )
        elif ctx.tree.topics and topic not in ctx.tree.topics:
            ctx.at(
                doc,
                q.line,
                1,
                "SK-STRUCT-TOPIC",
                f"question id '{q.id}' names unknown topic '{topic}'",
                f"use a course topic: {', '.join(ctx.tree.topics)}",
            )

    qtype = attrs.get("type")
    if qtype in OPTION_COUNTS:
        low, high = OPTION_COUNTS[qtype]
        n = len(q.options)
        if not low <= n <= high:
            want = f"exactly {low}" if low == high else f"{low} to {high}"
            ctx.at(
                doc,
                q.line,
                1,
                "SK-MCQ-COUNT",
                f"{qtype} question has {n} options, expected {want}",
                f"write {want} '- [ ]' / '- [x]' options",
            )
        correct = sum(o.correct for o in q.options)
        if qtype == "single" and correct != 1 and n:
            ctx.at(
                doc,
                q.line,
                1,
                "SK-MCQ-KEY",
                f"single-choice question has {correct} options marked [x]",
                "mark exactly one option [x]",
            )
        if qtype == "multi" and n and (correct == 0 or correct == n):
            ctx.at(
                doc,
                q.line,
                1,
                "SK-MCQ-KEY",
                f"multiple-choice question has {correct} of {n} options marked [x]",
                "mark at least one option [x] and leave at least one [ ]",
            )
    if not q.options:
        return
    for option in q.options:
        if len(option.paragraphs) != 2:
            ctx.at(
                doc,
                option.line,
                1,
                "SK-MCQ-WHY",
                "option has no why paragraph"
                if len(option.paragraphs) == 1
                else f"option has {len(option.paragraphs)} paragraphs, expected 2",
                "follow the option line with a blank line and one paragraph, indented two "
                "spaces, saying why it is right or which mistake it models",
            )
        if ALL_OF_THE_ABOVE_RE.search(_plain(option.text)):
            ctx.at(
                doc,
                option.line,
                1,
                "SK-MCQ-ALL-ABOVE",
                "'all of the above' option",
                "use a multi question instead; options are shuffled",
            )
        if LETTER_REF_RE.search(_plain(option.why)):
            ctx.at(
                doc,
                option.line,
                1,
                "SK-MCQ-LETTER",
                "why text refers to an option by letter",
                "options are shuffled; name the statement instead of its letter",
            )
    if len(q.explanations) != 1:
        line = q.explanations[1][0] if len(q.explanations) > 1 else q.line
        ctx.at(
            doc,
            line,
            1,
            "SK-MCQ-EXPLANATION",
            f"{len(q.explanations)} explanation blocks, expected exactly one",
            "end the question with one ::: explanation block",
        )
    for line, text in q.explanations:
        if not text.strip():
            ctx.at(
                doc,
                line,
                1,
                "SK-MCQ-EXPLANATION",
                "empty explanation",
                "explain the underlying concept in the explanation block",
            )
        if LETTER_REF_RE.search(_plain(text)):
            ctx.at(
                doc,
                line,
                1,
                "SK-MCQ-LETTER",
                "explanation refers to an option by letter",
                "options are shuffled; name the statement instead of its letter",
            )
    if attrs.get("pin-last") == "true" and not NONE_OF_THE_ABOVE_RE.search(
        _plain(q.options[-1].text)
    ):
        ctx.at(
            doc,
            q.line,
            1,
            "SK-MCQ-PIN-LAST",
            "pin-last is set, but the last option is not 'none of the above'",
            "remove pin-last, or make the last option 'Keine der Aussagen ist richtig.'",
        )


def _check_bias(ctx: Context, doc: Doc) -> None:
    singles = [q for q in doc.body.questions if q.type == "single" and len(q.options) >= 3]  # type: ignore[union-attr]
    if len(singles) < 4:
        return
    longest = 0
    for q in singles:
        lengths = [len(o.text) for o in q.options]
        best = max(lengths)
        winners = [o for o, n in zip(q.options, lengths, strict=True) if n == best]
        if len(winners) == 1 and winners[0].correct:
            longest += 1
    if longest / len(singles) > 0.5:
        ctx.at(
            doc,
            1,
            1,
            "SK-MCQ-BIAS",
            f"the correct option is the longest in {longest} of {len(singles)} "
            "single-choice questions",
            "make distractors as long and as specific as the correct option",
            "warning",
        )
    _check_letters(
        ctx, doc, [q for q in singles if q.id and sum(o.correct for o in q.options) == 1]
    )


PDF_KEYS = "ABCDEFGHIJ"
U32 = 0xFFFFFFFF


def _fnv1a(text: str) -> int:
    h = 0x811C9DC5
    for byte in text.encode("utf-8"):
        h = ((h ^ byte) * 0x01000193) & U32
    return h


def _mulberry32(seed: int) -> Callable[[], float]:
    state = seed & U32

    def rand() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & U32
        t = state
        t = ((t ^ (t >> 15)) * (t | 1)) & U32
        t = (t ^ ((t + (((t ^ (t >> 7)) * (t | 61)) & U32)) & U32)) & U32
        return ((t ^ (t >> 14)) & U32) / 4294967296

    return rand


def pdf_order(question_id: str, n: int, pin_last: bool = False) -> list[int]:
    """Source indices (0-based) in PDF display order; mirrors `M.order` in mcq.lua.

    FNV-1a 32-bit of the id seeds mulberry32, then Fisher-Yates from the end; pin-last
    keeps the last option in place.
    """
    order = list(range(n))
    rand = _mulberry32(_fnv1a(question_id))
    for i in range(n - 1 if pin_last else n, 1, -1):
        j = int(rand() * i)
        order[i - 1], order[j] = order[j], order[i - 1]
    return order


def _check_letters(ctx: Context, doc: Doc, singles: list) -> None:
    """Warn when one letter carries most correct answers after the PDF shuffle."""
    if len(singles) < 4:
        return
    letters: dict[str, list[str]] = {}
    for q in singles:
        order = pdf_order(q.id, len(q.options), q.block.attrs.get("pin-last") == "true")
        shown = next(k for k, src in enumerate(order) if q.options[src].correct)
        letters.setdefault(PDF_KEYS[shown], []).append(q.id)
    letter, ids = max(letters.items(), key=lambda kv: len(kv[1]))
    if len(ids) / len(singles) > 0.5:
        ctx.at(
            doc,
            1,
            1,
            "SK-MCQ-BIAS",
            f"after the PDF shuffle the correct answer is ({letter}) in {len(ids)} of "
            f"{len(singles)} single-choice questions: {', '.join(ids)}",
            "move the correct option to another place in the source of some of these questions; "
            "the shuffle is seeded by the id, so the letter follows the source position",
            "warning",
        )


# --- Math (SK-MATH) -----------------------------------------------------------------------

ALLOWED_ENVS = {"aligned", "gathered", "cases", "pmatrix", "bmatrix", "Bmatrix"}
TEX_TOKEN_RE = re.compile(r"\\(?:[A-Za-z]+|.)|\S")
BEGIN_RE = re.compile(r"\\begin\s*\{([^}]*)\}")
MINUS = "\u2212"
NUMBER_RE = re.compile(rf"(?<![\w.,}}])[-{MINUS}]?[0-9]+(?:(?:\{{,\}}|,|\.)[0-9]+)?(?![0-9])")


@dataclass
class DenyEntry:
    token: str
    use: str
    kind: str
    tokens: list[str]
    env: str | None


def tex_tokens(tex: str) -> list[str]:
    return TEX_TOKEN_RE.findall(tex)


def load_denylist(path: Path) -> list[DenyEntry]:
    entries = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for e in entries:
        token = e["token"]
        env = token[4:] if token.startswith("env:") else None
        out.append(
            DenyEntry(token, e.get("use", ""), e.get("kind", "fails"), tex_tokens(token), env)
        )
    return out


def denied(tex: str, denylist: list[DenyEntry]) -> list[DenyEntry]:
    """Denylist entries used in `tex`; control words match exactly (\\R never hits \\Rightarrow)."""
    tokens = tex_tokens(tex)
    envs = _environments(tex)
    hits = []
    for entry in denylist:
        if entry.env is not None:
            if any(name == entry.env and not wrapped for name, wrapped in envs):
                hits.append(entry)
            continue
        n = len(entry.tokens)
        if n and any(tokens[i : i + n] == entry.tokens for i in range(len(tokens) - n + 1)):
            hits.append(entry)
    return hits


def _environments(tex: str) -> list[tuple[str, bool]]:
    """(name, wrapped) per \\begin; wrapped = a matrix directly inside \\left<delim>."""
    out = []
    for m in BEGIN_RE.finditer(tex):
        before = tex_tokens(tex[: m.start()])
        wrapped = len(before) >= 2 and before[-2] == "\\left" and m.group(1) == "matrix"
        out.append((m.group(1).strip(), wrapped))
    return out


def katex_available(root: Path) -> str | None:
    if shutil.which("node") is None:
        return "node is not on PATH"
    if not (root / "site" / "scripts" / "check-math.mjs").is_file():
        return "site/scripts/check-math.mjs is missing"
    if not (root / "site" / "node_modules" / "katex").is_dir():
        return "site/node_modules is not installed (run `just setup`)"
    return None


def katex_errors(root: Path, formulas: list[tuple[str, bool]]) -> list[str | None]:
    payload = json.dumps([{"tex": t, "display": d} for t, d in formulas])
    proc = subprocess.run(
        ["node", str(root / "site" / "scripts" / "check-math.mjs")],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
        cwd=root / "site",
        timeout=120,
    )
    return [None if r["ok"] else r["error"] for r in json.loads(proc.stdout)]


def frontmatter_formulas(doc: Doc) -> list[Formula]:
    """Inline math in answer labels, rubric criteria and objectives."""
    data = doc.data
    if not isinstance(data, dict) or doc.yaml is None or not doc.yaml.ok:
        return []
    paths: list[tuple[list, Any]] = []
    for i, a in enumerate(data.get("answers") or []):
        if isinstance(a, dict):
            paths.append((["answers", i, "label"], a.get("label")))
    for i, r in enumerate(data.get("rubric") or []):
        if isinstance(r, dict):
            paths.append((["rubric", i, "criterion"], r.get("criterion")))
    for i, o in enumerate(data.get("objectives") or []):
        paths.append((["objectives", i], o))
    out = []
    for loc, value in paths:
        if isinstance(value, str):
            line, col = doc.yaml.locate(loc)
            for m in model.INLINE_MATH_RE.finditer(value):
                out.append(Formula(m.group()[1:-1], False, line, col))
    return out


@stage("Math", "SK-MATH", 50, quick=True)
def check_math(ctx: Context) -> None:
    docs = [d for d in ctx.docs() if d.body is not None and not d.split.error]
    formulas: list[tuple[Doc, Formula]] = []
    for doc in docs:
        body = doc.body
        assert body is not None
        for f in body.formulas:
            formulas.append((doc, f))
        ctx.extend(f for f in body.findings if f.code.startswith("SK-MATH"))
        for f in frontmatter_formulas(doc):
            formulas.append((doc, f))

    denylist: list[DenyEntry] = []
    path = ctx.config.denylist_path
    if path.is_file():
        denylist = load_denylist(path)
    else:
        ctx.note(f"denylist not checked: {display_path(path)} not found")

    clean: list[tuple[Doc, Formula]] = []
    for doc, f in formulas:
        hits = denied(f.tex, denylist)
        for entry in hits:
            ctx.at(
                doc,
                f.line,
                f.col,
                "SK-MATH-DENIED",
                f"'{entry.token}' is not allowed in math"
                + (" (it converts silently wrong in the PDF)" if entry.kind == "silent" else ""),
                entry.use or "rewrite the formula without it",
            )
        env_problem = False
        for name, wrapped in _environments(f.tex):
            if name in ALLOWED_ENVS or wrapped or any(e.env == name for e in hits):
                continue
            env_problem = True
            ctx.at(
                doc,
                f.line,
                f.col,
                "SK-MATH-ENV",
                f"environment '{name}' is not allowed",
                "use aligned, gathered, cases, pmatrix, bmatrix or Bmatrix "
                "(a determinant is \\left|\\begin{matrix}…\\end{matrix}\\right|)",
            )
        if not hits and not env_problem:
            clean.append((doc, f))

    if ctx.config.katex and clean:
        reason = katex_available(ctx.config.root)
        if reason:
            ctx.note(f"KaTeX strict check skipped: {reason}")
        else:
            try:
                errors = katex_errors(ctx.config.root, [(f.tex, f.display) for _, f in clean])
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                ctx.note(f"KaTeX strict check failed to run: {exc}")
                errors = [None] * len(clean)
            for (doc, f), error in zip(clean, errors, strict=True):
                if error:
                    ctx.at(
                        doc,
                        f.line,
                        f.col,
                        "SK-MATH-KATEX",
                        "KaTeX (strict) rejects the formula: " + error.replace("\u0332", ""),
                        "use the dialect of docs/architecture.md §2.3; words go in \\text{…}",
                    )

    for doc in ctx.docs("exercise", "exam-task"):
        if doc.body is not None and not doc.split.error:
            _check_hint_leak(ctx, doc)


def _numbers(text: str) -> list[float]:
    out = []
    for m in NUMBER_RE.finditer(text):
        raw = m.group().replace(MINUS, "-").replace("{,}", ".").replace(",", ".")
        try:
            out.append(float(raw))
        except ValueError:
            continue
    return out


def _significant(x: float) -> int:
    digits = f"{abs(x):.10g}".replace(".", "").lstrip("0")
    return len(digits.rstrip("0")) or 1


def _check_hint_leak(ctx: Context, doc: Doc) -> None:
    answers = doc.get("answers")
    if not isinstance(answers, list):
        return
    keys = []
    for a in answers:
        if not isinstance(a, dict):
            continue
        value = a.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value == 0:
            continue
        tol = max(
            abs(value) * a["rtol"] if isinstance(a.get("rtol"), (int, float)) else 0,
            a["atol"] if isinstance(a.get("atol"), (int, float)) else 0,
        )
        tol = tol or abs(value) * 1e-3
        keys.append((str(a.get("key")), float(value), tol))
    if not keys:
        return
    body = doc.body
    assert body is not None
    for block in body.blocks:
        if block.name != "hint":
            continue
        lines: list[Line] = body.block_text(block)
        for ln in lines:
            for n in _numbers(ln.text):
                if n.is_integer() and abs(n) < 10:
                    continue
                for key, value, tol in keys:
                    leaked = abs(abs(n) - abs(value)) <= tol
                    if not leaked and _significant(n) >= 3:
                        leaked = any(
                            abs(abs(n) * 10**k - abs(value)) <= tol for k in range(-12, 13, 3)
                        )
                    if leaked:
                        ctx.at(
                            doc,
                            ln.no,
                            1,
                            "SK-MATH-HINT-LEAK",
                            f"hint contains {n:g}, the answer '{key}'",
                            "give the method or an intermediate result, never the final value",
                            "warning",
                        )
                        break


# --- Pandoc filter run (needs the Lua filters from pandoc/) ----------------------------------


def _pandoc_ready(ctx: Context) -> str | None:
    from studykit import pandoc

    if not (ctx.config.root / "pandoc" / "filters" / "studykit.lua").is_file():
        return "pandoc/filters/studykit.lua not found"
    if not hasattr(pandoc, "run_filtered"):
        return "studykit.pandoc.run_filtered is not available"
    if not tools.bin_path(ctx.config.root, "pandoc").exists():
        return "pandoc is not installed in .tools/bin (run `just setup`)"
    return None


@stage("Pandoc", "SK-PANDOC", 55, quick=True, requires=_pandoc_ready)
def check_pandoc(ctx: Context) -> None:
    """Run every selected file through the Lua filters (guard, mcq, math, refs, …)."""
    from studykit import index, pandoc

    index.write(ctx.tree)
    for doc in ctx.docs():
        if doc.body is None or doc.split.error:
            continue
        try:
            pandoc.run_filtered(ctx.tree.root, doc.rel, "json")  # type: ignore[attr-defined]
        except Exception as exc:  # any pandoc failure is a finding
            found = findings_mod.parse(str(exc))
            last = str(exc).strip().splitlines()[-1:] or [type(exc).__name__]
            if not found:
                ctx.at(
                    doc,
                    1,
                    1,
                    "SK-PANDOC-FAIL",
                    f"pandoc failed: {last[0]}",
                    "run `studykit lint` on the file and fix the reported construct",
                )
            for f in found:
                path = Path(f.path)
                if not path.is_absolute() and (ctx.tree.root / path).exists():
                    f = Finding(
                        display_path(ctx.tree.root / path),
                        f.line,
                        f.col,
                        f.code,
                        f.message,
                        f.fix,
                        f.severity,
                    )
                ctx.add(f)


# --- References (SK-REF) -------------------------------------------------------------------

SRC_RE = re.compile(rf"^src:(?P<doc>{model.KEBAB})(?:#p=(?P<page>[0-9]+))?$")
EXTERNAL_RE = re.compile(r"^(?:https?://|mailto:)")


@stage("References", "SK-REF", 60)
def check_references(ctx: Context) -> None:
    tree = ctx.tree
    targets = {
        "ex": set(tree.ids("exercise")),
        "mc": {i.id for i in tree.items if i.kind == "mc" and i.rel.startswith("mc/")},
        "topic": set(tree.topics),
        "exam": set(tree.ids("exam")),
    }
    exam_mc = {i.id for i in tree.items if i.kind == "mc" and i.rel.startswith("exams/")}
    for doc in tree:
        if doc.body is None or doc.split.error:
            continue
        for link in doc.body.links:
            _check_link(ctx, doc, link, targets, exam_mc)
        _check_frontmatter_sources(ctx, doc)
    plan = tree.get("plan.yaml")
    if plan is not None and plan.model is not None:
        _check_plan(ctx, plan, targets)
    for exam_doc in tree.of_kind("exam"):
        _check_exam_refs(ctx, exam_doc)
    archetypes = tree.archetypes
    tasks = [d for d in tree.of_kind("exam-task") if isinstance(d.get("archetype"), str)]
    if tasks and archetypes is None:
        ctx.note("archetypes not checked: analysis/exam-profile.yaml not found")
    elif archetypes is not None:
        for doc in tasks:
            if doc.get("archetype") not in archetypes:
                ctx.at_yaml(
                    doc,
                    ["archetype"],
                    "SK-REF-MISSING",
                    f"archetype '{doc.get('archetype')}' is not in analysis/exam-profile.yaml",
                    f"use one of: {', '.join(sorted(archetypes)) or '(profile lists none)'}",
                )


def _check_link(ctx: Context, doc: Doc, link, targets: dict, exam_mc: set[str]) -> None:
    target = link.target
    scheme, _, rest = target.partition(":")
    if link.image:
        if scheme != "fig":
            ctx.at(
                doc,
                link.line,
                link.col,
                "SK-REF-IMAGE",
                f"image '{target}' is not a figure reference",
                "write a figure script figures/<slug>.py and embed it as ![Caption](fig:<slug>)",
            )
            return
        if rest not in ctx.tree.figure_slugs:
            ctx.at(
                doc,
                link.line,
                link.col,
                "SK-REF-MISSING",
                f"figure '{rest}' has no script figures/{rest}.py",
                "add the figure script or fix the slug",
            )
        if not link.alone or link.attrs or not link.text.strip():
            problem = (
                "has attributes"
                if link.attrs
                else "has no caption"
                if not link.text.strip()
                else "is not alone in its paragraph"
            )
            ctx.at(
                doc,
                link.line,
                link.col,
                "SK-REF-FIGURE",
                f"figure '{rest}' {problem}",
                "put ![Caption, doubles as alt text](fig:<slug>) on its own line between blank "
                "lines; the size comes from the figure script",
            )
        return
    if EXTERNAL_RE.match(target):
        return
    if scheme == "src":
        _check_src(ctx, doc, target, link.line, link.col)
        return
    if scheme in targets:
        if rest not in targets[scheme]:
            hint = (
                "exam questions are not in a practice bank; link the exam instead"
                if scheme == "mc" and rest in exam_mc
                else f"use an existing {scheme} id (`studykit ls` lists them)"
            )
            ctx.at(
                doc,
                link.line,
                link.col,
                "SK-REF-MISSING",
                f"link target '{target}' does not exist",
                hint,
            )
        return
    ctx.at(
        doc,
        link.line,
        link.col,
        "SK-REF-SCHEME",
        f"link target '{target}' is not a study-kit reference",
        "link with ex:, mc:, topic:, exam: or src:<doc>#p=<n> (figures use ![…](fig:<slug>))",
    )


def _check_src(ctx: Context, doc: Doc, target: str, line: int, col: int, yaml_loc=None) -> None:
    def report(code: str, message: str, fix: str) -> None:
        if yaml_loc is not None:
            ctx.at_yaml(doc, yaml_loc, code, message, fix)
        else:
            ctx.at(doc, line, col, code, message, fix)

    m = SRC_RE.match(target)
    if not m:
        report("SK-REF-SRC", f"malformed source link '{target}'", "write src:<doc>#p=<page>")
        return
    sources = ctx.tree.sources
    if m["doc"] not in sources:
        report(
            "SK-REF-MISSING",
            f"source document '{m['doc']}' is not in sources/manifest.yaml",
            f"use one of: {', '.join(sources) or '(no sources/manifest.yaml yet)'}",
        )
        return
    pages = sources[m["doc"]]["pages"]
    if m["page"] and pages and not 1 <= int(m["page"]) <= pages:
        report(
            "SK-REF-SRC",
            f"page {m['page']} is outside '{m['doc']}' (1 to {pages})",
            "link a page that exists in the PDF",
        )


def _check_frontmatter_sources(ctx: Context, doc: Doc) -> None:
    sources = ctx.tree.sources
    data = doc.data
    if not isinstance(data, dict):
        return
    refs: list[tuple[list, Any]] = []
    for i, s in enumerate(data.get("sources") or []):
        if isinstance(s, dict):
            refs.append((["sources", i, "doc"], s.get("doc")))
    if isinstance(data.get("source"), dict):
        refs.append((["source", "doc"], data["source"].get("doc")))
    for loc, value in refs:
        if isinstance(value, str) and value not in sources:
            ctx.at_yaml(
                doc,
                loc,
                "SK-REF-MISSING",
                f"source document '{value}' is not in sources/manifest.yaml",
                f"use one of: {', '.join(sources) or '(no sources/manifest.yaml yet)'}",
            )


def _check_plan(ctx: Context, plan: Doc, targets: dict) -> None:
    for i, session in enumerate(plan.model.sessions):
        for j, task in enumerate(session.tasks):
            refs = ([(["sessions", i, "tasks", j, "ref"], task.ref)] if task.ref else []) + [
                (["sessions", i, "tasks", j, "refs", k], r) for k, r in enumerate(task.refs)
            ]
            for loc, ref in refs:
                scheme, _, rest = ref.partition(":")
                if scheme == "src":
                    _check_src(ctx, plan, ref, 0, 0, yaml_loc=loc)
                elif scheme in targets and rest not in targets[scheme]:
                    ctx.at_yaml(
                        plan,
                        loc,
                        "SK-REF-MISSING",
                        f"plan reference '{ref}' does not exist",
                        "regenerate the plan with `studykit plan` or fix the id",
                    )
                elif scheme not in targets:
                    ctx.at_yaml(
                        plan,
                        loc,
                        "SK-REF-SCHEME",
                        f"plan reference '{ref}' cannot be resolved",
                        "use topic:, ex:, mc:, exam: or src: references",
                    )


def _check_exam_refs(ctx: Context, exam_doc: Doc) -> None:
    exam = exam_doc.model
    if exam is None:
        return
    folder = exam_doc.rel.rsplit("/", 1)[0]
    for i, name in enumerate(exam.tasks):
        if ctx.tree.get(f"{folder}/{name}") is None:
            ctx.at_yaml(
                exam_doc,
                ["tasks", i],
                "SK-REF-MISSING",
                f"task file {folder}/{name} does not exist",
                "create the task file or remove it from tasks",
            )
    if exam.mc is not None and ctx.tree.get(f"{folder}/{exam.mc.file}") is None:
        ctx.at_yaml(
            exam_doc,
            ["mc", "file"],
            "SK-REF-MISSING",
            f"{folder}/{exam.mc.file} does not exist",
            "write the MC part or remove mc: from exam.yaml",
        )
    sources = ctx.tree.sources
    for i, doc_id in enumerate(exam.modeled_on):
        if doc_id not in sources:
            ctx.at_yaml(
                exam_doc,
                ["modeled_on", i],
                "SK-REF-MISSING",
                f"past exam '{doc_id}' is not in sources/manifest.yaml",
                f"use one of: {', '.join(sources) or '(no sources/manifest.yaml yet)'}",
            )


# --- Figures (SK-FIG) ----------------------------------------------------------------------


@stage("Figures", "SK-FIG", 70)
def check_figures(ctx: Context) -> None:
    used = {
        link.target[4:]
        for doc in ctx.tree
        if doc.body is not None and not doc.split.error
        for link in doc.body.links
        if link.image and link.target.startswith("fig:")
    }
    for doc in ctx.tree.of_kind("figure"):
        slug = doc.parts["slug"]
        if slug not in used:
            ctx.at(
                doc,
                1,
                1,
                "SK-FIG-UNUSED",
                f"figure script '{slug}' is not referenced",
                f"embed it with ![Caption](fig:{slug}) or delete the script",
                "warning",
            )
    ctx.note("figure build and SVG validation not run here; use `studykit fig build`")


# --- later phases: pluggable stages that skip until their tools exist ------------------------


def _module_missing(name: str, phase: str) -> Callable[[Context], str | None]:
    def check(ctx: Context) -> str | None:
        import importlib.util

        if importlib.util.find_spec(f"studykit.{name}") is None:
            return f"studykit.{name} is not available yet ({phase})"
        return None

    return check


@stage("Verification", "SK-VER", 80, requires=_module_missing("verify", "Phase 5"))
def check_verification(ctx: Context) -> None:  # pragma: no cover - replaced in Phase 5
    ctx.note("verification ledger checks are not implemented yet")


@stage("PDF", "SK-PDF", 90, requires=_module_missing("pdf", "Phase 4"))
def check_pdf(ctx: Context) -> None:  # pragma: no cover - replaced in Phase 4
    ctx.note("PDF checks are not implemented yet")


def _site_ready(ctx: Context) -> str | None:
    if not (ctx.config.root / "site" / "astro.config.mjs").is_file():
        return "site/astro.config.mjs not found (the site is built in Phase 3)"
    return "site build checks run in `just build`"


@stage("Site", "SK-SITE", 95, requires=_site_ready)
def check_site(ctx: Context) -> None:  # pragma: no cover - replaced with the site
    pass


# --- Coverage (SK-COV, --release only) -------------------------------------------------------

DEFAULT_MIX = {"single": 0.60, "multi": 0.25, "kprim": 0.15}


@stage("Coverage", "SK-COV", 100, release_only=True)
def check_coverage(ctx: Context) -> None:
    tree = ctx.tree
    course = tree.model
    course_doc = tree.course_doc
    if course is None or course_doc is None:
        ctx.note("coverage not checked: course.yaml does not validate")
        return
    topics = [t for t in course.topics if t.id not in course.skip]

    def at_topic(topic_id: str, code: str, message: str, fix: str, severity="error") -> None:
        index = course.topic_ids.index(topic_id)
        ctx.at_yaml(course_doc, ["topics", index], code, message, fix, severity)

    overview = tree.get("overview.md")  # a missing file is SK-STRUCT-MISSING
    if overview is not None and overview.body is not None:
        linked = {
            link.target[6:] for link in overview.body.links if link.target.startswith("topic:")
        }
        for topic in topics:
            if topic.id not in linked:
                ctx.at(
                    overview,
                    1,
                    1,
                    "SK-COV-OVERVIEW",
                    f"overview.md never links topic '{topic.id}'",
                    f"link it once, e.g. [{topic.title}](topic:{topic.id})",
                )

    summaries = {d.parts["topic"] for d in tree.of_kind("summary")}
    exercises: dict[str, list[Doc]] = {}
    for doc in tree.of_kind("exercise"):
        exercises.setdefault(doc.parts["topic"], []).append(doc)
    banks = {d.parts["topic"]: d for d in tree.of_kind("mc")}
    mix = DEFAULT_MIX
    if course.exam.mc and course.exam.mc.types:
        mix = {t: DEFAULT_MIX[t] for t in course.exam.mc.types}
    ex_target = course.targets.exercises_per_topic
    mc_target = course.targets.mc_per_topic
    for topic in topics:
        if topic.id not in summaries:
            at_topic(
                topic.id,
                "SK-COV-SUMMARY",
                f"topic '{topic.id}' has no summary chapter",
                f"write summary/NN-{topic.id}.md",
            )
        ex = exercises.get(topic.id, [])
        need = ex_target if isinstance(ex_target, int) else 4
        levels = {d.get("difficulty") for d in ex}
        if len(ex) < need or len(levels) < 2:
            at_topic(
                topic.id,
                "SK-COV-EXERCISES",
                f"topic '{topic.id}' has {len(ex)} exercises over {len(levels)} difficulty "
                f"level(s); needs at least {need} over two or more levels",
                f"add exercises in exercises/{topic.id}/",
            )
        bank = banks.get(topic.id)
        questions = bank.body.questions if bank and bank.body else []
        need_mc = mc_target if isinstance(mc_target, int) else max(10, math.ceil(25 * topic.weight))
        need_mc = min(need_mc, 25)
        if len(questions) < need_mc:
            at_topic(
                topic.id,
                "SK-COV-MC",
                f"topic '{topic.id}' has {len(questions)} MC questions, needs {need_mc}",
                f"add questions to mc/{topic.id}.md",
            )
        elif questions:
            counts = Counter(q.type for q in questions)
            missing = [t for t in mix if counts.get(t, 0) == 0]
            if missing:
                at_topic(
                    topic.id,
                    "SK-COV-MC",
                    f"MC bank '{topic.id}' has no {', '.join(missing)} questions",
                    "follow the type mix of the exam profile (default 60% single, 25% multi, "
                    "15% kprim)",
                    "warning",
                )

    exams = tree.of_kind("exam")
    if len(exams) < course.targets.mock_exams:
        ctx.at_yaml(
            course_doc,
            ["targets", "mock_exams"],
            "SK-COV-EXAM",
            f"{len(exams)} mock exam(s), the target is {course.targets.mock_exams}",
            "author the missing mock exams or lower targets.mock_exams",
        )
    for exam_doc in exams:
        _check_exam_size(ctx, exam_doc, course.exam)


EXAM_TOLERANCE = 0.10


def _check_exam_size(ctx: Context, exam_doc: Doc, real: model.CourseExam) -> None:
    """Mock exam points and time within ±10% of the real exam (course.yaml `exam`, §2.7).

    course.yaml carries the real exam's duration and points as the exam analyst found them
    in the profile (or as the user gave them), already validated.
    """
    exam = exam_doc.model
    if exam is None:
        return
    for field_name, unit in (("points", "points"), ("duration_min", "minutes")):
        target = getattr(real, field_name)
        value = getattr(exam, field_name)
        if target is None:
            ctx.note(f"{exam_doc.rel}: {field_name} not compared, course.yaml exam has none")
            continue
        if abs(value - target) > EXAM_TOLERANCE * target:
            ctx.at_yaml(
                exam_doc,
                [field_name],
                "SK-COV-EXAM",
                f"{field_name} is {value:g} {unit}, but the real exam has {target:g} "
                f"(allowed ±{EXAM_TOLERANCE:.0%})",
                f"scale the mock exam to {target:g} {unit}, as course.yaml exam says",
            )


# --- runner ---------------------------------------------------------------------------------


def run_course(
    tree: CourseTree,
    config: Config | None = None,
    *,
    selected: set[str] | None = None,
    quick: bool = False,
    release: bool = False,
) -> CourseReport:
    config = config or Config()
    report = CourseReport(tree.id, display_path(tree.root))
    if tree.course_doc is None:
        report.findings.append(
            Finding(
                display_path(tree.root),
                1,
                1,
                "SK-STRUCT-MISSING",
                "course.yaml is missing",
                "create course.yaml (schema in schemas/course.schema.json)",
            )
        )
        return report
    for st in STAGES:
        if quick and not st.quick:
            continue
        if st.release_only and not release:
            continue
        ctx = Context(tree, config, selected, quick, release)
        reason = st.requires(ctx) if st.requires else None
        if reason:
            report.stages.append(StageResult(st.name, "skipped", [f"skipped: {reason}"]))
            continue
        st.run(ctx)
        found = ctx.findings
        if selected is not None:
            shown = {d.display for d in tree if d.rel in selected}
            found = [f for f in found if f.path in shown]
        status = "failed" if any(f.is_error for f in found) else "warnings" if found else "ok"
        report.stages.append(StageResult(st.name, status, ctx.notes))
        report.findings.extend(found)
    report.findings = sorted(set(report.findings), key=lambda f: (f.path, f.line, f.col, f.code))
    return report


def validate(
    courses: list[Path],
    *,
    paths: list[Path] | None = None,
    quick: bool = False,
    release: bool = False,
    config: Config | None = None,
) -> Report:
    """Validate whole courses, or with `paths` only those files (in their course context)."""
    config = config or Config()
    report = Report()
    for root in courses:
        tree = CourseTree(root)
        selected = None
        if paths is not None:
            selected = set()
            for p in paths:
                try:
                    rel = p.resolve().relative_to(tree.root).as_posix()
                except ValueError:
                    continue
                if p.is_dir():  # a directory selects every course file below it
                    prefix = "" if rel == "." else rel + "/"
                    selected.update(r for r in tree.docs if r.startswith(prefix))
                else:
                    selected.add(rel)
        report.courses.append(
            run_course(tree, config, selected=selected, quick=quick, release=release)
        )
    return report
