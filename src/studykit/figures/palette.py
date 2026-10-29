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
    # Page background, for shapes that must hide what is behind them (state nodes, labels).
    "bg": "#ffffff",
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
BG = ROLES["bg"]
MUTED = ROLES["muted"]
GRID = ROLES["grid"]

HEX_TO_ROLE: dict[str, str] = {hex_.lower(): role for role, hex_ in ROLES.items()}

# WCAG 2 contrast a text needs against the page (1.4.3, normal-size text).
TEXT_CONTRAST = 4.5


def _luminance(hex_: str) -> float:
    channels = (int(hex_.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4))
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG 2 contrast ratio of two hex colours (1 to 21)."""
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


# Colours a figure may draw text in: readable on the page (fg, muted and c1). Labels are
# drawn in fg; a coloured line or marker next to them is the key. Okabe-Ito c2 to c6 are
# below 4.5:1 on white, so text in them is rejected by figures.validate.
TEXT_ROLES: tuple[str, ...] = tuple(
    role for role, hex_ in ROLES.items() if contrast(hex_, BG) >= TEXT_CONTRAST
)


def color(role_or_index: str | int) -> str:
    """Palette colour by role name (`"fg"`, `"c2"`) or series index (0 = c1)."""
    if isinstance(role_or_index, int):
        return SERIES[role_or_index % len(SERIES)]
    return ROLES[role_or_index]
