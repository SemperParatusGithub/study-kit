"""Command line entry point: `studykit <command>`."""

from __future__ import annotations

import argparse
import subprocess
import sys

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

    p_fig = sub.add_parser("fig", help="figures: build course figure scripts")
    fig_sub = p_fig.add_subparsers(dest="fig_command", metavar="<action>", required=True)
    p_fig_build = fig_sub.add_parser("build", help="render figures to _build/figures")
    p_fig_build.add_argument("course", nargs="?", help="course id (default: all courses)")
    p_fig_build.add_argument("--only", action="append", metavar="SLUG", help="only this figure")
    p_fig_build.add_argument("--force", action="store_true", help="ignore the cache")
    p_fig_build.set_defaults(func=cmd_fig_build)

    return parser


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
