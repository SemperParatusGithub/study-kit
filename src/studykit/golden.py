"""Golden math corpus: every formula must work in KaTeX and in pandoc -> Typst.

`tests/golden/math.md` holds the allowed dialect: each formula must render in KaTeX
(strict) and survive pandoc -> Typst -> PDF without a single warning.
`tests/golden/math-denied.md` documents constructs on the denylist: each must still fail
in at least one engine, so a toolchain upgrade that fixes one is noticed.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from studykit import pandoc, tools


@dataclass
class Formula:
    tex: str
    display: bool

    def markdown(self) -> str:
        tex = self.tex.strip()
        return f"$$\n{tex}\n$$\n" if self.display else f"${tex}$\n"


@dataclass
class Result:
    formula: Formula
    katex_error: str | None
    typst_error: str | None

    @property
    def ok(self) -> bool:
        return self.katex_error is None and self.typst_error is None


def katex_check(root: Path, formulas: list[Formula]) -> list[str | None]:
    payload = json.dumps([{"tex": f.tex, "display": f.display} for f in formulas])
    proc = subprocess.run(
        ["node", str(root / "site" / "scripts" / "check-math.mjs")],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
        cwd=root / "site",
        timeout=120,
    )
    return [None if r["ok"] else r["error"] for r in json.loads(proc.stdout)]


def typst_check(root: Path, markdown: str) -> str | None:
    """Convert Markdown to Typst and compile it; return the problem or None."""
    try:
        typ = pandoc.run(
            ["-f", pandoc.READER, "-t", "typst", "--standalone", "--fail-if-warnings"],
            stdin=markdown,
        ).stdout
    except pandoc.PandocError as exc:
        return f"pandoc: {exc}"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "doc.typ"
        src.write_text(typ)
        proc = subprocess.run(
            [
                str(tools.bin_path(root, "typst")),
                "compile",
                "--root",
                tmp,
                "--ignore-system-fonts",
                "--diagnostic-format",
                "short",
                str(src),
                str(Path(tmp) / "doc.pdf"),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            env={"SOURCE_DATE_EPOCH": "0", "PATH": "/usr/bin:/bin"},
        )
    problems = [ln for ln in proc.stderr.splitlines() if "error" in ln or "warning" in ln]
    if proc.returncode != 0 or problems:
        return "typst: " + ("; ".join(problems) or proc.stderr.strip())
    return None


def check_corpus(root: Path, path: Path) -> list[Result]:
    formulas = [Formula(tex, display) for tex, display in pandoc.math_nodes(path.read_text())]
    katex_errors = katex_check(root, formulas)
    # One combined Typst run is fast; only bisect per formula when it fails.
    combined = "\n\n".join(f.markdown() for f in formulas)
    if typst_check(root, combined) is None:
        typst_errors: list[str | None] = [None] * len(formulas)
    else:
        typst_errors = [typst_check(root, f.markdown()) for f in formulas]
    return [Result(f, k, t) for f, k, t in zip(formulas, katex_errors, typst_errors, strict=True)]


def unparsed_display_blocks(markdown: str, formulas: list[Formula]) -> int:
    """Display blocks pandoc did not read as math (e.g. a line starting with `=`)."""
    fences = sum(1 for line in markdown.splitlines() if line.strip() == "$$")
    return fences // 2 - sum(1 for f in formulas if f.display)


def typst_snapshot(formulas: list[Formula]) -> str:
    """The pandoc -> Typst translation of every formula, for drift detection."""
    with ThreadPoolExecutor() as pool:
        typst = pool.map(
            lambda f: pandoc.run(["-f", pandoc.READER, "-t", "typst"], stdin=f.markdown()).stdout,
            formulas,
        )
        return "".join(
            f"# {' '.join(f.tex.split())}\n{' '.join(t.split())}\n\n"
            for f, t in zip(formulas, typst, strict=True)
        )


def run_golden(root: Path, update: bool = False) -> int:
    golden = root / "tests" / "golden"
    status = 0

    source = (golden / "math.md").read_text()
    allowed = check_corpus(root, golden / "math.md")
    bad = [r for r in allowed if not r.ok]
    print(f"math.md: {len(allowed) - len(bad)}/{len(allowed)} formulas pass both engines")
    for r in bad:
        status = 1
        print(f"  FAIL {r.formula.tex!r}")
        if r.katex_error:
            print(f"       katex: {r.katex_error}")
        if r.typst_error:
            print(f"       {r.typst_error}")

    lost = unparsed_display_blocks(source, [r.formula for r in allowed])
    if lost:
        status = 1
        print(f"  FAIL {lost} display block(s) were not parsed as math")
        print(
            "       (a line inside $$ must not start with a Markdown block marker like = - + # >)"
        )

    snapshot_path = golden / "math.typ.snap"
    snapshot = typst_snapshot([r.formula for r in allowed])
    if update or not snapshot_path.is_file():
        snapshot_path.write_text(snapshot)
        print(f"math.typ.snap: written ({len(allowed)} formulas); review the rendered PDF")
    elif snapshot_path.read_text() != snapshot:
        status = 1
        old = snapshot_path.read_text().split("\n\n")
        new = snapshot.split("\n\n")
        changed = [n for o, n in zip(old, new, strict=False) if o != n] or new[len(old) :]
        print(f"math.typ.snap: Typst translation changed for {len(changed)} formula(s):")
        for entry in changed[:10]:
            print("  " + entry.replace("\n", "\n  => "))
        print("  render and review them, then run `studykit golden --update`")
    else:
        print("math.typ.snap: Typst translation unchanged")

    denied_path = golden / "math-denied.md"
    if denied_path.is_file():
        denied = check_corpus(root, denied_path)
        fixed = [r for r in denied if r.ok]
        print(f"math-denied.md: {len(denied) - len(fixed)}/{len(denied)} still fail an engine")
        for r in fixed:
            status = 1
            print(f"  NOW WORKS (review the denylist): {r.formula.tex!r}")
    return status
