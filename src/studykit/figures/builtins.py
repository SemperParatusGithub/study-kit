"""Figures every course gets without a script; importing this module registers them.

Kept apart from the templates so that `graph` never imports `runner` (no import cycle):
the runner imports this module once before it looks at `runner.BUILTINS`.
"""

from __future__ import annotations

from studykit.figures import runner
from studykit.figures.graph import topic_map

runner.BUILTINS["topic-map"] = topic_map

__all__ = ["topic_map"]
