"""Command line entry point: `studykit <command>`."""

from __future__ import annotations

import argparse
import subprocess
import sys

from studykit import __version__, tools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="studykit", description=__doc__)
    parser.add_argument("--version", action="version", version=f"studykit {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_tools = sub.add_parser("tools", help="manage the pinned external toolchain")
    tools_sub = p_tools.add_subparsers(dest="tools_command", metavar="<action>", required=True)
    p_install = tools_sub.add_parser("install", help="install pandoc and typst into .tools/bin")
    p_install.add_argument("--force", action="store_true", help="reinstall even if up to date")
    p_install.set_defaults(func=cmd_tools_install)

    return parser


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
