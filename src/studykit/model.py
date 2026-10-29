"""Pydantic models: the single schema source for course data (docs/architecture.md §2).

Every model is strict (no type coercion, so `points: '10'` and `negative_marking: no`
are errors) and forbids unknown fields. Dates are ISO strings in YAML and JSON; the
restricted YAML loader never creates date objects itself, and `IsoDate` turns the string
into a date only where a field expects one.

Cross-file rules that need the course (topic ids, the cheat-sheet page cap) read it from
the validation context: `Model.model_validate(data, context=course_context(course))`.
Errors raised by these validators use the SK-code as their pydantic error type, so
`studykit validate` reports them under that code.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationInfo,
    WithJsonSchema,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

SCHEMA_VERSION = 1

KEBAB = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PATTERNS = {
    "course": r"^[a-z0-9][a-z0-9-]{1,39}$",
    "topic": rf"^{KEBAB}$",
    "exercise": rf"^ex-{KEBAB}$",
    "mc": rf"^mc-{KEBAB}-[0-9]{{3}}$",
    "task": rf"^{KEBAB}-t[0-9]+$",
    "exam": rf"^{KEBAB}$",
    "doc": rf"^{KEBAB}$",
    "slug": rf"^{KEBAB}$",
    "archetype": rf"^{KEBAB}$",
    "session": r"^s-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z]+$",
    "answer-key": r"^[A-Za-z][A-Za-z0-9_]*$",
    "task-file": rf"^[0-9]{{2}}-{KEBAB}-t[0-9]+\.md$",
}
EXAMPLES = {
    "course": "get2",
    "topic": "rc-filter",
    "exercise": "ex-rc-tp-grenzfrequenz",
    "mc": "mc-rc-filter-003",
    "task": "pk1-t1",
    "exam": "probeklausur-1",
    "doc": "vl-05",
    "slug": "rc-bode",
    "archetype": "bode-diagramm",
    "session": "s-2026-11-02-a",
    "answer-key": "fg",
    "task-file": "01-pk1-t1.md",
}
MC_ID_RE = re.compile(rf"^mc-(?P<topic>{KEBAB})-(?P<num>[0-9]{{3}})$")
REF_RE = re.compile(r"^(?P<scheme>ex|mc|topic|exam|src|fig):(?P<target>\S+)$")
MC_TYPES = ("single", "multi", "kprim")


def sk_error(code: str, message: str, fix: str) -> PydanticCustomError:
    """A validation error whose pydantic type is the SK-code."""
    # pydantic only substitutes `{fix}` (the one context key); other braces stay literal.
    return PydanticCustomError(code, message, {"fix": fix})


def mc_topic(mc_id: str) -> str | None:
    """The topic encoded in an MC question id: mc-rc-filter-003 -> rc-filter."""
    m = MC_ID_RE.match(mc_id)
    return m["topic"] if m else None


# --- scalar types -----------------------------------------------------------------------


def _id(kind: str, code: str = "SK-STRUCT-ID"):
    rx = re.compile(PATTERNS[kind])

    def check(value: str) -> str:
        if not rx.match(value):
            raise sk_error(
                code,
                f"{kind} id '{value}' does not match {PATTERNS[kind]}",
                f"use lowercase kebab-case ASCII like '{EXAMPLES[kind]}'",
            )
        return value

    return Annotated[
        str,
        AfterValidator(check),
        WithJsonSchema({"type": "string", "pattern": PATTERNS[kind]}),
    ]


def _known_topic(value: str, info: ValidationInfo) -> str:
    topics = (info.context or {}).get("topics")
    if topics is not None and value not in topics:
        raise sk_error(
            "SK-STRUCT-TOPIC",
            f"unknown topic '{value}'",
            f"use a topic id from course.yaml: {', '.join(topics)}",
        )
    return value


CourseId = _id("course")
TopicId = _id("topic")
TopicRef = Annotated[TopicId, AfterValidator(_known_topic)]
ExerciseId = _id("exercise")
McId = _id("mc")
TaskId = _id("task")
ExamId = _id("exam")
DocId = _id("doc")
Slug = _id("slug")
ArchetypeId = _id("archetype")
SessionId = _id("session")
AnswerKey = _id("answer-key", code="SK-SCHEMA-VALUE")
TaskFile = _id("task-file")

PositiveInt = Annotated[int, Field(gt=0)]
PositiveNumber = Annotated[float, Field(gt=0)]
Text = Annotated[str, Field(min_length=1, pattern=r"^[^\n]*\S[^\n]*$")]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Ref = Annotated[
    str,
    Field(pattern=REF_RE.pattern),
]

ISO_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def _iso_date(value: Any) -> Any:
    if isinstance(value, str) and ISO_DATE_RE.match(value):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise sk_error("SK-SCHEMA-VALUE", f"invalid date '{value}'", "use YYYY-MM-DD") from exc
    return value


def _iso_datetime(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise sk_error(
                "SK-SCHEMA-VALUE",
                f"invalid timestamp '{value}'",
                "use ISO 8601 like 2026-10-30T10:12:00Z",
            ) from exc
    return value


IsoDate = Annotated[date, BeforeValidator(_iso_date)]
IsoDateTime = Annotated[datetime, BeforeValidator(_iso_datetime)]

INLINE_MATH_RE = re.compile(r"\$(?=\S)[^$]*(?<=\S)\$")
LABEL_FORBIDDEN = "*_`[]<>^|\\$"


def label_problem(text: str) -> str | None:
    """Why `text` is not plain text plus inline `$…$` math, or None."""
    if "\n" in text:
        return "it spans several lines"
    if "$$" in text:
        return "it contains display math ($$)"
    rest = INLINE_MATH_RE.sub("", text)
    for char in LABEL_FORBIDDEN:
        if char in rest:
            if char == "$":
                return "it has an unbalanced $ or a space just inside the dollars"
            return f"it has Markdown or TeX syntax '{char}' outside $…$"
    return None


def _check_label(value: str) -> str:
    problem = label_problem(value)
    if problem:
        raise sk_error(
            "SK-SCHEMA-LABEL",
            f"label must be plain text plus inline math, but {problem}",
            "write words as text and put every symbol in $…$, e.g. '$|\\underline{H}|$ in dB'",
        )
    return value


Label = Annotated[Text, AfterValidator(_check_label)]

DATE_RANGE_RE = re.compile(
    r"^(?P<a>[0-9]{4}-[0-9]{2}-[0-9]{2})(?:\.\.(?P<b>[0-9]{4}-[0-9]{2}-[0-9]{2}))?$"
)


def _check_range(value: str) -> str:
    m = DATE_RANGE_RE.match(value)
    fix = "write a day as 'YYYY-MM-DD' or a range as 'YYYY-MM-DD..YYYY-MM-DD'"
    if not m:
        raise sk_error("SK-SCHEMA-VALUE", f"invalid blocked period '{value}'", fix)
    try:
        start = date.fromisoformat(m["a"])
        end = date.fromisoformat(m["b"] or m["a"])
    except ValueError as exc:
        raise sk_error("SK-SCHEMA-VALUE", f"invalid date in '{value}'", fix) from exc
    if end < start:
        raise sk_error("SK-SCHEMA-VALUE", f"blocked period '{value}' ends before it starts", fix)
    return value


DateRange = Annotated[
    str,
    AfterValidator(_check_range),
    WithJsonSchema({"type": "string", "pattern": DATE_RANGE_RE.pattern}),
]


class Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", populate_by_name=True)


# --- course.yaml (§2.2) -------------------------------------------------------------------


class ExamMc(Strict):
    present: bool
    types: list[Literal["single", "multi", "kprim"]] = []
    scoring: Literal["all-or-nothing", "partial", "kprim"] = "all-or-nothing"
    negative_marking: bool = False


class CourseExam(Strict):
    date: IsoDate | None = Field(None, description="null = unknown; the plan uses a placeholder")
    duration_min: PositiveInt | None = None
    points: PositiveNumber | None = None
    format: Literal["written", "mc", "oral", "mixed"]
    aids: list[Text] = []
    mc: ExamMc | None = None


class CheatsheetPolicy(Strict):
    allowed: bool
    max_pages: int = Field(2, ge=1, le=3, description="the validator caps it at 3")


class Study(Strict):
    start: IsoDate | None = None
    hours_per_week: PositiveNumber
    blocked: list[DateRange] = []


class Topic(Strict):
    id: TopicId
    title: Text
    weight: float = Field(gt=0, le=1)
    prereq: list[TopicRef] = []


class Targets(Strict):
    exercises_per_topic: Literal["auto"] | PositiveInt = "auto"
    mc_per_topic: Literal["auto"] | PositiveInt = "auto"
    mock_exams: int = Field(2, ge=0, le=3)


def _cycle(topics: list[Topic]) -> list[str] | None:
    graph = {t.id: list(t.prereq) for t in topics}
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                return [*stack[stack.index(nxt) :], nxt]
            if nxt in graph and state.get(nxt) is None and (found := visit(nxt)):
                return found
        stack.pop()
        state[node] = 2
        return None

    for topic in graph:
        if state.get(topic) is None and (found := visit(topic)):
            return found
    return None


class Course(Strict):
    """`course.yaml`: one per course directory."""

    schema_version: Literal[1] = Field(alias="schema")
    id: CourseId
    title: Text
    short: Text | None = None
    lang: Literal["de", "en"] = Field(description="language of generated content")
    semester: Text | None = None
    status: Literal["draft", "ready"] = "draft"
    exam: CourseExam
    cheatsheet: CheatsheetPolicy = CheatsheetPolicy(allowed=False)
    study: Study | None = None
    topics: list[Topic] = Field(min_length=1, description="order = teaching order")
    focus: list[TopicRef] = []
    skip: list[TopicRef] = []
    targets: Targets = Targets()
    retired_ids: list[str] = []

    @field_validator("topics")
    @classmethod
    def _topics_graph(cls, topics: list[Topic]) -> list[Topic]:
        seen: set[str] = set()
        for topic in topics:
            if topic.id in seen:
                raise sk_error(
                    "SK-STRUCT-DUP",
                    f"topic id '{topic.id}' appears twice",
                    "give every topic a unique id",
                )
            seen.add(topic.id)
        for topic in topics:
            for pre in topic.prereq:
                if pre not in seen:
                    raise sk_error(
                        "SK-STRUCT-TOPIC",
                        f"topic '{topic.id}' has unknown prerequisite '{pre}'",
                        f"use a topic id from this list: {', '.join(seen)}",
                    )
        cycle = _cycle(topics)
        if cycle:
            raise sk_error(
                "SK-STRUCT-CYCLE",
                f"prerequisites form a cycle: {' -> '.join(cycle)}",
                "remove one prerequisite so that the topics can be taught in order",
            )
        return topics

    @model_validator(mode="after")
    def _focus_and_skip(self, info: ValidationInfo) -> Course:
        ids = [t.id for t in self.topics]
        if (info.context or {}).get("topics") is None:
            for name in ("focus", "skip"):
                for value in getattr(self, name):
                    if value not in ids:
                        raise sk_error(
                            "SK-STRUCT-TOPIC",
                            f"{name} lists unknown topic '{value}'",
                            f"use a topic id from this list: {', '.join(ids)}",
                        )
        return self

    @property
    def topic_ids(self) -> list[str]:
        return [t.id for t in self.topics]


def course_context(course: Course | None) -> dict[str, Any]:
    """Validation context for item frontmatter: the course's topics and limits."""
    if course is None:
        return {}
    return {
        "topics": course.topic_ids,
        "cheatsheet_max_pages": course.cheatsheet.max_pages,
    }


def validate_course(data: Any) -> Course:
    """Validate course.yaml, reporting unknown prerequisites at the exact list entry."""
    topics = None
    if isinstance(data, dict) and isinstance(data.get("topics"), list):
        topics = [t.get("id") for t in data["topics"] if isinstance(t, dict)]
    return Course.model_validate(data, context={"topics": topics} if topics else None)


# --- item frontmatter (§2.4 to §2.8, §2.12) ---------------------------------------------------

PageSpec = Annotated[str, Field(pattern=r"^[0-9]+(?:-[0-9]+)?$")] | PositiveInt


class SourcePages(Strict):
    doc: DocId
    pages: PageSpec | None = None


class ItemSource(Strict):
    doc: DocId
    page: PositiveInt | None = None
    relation: Literal["original", "adapted", "inspired"]


class Summary(Strict):
    """Frontmatter of `summary/NN-<topic>.md`."""

    topic: TopicRef
    title: Text
    objectives: list[Label] = []
    sources: list[SourcePages] = []


class Overview(Strict):
    """Frontmatter of `overview.md`."""

    title: Text


class Answer(Strict):
    """One answer-key entry: numeric with a tolerance, or symbolic with its symbols."""

    key: AnswerKey
    label: Label
    value: float | None = None
    unit: Text | None = None
    rtol: float | None = Field(None, gt=0)
    atol: float | None = Field(None, gt=0)
    expr: Text | None = None
    symbols: list[Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")]] = []

    @model_validator(mode="after")
    def _numeric_or_symbolic(self) -> Answer:
        fix = (
            "write {key: fg, label: '…', value: 1591.55, unit: Hz, rtol: 1.0e-3} or "
            "{key: H, label: '…', expr: '1/(1+s*R*C)', symbols: [s, R, C]}"
        )
        if (self.value is None) == (self.expr is None):
            raise sk_error(
                "SK-SCHEMA-ANSWER",
                f"answer '{self.key}' needs exactly one of value and expr",
                fix,
            )
        if self.value is not None and self.rtol is None and self.atol is None:
            raise sk_error(
                "SK-SCHEMA-ANSWER", f"numeric answer '{self.key}' needs rtol or atol", fix
            )
        if self.expr is not None and (not self.symbols or self.rtol or self.atol):
            raise sk_error(
                "SK-SCHEMA-ANSWER",
                f"symbolic answer '{self.key}' needs symbols and takes no tolerance",
                fix,
            )
        return self


def _unique_keys(answers: list[Answer]) -> list[Answer]:
    keys = [a.key for a in answers]
    for key in keys:
        if keys.count(key) > 1:
            raise sk_error(
                "SK-SCHEMA-ANSWER",
                f"answer key '{key}' appears twice",
                "give every answer a unique key",
            )
    return answers


Answers = Annotated[list[Answer], AfterValidator(_unique_keys)]


class Exercise(Strict):
    """Frontmatter of `exercises/<topic>/<ex-id>.md`."""

    id: ExerciseId
    title: Text
    topic: TopicRef
    difficulty: int = Field(ge=1, le=4, description="1 worked-example level … 4 exam-hard")
    kind: Literal["compute", "derive", "concept", "sketch", "code"]
    minutes: PositiveInt
    source: ItemSource | None = None
    answers: Answers = []


class RubricItem(Strict):
    points: PositiveNumber
    criterion: Label


class ExamTask(Strict):
    """Frontmatter of `exams/<exam-id>/NN-<task-id>.md`: the exercise schema for exams."""

    id: TaskId
    title: Text
    topic: TopicRef
    kind: Literal["exam-task"]
    points: PositiveNumber
    archetype: ArchetypeId
    rubric: list[RubricItem] = Field(min_length=1)
    difficulty: int | None = Field(None, ge=1, le=4)
    minutes: PositiveInt | None = None
    source: ItemSource | None = None
    answers: Answers = []

    @field_validator("rubric")
    @classmethod
    def _rubric_sum(cls, rubric: list[RubricItem], info: ValidationInfo) -> list[RubricItem]:
        points = info.data.get("points")
        total = sum(r.points for r in rubric)
        if points is not None and abs(total - points) > 1e-9:
            raise sk_error(
                "SK-SCHEMA-RUBRIC",
                f"rubric points add up to {total:g}, but the task has {points:g} points",
                "make the rubric points add up exactly to `points`",
            )
        return rubric


class McBank(Strict):
    """Frontmatter of a practice bank `mc/<topic>.md`."""

    topic: TopicRef
    title: Text


class ExamMcBank(Strict):
    """Frontmatter of `exams/<exam-id>/mc.md`; each question's topic comes from its id."""

    title: Text
    topic: TopicRef | None = None


class Cheatsheet(Strict):
    """Frontmatter of `cheatsheet.md`."""

    title: Text
    max_pages: int = Field(ge=1, le=3)
    priority: list[TopicRef] = []

    @field_validator("max_pages")
    @classmethod
    def _within_course_limit(cls, value: int, info: ValidationInfo) -> int:
        limit = (info.context or {}).get("cheatsheet_max_pages")
        if limit is not None and value > limit:
            raise sk_error(
                "SK-SCHEMA-VALUE",
                f"max_pages {value} exceeds course.yaml cheatsheet.max_pages {limit}",
                f"set max_pages to at most {limit}",
            )
        return value


# --- exam.yaml (§2.7) ---------------------------------------------------------------------


class ExamMcPart(Strict):
    file: Literal["mc.md"] = "mc.md"
    points_each: PositiveNumber


class Exam(Strict):
    """`exams/<exam-id>/exam.yaml`."""

    schema_version: Literal[1] = Field(alias="schema")
    id: ExamId
    title: Text
    duration_min: PositiveInt
    points: PositiveNumber
    pass_points: PositiveNumber
    aids: Literal["inherit"] | list[Text] = "inherit"
    modeled_on: list[DocId] = []
    tasks: list[TaskFile] = Field(min_length=1)
    mc: ExamMcPart | None = None

    @field_validator("pass_points")
    @classmethod
    def _pass_below_total(cls, value: float, info: ValidationInfo) -> float:
        total = info.data.get("points")
        if total is not None and value > total:
            raise sk_error(
                "SK-SCHEMA-VALUE",
                f"pass_points {value:g} exceed the exam's {total:g} points",
                "set pass_points to at most points",
            )
        return value

    @field_validator("tasks")
    @classmethod
    def _unique_tasks(cls, tasks: list[str]) -> list[str]:
        for task in tasks:
            if tasks.count(task) > 1:
                raise sk_error(
                    "SK-STRUCT-DUP", f"task file '{task}' is listed twice", "list each task once"
                )
        return tasks


# --- plan.yaml (§2.9) ---------------------------------------------------------------------


class PlanTask(Strict):
    do: Literal["read", "exercises", "mc", "exam", "review", "cheatsheet"]
    ref: Ref | None = None
    refs: list[Ref] = []
    topic: TopicRef | None = None
    count: PositiveInt | None = None

    @model_validator(mode="after")
    def _fields_for_kind(self) -> PlanTask:
        need = {
            "read": self.ref is not None,
            "exercises": bool(self.refs),
            "mc": self.topic is not None and self.count is not None,
            "exam": self.ref is not None and self.ref.startswith("exam:"),
            "review": self.topic is not None or bool(self.refs),
            "cheatsheet": True,
        }
        if not need[self.do]:
            shape = {
                "read": "{do: read, ref: 'topic:<id>'}",
                "exercises": "{do: exercises, refs: ['ex:<id>', …]}",
                "mc": "{do: mc, topic: <id>, count: 10}",
                "exam": "{do: exam, ref: 'exam:<id>'}",
                "review": "{do: review, topic: <id>} or refs",
            }[self.do]
            raise sk_error(
                "SK-SCHEMA-VALUE", f"plan task '{self.do}' is incomplete", f"write {shape}"
            )
        return self


class Session(Strict):
    id: SessionId
    date: IsoDate
    minutes: PositiveInt
    kind: Literal["learn", "review", "mixed", "mock-exam", "cheatsheet", "buffer"]
    topics: list[TopicRef] = []
    goal: Text | None = None
    note: Text | None = None
    tasks: list[PlanTask] = []


class Plan(Strict):
    """`plan.yaml`, written by `studykit plan` (goal and note text by Claude)."""

    schema_version: Literal[1] = Field(alias="schema")
    generated: IsoDate
    exam_date: IsoDate | None = None
    sessions: list[Session] = []

    @field_validator("sessions")
    @classmethod
    def _unique_sessions(cls, sessions: list[Session]) -> list[Session]:
        ids = [s.id for s in sessions]
        for sid in ids:
            if ids.count(sid) > 1:
                raise sk_error(
                    "SK-STRUCT-DUP",
                    f"session id '{sid}' appears twice",
                    "give every session a unique id",
                )
        return sessions


# --- verification ledger (§2.10) ----------------------------------------------------------


class AnswerCheck(Strict):
    claimed: float | None = None
    computed: float | None = None
    rel_err: float | None = None
    abs_err: float | None = None


class VerifyEntry(Strict):
    """`state/verify/<item-id>.json`."""

    item: Annotated[str, Field(pattern=rf"^{KEBAB}$")]
    content_sha256: Sha256
    check_sha256: Sha256 | None = None
    method: Literal["script", "blind", "audit"]
    result: Literal["pass", "fixed", "disputed", "quarantined"]
    answers: dict[str, AnswerCheck] = {}
    reason: str | None = None
    verified_at: IsoDateTime


# --- browser progress export (§2.11) ------------------------------------------------------

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{8,64}$")]
Box = Annotated[int, Field(ge=0, le=5)]


class McAttempt(Strict):
    t: IsoDateTime
    chosen: list[Annotated[str, Field(pattern=r"^[A-F]$")]]
    score: float = Field(ge=0, le=1)
    conf: Literal["sure", "unsure"]
    ms: int = Field(ge=0)


class McProgress(Strict):
    h: Hash
    box: Box | None = None
    due: IsoDate | None = None
    attempts: list[McAttempt] = []


class ExerciseProgress(Strict):
    h: Hash
    hints: int = Field(0, ge=0)
    answer_ok: bool | None = None
    rating: Literal["solved", "partial", "not-yet"] | None = None
    box: Box | None = None
    due: IsoDate | None = None


class ExamAttempt(Strict):
    started: IsoDateTime
    duration_s: int = Field(ge=0)
    points: dict[str, float]
    total: float = Field(ge=0)


class ExamProgress(Strict):
    attempts: list[ExamAttempt] = []


class PlanProgress(Strict):
    done: bool


ITEM_KEY_RE = r"^(mc|ex|exam|plan):[a-z0-9][a-z0-9-]*$"
PROGRESS_KINDS: dict[str, type[Strict]] = {
    "mc": McProgress,
    "ex": ExerciseProgress,
    "exam": ExamProgress,
    "plan": PlanProgress,
}


class Progress(Strict):
    """A browser progress export, `studykit-progress-<course>-<date>.json`."""

    schema_version: Literal["studykit-progress/1"] = Field(alias="schema")
    course: CourseId
    exported_at: IsoDateTime
    items: dict[
        Annotated[str, Field(pattern=ITEM_KEY_RE)],
        McProgress | ExerciseProgress | ExamProgress | PlanProgress,
    ] = {}

    @field_validator("items", mode="before")
    @classmethod
    def _by_key_prefix(cls, items: Any) -> Any:
        """Validate each entry with the model its key prefix names (mc:, ex:, exam:, plan:)."""
        if not isinstance(items, dict):
            return items
        validated: dict[str, Any] = {}
        for kind, model in PROGRESS_KINDS.items():
            group = {
                k: v for k, v in items.items() if isinstance(k, str) and k.split(":", 1)[0] == kind
            }
            if group:
                validated.update(TypeAdapter(dict[str, model]).validate_python(group))
        return {key: validated.get(key, value) for key, value in items.items()}


# --- registry ------------------------------------------------------------------------------

# File kind (content.py) -> frontmatter or YAML model.
MODELS: dict[str, type[Strict]] = {
    "course": Course,
    "overview": Overview,
    "summary": Summary,
    "exercise": Exercise,
    "exam-task": ExamTask,
    "mc": McBank,
    "exam-mc": ExamMcBank,
    "cheatsheet": Cheatsheet,
    "exam": Exam,
    "plan": Plan,
}

# Exported JSON schemas: schemas/<name>.schema.json.
SCHEMAS: dict[str, type[Strict]] = {
    "course": Course,
    "overview": Overview,
    "summary": Summary,
    "exercise": Exercise,
    "exam-task": ExamTask,
    "mc-bank": McBank,
    "exam-mc-bank": ExamMcBank,
    "cheatsheet": Cheatsheet,
    "exam": Exam,
    "plan": Plan,
    "verify": VerifyEntry,
    "progress": Progress,
}
