"""Write the browser-harness fixtures from REAL filter output.

Sources: tests/fixtures/courses/mini (course "mini") and tests/fixtures/pandoc/ok (with its
index.json). The fragments are what pandoc + pandoc/filters/studykit.lua emit for html, with
sk-meta removed and data-h added the way the site loader does it, and wrapped in the
exercise and exam elements the way the site shell does it (docs/architecture.md §3.2).
<sk-math> stays in place; tests/elements/server.mjs renders it with KaTeX like the loader.

Regenerate from the repository root (needs the pinned pandoc in .tools/bin):
    uv run --frozen python site/tests/elements/make_fixtures.py
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import tempfile
from pathlib import Path

import yaml

from studykit import content, index, pandoc, tools

ROOT = tools.repo_root()
HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures"
MINI = ROOT / "tests" / "fixtures" / "courses" / "mini"
OK = ROOT / "tests" / "fixtures" / "pandoc" / "ok"
OK_INDEX = ROOT / "tests" / "fixtures" / "pandoc" / "index.json"

META_RE = re.compile(r'\n?<script type="application/json" id="sk-meta">.*?</script>\n?', re.S)
MC_RE = re.compile(r"<sk-mc (?P<attrs>[^>]*)>.*?</sk-mc>", re.S)
HINTS_RE = re.compile(r'(?:<details class="sk-hint".*?</details>\n?)+', re.S)
SOLUTION_RE = re.compile(r'<details class="sk-solution">.*?</details>\n?', re.S)


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def attr(attrs: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', attrs)
    return m.group(1) if m else ""


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


def render_ok(rel: str) -> str:
    return META_RE.sub("\n", pandoc.run_filtered(OK, rel, "html", index=OK_INDEX)).strip() + "\n"


def with_hashes(fragment: str) -> tuple[str, list[dict]]:
    """Add data-h to every <sk-mc> and return the questions for a pool file."""
    questions: list[dict] = []

    def add(m: re.Match[str]) -> str:
        h = short_hash(m.group(0))
        tagged = m.group(0).replace("<sk-mc ", f'<sk-mc data-h="{h}" ', 1)
        a = m.group("attrs")
        questions.append(
            {
                "id": attr(a, "data-id"),
                "type": attr(a, "data-type"),
                "difficulty": int(attr(a, "data-difficulty") or 0),
                "topic": attr(a, "data-topic"),
                "h": h,
                "html": tagged,
            }
        )
        return tagged

    return MC_RE.sub(add, fragment), questions


def exercise(rel: str) -> str:
    fm = frontmatter(OK / rel)
    body = render_ok(rel)
    item = f"ex:{fm['id']}"
    h = short_hash(body)
    answers = html.escape(json.dumps(fm.get("answers", []), ensure_ascii=False), quote=True)
    attrs = f'data-item="{item}" data-h="{h}"'
    body = HINTS_RE.sub(lambda m: f"<sk-hints {attrs}>\n{m.group(0)}</sk-hints>\n", body)
    body = SOLUTION_RE.sub(
        lambda m: (
            f'<sk-answer-check {attrs} data-answers="{answers}"></sk-answer-check>\n'
            f"<sk-reveal {attrs}>\n{m.group(0)}</sk-reveal>\n"
            f"<sk-self-assess {attrs}></sk-self-assess>\n"
        ),
        body,
    )
    return f'<article class="sk-exercise" data-item="{item}">\n{body}</article>\n'


def exam(mini_mc: str) -> str:
    rel = "exams/probeklausur-1/01-pk1-t1.md"
    fm = frontmatter(OK / rel)
    rubric = html.escape(json.dumps(fm["rubric"], ensure_ascii=False), quote=True)
    task = render_ok(rel)
    exam_mc, _ = with_hashes(render_ok("exams/probeklausur-1/mc.md"))
    # The exam's own question plus the mini bank, so the MC part has every type.
    questions = [m.group(0) for m in MC_RE.finditer(exam_mc + mini_mc)]
    course = yaml.safe_load((MINI / "course.yaml").read_text(encoding="utf-8"))
    aids = html.escape(json.dumps(course["exam"]["aids"], ensure_ascii=False), quote=True)
    points_each = 2
    mc_points = points_each * len(questions)
    total = fm["points"] + mc_points
    task_attrs = f'data-task="{fm["id"]}" data-points="{fm["points"]}" data-rubric="{rubric}"'
    mc = "\n".join(questions)
    return (
        f'<sk-exam data-exam="probeklausur-1" data-duration-min="60" data-points="{total}" '
        f'data-pass-points="{total // 2}" data-aids="{aids}" data-mc-scoring="all-or-nothing">\n'
        f'<section class="sk-exam-task" {task_attrs}>\n'
        f"<h2>Aufgabe 1: {fm['title']} ({fm['points']} P)</h2>\n{task}</section>\n"
        f'<section class="sk-exam-mc" data-points="{mc_points}">\n'
        f"<h2>Multiple-Choice-Teil ({mc_points} P)</h2>\n{mc}\n</section>\n</sk-exam>\n"
    )


def plan() -> str:
    data = yaml.safe_load((MINI / "plan.yaml").read_text(encoding="utf-8"))
    items = []
    for s in data["sessions"]:
        goal = f" · {s['goal']}" if s.get("goal") else ""
        topics = ", ".join(s.get("topics", []))
        day = s["date"]
        text = f"{s['kind']} · {s['minutes']} min{' · ' + topics if topics else ''}{goal}"
        items.append(
            f'<li data-session="{s["id"]}" data-date="{day}">'
            f'<time datetime="{day}">{day}</time> · {html.escape(text)}</li>'
        )
    lines = "\n".join(items)
    return f'<sk-plan data-course="mini">\n<ol class="plan-sessions">\n{lines}\n</ol>\n</sk-plan>\n'


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "pools").mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="sk-elements-") as tmp:
        course_dir = Path(tmp) / "mini"
        shutil.copytree(MINI, course_dir)
        tree = content.CourseTree(course_dir)
        index.write(tree)
        mini = pandoc.run_filtered(course_dir, "mc/rc-tiefpass.md", "html")
    mini, mini_q = with_hashes(META_RE.sub("\n", mini).strip() + "\n")
    ok_mc, ok_q = with_hashes(render_ok("mc/rc-filter.md"))
    files = {
        "mc-rc-tiefpass.html": mini,
        "mc-rc-filter.html": ok_mc,
        "exercise.html": exercise("exercises/rc-filter/ex-rc-tp-grenzfrequenz.md"),
        "exam.html": exam(mini),
        "plan.html": plan(),
    }
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
    for topic, questions in (("rc-tiefpass", mini_q), ("rc-filter", ok_q)):
        pool = {"topic": topic, "questions": questions}
        (OUT / "pools" / f"{topic}.json").write_text(
            json.dumps(pool, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
