"""Every template through the real runner, as a course figure script would use it.

tests/fixtures/figures/gallery/ is a small German course with one script per template;
the runner builds them in isolated subprocesses, plus the builtin topic map. The facts of
each figure are compared with tests/golden/figures/<slug>.facts.json, so a dependency bump
that moves a computed number or a label fails here. After checking the new PNGs in
tests/fixtures/figures/gallery/_build/figures/, refresh the snapshots with

    STUDYKIT_UPDATE_SNAPSHOTS=1 uv run --frozen pytest tests/py/test_figures_gallery.py
"""

from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path

import pytest

from studykit.figures import runner
from studykit.figures.validate import validate_svg

REPO = Path(__file__).resolve().parents[2]
GALLERY = REPO / "tests" / "fixtures" / "figures" / "gallery"
SNAPSHOTS = REPO / "tests" / "golden" / "figures"
UPDATE = os.environ.get("STUDYKIT_UPDATE_SNAPSHOTS") == "1"

# Every template a course can use (facts name the defining module; plot.bode is
# signals.bode); the gallery must show each one at least once.
TEMPLATES = {
    "plot.functions",
    "plot.custom",
    "signals.bode",
    "signals.nyquist",
    "signals.pole_zero",
    "signals.step_response",
    "signals.root_locus",
    "signals.phasor",
    "signals.signals",
    "circuit.voltage_divider",
    "circuit.rc",
    "circuit.rlc",
    "circuit.opamp",
    "circuit.bridge",
    "circuit.drawing",
    "block.feedback_loop",
    "block.chain",
    "block.parallel",
    "graph.state_machine",
    "graph.flowchart",
    "graph.topic_map",
}


@pytest.fixture(scope="module")
def built() -> dict[str, dict]:
    """Build the gallery once (in the fixture tree, so the PNGs stay for review)."""
    shutil.rmtree(GALLERY / "_build", ignore_errors=True)
    outcomes = runner.build_course(GALLERY)
    failed = {o.slug: o.problems for o in outcomes if o.status != "built"}
    assert not failed, failed
    out = GALLERY / "_build" / "figures"
    return {
        o.slug: json.loads((out / f"{o.slug}.facts.json").read_text(encoding="utf-8"))
        for o in outcomes
    }


def test_every_template_is_in_the_gallery(built):
    assert {facts["template"] for facts in built.values()} == TEMPLATES


def test_outputs_are_valid(built):
    out = GALLERY / "_build" / "figures"
    for slug in built:
        assert validate_svg((out / f"{slug}.web.svg").read_text(encoding="utf-8")) == [], slug
        assert (out / f"{slug}.png").read_bytes().startswith(b"\x89PNG"), slug
        assert built[slug]["alt"].strip(), slug


def differences(want, got, path: str = "") -> list[str]:
    """Where got differs from want; floats agree to 1e-6 relative (platform libm, BLAS)."""
    if isinstance(want, float) or isinstance(got, float):
        ok = isinstance(want, int | float) and isinstance(got, int | float)
        if ok and math.isclose(want, got, rel_tol=1e-6, abs_tol=1e-9):
            return []
        return [f"{path}: {want!r} != {got!r}"]
    if isinstance(want, dict) and isinstance(got, dict):
        out = [f"{path}.{k}: missing" for k in want.keys() - got.keys()]
        out += [f"{path}.{k}: unexpected" for k in got.keys() - want.keys()]
        for k in want.keys() & got.keys():
            out += differences(want[k], got[k], f"{path}.{k}")
        return out
    if isinstance(want, list) and isinstance(got, list):
        if len(want) != len(got):
            return [f"{path}: {len(want)} items != {len(got)} items"]
        return [
            d
            for i, (w, g) in enumerate(zip(want, got, strict=True))
            for d in differences(w, g, f"{path}[{i}]")
        ]
    return [] if want == got else [f"{path}: {want!r} != {got!r}"]


def test_facts_match_the_snapshots(built):
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    if UPDATE:
        for old in SNAPSHOTS.glob("*.facts.json"):
            old.unlink()
        for slug, facts in built.items():
            text = json.dumps(facts, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
            (SNAPSHOTS / f"{slug}.facts.json").write_text(text, encoding="utf-8")
    assert sorted(
        p.name.removesuffix(".facts.json") for p in SNAPSHOTS.glob("*.facts.json")
    ) == sorted(built)
    problems = {}
    for slug, facts in built.items():
        want = json.loads((SNAPSHOTS / f"{slug}.facts.json").read_text(encoding="utf-8"))
        found = differences(want, facts)
        if found:
            problems[slug] = found[:10]
    assert not problems, json.dumps(problems, indent=1, ensure_ascii=False)


def test_course_decimal_sign_comes_from_the_notation(tmp_path: Path):
    """notation.yaml's `decimal` wins over the language and is part of the cache key."""
    course = tmp_path / "c"
    (course / "analysis").mkdir(parents=True)
    (course / "course.yaml").write_text("lang: de\n")
    assert runner.course_decimal(course) == "comma"
    german = runner.style_key(course)
    (course / "analysis" / "notation.yaml").write_text("schema: 1\ndecimal: point\n")
    assert runner.course_decimal(course) == "point"
    assert runner.style_key(course) != german
    assert runner.child_env("de", decimal="point")["STUDYKIT_DECIMAL"] == "point"
    (course / "course.yaml").write_text("lang: en\n")
    (course / "analysis" / "notation.yaml").write_text("schema: 1\n")
    assert runner.course_decimal(course) == "point"


def test_children_use_only_the_bundled_fonts(tmp_path: Path):
    """A cold font cache holds matplotlib's own fonts only (docs/architecture.md §3.4).

    Without MPL_IGNORE_SYSTEM_FONTS every child of the first wave scans all system fonts
    itself; on a busy machine they all hit the timeout and none writes the cache.
    """
    import matplotlib

    env = runner.child_env("de", mpl_dir=tmp_path)
    assert env["MPL_IGNORE_SYSTEM_FONTS"] == "1"
    assert runner.child_env("de")["MPLCONFIGDIR"] == str(runner.mpl_config_dir())
    runner.warm_font_cache(env)
    (cache,) = tmp_path.glob("fontlist-*.json")
    fonts = json.loads(cache.read_text())["ttflist"]
    # matplotlib stores its own fonts relative to its data directory
    bundled = Path(matplotlib.get_data_path()).resolve()
    paths = {f["fname"]: (bundled / f["fname"]).resolve() for f in fonts}
    outside = sorted(name for name, path in paths.items() if not path.is_relative_to(bundled))
    assert fonts and not outside, outside[:5]
