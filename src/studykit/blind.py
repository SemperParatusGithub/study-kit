"""`studykit blind <course> <id>`: the verifier's view of one item (§5.3).

Writes `_build/blind/<id>.md` with what the verifier may know and nothing more:

- exercises and exam tasks: title, topic, kind, the statement without hints and solution,
  and the results to compute (answer keys with label and unit, symbols for symbolic
  answers), never the values, the rubric or the solution;
- MC questions (practice banks and exam MC): the stem and the options in source order,
  labelled A to F, without `[x]` marks, without the `why` of each option and without the
  explanation.

Figures point at the built PNG in `_build/figures/`. Course links keep their text only.
The verifier's guard hook (`studykit hook verifier-guard`) keeps it out of the source
files, so this view is how it learns the item.
"""

from __future__ import annotations

import re
from pathlib import Path

from studykit import verify
from studykit.content import CourseTree, display_path

FIG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\(fig:(?P<slug>[a-z0-9-]+)\)")
LINK_RE = re.compile(r"(?<!!)\[(?P<text>[^\]]*)\]\((?:ex|mc|topic|exam|src):[^)]*\)")
TYPES = {
    "single": "single choice: exactly one option is correct",
    "multi": "multiple choice: one or more options are correct",
    "kprim": "Kprim: judge every statement true or false",
}


def blind_path(tree: CourseTree, item_id: str) -> Path:
    return tree.root / "_build" / "blind" / f"{item_id}.md"


def _clean(text: str, figures: list[str]) -> str:
    def fig(m: re.Match[str]) -> str:
        figures.append(m["slug"])
        return f"![{m['alt']}](../figures/{m['slug']}.png)"

    return LINK_RE.sub(lambda m: m["text"], FIG_RE.sub(fig, text))


def _squeeze(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        if not line.strip() and (not out or not out[-1].strip()):
            continue
        out.append(line.rstrip())
    while out and not out[-1].strip():
        out.pop()
    return out


def _statement(item: verify.VItem) -> list[str]:
    body = item.doc.body
    assert body is not None
    hidden: set[int] = set()
    for block in body.all_blocks():
        if block.name in ("hint", "solution"):
            end = block.close_line if block.close_line is not None else len(body.lines) - 1
            hidden.update(range(block.open_line, end + 1))
    return _squeeze([ln.text for i, ln in enumerate(body.lines) if i not in hidden])


def render(tree: CourseTree, item_id: str) -> str:
    item = verify.find(tree, item_id)
    figures: list[str] = []
    out = [
        f"# Blind view: {item.id}",
        "",
        f"Course `{tree.id}` · {item.kind}" + (f" · topic `{item.topic}`" if item.topic else ""),
        "",
    ]
    if item.kind == "mc":
        q = item.question
        assert q is not None
        out += [f"Type: {TYPES.get(q.type or '', q.type or '?')}.", "", "## Question", ""]
        out += [_clean(line, figures) for line in _squeeze(q.stem)]
        out += ["", "## Options (source order)", ""]
        for letter, option in zip(verify.LETTERS, q.options, strict=False):
            text = " ".join(line.strip() for line in option.paragraphs[0])
            out.append(f"- **{letter}** {_clean(text, figures)}")
        out += ["", "## Your answer", ""]
        if q.type == "kprim":
            out.append(
                f"Write `checks/{item.id}.json` as "
                '`{"answer": {"A": true, "B": false, "C": …, "D": …}, "confidence": "high", '
                '"ambiguous": false, "reason": "…"}`, or a script ending with '
                "`mc_answer({...})`."
            )
        elif verify.numeric_question(q):
            out.append(
                f"Every option is a number: write `checks/{item.id}.py` ending with "
                "`mc_numeric(correct=…, options={…}, mistakes={…})` from `studykit.check`, "
                "every option's value in SI units and, for each distractor, the value its "
                "mistake gives. A JSON answer does not count for a numeric question."
            )
        else:
            out.append(
                f"Write `checks/{item.id}.json` as "
                '`{"answer": ["…"], "confidence": "high", "ambiguous": false, "reason": "…"}`, '
                "or a script ending with `mc_answer([...])`."
            )
    else:
        doc = item.doc
        data = doc.data if isinstance(doc.data, dict) else {}
        meta = [f"kind `{data.get('kind')}`"] if data.get("kind") else []
        if item.kind == "exam-task" and data.get("points"):
            meta.append(f"{data['points']} points")
        out += [f"## {data.get('title') or item.id}", ""]
        if meta:
            out += [" · ".join(meta), ""]
        out += [_clean(line, figures) for line in _statement(item)]
        answers = verify._answers_of(item) or []
        out += ["", "## Results to compute", ""]
        if answers:
            for a in answers:
                if a.expr is not None:
                    what = f"an expression in {', '.join(a.symbols)}"
                else:
                    what = f"a number in {a.unit}" if a.unit else "a number"
                out.append(f"- `{a.key}`: {a.label} ({what})")
            call = ", ".join(f"{a.key}=…" for a in answers)
            out += [
                "",
                f"Write `checks/{item.id}.py` ending with `answers({call})` from `studykit.check`.",
            ]
        else:
            out.append(
                "The item has no answer keys. Work it out independently; the protocol says "
                "how to review its solution."
            )
    if figures:
        out += ["", "## Figures", ""]
        for slug in dict.fromkeys(figures):
            png = tree.root / "_build" / "figures" / f"{slug}.png"
            state = (
                ""
                if png.is_file()
                else f" (not built yet: `studykit fig build {tree.id} --only {slug}`)"
            )
            out.append(f"- `{display_path(png)}`{state}")
    return "\n".join(out) + "\n"


def write(tree: CourseTree, item_id: str) -> tuple[Path, str]:
    text = render(tree, item_id)
    path = blind_path(tree, item_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, text
