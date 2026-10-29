"""`studykit pipeline status|report <course>`: the state of /register-new-subject (§5.4).

There is no state file. Every step's status is derived from what the steps leave behind:
the source manifest and its hashes, the files each step writes, the verification ledger
and the PDF digests. A step is `done`, `pending` (nothing of it yet), `partial` (begun,
or its gate fails) or `stale` (its output is older than what it was made from); the first
step that is not done is where a run resumes. With `scope: core` (round 2) the exercises,
mock exams and the cheat sheet are deferred: reported, but not a resume point.

What proves each step:

- 0 preflight: the course directory with `sources/manifest.yaml` (init ran after scan)
- 1 ask-1: `answers.round1` in the manifest
- 2 scaffold: the manifest and `course.yaml` validate; every document is in `sources/raw/`
  with its sha256; the ingested folder (`folder`) has no new or changed PDF
- 3 extract: `sources/text/<doc>/index.json` at the document's sha256 with every page file;
  `sources/chunks.yaml` covers every document at its sha256
- 4 read: `sources/notes/<chunk>.md` for every chunk (schema; chunk, pages and
  `source_sha256` match); `analysis/exam-profile.yaml` and `analysis/notation.yaml`
  validate; no lint errors in the notes and the analysis
- 5 synthesize: `sources/outline.md` names every course topic and every chunk id;
  `course.yaml` has real topics, not the placeholder `draft`
- 6 ask-2: `answers.round2` with go, and `targets.mock_exams` as answered
- 7 author: `overview.md`, and per topic not skipped the summary, exercises and MC bank the
  Coverage stage of `validate --release` asks for
- 8 figures: every figure script and the built-in topic map built from their current
  inputs (`_build/figures/manifest.json`)
- 9 verify: every exercise and MC question of the topics verified or quarantined in the
  ledger, none stale
- 10 mock-exams: `targets.mock_exams` exams within the Coverage stage's points and time,
  with an MC part when the exam has one, archetypes of the profile, every item verified
  or quarantined
- 11 cheatsheet: `cheatsheet.md` and a fresh `cheatsheet.pdf` within `max_pages` (done
  when no cheat sheet is allowed)
- 12 plan: `plan.yaml` validates, is made for the exam date, refers to existing items and
  has a goal in every session
- 13 publish: `course.yaml` has `status: ready`, every PDF is fresh, the built site has
  the course
- 14 report: `state/pipeline/report.md` (`pipeline report`) written for the current
  content (its fingerprint)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from studykit import content, ingest, model, tools, verify
from studykit.content import CourseTree, display_path

STEPS = [
    "preflight",
    "ask-1",
    "scaffold",
    "extract",
    "read",
    "synthesize",
    "ask-2",
    "author",
    "figures",
    "verify",
    "mock-exams",
    "cheatsheet",
    "plan",
    "publish",
    "report",
]
STATUSES = ("done", "pending", "partial", "stale")
REPORT = Path("state") / "pipeline" / "report.md"
FINGERPRINT_RE = re.compile(r"<!-- studykit-pipeline fingerprint ([0-9a-f]{64}) -->")
FONT_PT = {0: 9, 1: 8.5, 2: 8, 3: 7.5, 4: 7}  # cheat-sheet density levels (§3.3)


@dataclass
class Step:
    n: int
    name: str
    status: str = "pending"
    proof: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    todo: dict[str, Any] = field(default_factory=dict)
    deferred: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "step": self.n,
            "name": self.name,
            "status": self.status,
            "deferred": self.deferred,
            "proof": self.proof,
            "details": self.details,
            "todo": self.todo,
        }


def _combine(done: bool, started: bool, stale: bool) -> str:
    if stale:
        return "stale"
    if done:
        return "done"
    return "partial" if started else "pending"


class Inputs:
    """What the steps read, loaded once."""

    def __init__(self, root: Path):
        self.root = root
        self.exists = root.is_dir()
        self.tree = CourseTree(root) if self.exists else None
        self.manifest, self.manifest_findings = (
            ingest.read_manifest(root) if self.exists else (None, [])
        )
        self.chunks, self.chunk_findings = ingest.read_chunks(root) if self.exists else (None, [])
        self.course = self.tree.model if self.tree else None
        r2 = self.manifest.answers.round2 if self.manifest else None
        self.core = bool(r2 and r2.scope == "core")

    def doc(self, rel: str):
        return self.tree.get(rel) if self.tree else None

    def valid(self, rel: str) -> tuple[bool, list[str]]:
        """(file exists and validates, its problems as text)."""
        doc = self.doc(rel)
        if doc is None:
            return False, []
        problems = [f.format() for f in (doc.yaml.findings if doc.yaml else []) if f.is_error]
        problems += [f.format() for f in doc.validated[1]]
        return doc.model is not None and not problems, problems

    @property
    def real_topics(self) -> list[model.Topic]:
        if self.course is None:
            return []
        return [t for t in self.course.topics if t.id != model.DRAFT_TOPIC]

    @property
    def taught(self) -> list[model.Topic]:
        skip = set(self.course.skip) if self.course else set()
        return [t for t in self.real_topics if t.id not in skip]


# --- steps 0 to 6: ingest ----------------------------------------------------------------------


def step_preflight(inp: Inputs, s: Step) -> None:
    s.proof = ["sources/manifest.yaml"]
    if inp.exists and ingest.manifest_path(inp.root).is_file():
        s.status = "done"
    else:
        s.details.append(
            "no course yet: `just doctor --quick`, then `studykit ingest scan <folder> "
            "--dry-run --json`"
        )


def step_ask1(inp: Inputs, s: Step) -> None:
    s.proof = ["sources/manifest.yaml: answers.round1"]
    if inp.manifest is None:
        return
    if inp.manifest.answers.round1 is not None:
        s.status = "done"
    else:
        s.status = "partial"
        s.details.append("the round-1 answers are not recorded (`studykit ingest init` flags)")


def _folder_changes(m: model.SourceManifest) -> tuple[list[str], list[str]]:
    """(changed, new) PDFs of the ingested folder, compared by sha256."""
    if not m.folder:
        return [], []
    folder = Path(m.folder)
    if not folder.is_dir():
        return [], []
    known = {d.sha256 for d in m.documents}
    by_origin = {d.origin: d for d in m.documents}
    skipped = {s.origin for s in m.skipped}
    changed, new = [], []
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue
        rel = path.relative_to(folder)
        if any(part.startswith(".") for part in rel.parts):
            continue
        origin = rel.as_posix()
        digest = ingest.sha256_file(path)
        if digest in known or origin in skipped:
            continue
        (changed if origin in by_origin else new).append(origin)
    return changed, new


def step_scaffold(inp: Inputs, s: Step) -> None:
    s.proof = ["sources/manifest.yaml", "sources/raw/<doc>.pdf", "course.yaml"]
    if not inp.exists or not ingest.manifest_path(inp.root).is_file():
        return
    problems = [f.format() for f in inp.manifest_findings]
    ok_course, course_problems = inp.valid("course.yaml")
    problems += course_problems
    if not (inp.root / "course.yaml").is_file():
        problems.append("course.yaml is missing")
    missing, edited = [], []
    m = inp.manifest
    for d in m.documents if m else []:
        raw = inp.root / "sources" / "raw" / d.file
        if not raw.is_file():
            missing.append(d.id)
        elif ingest.sha256_file(raw) != d.sha256:
            edited.append(d.id)
    changed, new = _folder_changes(m) if m else ([], [])
    if problems:
        s.todo["problems"] = problems
        s.details += problems[:3]
    if missing:
        s.todo["missing_raw"] = missing
        s.details.append(f"{len(missing)} source PDF(s) missing in sources/raw")
    if edited:
        s.todo["edited_raw"] = edited
        s.details.append(f"sources/raw differs from the manifest: {', '.join(edited)}")
    if changed or new:
        s.todo["folder_changed"], s.todo["folder_new"] = changed, new
        s.details.append(
            f"the folder has {len(changed)} changed and {len(new)} new PDF(s): "
            "`studykit ingest add <course> <folder>`"
        )
    if m is not None and not m.documents:
        problems.append("no documents")
    done = not problems and not missing and ok_course
    s.status = _combine(done, True, bool(edited or changed or new) and done)


def step_extract(inp: Inputs, s: Step) -> None:
    s.proof = ["sources/text/<doc>/index.json", "sources/chunks.yaml"]
    m = inp.manifest
    if m is None:
        return
    not_extracted = [d.id for d in m.documents if not ingest.extracted(inp.root, d)]
    plan = inp.chunks
    stale: list[str] = []
    uncovered: list[str] = []
    if plan is not None:
        by_doc: dict[str, list[model.Chunk]] = {}
        for c in plan.chunks:
            by_doc.setdefault(c.doc, []).append(c)
        for d in m.documents:
            chunks = by_doc.get(d.id)
            if not chunks:
                uncovered.append(d.id)
            elif any(c.sha256 != d.sha256 for c in chunks):
                stale.append(d.id)
    started = plan is not None or len(not_extracted) < len(m.documents)
    if inp.chunk_findings:
        s.todo["problems"] = [f.format() for f in inp.chunk_findings]
        s.details.append("sources/chunks.yaml does not validate")
    if not_extracted:
        s.todo["not_extracted"] = not_extracted
        s.details.append(f"no current page text for {', '.join(not_extracted)}")
    if uncovered:
        s.todo["no_chunks"] = uncovered
    if stale:
        s.todo["replan"] = stale
        s.details.append(f"chunks planned from an older version of {', '.join(stale)}")
    if plan is None and not inp.chunk_findings:
        s.details.append("no sources/chunks.yaml")
    if s.todo:
        s.details.append("run `studykit ingest extract <course>`")
    done = plan is not None and not s.todo
    s.status = _combine(done, started, bool(stale or (not_extracted and plan is not None)))


def step_read(inp: Inputs, s: Step) -> None:
    s.proof = [
        "sources/notes/<chunk>.md",
        "analysis/exam-profile.yaml",
        "analysis/notation.yaml",
    ]
    plan = inp.chunks
    if plan is None or inp.tree is None:
        return
    missing, invalid, stale = [], [], []
    for c in plan.chunks:
        doc = inp.tree.get(f"sources/notes/{c.id}.md")
        if doc is None:
            missing.append(c.id)
            continue
        notes = doc.model
        if notes is None or notes.doc != c.doc or notes.pages != f"{c.first}-{c.last}":
            invalid.append(c.id)
        elif notes.source_sha256 != c.sha256:
            stale.append(c.id)
    profile_ok, profile_problems = inp.valid("analysis/exam-profile.yaml")
    notation_ok, notation_problems = inp.valid("analysis/notation.yaml")
    lint = _lint(inp, ["sources/notes", "analysis"])
    transcribe = [
        f"{c.doc} p. {n}"
        for c in plan.chunks
        for n in c.scanned
        if not ingest.vision_file(inp.root, c.doc, n).is_file()
    ]
    for key, value in (
        ("chunks_without_notes", missing),
        ("notes_invalid", invalid),
        ("notes_stale", stale),
        ("lint_errors", lint),
    ):
        if value:
            s.todo[key] = value
    if missing:
        s.details.append(f"{len(missing)} of {len(plan.chunks)} chunk(s) without notes")
    if invalid:
        s.details.append(f"notes that do not match their chunk: {', '.join(invalid)}")
    if stale:
        s.details.append(f"notes of an older document version: {', '.join(stale)}")
    if not profile_ok:
        s.todo["exam_profile"] = profile_problems or ["analysis/exam-profile.yaml is missing"]
        s.details.append(s.todo["exam_profile"][0])
    if not notation_ok:
        s.todo["notation"] = notation_problems or ["analysis/notation.yaml is missing"]
        s.details.append(s.todo["notation"][0])
    if lint:
        s.details.append(f"{len(lint)} lint error(s) in the notes or analysis")
    if transcribe:
        # a chunk's notes digest its scanned pages from the transcription (ingest skill)
        s.todo["transcriptions_missing"] = transcribe
        s.details.append(f"scanned page(s) without a transcription: {', '.join(transcribe)}")
    started = len(missing) < len(plan.chunks) or (inp.root / "analysis").is_dir()
    done = not (missing or invalid or stale or lint or transcribe) and profile_ok and notation_ok
    s.status = _combine(done, started, bool(stale) and not (missing or invalid))


def _lint(inp: Inputs, dirs: list[str]) -> list[str]:
    """Errors of the quick stages (schema, fences, math) in these course directories."""
    from studykit import validate

    paths = [inp.root / d for d in dirs if (inp.root / d).is_dir()]
    if not paths or inp.tree is None:
        return []
    report = validate.validate([inp.root], paths=paths, quick=True)
    return [f.format() for f in report.findings if f.is_error]


def _outline_names(inp: Inputs) -> str | None:
    path = inp.root / "sources" / "outline.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def step_synthesize(inp: Inputs, s: Step) -> None:
    s.proof = ["sources/outline.md", "course.yaml: topics"]
    if inp.course is None and not (inp.root / "sources" / "outline.md").is_file():
        return
    outline = _outline_names(inp)
    topics = inp.real_topics
    draft = inp.course is not None and model.DRAFT_TOPIC in inp.course.topic_ids
    if outline is None:
        s.details.append("sources/outline.md is missing")
    if draft or not topics:
        s.details.append("course.yaml still has only the placeholder topic 'draft'")
        s.todo["topics"] = True
    words = set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", outline or ""))
    unnamed_topics = [t.id for t in topics if outline is not None and t.id not in words]
    chunks = inp.chunks.chunks if inp.chunks else []
    unnamed_chunks = [c.id for c in chunks if outline is not None and c.id not in words]
    if unnamed_topics:
        s.todo["topics_not_in_outline"] = unnamed_topics
        s.details.append(f"outline.md does not name the topics {', '.join(unnamed_topics)}")
    if unnamed_chunks:
        s.todo["chunks_not_in_outline"] = unnamed_chunks
        s.details.append(
            f"{len(unnamed_chunks)} chunk(s) not in outline.md (new material): "
            "merge their notes into the topics"
        )
    if topics and not 6 <= len(topics) <= 15:
        s.details.append(f"{len(topics)} topics (§5.4 aims at 6 to 15)")
    weights = sum(t.weight for t in topics)
    if topics and abs(weights - 1) > model.SHARE_TOLERANCE:
        s.details.append(f"topic weights add up to {weights:.3g}, not 1")
    complete = outline is not None and topics and not draft and not unnamed_topics
    started = outline is not None or bool(topics)
    s.status = _combine(
        bool(complete) and not unnamed_chunks, started, bool(complete and unnamed_chunks)
    )


def step_ask2(inp: Inputs, s: Step) -> None:
    s.proof = ["sources/manifest.yaml: answers.round2", "course.yaml: targets.mock_exams"]
    r2 = inp.manifest.answers.round2 if inp.manifest else None
    if r2 is None:
        return
    s.status = "done"
    if not r2.go:
        s.status = "partial"
        s.details.append("the user chose no-go: `studykit ingest round2 … ` without --no-go")
    if inp.course is not None and inp.course.targets.mock_exams != r2.mock_exams:
        s.status = "partial"
        s.details.append(
            f"course.yaml targets.mock_exams is {inp.course.targets.mock_exams}, the user "
            f"chose {r2.mock_exams}"
        )
    if r2.scope == "core":
        s.details.append("scope core: exercises, mock exams and the cheat sheet come later")


# --- steps 7 to 14: authoring and publishing ---------------------------------------------------


def _coverage(inp: Inputs) -> list[Any]:
    from studykit import validate

    assert inp.tree is not None
    ctx = validate.Context(inp.tree, validate.Config(), None, False, True)
    validate.check_coverage(ctx)
    return [f for f in ctx.findings if f.is_error]


def _topic_of(finding: Any) -> str | None:
    m = re.search(r"topic '([a-z0-9-]+)'|bank '([a-z0-9-]+)'", finding.message)
    return (m[1] or m[2]) if m else None


def step_author(inp: Inputs, s: Step, cov: list[Any]) -> None:
    s.proof = ["overview.md", "summary/", "exercises/", "mc/"]
    if inp.tree is None or not inp.taught:
        return
    todo: dict[str, list[str]] = {}
    for f in cov:
        part = {
            "SK-COV-SUMMARY": "summary",
            "SK-COV-EXERCISES": "exercises",
            "SK-COV-MC": "mc",
            "SK-COV-OVERVIEW": "overview_links",
        }.get(f.code)
        if part == "exercises" and inp.core:
            continue
        if part:
            todo.setdefault(part, []).append(_topic_of(f) or f.message)
    if inp.tree.get("overview.md") is None:
        todo["overview"] = ["overview.md"]
    for part, items in todo.items():
        s.details.append(f"{part}: {', '.join(items)}")
    schema = [
        f.format()
        for d in inp.tree
        if d.kind in ("overview", "summary", "exercise", "mc")
        for f in d.validated[1]
    ]
    if schema:
        todo["schema_errors"] = schema
        s.details.append(f"{len(schema)} schema error(s) in authored files")
    s.todo = todo
    started = any(inp.tree.of_kind("overview", "summary", "exercise", "mc"))
    if inp.core:
        s.details.append("scope core: exercises deferred")
    s.status = _combine(not todo, started, False)


def step_figures(inp: Inputs, s: Step) -> None:
    from studykit.figures import builtins, runner  # builtins registers runner.BUILTINS

    del builtins

    s.proof = ["_build/figures/manifest.json", "_build/figures/<slug>.svg"]
    if inp.tree is None or inp.course is None or not inp.real_topics:
        return
    out_dir = inp.root / "_build" / "figures"
    try:
        built = json.loads((out_dir / "manifest.json").read_text())
    except OSError, ValueError:
        built = {}
    tree_key = runner._tree_digest(tools.repo_root()).encode()
    style = runner.style_key(inp.root)
    expected: dict[str, str] = {}
    for script in sorted((inp.root / "figures").glob("*.py")):
        expected[script.stem] = runner._key([script.read_bytes(), tree_key, style])
    course_bytes = (inp.root / "course.yaml").read_bytes()
    for name in sorted(runner.BUILTINS):
        expected[name] = runner._key([name.encode(), course_bytes, tree_key, style])
    missing = [
        slug for slug in expected if slug not in built or not runner._outputs_exist(out_dir, slug)
    ]
    stale = [
        slug
        for slug, key in expected.items()
        if slug not in missing and built[slug].get("key") != key
    ]
    if missing:
        s.todo["not_built"] = missing
        s.details.append(f"not built: {', '.join(missing)}")
    if stale:
        s.todo["stale"] = stale
        s.details.append(f"built from older inputs: {', '.join(stale)}")
    if s.todo:
        s.details.append("run `just figures <course>`, then look at the PNGs")
    s.status = _combine(not s.todo, len(missing) < len(expected), bool(stale))


def _ledger(inp: Inputs, items: list[verify.VItem]) -> tuple[dict[str, list[str]], int]:
    """Item ids by outcome (no-ledger, stale, unverified, disputed, verified, quarantined)."""
    out: dict[str, list[str]] = {}
    for item in items:
        try:
            entry = verify.read_ledger(inp.root, item.id)
        except ValueError:
            entry = None
        if entry is None:
            outcome = "no-ledger"
        elif verify.is_stale(entry, item):
            outcome = "stale"
        else:
            outcome = entry.status
        out.setdefault(outcome, []).append(item.id)
    return out, len(items)


def _verify_status(s: Step, by: dict[str, list[str]], total: int) -> None:
    open_ = {k: v for k, v in by.items() if k not in ("verified", "quarantined")}
    for k, v in open_.items():
        s.todo[k.replace("-", "_")] = v
    if open_:
        s.details.append(", ".join(f"{len(v)} {k}" for k, v in sorted(open_.items())))
    if by.get("quarantined"):
        s.details.append(f"{len(by['quarantined'])} quarantined")
    started = total > len(by.get("no-ledger", []))
    s.status = _combine(total > 0 and not open_, started, bool(by.get("stale")))


def step_verify(inp: Inputs, s: Step) -> None:
    s.proof = ["state/verify/<item>.json"]
    if inp.tree is None or not inp.taught:
        return
    items = [
        i
        for i in verify.items(inp.tree)
        if i.exam is None and not (inp.core and i.kind == "exercise")
    ]
    if not items:
        return
    by, total = _ledger(inp, items)
    _verify_status(s, by, total)
    s.details.insert(0, f"{len(by.get('verified', []))} of {total} topic item(s) verified")


def step_mock_exams(inp: Inputs, s: Step, cov: list[Any]) -> None:
    s.proof = ["exams/<exam>/", "state/verify/<task>.json"]
    s.deferred = inp.core
    if inp.tree is None or inp.course is None or not inp.taught:
        return
    exams = inp.tree.of_kind("exam")
    need = inp.course.targets.mock_exams
    size = [f.message for f in cov if f.code == "SK-COV-EXAM"]
    if len(exams) < need:
        s.todo["missing_exams"] = need - len(exams)
        s.details.append(f"{len(exams)} of {need} mock exam(s)")
    sizes = [m for m in size if "mock exam(s), the target" not in m]
    if sizes:
        s.todo["size"] = sizes
        s.details += sizes[:2]
    mc_present = bool(inp.course.exam.mc and inp.course.exam.mc.present)
    no_mc = [d.parts["exam"] for d in exams if mc_present and d.model and d.model.mc is None]
    if no_mc:
        s.todo["no_mc_part"] = no_mc
        s.details.append(f"no MC part: {', '.join(no_mc)}")
    archetypes = inp.tree.archetypes
    tasks = inp.tree.of_kind("exam-task")
    unknown = [
        d.rel
        for d in tasks
        if archetypes is not None
        and isinstance(d.get("archetype"), str)
        and d.get("archetype") not in archetypes
    ]
    if unknown:
        s.todo["unknown_archetypes"] = unknown
        s.details.append(f"{len(unknown)} task(s) with an archetype not in the profile")
    items = [i for i in verify.items(inp.tree) if i.exam is not None]
    by, total = _ledger(inp, items)
    if total:
        sub = Step(s.n, s.name)
        _verify_status(sub, by, total)
        s.todo.update(sub.todo)
        s.details += sub.details
    started = bool(exams)
    s.status = _combine(started and not s.todo, started, bool(by.get("stale")))


def _freshness(inp: Inputs) -> dict[str, str] | None:
    from studykit import pdf

    try:
        return pdf.freshness(inp.root)
    except FileNotFoundError:
        return None


def step_cheatsheet(inp: Inputs, s: Step, fresh: dict[str, str] | None) -> None:
    from studykit import pdf

    s.proof = ["cheatsheet.md", "_build/pdf/cheatsheet.pdf"]
    s.deferred = inp.core
    if inp.course is None or not inp.real_topics:
        return
    if not inp.course.cheatsheet.allowed:
        s.status = "done"
        s.details.append("no cheat sheet allowed")
        return
    if inp.tree is None or inp.tree.get("cheatsheet.md") is None:
        return
    entry = next(
        (
            d
            for d in (pdf.read_manifest(inp.root) or {}).get("docs") or []
            if d.get("id") == "cheatsheet"
        ),
        None,
    )
    limit = inp.course.cheatsheet.max_pages
    state = (fresh or {}).get("cheatsheet", "missing")
    if entry is None or state == "missing":
        s.todo["fit"] = True
        s.details.append("not fitted yet: `just cheatsheet <course>`")
    elif entry.get("pages", limit + 1) > limit:
        s.todo["over_limit"] = entry.get("pages")
        s.details.append(f"{entry.get('pages')} pages, the limit is {limit}")
    else:
        level = entry.get("density")
        s.details.append(f"{entry.get('pages')} of {limit} page(s) at {FONT_PT.get(level, '?')} pt")
    if fresh is None:
        s.details.append("freshness not checked: pandoc or typst is not installed")
    stale = state == "stale"
    if stale:
        s.todo["stale"] = True
        s.details.append("cheatsheet.pdf is older than the cheat sheet: fit it again")
    s.status = _combine(not s.todo, True, stale)


def step_plan(inp: Inputs, s: Step) -> None:
    s.proof = ["plan.yaml"]
    if inp.tree is None or inp.course is None:
        return
    doc = inp.tree.get("plan.yaml")
    if doc is None:
        return
    ok, problems = inp.valid("plan.yaml")
    if not ok:
        s.todo["problems"] = problems
        s.details += problems[:2]
        s.status = "partial"
        return
    plan = doc.model
    targets = {
        "ex": set(inp.tree.ids("exercise")),
        "exam": set(inp.tree.ids("exam")),
        "topic": set(inp.tree.topics),
    }
    broken = sorted(
        {
            ref
            for session in plan.sessions
            for task in session.tasks
            for ref in [*([task.ref] if task.ref else []), *task.refs]
            if ref.split(":", 1)[0] in targets
            and ref.split(":", 1)[1] not in targets[ref.split(":", 1)[0]]
        }
    )
    no_goal = [x.id for x in plan.sessions if not x.goal]
    stale_date = plan.exam_date != inp.course.exam.date
    if broken:
        s.todo["missing_refs"] = broken
        s.details.append(f"refers to {len(broken)} item(s) that are gone: replan")
    if stale_date:
        s.todo["exam_date"] = str(inp.course.exam.date)
        s.details.append("made for another exam date: `studykit plan <course>`")
    if no_goal:
        s.todo["goals_missing"] = no_goal
        s.details.append(f"{len(no_goal)} session(s) without a goal")
    s.status = _combine(not s.todo, True, bool(broken or stale_date))


def step_publish(inp: Inputs, s: Step, fresh: dict[str, str] | None) -> None:
    s.proof = ["course.yaml: status ready", "_build/pdf/manifest.json", "site/dist/c/<course>/"]
    if inp.course is None or not inp.real_topics:
        return
    ready = inp.course.status == "ready"
    fresh = fresh or {}
    missing = [d for d, st in fresh.items() if st == "missing"]
    stale = [d for d, st in fresh.items() if st == "stale"]
    page = tools.repo_root() / "site" / "dist" / "c" / inp.course.id / "index.html"
    if missing:
        s.todo["pdf_missing"] = missing
        s.details.append(f"PDFs not built: {', '.join(missing)}")
    if stale:
        s.todo["pdf_stale"] = stale
        s.details.append(f"PDFs older than their sources: {', '.join(stale)}")
    if not page.is_file():
        s.todo["site"] = "not built"
        s.details.append("the site has no page for the course: `just build <course>`")
    else:
        newest = max(
            (p.stat().st_mtime for p in (inp.root / "_build" / "pdf").glob("*.pdf")), default=0
        )
        if newest > page.stat().st_mtime:
            s.todo["site"] = "older than the PDFs"
            s.details.append("the site was built before the PDFs: `just build <course>`")
    if not ready:
        s.todo["status"] = "draft"
        s.details.append("course.yaml status is draft; ready after a green validate --release")
    started = ready or any(st != "missing" for st in fresh.values())
    # a ready course whose PDFs or site fell behind: the ready claim itself is stale
    s.status = _combine(not s.todo, started, ready and bool(s.todo))


def fingerprint(root: Path) -> str:
    """sha256 over the course's content files, the ledger and the PDF manifest."""
    tree = CourseTree(root)
    h = hashlib.sha256()
    files = [d.path for d in tree] + sorted((root / "state" / "verify").glob("*.json"))
    files.append(root / "_build" / "pdf" / "manifest.json")
    for path in files:
        if path.is_file():
            h.update(path.relative_to(root).as_posix().encode() + b"\0")
            h.update(path.read_bytes() + b"\0")
    return h.hexdigest()


def step_report(inp: Inputs, s: Step) -> None:
    s.proof = [REPORT.as_posix()]
    path = inp.root / REPORT
    if not path.is_file():
        return
    m = FINGERPRINT_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if m and m[1] == fingerprint(inp.root):
        s.status = "done"
    else:
        s.status = "stale"
        s.details.append("the course changed since the report: `studykit pipeline report`")


# --- status ----------------------------------------------------------------------------------


def status(root: Path) -> dict[str, Any]:
    """Every step's status and the resume point."""
    inp = Inputs(root.resolve())
    steps = [Step(n, name) for n, name in enumerate(STEPS)]
    step_preflight(inp, steps[0])
    step_ask1(inp, steps[1])
    step_scaffold(inp, steps[2])
    step_extract(inp, steps[3])
    step_read(inp, steps[4])
    step_synthesize(inp, steps[5])
    step_ask2(inp, steps[6])
    if inp.tree is not None and inp.course is not None and inp.real_topics:
        cov = _coverage(inp)
        fresh = _freshness(inp)
    else:
        cov, fresh = [], None
    step_author(inp, steps[7], cov)
    step_figures(inp, steps[8])
    step_verify(inp, steps[9])
    step_mock_exams(inp, steps[10], cov)
    step_cheatsheet(inp, steps[11], fresh)
    step_plan(inp, steps[12])
    step_publish(inp, steps[13], fresh)
    step_report(inp, steps[14])
    if inp.core:
        steps[10].deferred = steps[11].deferred = True
    resume = next((x for x in steps if x.status != "done" and not x.deferred), None)
    deferred = [x.name for x in steps if x.deferred and x.status != "done"]
    return {
        "course": root.name,
        "dir": str(root.resolve()),
        "exists": inp.exists,
        "course_status": inp.course.status if inp.course else None,
        "scope": "core" if inp.core else "full",
        "resume": {"step": resume.n, "name": resume.name} if resume else None,
        "complete": resume is None and not deferred,
        "deferred": deferred,
        "steps": [x.to_json() for x in steps],
    }


def format_status(result: dict[str, Any]) -> str:
    lines = [f"pipeline of {result['course']} ({result['dir']}), scope {result['scope']}"]
    for st in result["steps"]:
        mark = " (deferred)" if st["deferred"] else ""
        first = f"  {st['details'][0]}" if st["details"] else ""
        lines.append(f"  {st['step']:>2} {st['name']:<11} {st['status']:<8}{mark}{first}")
        for more in st["details"][1:3]:
            lines.append(f"{'':<25}{more}")
    if result["resume"]:
        r = result["resume"]
        lines.append(f"resume at step {r['step']} ({r['name']})")
    elif result["deferred"]:
        lines.append(f"done but for the deferred steps: {', '.join(result['deferred'])}")
    else:
        lines.append("every step is done")
    return "\n".join(lines)


# --- report (step 14) --------------------------------------------------------------------------


def report(root: Path, today: dt.date | None = None) -> tuple[Path, dict[str, Any]]:
    """Write state/pipeline/report.md: counts per part, verification, cheat sheet, next steps."""
    from studykit import pdf

    today = today or dt.date.today()
    root = root.resolve()
    tree = CourseTree(root)
    course = tree.model
    if course is None:
        raise ValueError(f"{display_path(root / 'course.yaml')} does not validate")
    exercises = tree.of_kind("exercise")
    difficulty = Counter(d.get("difficulty") for d in exercises)
    mc_types: Counter[str] = Counter()
    for bank in tree.of_kind("mc"):
        for q in bank.body.questions if bank.body else []:
            mc_types[q.type] += 1
    exams = sorted(d.parts["exam"] for d in tree.of_kind("exam"))
    figures = sorted(p.stem for p in (root / "figures").glob("*.py"))
    items = verify.items(tree)
    by: dict[str, list[tuple[str, str]]] = {}
    fixed = 0
    for item in items:
        try:
            entry = verify.read_ledger(root, item.id)
        except ValueError:
            entry = None
        if entry is None:
            outcome, note = "unverified", "no check yet"
        elif verify.is_stale(entry, item):
            outcome, note = "stale", "changed since its check"
        else:
            outcome, note = entry.status, entry.note or "; ".join(entry.problems[:1]) or ""
            fixed += entry.status == "verified" and bool(entry.disputes)
        by.setdefault(outcome, []).append((item.id, note))
    total = len(items)

    def share(n: int) -> str:
        return f"{n} ({n / total:.0%})" if total else "0"

    manifest = pdf.read_manifest(root) or {}
    sheet = next((d for d in manifest.get("docs") or [] if d.get("id") == "cheatsheet"), None)
    data = {
        "course": course.id,
        "generated": today.isoformat(),
        "overview": tree.get("overview.md") is not None,
        "summaries": len(tree.of_kind("summary")),
        "topics": len(course.topics),
        "exercises": {"total": len(exercises), "by_difficulty": dict(sorted(difficulty.items()))},
        "mc": {"total": sum(mc_types.values()), "by_type": dict(sorted(mc_types.items()))},
        "exams": exams,
        "figures": len(figures),
        "verification": {
            "items": total,
            "verified": len(by.get("verified", [])),
            "fixed": fixed,
            "quarantined": [{"id": i, "reason": n} for i, n in by.get("quarantined", [])],
            "disputed": [{"id": i, "reason": n} for i, n in by.get("disputed", [])],
            "unverified": len(by.get("unverified", [])),
            "stale": len(by.get("stale", [])),
        },
        "cheatsheet": None
        if sheet is None
        else {
            "pages": sheet.get("pages"),
            "max_pages": sheet.get("max_pages"),
            "density": sheet.get("density"),
            "font_pt": FONT_PT.get(sheet.get("density")),
        },
    }
    v = data["verification"]
    by_diff = ", ".join(f"{k}: {n}" for k, n in data["exercises"]["by_difficulty"].items())
    by_type = ", ".join(f"{k}: {n}" for k, n in data["mc"]["by_type"].items())
    lines = [
        f"# Pipeline report: {course.title} ({course.id})",
        "",
        f"<!-- studykit-pipeline fingerprint {fingerprint(root)} -->",
        f"Written by `studykit pipeline report` on {today.isoformat()}.",
        "",
        "## Content",
        "",
        "| Part | Count | Detail |",
        "|---|---|---|",
        f"| Overview | {'yes' if data['overview'] else 'no'} | |",
        f"| Summary chapters | {data['summaries']} | {data['topics']} topics |",
        f"| Exercises | {len(exercises)} | by difficulty {by_diff or '-'} |",
        f"| MC questions | {data['mc']['total']} | {by_type or '-'} |",
        f"| Mock exams | {len(exams)} | {', '.join(exams) or '-'} |",
        f"| Figure scripts | {len(figures)} | |",
        "",
        "## Verification",
        "",
        f"- verified: {share(v['verified'])}, of them fixed after a dispute: {fixed}",
        f"- quarantined: {share(len(v['quarantined']))}",
        f"- disputed: {share(len(v['disputed']))}",
        f"- unverified: {share(v['unverified'])}; stale: {share(v['stale'])}",
    ]
    for kind in ("quarantined", "disputed"):
        for entry in v[kind]:
            lines.append(f"  - {kind} {entry['id']}: {entry['reason'] or 'no reason recorded'}")
    lines += ["", "## Cheat sheet", ""]
    cs = data["cheatsheet"]
    if cs is None:
        lines.append("not built" if course.cheatsheet.allowed else "not allowed in this exam")
    else:
        lines.append(f"{cs['pages']} of {cs['max_pages']} page(s), {cs['font_pt']} pt")
    lines += [
        "",
        "## Next steps",
        "",
        f"- `just dev`, then http://localhost:4321/c/{course.id}/",
        f"- `/examine {course.id} diagnostic`: 15 MC questions seed the Leitner boxes and the plan",
        f"- `/tutor {course.id}` for a topic or an exercise",
        "",
    ]
    path = root / REPORT
    ingest._write(path, "\n".join(lines))
    return path, data


def resolve(arg: str) -> Path:
    return content.resolve_course(arg)
