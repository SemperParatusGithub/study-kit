"""Build the fake lecture materials into `_build/materials/` (gitignored; `just sample-materials`).

The Typst sources in `src/` stand in for a lecturer's PDFs (examples/sample-materials/README.md):
slides, a script excerpt, an exercise sheet with solutions, a past exam with solutions, and
one scanned exercise sheet. The circuit figures come from `figures/*.py` (studykit.figures),
rendered first into `_build/work/figures/`. The scan is rendered to a low-resolution PNG,
rotated, darkened and given seeded noise, then wrapped into a PDF that has no text layer.
Every step is deterministic, and the PDFs are never committed.

    uv run --frozen python examples/sample-materials/build.py [--out DIR]
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Typst source -> file name in the materials folder (named like a lecturer would)
DOCS = {
    "vl03-folien.typ": "VL03_Operationsverstaerker_Grundschaltungen.pdf",
    "skript-kap4.typ": "Skript_Kapitel4_Operationsverstaerker.pdf",
    "uebung03.typ": "Uebung03_OPV_Grundschaltungen.pdf",
    "uebung03-loesung.typ": "Uebung03_OPV_Grundschaltungen_Loesung.pdf",
    "klausur-ws2526.typ": "Klausur_WS2025-26.pdf",
    "klausur-ws2526-loesung.typ": "Klausur_WS2025-26_Loesung.pdf",
}
SCAN_SOURCE, SCAN_FILE = "scan-uebung02.typ", "Altes_Uebungsblatt02_Scan.pdf"
SCAN_PPI = 100
SCAN_DATE = time.gmtime(dt.datetime(2024, 1, 15, 9, 30, tzinfo=dt.UTC).timestamp())


def typst(args: list[str]) -> None:
    from studykit import pdf

    env = {k: v for k, v in os.environ.items() if not k.startswith("TYPST_")}
    env["SOURCE_DATE_EPOCH"] = "0"
    cmd = [
        str(pdf.typst_bin()),
        "compile",
        "--root",
        str(HERE),
        "--ignore-system-fonts",
        "--diagnostic-format",
        "short",
        *args,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0 or proc.stderr.strip():
        sys.exit(f"typst {' '.join(args)} failed:\n{proc.stderr.strip()}")


def figures(work: Path) -> None:
    from studykit.figures import runner

    out = work / "figures"
    env = runner.child_env("de")
    for script in sorted((HERE / "figures").glob("*.py")):
        proc = subprocess.run(
            [
                sys.executable,
                "-I",
                "-m",
                "studykit.figures.child",
                str(script),
                str(out),
                script.stem,
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")]
        if proc.returncode != 0 or not lines or '"ok": true' not in lines[-1]:
            sys.exit(f"figure {script.name} failed:\n{proc.stdout}{proc.stderr}")


def scan(work: Path, target: Path) -> None:
    """Render the scan source to PNG pages and wrap them, degraded, into an image-only PDF."""
    import numpy as np
    from PIL import Image, ImageFilter

    for old in work.glob("scan-*.png"):
        old.unlink()
    typst(
        [
            "--format",
            "png",
            "--ppi",
            str(SCAN_PPI),
            str(HERE / "src" / SCAN_SOURCE),
            str(work / "scan-{0p}.png"),
        ]
    )
    rng = np.random.default_rng(2526)
    pages = []
    for i, png in enumerate(sorted(work.glob("scan-*.png"))):
        img = Image.open(png).convert("L")
        img = img.rotate(-1.3 + 0.4 * i, Image.Resampling.BICUBIC, expand=True, fillcolor=246)
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        arr = np.asarray(img, dtype=np.float64) * 0.9 + 14
        arr += rng.normal(0, 11, arr.shape)
        h, w = arr.shape
        arr[:, : w // 30] -= np.linspace(60, 0, w // 30)[None, :]  # scanner shadow
        for _ in range(60):  # dust
            y, x = rng.integers(0, h - 3), rng.integers(0, w - 3)
            arr[y : y + 2, x : x + 2] = 40
        pages.append(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L"))
    pages[0].save(
        target,
        "PDF",
        resolution=SCAN_PPI,
        save_all=True,
        append_images=pages[1:],
        title="Scan",
        creationDate=SCAN_DATE,
        modDate=SCAN_DATE,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "_build" / "materials",
        help="folder for the PDFs (default: examples/sample-materials/_build/materials)",
    )
    args = parser.parse_args(argv)
    out: Path = args.out.resolve()
    work = HERE / "_build" / "work"
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    figures(work)
    for source, name in DOCS.items():
        typst([str(HERE / "src" / source), str(out / name)])
    scan(work, out / SCAN_FILE)
    names = sorted(p.name for p in out.glob("*.pdf"))
    print(f"built {len(names)} PDFs into {out}:")
    for name in names:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
