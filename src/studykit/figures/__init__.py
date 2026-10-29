"""study-kit figures: figures are code, rendered to SVG by `studykit fig build`.

A course figure script `courses/<c>/figures/<slug>.py` defines `build()` and returns a
`Figure` made by one of the templates in this package; see docs/architecture.md §3.4.
"""

from studykit.figures.core import SIZES, Figure, axis_label, fmt_number
from studykit.figures.palette import ROLES, color

__all__ = ["ROLES", "SIZES", "Figure", "axis_label", "color", "fmt_number"]
