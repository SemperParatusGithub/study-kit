"""Shared fixtures for the content-format tests (schema, lint, validate, content)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

# The checkout these tests belong to (STUDYKIT_ROOT may point tools elsewhere).
REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures"
MINI = FIXTURES / "courses" / "mini"
BAD = FIXTURES / "bad"

# A small denylist in the shape of pandoc/math-denylist.json (contract: token, use, kind),
# so the math rules are tested without depending on the pandoc filter files.
SAMPLE_DENYLIST = [
    {"token": "\\overset", "use": "write := or \\Rightarrow", "kind": "silent"},
    {"token": "\\tag", "use": "name the formula in prose", "kind": "silent"},
    {"token": "\\R", "use": "\\mathbb{R}", "kind": "fails"},
    {"token": "\\operatorname*", "use": "(none)", "kind": "silent"},
    {"token": "\\left\\|", "use": "\\lVert … \\rVert", "kind": "silent"},
    {"token": "\\def", "use": "no custom macros", "kind": "fails"},
    {
        "token": "env:vmatrix",
        "use": "\\left|\\begin{matrix}…\\end{matrix}\\right|",
        "kind": "fails",
    },
]


@pytest.fixture
def denylist(tmp_path: Path) -> Path:
    path = tmp_path / "math-denylist.json"
    path.write_text(json.dumps(SAMPLE_DENYLIST))
    return path


@pytest.fixture
def mini(tmp_path: Path) -> Path:
    """A writable copy of the mini course (the directory name is the course id)."""
    target = tmp_path / "courses" / "mini"
    shutil.copytree(MINI, target, ignore=shutil.ignore_patterns("_build"))
    return target


def overlay(course: Path, case: Path) -> list[Path]:
    """Copy a bad-fixture tree over a course; return the course paths it wrote."""
    written = []
    for src in sorted(p for p in case.rglob("*") if p.is_file()):
        dest = course / src.relative_to(case)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        written.append(dest)
    return written
