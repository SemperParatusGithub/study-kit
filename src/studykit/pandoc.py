"""Thin wrapper around the pinned pandoc binary."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

from studykit import tools

# The one Markdown dialect study-kit accepts (docs/architecture.md §2.3).
READER = "commonmark_x-smart-raw_html-raw_attribute-yaml_metadata_block-alerts-emoji"


class PandocError(RuntimeError):
    pass


def pandoc_bin() -> Path:
    return tools.bin_path(tools.repo_root(), "pandoc")


def run(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [str(pandoc_bin()), *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if proc.returncode != 0:
        raise PandocError(proc.stderr.strip() or f"pandoc exited with {proc.returncode}")
    return proc


def to_json(markdown: str) -> dict:
    return json.loads(run(["-f", READER, "-t", "json"], stdin=markdown).stdout)


def walk(node: object) -> Iterator[dict]:
    """Yield every pandoc AST element (dicts with a "t" key), depth first."""
    if isinstance(node, dict):
        if "t" in node:
            yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def math_nodes(markdown: str) -> list[tuple[str, bool]]:
    """All formulas in document order as (tex, is_display)."""
    out = []
    for el in walk(to_json(markdown)["blocks"]):
        if el["t"] == "Math":
            kind, tex = el["c"]
            out.append((tex, kind["t"] == "DisplayMath"))
    return out
