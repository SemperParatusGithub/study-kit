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
    p_validate.add_argument("--quick", action="store_true", help="stages up to Math only")
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

    p_fig = sub.add_parser("fig", help="figures: build course figure scripts")
    fig_sub = p_fig.add_subparsers(dest="fig_command", metavar="<action>", required=True)
    p_fig_build = fig_sub.add_parser("build", help="render figures to _build/figures")
    p_fig_build.add_argument("course", nargs="?", help="course id (default: all courses)")
    p_fig_build.add_argument("--only", action="append", metavar="SLUG", help="only this figure")
    p_fig_build.add_argument("--force", action="store_true", help="ignore the cache")
    p_fig_build.set_defaults(func=cmd_fig_build)

    return parser


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
    elif args.paths:
        roots = {content.find_course_root(p.parent if p.is_file() else p) for p in args.paths}
        courses = sorted(r for r in roots if r is not None)
    else:
        courses = content.list_courses()
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
