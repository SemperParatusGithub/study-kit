"""The closed figure palette.

Every colour in a figure must be one of these. The web variant of each SVG rewrites the
hex values to `var(--fig-<role>, #hex)`, so the site theme (light/dark) recolours
figures; Typst gets the literal colours.
"""

from __future__ import annotations

ROLES: dict[str, str] = {
    "fg": "#1f2328",
    "muted": "#6e7781",
    "grid": "#d0d7de",
    # Okabe-Ito: distinguishable for common colour-vision deficiencies.
    "c1": "#0072b2",
    "c2": "#d55e00",
    "c3": "#009e73",
    "c4": "#cc79a7",
    "c5": "#e69f00",
    "c6": "#56b4e9",
}

SERIES: tuple[str, ...] = tuple(ROLES[f"c{i}"] for i in range(1, 7))

FG = ROLES["fg"]
MUTED = ROLES["muted"]
GRID = ROLES["grid"]

HEX_TO_ROLE: dict[str, str] = {hex_.lower(): role for role, hex_ in ROLES.items()}


def color(role_or_index: str | int) -> str:
    """Palette colour by role name (`"fg"`, `"c2"`) or series index (0 = c1)."""
    if isinstance(role_or_index, int):
        return SERIES[role_or_index % len(SERIES)]
    return ROLES[role_or_index]
