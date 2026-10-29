"""Build one figure script in an isolated interpreter.

Run as `python -I -m studykit.figures.child <script> <out_dir> <slug>`; prints one JSON
line describing the result. The runner never imports course scripts into its own process.
"""

from __future__ import annotations

import json
import runpy
import sys
import warnings
from pathlib import Path

from studykit.figures.core import Figure
from studykit.figures.finalize import finalize
from studykit.figures.validate import validate_svg


def write_outputs(fig: Figure, out_dir: Path, slug: str) -> list[str]:
    problems = validate_svg(fig.svg)
    if problems:
        return problems
    typst_svg, web_svg = finalize(fig.svg, slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{slug}.svg").write_text(typst_svg)
    (out_dir / f"{slug}.web.svg").write_text(web_svg)
    (out_dir / f"{slug}.png").write_bytes(fig.png)
    facts = {"alt": fig.alt, **fig.facts}
    (out_dir / f"{slug}.facts.json").write_text(json.dumps(facts, indent=2, ensure_ascii=False))
    return []


def main(argv: list[str]) -> int:
    script, out_dir, slug = Path(argv[0]), Path(argv[1]), argv[2]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        namespace = runpy.run_path(str(script), run_name="studykit_figure")
        build = namespace.get("build")
        if not callable(build):
            print(json.dumps({"ok": False, "problems": ["script defines no build() function"]}))
            return 1
        fig = build()
    if not isinstance(fig, Figure):
        msg = f"build() returned {type(fig).__name__}, expected a studykit Figure"
        print(json.dumps({"ok": False, "problems": [msg]}))
        return 1
    fatal = [
        str(w.message)
        for w in caught
        if "Glyph" in str(w.message) or "missing from" in str(w.message)
    ]
    problems = fatal + write_outputs(fig, out_dir, slug)
    print(json.dumps({"ok": not problems, "problems": problems, "alt": fig.alt}))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
