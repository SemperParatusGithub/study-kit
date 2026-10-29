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

    return parser


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
