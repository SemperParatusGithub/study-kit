"""The figure palette's contrast and the text-colour rule of figures.validate.

Labels are text and need 4.5:1 on the page (WCAG 1.4.3); the series colours c2 to c6 are
for lines and markers. The site's light figure tokens must equal the palette, which the
PDFs use as is.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from studykit.figures import color, plot
from studykit.figures.palette import BG, ROLES, TEXT_CONTRAST, TEXT_ROLES, contrast
from studykit.figures.validate import validate_svg

REPO = Path(__file__).resolve().parents[2]
TOKENS = REPO / "site" / "src" / "styles" / "tokens.css"
TOKEN = re.compile(
    r"--fig-(?P<role>[a-z0-9]+):\s*light-dark\("
    r"(?P<light>#[0-9a-f]{6}),\s*(?P<dark>#[0-9a-f]{6})\)"
)


def test_contrast_matches_wcag():
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast("#ffffff", "#ffffff") == pytest.approx(1.0)
    assert contrast(ROLES["c5"], BG) == pytest.approx(2.25, abs=0.01)


def test_text_colours_are_readable_on_the_page():
    assert TEXT_ROLES == ("fg", "muted", "c1")
    for role in TEXT_ROLES:
        assert contrast(ROLES[role], BG) >= TEXT_CONTRAST, role


def test_site_figure_tokens_match_the_palette():
    tokens = {m["role"]: (m["light"], m["dark"]) for m in TOKEN.finditer(TOKENS.read_text())}
    assert {role: light for role, (light, _) in tokens.items()} == ROLES
    dark_bg = tokens["bg"][1]
    for role in TEXT_ROLES:
        assert contrast(tokens[role][1], dark_bg) >= TEXT_CONTRAST, role
    for i in range(1, 7):  # lines and markers: 3:1 (WCAG 1.4.11)
        assert contrast(tokens[f"c{i}"][1], dark_bg) >= 3.0, f"c{i}"


def labelled(label_colour: str | None, marker_colour: str) -> str:
    with plot.custom(alt="Testbild") as c:
        c.ax.plot([0, 1], [0, 1], "o", color=marker_colour)
        style = {} if label_colour is None else {"color": label_colour}
        c.ax.annotate("$U_C$ Spannung", (0.5, 0.5), **style)
    return c.figure.svg


def text_problems(svg: str) -> list[str]:
    return [p for p in validate_svg(svg) if p.startswith("text in ")]


@pytest.mark.parametrize("role", ["c2", "c3", "c4", "c5", "c6"])
def test_text_in_a_series_colour_is_rejected(role: str):
    (problem,) = text_problems(labelled(color(role), color("fg")))
    assert problem.startswith(f"text in {role} ")
    assert "draw labels in fg" in problem


@pytest.mark.parametrize("label", [None, "fg", "muted", "c1"])
def test_readable_text_and_coloured_markers_pass(label: str | None):
    svg = labelled(None if label is None else color(label), color("c5"))
    assert validate_svg(svg) == []
