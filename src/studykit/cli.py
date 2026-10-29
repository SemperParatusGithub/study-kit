"""Command line entry point: `studykit <command>`."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from studykit import __version__, doctor, golden, tools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="studykit", description=__doc__)
    parser.add_argument("--version", action="version", version=f"studykit {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_tools = sub.add_parser("tools", help="manage the pinned external toolchain")
    tools_sub = p_tools.add_subparsers(dest="tools_command", metavar="<action>", required=True)
    p_install = tools_sub.add_parser("install", help="install pandoc and typst into .tools/bin")
    p_install.add_argument("--force", action="store_true", help="reinstall even if up to date")
    p_install.set_defaults(func=cmd_tools_install)

    p_doctor = sub.add_parser("doctor", help="check that the toolchain matches toolchain.toml")
    p_doctor.add_argument("--quick", action="store_true", help="skip site, fonts and port checks")
    p_doctor.add_argument("--json", action="store_true", help="machine-readable output")
    p_doctor.set_defaults(func=cmd_doctor)

    p_golden = sub.add_parser("golden", help="run the golden math corpus through both engines")
    p_golden.add_argument("--update", action="store_true", help="rewrite the Typst snapshot")
    p_golden.set_defaults(func=cmd_golden)

    p_schema = sub.add_parser("schema", help="JSON schemas generated from the pydantic models")
    schema_sub = p_schema.add_subparsers(dest="schema_command", metavar="<action>", required=True)
    p_export = schema_sub.add_parser("export", help="write schemas/*.schema.json")
    p_export.add_argument("--check", action="store_true", help="fail if the files are stale")
    p_export.set_defaults(func=cmd_schema_export)

    p_ls = sub.add_parser("ls", help="list courses, or a course's content files by kind")
    p_ls.add_argument("course", nargs="?", help="course id or directory (default: all courses)")
    p_ls.add_argument("--kind", action="append", metavar="KIND", help="only files of this kind")
    p_ls.add_argument("--json", action="store_true", help="machine-readable output")
    p_ls.set_defaults(func=cmd_ls)

    p_index = sub.add_parser("index", help="write the id index _build/index.json for pandoc")
    p_index.add_argument("course", help="course id or directory")
    p_index.add_argument("--json", action="store_true", help="also print the index")
    p_index.set_defaults(func=cmd_index)

    p_lint = sub.add_parser("lint", help="fast per-file content check (the edit hook)")
    p_lint.add_argument("files", nargs="*", type=Path, help="course files to check")
    p_lint.add_argument(
        "--hook", action="store_true", help="read a Claude Code PostToolUse event from stdin"
    )
    p_lint.add_argument("--json", action="store_true", help="machine-readable output")
    p_lint.set_defaults(func=cmd_lint)

    p_validate = sub.add_parser("validate", help="validate courses stage by stage (SK-codes)")
    p_validate.add_argument("course", nargs="?", help="course id or directory (default: all)")
    p_validate.add_argument("--paths", nargs="+", type=Path, help="only report these files")
    p_validate.add_argument(
        "--quick", action="store_true", help="quick stages: Structure to Math, Pandoc backstop"
    )
    p_validate.add_argument(
        "--release", action="store_true", help="add the Site and Coverage stages"
    )
    p_validate.add_argument("--json", action="store_true", help="machine-readable output")
    p_validate.set_defaults(func=cmd_validate)

    p_render = sub.add_parser("render", help="render course files to HTML for the website")
    p_render.add_argument("course", help="course id or directory")
    p_render.add_argument(
        "--paths", nargs="+", metavar="PATH", help="only these files (course-relative or paths)"
    )
    p_render.add_argument(
        "--known",
        metavar="FILE",
        help="JSON {rel: digest} of renders the caller holds ('-' reads stdin); those come "
        "back as cached",
    )
    p_render.add_argument("--jobs", type=int, help="parallel pandoc runs (default: CPU count)")
    p_render.add_argument("--json", action="store_true", help="print the full result as JSON")
    p_render.set_defaults(func=cmd_render)

    p_links = sub.add_parser("check-links", help="check internal links and anchors of the site")
    p_links.add_argument("dist", nargs="?", type=Path, default=Path("site/dist"))
    p_links.add_argument(
        "--strict-documents",
        action="store_true",
        help="fail on missing PDFs under /c/<c>/src/ and /c/<c>/pdf/ too (default: warn)",
    )
    p_links.add_argument("--json", action="store_true", help="machine-readable output")
    p_links.set_defaults(func=cmd_check_links)

    p_pdf = sub.add_parser("pdf", help="build the course's PDF documents into _build/pdf")
    p_pdf.add_argument("course", nargs="?", help="course id or directory (default: all)")
    p_pdf.add_argument(
        "docs",
        nargs="*",
        metavar="doc",
        help="only these documents: overview, summary, exercises, exercises-blank, mc, "
        "<exam>, <exam>-solutions, cheatsheet, plan (default: all)",
    )
    p_pdf.add_argument("--force", action="store_true", help="rebuild even if up to date")
    p_pdf.add_argument(
        "--no-figures", action="store_true", help="do not build the figures (cached) first"
    )
    p_pdf.add_argument("--jobs", type=int, help="documents built in parallel (default: CPUs)")
    p_pdf.add_argument("--json", action="store_true", help="machine-readable output")
    p_pdf.set_defaults(func=cmd_pdf)

    p_cs = sub.add_parser("cheatsheet", help="the cheat sheet PDF and its page limit")
    cs_sub = p_cs.add_subparsers(dest="cheatsheet_command", metavar="<action>", required=True)
    p_fit = cs_sub.add_parser(
        "fit",
        help="build cheatsheet.pdf at the first density (0-4) within its page limit; "
        "exit 3 with the overflow when none fits",
    )
    p_fit.add_argument("course", help="course id or directory")
    p_fit.add_argument("--force", action="store_true", help="rebuild even if up to date")
    p_fit.add_argument(
        "--no-figures", action="store_true", help="do not build the figures (cached) first"
    )
    p_fit.add_argument("--json", action="store_true", help="machine-readable output")
    p_fit.set_defaults(func=cmd_cheatsheet_fit)

    p_calc = sub.add_parser(
        "calc",
        help="evaluate a SymPy expression: exact, numeric, complex (j) and units",
        description="Evaluate an expression safely with SymPy. ^ is a power, j the imaginary "
        "unit; helpers: par(a, b, ...) parallel, pol(r, deg) phasor, mag, angd (angle in "
        "degrees), db, lg, deg, rad, solve, diff, integrate.",
    )
    p_calc.add_argument("expr", help="the expression, e.g. '1/(2*pi*R*C)'")
    p_calc.add_argument(
        "--subs",
        nargs="+",
        action="extend",
        default=[],
        metavar="NAME=VALUE",
        help="values for symbols (repeat --subs or list several)",
    )
    p_calc.add_argument(
        "--units",
        action="store_true",
        help="allow units (V, mA, kohm, kΩ, nF, µs, MHz, …) and give the result in SI units",
    )
    p_calc.add_argument("--digits", type=int, default=6, help="significant digits shown")
    p_calc.add_argument("--json", action="store_true", help="machine-readable output")
    p_calc.set_defaults(func=cmd_calc)

    p_verify = sub.add_parser(
        "verify",
        help="run the verifier's checks and update the ledger state/verify/<id>.json",
        description="Run checks/<id>.py or .json for the selected items, compare them with "
        "the answer key and write the ledger. Other actions record the steps of the dispute "
        "protocol (docs/architecture.md §5.3).",
    )
    p_verify.add_argument("course", help="course id or directory")
    p_verify.add_argument(
        "target",
        nargs="?",
        default="all",
        help="an item id, a topic, an exam or all (default); for --clear also stale or orphans",
    )
    actions = p_verify.add_mutually_exclusive_group()
    actions.add_argument(
        "--status", action="store_true", help="show the ledger state without running checks"
    )
    actions.add_argument(
        "--confirm",
        metavar="FILE",
        type=Path,
        help="run a second method (checks/<id>.<tag>.py or .json) for one item and record it",
    )
    actions.add_argument(
        "--dispute",
        action="store_true",
        help="record a dispute for one item by hand (with --note and --computed)",
    )
    actions.add_argument(
        "--quarantine",
        action="store_true",
        help="quarantine one item by hand (with --note): hidden from the site and the PDFs",
    )
    actions.add_argument(
        "--clear", action="store_true", help="delete the ledger entries of the target"
    )
    p_verify.add_argument("--method", help="--confirm: what the second method does")
    p_verify.add_argument("--note", help="--dispute, --quarantine: the reason")
    p_verify.add_argument(
        "--computed",
        nargs="+",
        default=[],
        metavar="KEY=VALUE",
        help="--dispute: the verifier's numbers",
    )
    p_verify.add_argument("--report", action="store_true", help="also write state/verify/report.md")
    p_verify.add_argument(
        "--show-key",
        action="store_true",
        help="show the answer key in problems (the text output hides it from the verifier)",
    )
    p_verify.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="seconds per check script (default 120)",
    )
    p_verify.add_argument("--json", action="store_true", help="machine-readable output")
    p_verify.set_defaults(func=cmd_verify)

    p_blind = sub.add_parser(
        "blind",
        help="write the blind view _build/blind/<id>.md of an item for the verifier",
    )
    p_blind.add_argument("course", help="course id or directory")
    p_blind.add_argument("id", help="exercise, exam task or MC question id")
    p_blind.add_argument("--stdout", action="store_true", help="also print the view")
    p_blind.set_defaults(func=cmd_blind)

    p_hook = sub.add_parser(
        "hook",
        help="Claude Code PreToolUse hooks: read the event on stdin, print a decision",
    )
    p_hook.add_argument(
        "name",
        choices=["verifier-guard", "pre-git"],
        help="verifier-guard: keep the verifier blind; pre-git: keep course files out of git",
    )
    p_hook.set_defaults(func=cmd_hook)

    _add_study_commands(sub)
    _add_ingest_commands(sub)
    _add_pipeline_commands(sub)

    p_fig = sub.add_parser("fig", help="figures: build course figure scripts")
    fig_sub = p_fig.add_subparsers(dest="fig_command", metavar="<action>", required=True)
    p_fig_build = fig_sub.add_parser("build", help="render figures to _build/figures")
    p_fig_build.add_argument("course", nargs="?", help="course id (default: all courses)")
    p_fig_build.add_argument("--only", action="append", metavar="SLUG", help="only this figure")
    p_fig_build.add_argument("--force", action="store_true", help="ignore the cache")
    p_fig_build.set_defaults(func=cmd_fig_build)

    return parser


def _day(value: str) -> str:
    from datetime import date

    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a day YYYY-MM-DD: {value!r}") from exc


def _add_study_commands(sub) -> None:
    """progress, plan and status: the student's side of a course (§2.9, §2.11)."""
    p_prog = sub.add_parser("progress", help="browser progress, examiner results, mastery")
    prog_sub = p_prog.add_subparsers(dest="progress_command", metavar="<action>", required=True)

    p_imp = prog_sub.add_parser(
        "import", help="validate a browser export and merge it into progress/state.json"
    )
    p_imp.add_argument("course", help="course id or directory")
    p_imp.add_argument("file", type=Path, help="studykit-progress-<course>-<date>.json")
    p_imp.add_argument("--dry-run", action="store_true", help="report the changes, write nothing")
    p_imp.add_argument("--json", action="store_true", help="machine-readable output")
    p_imp.set_defaults(func=cmd_progress_import)

    p_log = prog_sub.add_parser(
        "log", help="append examiner results (JSON objects) to progress/examiner.jsonl"
    )
    p_log.add_argument("course", help="course id or directory")
    p_log.add_argument(
        "--json-line",
        action="append",
        metavar="JSON",
        help="one result as a JSON object (repeatable); without it, JSON lines from stdin",
    )
    p_log.add_argument("--json", action="store_true", help="machine-readable output")
    p_log.set_defaults(func=cmd_progress_log)

    p_rep = prog_sub.add_parser("report", help="write progress/mastery.json and progress/report.md")
    p_rep.add_argument("course", help="course id or directory")
    p_rep.add_argument("--today", type=_day, help="the day to report for (default: today)")
    p_rep.add_argument("--json", action="store_true", help="print mastery.json")
    p_rep.set_defaults(func=cmd_progress_report)

    p_plan = sub.add_parser("plan", help="schedule the study plan into plan.yaml (deterministic)")
    p_plan.add_argument("course", help="course id or directory")
    p_plan.add_argument(
        "--from", dest="start", type=_day, help="first day to plan (default: today)"
    )
    p_plan.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    p_plan.add_argument("--json", action="store_true", help="machine-readable output")
    p_plan.set_defaults(func=cmd_plan)

    p_status = sub.add_parser(
        "status", help="study status: days left, plan adherence, weak topics, reviews due"
    )
    p_status.add_argument("course", help="course id or directory")
    p_status.add_argument("--today", type=_day, help="the day to report for (default: today)")
    p_status.add_argument("--json", action="store_true", help="machine-readable output")
    p_status.set_defaults(func=cmd_status)


def _add_ingest_commands(sub) -> None:
    """ingest and pipeline: the Python steps of /register-new-subject (§5.4)."""
    kind_help = "a document's kind, DOC=KIND (DOC: id or path in the folder; repeatable)"
    p_ing = sub.add_parser("ingest", help="scan, copy and read lecture material (§5.4)")
    ing_sub = p_ing.add_subparsers(dest="ingest_command", metavar="<action>", required=True)

    p_scan = ing_sub.add_parser(
        "scan", help="inventory a folder of lecture PDFs (pages, text layer, kind, duplicates)"
    )
    p_scan.add_argument("folder", type=Path, help="the folder (or one file) to inventory")
    p_scan.add_argument(
        "--dry-run", action="store_true", help="accepted for clarity: scan never writes"
    )
    p_scan.add_argument("--kind", action="append", default=[], metavar="DOC=KIND", help=kind_help)
    p_scan.add_argument("--today", type=_day, help="the day exam dates must follow")
    p_scan.add_argument("--json", action="store_true", help="machine-readable output")
    p_scan.set_defaults(func=cmd_ingest_scan)

    p_init = ing_sub.add_parser(
        "init",
        help="copy the PDFs into courses/<id>/sources, write the manifest and a draft "
        "course.yaml (resumes an existing course)",
    )
    p_init.add_argument("folder", type=Path, help="the folder with the lecture PDFs (only read)")
    p_init.add_argument("course", help="the new course id, e.g. elektronik-1")
    p_init.add_argument("--lang", choices=["de", "en"], help="content language (default: guessed)")
    p_init.add_argument("--title", help="course title (default: the course id)")
    p_init.add_argument("--short", help="short course name")
    p_init.add_argument("--semester", help="e.g. 'WS 2026/27'")
    p_init.add_argument(
        "--exam-date", metavar="unknown|YYYY-MM-DD", type=_exam_day, help="round 1: exam date"
    )
    p_init.add_argument(
        "--exam-format",
        choices=["written", "written-mc", "mc", "oral"],
        help="round 1: written, written with an MC part, MC only, oral",
    )
    p_init.add_argument(
        "--cheatsheet",
        type=int,
        choices=[0, 1, 2, 3],
        help="round 1: cheat-sheet pages allowed (0: none)",
    )
    p_init.add_argument("--hours-per-week", type=float, help="round 1: study hours per week")
    p_init.add_argument("--exam-minutes", type=int, help="exam duration, if known")
    p_init.add_argument("--exam-points", type=float, help="exam points, if known")
    p_init.add_argument("--start", type=_day, help="first study day (default: today)")
    p_init.add_argument("--kind", action="append", default=[], metavar="DOC=KIND", help=kind_help)
    p_init.add_argument("--today", type=_day, help="the day recorded (default: today)")
    p_init.add_argument("--dry-run", action="store_true", help="report, write nothing")
    p_init.add_argument("--json", action="store_true", help="machine-readable output")
    p_init.set_defaults(func=cmd_ingest_init)

    p_ext = ing_sub.add_parser(
        "extract", help="page text into sources/text and the chunk plan sources/chunks.yaml"
    )
    p_ext.add_argument("course", help="course id or directory")
    p_ext.add_argument("--json", action="store_true", help="machine-readable output")
    p_ext.set_defaults(func=cmd_ingest_extract)

    p_add = ing_sub.add_parser(
        "add", help="add new or changed PDFs to a course and extract them (/add-material)"
    )
    p_add.add_argument("course", help="course id or directory")
    p_add.add_argument("source", type=Path, help="a PDF or a folder (only read)")
    p_add.add_argument("--kind", action="append", default=[], metavar="DOC=KIND", help=kind_help)
    p_add.add_argument("--today", type=_day, help="the day recorded (default: today)")
    p_add.add_argument("--dry-run", action="store_true", help="report, write nothing")
    p_add.add_argument("--json", action="store_true", help="machine-readable output")
    p_add.set_defaults(func=cmd_ingest_add)

    p_r2 = ing_sub.add_parser("round2", help="record the answers of ask round 2 (§5.4 step 6)")
    p_r2.add_argument("course", help="course id or directory")
    p_r2.add_argument("--mock-exams", type=int, choices=[1, 2, 3], required=True)
    p_r2.add_argument(
        "--scope",
        choices=["full", "core"],
        required=True,
        help="core: summary, MC and plan first, the rest later",
    )
    p_r2.add_argument("--no-go", action="store_true", help="the user stopped the run here")
    p_r2.add_argument("--today", type=_day, help="the day recorded (default: today)")
    p_r2.add_argument("--json", action="store_true", help="machine-readable output")
    p_r2.set_defaults(func=cmd_ingest_round2)


def _add_pipeline_commands(sub) -> None:
    p_pipe = sub.add_parser(
        "pipeline", help="the state of /register-new-subject, derived from its outputs (§5.4)"
    )
    pipe_sub = p_pipe.add_subparsers(dest="pipeline_command", metavar="<action>", required=True)
    p_st = pipe_sub.add_parser(
        "status", help="each step done, pending, partial or stale, and the step to resume at"
    )
    p_st.add_argument("course", help="course id or directory (need not exist yet)")
    p_st.add_argument("--json", action="store_true", help="machine-readable output")
    p_st.set_defaults(func=cmd_pipeline_status)
    p_rep = pipe_sub.add_parser(
        "report", help="write state/pipeline/report.md (step 14): counts, verification, sheet"
    )
    p_rep.add_argument("course", help="course id or directory")
    p_rep.add_argument("--today", type=_day, help="the day written (default: today)")
    p_rep.add_argument("--json", action="store_true", help="machine-readable output")
    p_rep.set_defaults(func=cmd_pipeline_report)


def cmd_pipeline_status(args: argparse.Namespace) -> int:
    import re

    from studykit import model, pipeline

    as_path = "/" in args.course or Path(args.course).is_dir()
    if not as_path and not re.fullmatch(model.PATTERNS["course"], args.course):
        print(f"error: {args.course!r} is not a course id or directory", file=sys.stderr)
        return 2
    result = pipeline.status(pipeline.resolve(args.course))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(pipeline.format_status(result))
    return 0


def cmd_pipeline_report(args: argparse.Namespace) -> int:
    from studykit import content, pipeline

    tree = _course_tree(args.course)
    if tree is None:
        return 1
    try:
        path, data = pipeline.report(tree.root, _date_arg(args.today))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"report": content.display_path(path), **data}, indent=2))
    else:
        print(f"wrote {content.display_path(path)}")
    return 0


def _exam_day(value: str) -> str:
    return value if value == "unknown" else _day(value)


def _ingest_out(result: dict, found, as_json: bool, text) -> int:
    errors = [f for f in found if f.is_error]
    if as_json:
        out = {"ok": not errors, "findings": [f.to_dict() for f in found], **result}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for f in found:
            print(f.format(), file=sys.stderr)
        if result and not errors:
            print(text(result))
    return 1 if errors else 0


def _ingest_call(fn, *args, **kwargs):
    """(result, findings), or None after printing a usage error."""
    from studykit import ingest

    try:
        return fn(*args, **kwargs)
    except ingest.IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None


def _date_arg(value: str | None):
    from datetime import date

    return date.fromisoformat(value) if value else None


def cmd_ingest_scan(args: argparse.Namespace) -> int:
    from studykit import ingest

    try:
        kinds = ingest.parse_kinds(args.kind)
    except ingest.IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sc = ingest.scan(args.folder, kinds=kinds, today=_date_arg(args.today))
    data = sc.to_json()
    errors = [f for f in sc.findings if f.is_error]
    if args.json:
        print(json.dumps({"ok": not errors, **data}, ensure_ascii=False, indent=2))
    else:
        for f in sc.findings:
            print(f.format(), file=sys.stderr)
        print(ingest.format_scan(data))
    return 1 if errors else 0


def cmd_ingest_init(args: argparse.Namespace) -> int:
    from studykit import ingest

    try:
        kinds = ingest.parse_kinds(args.kind)
    except ingest.IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    got = _ingest_call(
        ingest.init,
        args.folder,
        args.course,
        lang=args.lang,
        title=args.title,
        short=args.short,
        semester=args.semester,
        exam_date=args.exam_date,
        exam_format=args.exam_format,
        cheatsheet=args.cheatsheet,
        hours=args.hours_per_week,
        duration=args.exam_minutes,
        points=args.exam_points,
        start=_date_arg(args.start),
        kinds=kinds,
        today=_date_arg(args.today),
        dry_run=args.dry_run,
    )
    if got is None:
        return 2
    return _ingest_out(*got, args.json, lambda r: ingest.format_result(r, "init"))


def cmd_ingest_extract(args: argparse.Namespace) -> int:
    from studykit import ingest

    try:
        course = ingest.resolve(args.course)
    except ingest.IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    got = _ingest_call(ingest.extract, course)
    if got is None:
        return 2
    return _ingest_out(*got, args.json, lambda r: ingest.format_result(r, "extract"))


def cmd_ingest_add(args: argparse.Namespace) -> int:
    from studykit import ingest

    try:
        course = ingest.resolve(args.course)
        kinds = ingest.parse_kinds(args.kind)
    except ingest.IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    got = _ingest_call(
        ingest.add,
        course,
        args.source,
        kinds=kinds,
        today=_date_arg(args.today),
        dry_run=args.dry_run,
    )
    if got is None:
        return 2
    return _ingest_out(*got, args.json, lambda r: ingest.format_result(r, "add"))


def cmd_ingest_round2(args: argparse.Namespace) -> int:
    from studykit import ingest

    try:
        course = ingest.resolve(args.course)
    except ingest.IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    got = _ingest_call(
        ingest.round2,
        course,
        mock_exams=args.mock_exams,
        scope=args.scope,
        go=not args.no_go,
        today=_date_arg(args.today),
    )
    if got is None:
        return 2

    def text(r: dict) -> str:
        a = r["round2"]
        return (
            f"round 2 of {r['course']}: {a['mock_exams']} mock exam(s), scope {a['scope']}, "
            f"{'go' if a['go'] else 'no-go'}"
            + ("; course.yaml targets.mock_exams updated" if r["course_yaml_updated"] else "")
        )

    return _ingest_out(*got, args.json, text)


def _print_findings(found, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"ok": False, "findings": [f.to_dict() for f in found]}, indent=2))
    else:
        for f in found:
            print(f.format(), file=sys.stderr)


def cmd_progress_import(args: argparse.Namespace) -> int:
    from studykit import progress

    tree = _course_tree(args.course)
    if tree is None:
        return 1
    result, found = progress.import_file(tree.root, args.file, dry_run=args.dry_run)
    if found:
        _print_findings(found, args.json)
        return 1
    if args.json:
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    else:
        print(progress.format_import(result))
    return 0


def cmd_progress_log(args: argparse.Namespace) -> int:
    from studykit import content, progress

    tree = _course_tree(args.course)
    if tree is None:
        return 1
    if tree.model is None:
        print(f"error: {tree.id}: course.yaml does not validate", file=sys.stderr)
        return 1
    if args.json_line:
        lines = [("--json-line", i, text) for i, text in enumerate(args.json_line, 1)]
    else:
        lines = [("<stdin>", i, text) for i, text in enumerate(sys.stdin.read().splitlines(), 1)]
    results, found = progress.parse_examiner(lines, tree)
    if found:
        _print_findings(found, args.json)
        return 1
    if not results:
        print("error: no examiner results given", file=sys.stderr)
        return 2
    path = progress.append_examiner(tree.root, results)
    if args.json:
        out = {
            "ok": True,
            "logged": len(results),
            "file": content.display_path(path),
            "results": results,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"  {r.get('item') or r['topic']:<28} {r['kind']:<9} score {r['score']:g}")
        print(f"logged {len(results)} result(s) to {content.display_path(path)}")
    return 0


def cmd_progress_report(args: argparse.Namespace) -> int:
    from studykit import content, progress

    tree = _course_tree(args.course)
    if tree is None:
        return 1
    try:
        snap = progress.snapshot(tree.root, args.today)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if snap.findings:
        _print_findings(snap.findings, args.json)
        return 1
    report = progress.compute_report(snap)
    mastery_path, report_path = progress.write_report(tree.root, report, snap.info)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"mastery {progress.pct(report['overall'])}; "
            f"{report['due']['mc']} MC and {report['due']['exercises']} exercise review(s) due; "
            f"{len(report['misconceptions'])} misconception(s)\n"
            f"wrote {content.display_path(mastery_path)} and {content.display_path(report_path)}"
        )
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    from studykit import plan

    tree = _course_tree(args.course)
    if tree is None:
        return 1
    result, found = plan.run(tree.root, start=args.start, write=not args.dry_run)
    errors = [f for f in found if f.is_error]
    if args.json:
        out = {"ok": not errors, "findings": [f.to_dict() for f in found], **result}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for f in found:
            print(f.format(), file=sys.stderr)
        if result:
            print(plan.format_text(result, dry_run=args.dry_run))
    return 1 if errors else 0


def cmd_status(args: argparse.Namespace) -> int:
    from studykit import status

    tree = _course_tree(args.course)
    if tree is None:
        return 1
    try:
        result, found = status.study_status(tree.root, args.today)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if found:
        _print_findings(found, args.json)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(status.format_text(result))
    return 0


def _course_tree(arg: str):
    from studykit import content

    root = content.resolve_course(arg)
    if not (root / "course.yaml").is_file():
        print(
            f"error: no course at {root} (expected course.yaml; courses live in "
            f"{content.courses_dir()})",
            file=sys.stderr,
        )
        return None
    return content.CourseTree(root)


def cmd_ls(args: argparse.Namespace) -> int:
    from studykit import content

    if args.course is None:
        rows = []
        for root in content.list_courses():
            tree = content.CourseTree(root)
            data = tree.course_doc.data if tree.course_doc else None
            title = data.get("title") if isinstance(data, dict) else None
            rows.append({"id": tree.id, "title": title, "path": content.display_path(root)})
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                print(f"{row['id']}\t{row['title'] or ''}\t{row['path']}")
        return 0
    tree = _course_tree(args.course)
    if tree is None:
        return 1
    rows = content.describe(tree)
    if args.kind:
        rows = [r for r in rows if r["kind"] in args.kind]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        width = max((len(r["kind"]) for r in rows), default=0)
        for row in rows:
            print(f"{row['kind']:<{width}}  {row['path']}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    from studykit import content, index

    tree = _course_tree(args.course)
    if tree is None:
        return 1
    path, data = index.write(tree)
    if args.json:
        print(index.dumps(data), end="")
    else:
        print(f"wrote {content.display_path(path)}")
    return 0


def _print_report(report, as_json: bool, label: str) -> None:
    if as_json:
        print(json.dumps(report.to_json(), ensure_ascii=False, indent=2))
    else:
        print(report.format_text(label))


def cmd_lint(args: argparse.Namespace) -> int:
    from studykit import lint

    if args.hook:
        code, text = lint.run_hook(sys.stdin.read())
        if text:
            sys.stderr.write(text)
        return code
    if not args.files:
        print("error: give the files to lint (or --hook)", file=sys.stderr)
        return 2
    report = lint.lint_files(args.files)
    _print_report(report, args.json, "lint")
    return 0 if report.ok else 1


def cmd_validate(args: argparse.Namespace) -> int:
    from studykit import content, validate

    if args.course:
        root = content.resolve_course(args.course)
        if not root.is_dir():
            print(f"error: no course directory {root}", file=sys.stderr)
            return 1
        courses = [root]
        # a path from the working directory or from the course directory, inside the course
        missing = [
            p
            for p in args.paths or []
            if validate.course_rel(p, root) is None or not (p.exists() or (root / p).exists())
        ]
    elif args.paths:
        roots = {content.find_course_root(p.parent if p.is_file() else p) for p in args.paths}
        courses = sorted(r for r in roots if r is not None)
        missing = [p for p in args.paths if not p.exists()]
    else:
        courses = content.list_courses()
        missing = []
    if missing:
        where = f" in {content.display_path(courses[0])}" if args.course else ""
        for p in missing:
            print(f"error: --paths {p}: no such course file{where}", file=sys.stderr)
        return 2
    report = validate.validate(courses, paths=args.paths, quick=args.quick, release=args.release)
    if not courses:
        report.notes.append(f"no courses found in {content.courses_dir()}")
    _print_report(report, args.json, "validate")
    return 0 if report.ok else 1


def cmd_schema_export(args: argparse.Namespace) -> int:
    from studykit import model

    out_dir = tools.repo_root() / "schemas"
    wanted = model.json_schemas()
    if args.check:
        present = {p.name for p in out_dir.glob("*.schema.json")} if out_dir.is_dir() else set()
        stale = sorted(
            name
            for name, text in wanted.items()
            if name not in present or (out_dir / name).read_text() != text
        )
        extra = sorted(present - set(wanted))
        for name in stale:
            print(f"schemas/{name}: out of date", file=sys.stderr)
        for name in extra:
            print(f"schemas/{name}: no model exports it", file=sys.stderr)
        if stale or extra:
            print("run `studykit schema export` and commit the result", file=sys.stderr)
            return 1
        print(f"schemas: {len(wanted)} files up to date")
        return 0
    out_dir.mkdir(exist_ok=True)
    for name, text in wanted.items():
        path = out_dir / name
        if not path.is_file() or path.read_text() != text:
            path.write_text(text)
            print(f"wrote schemas/{name}")
    for path in out_dir.glob("*.schema.json"):
        if path.name not in wanted:
            path.unlink()
            print(f"removed schemas/{path.name}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    from studykit import render

    tree = _course_tree(args.course)
    if tree is None:
        return 1
    known = None
    if args.known:
        text = sys.stdin.read() if args.known == "-" else Path(args.known).read_text("utf-8")
        known = json.loads(text) if text.strip() else {}
        if not isinstance(known, dict):
            print("error: --known must be a JSON object {rel: digest}", file=sys.stderr)
            return 2
    result = render.render_course(tree.root, paths=args.paths, known=known, jobs=args.jobs)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
        return 0
    errors = 0
    for row in result["files"]:
        state = "cached" if row["cached"] else f"{len(row['findings'])} finding(s)"
        print(f"{row['kind']:<10} {row['rel']}  {state}")
        for f in row["findings"]:
            errors += f["severity"] == "error"
            print(f"  {f['path']}:{f['line']}:{f['col']} {f['code']} {f['message']}")
    for row in result["skipped"]:
        print(f"skipped    {row['rel']}  ({row['reason']})")
    print(f"render: {len(result['files'])} file(s), {errors} error(s)")
    return 0


def cmd_check_links(args: argparse.Namespace) -> int:
    from studykit import checklinks

    dist = args.dist if args.dist.is_absolute() else Path.cwd() / args.dist
    if not dist.is_dir():
        print(f"error: {args.dist} is not a directory (build the site first)", file=sys.stderr)
        return 2
    found = checklinks.check(dist, strict_documents=args.strict_documents)
    errors = [f for f in found if f.is_error]
    if args.json:
        print(json.dumps([f.to_dict() for f in found], ensure_ascii=False, indent=2))
    else:
        for f in found:
            print(f.format())
        pages = sum(1 for _ in checklinks.html_files(dist))
        print(
            f"check-links: {pages} page(s), {len(errors)} broken link(s), "
            f"{len(found) - len(errors)} warning(s)"
        )
    return 1 if errors else 0


def cmd_pdf(args: argparse.Namespace) -> int:
    """One course (an object with --json), or every course (a list)."""
    from studykit import content, pdf

    if args.course is None:
        roots = content.list_courses()
        if not roots:
            print(f"no courses in {content.courses_dir()}", file=sys.stderr)
    else:
        tree = _course_tree(args.course)
        if tree is None:
            return 1
        roots = [tree.root]
    results = []
    for root in roots:
        try:
            result = pdf.build(
                root,
                args.docs or None,
                force=args.force,
                figures=not args.no_figures,
                jobs=args.jobs,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        results.append(result)
        if not args.json:
            print(pdf.format_text(result))
    if args.json:
        out = results[0] if args.course is not None else results
        print(json.dumps(out, ensure_ascii=False, indent=2))
    failed = any(d["status"] == "failed" for r in results for d in r["docs"])
    return 1 if failed else 0


def cmd_cheatsheet_fit(args: argparse.Namespace) -> int:
    from studykit import cheatsheet

    tree = _course_tree(args.course)
    if tree is None:
        return 1
    try:
        code, result = cheatsheet.run(tree.root, force=args.force, figures=not args.no_figures)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(cheatsheet.format_text(result))
    return code


def cmd_calc(args: argparse.Namespace) -> int:
    from studykit import calc

    try:
        result = calc.evaluate(args.expr, args.subs, units=args.units, digits=args.digits)
    except calc.CalcError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(calc.format_text(result, args.digits))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from studykit import content, verify

    tree = _course_tree(args.course)
    if tree is None:
        return 2
    one = (
        ("--confirm", args.confirm),
        ("--dispute", args.dispute),
        ("--quarantine", args.quarantine),
    )
    try:
        for flag, used in one:
            if used and args.target in (None, "all"):
                raise verify.VerifyError(f"{flag} needs one item id")
        if (args.dispute or args.quarantine) and not args.note:
            raise verify.VerifyError("give the reason with --note")
        if args.confirm:
            result = verify.confirm(
                tree,
                args.target,
                args.confirm,
                method=args.method,
                timeout=args.timeout,
                show_key=args.show_key or args.json,
            )
            failed = result["confirmation"] == "error"
        elif args.dispute:
            computed = verify.parse_pairs(args.computed)
            result = verify.dispute(tree, args.target, note=args.note, computed=computed)
            failed = False
        elif args.quarantine:
            result = verify.quarantine(tree, args.target, note=args.note)
            failed = False
        elif args.clear:
            result = verify.clear(tree, args.target)
            failed = False
        elif args.status:
            result = verify.status(tree, args.target, show_key=args.show_key or args.json)
            failed = False
        else:
            result = verify.run(
                tree, args.target, timeout=args.timeout, show_key=args.show_key or args.json
            )
            failed = any(
                r["outcome"] in ("mismatch", "error") or r["status"] == "quarantined"
                for r in result["items"]
            )
    except verify.VerifyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.report:
        path = verify.write_report(content.CourseTree(tree.root))
        result["report"] = content.display_path(path)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "items" in result:
        print(verify.format_text(result))
    else:
        print(verify.format_action(result))
    if not args.json and result.get("report"):
        print(f"wrote {result['report']}")
    return 1 if failed else 0


def cmd_blind(args: argparse.Namespace) -> int:
    from studykit import blind, content, verify

    tree = _course_tree(args.course)
    if tree is None:
        return 2
    try:
        path, text = blind.write(tree, args.id)
    except verify.VerifyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.stdout:
        print(text, end="")
    else:
        print(f"wrote {content.display_path(path)}")
    return 0


def cmd_hook(args: argparse.Namespace) -> int:
    from studykit import hook

    sys.stdout.write(hook.run(args.name, sys.stdin.read()))
    return 0


def cmd_fig_build(args: argparse.Namespace) -> int:
    from studykit.figures import runner  # imports Matplotlib; keep other commands fast

    only = set(args.only) if args.only else None
    return runner.build(args.course, only=only, force=args.force)


def cmd_golden(args: argparse.Namespace) -> int:
    return golden.run_golden(tools.repo_root(), update=args.update)


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = doctor.run_checks(tools.repo_root(), quick=args.quick)
    return doctor.report(checks, as_json=args.json)


def cmd_tools_install(args: argparse.Namespace) -> int:
    root = tools.repo_root()
    try:
        results = tools.install_all(root, force=args.force)
    except (tools.ToolchainError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for r in results:
        print(f"{r.name} {r.version}: {r.action} ({r.path.relative_to(root)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
