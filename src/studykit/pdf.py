"""`studykit pdf <course> [doc ...]`: the course's PDF documents (docs/architecture.md §3.3).

Each document goes through three explicit steps:

1. **Assemble** `_build/typ/<doc>.md`: the course files' bodies (frontmatter stripped) in
   course order, each inside a part (`:::::: {.sk-part file=… lines=… first=…}`), plus
   generated blocks: headings, the document info, the exam cover, rubrics, objectives and
   answer labels as plain text with inline math (pandoc/filters/lib/document.lua has the
   vocabulary). Generated plain text is escaped, so no title is ever read as Markdown.
2. **pandoc** through `studykit.pandoc` (`-d common -d typst -M sk-doc=<kind>`,
   `--log _build/logs/<doc>.json`) into `_build/typ/<doc>.typ`.
3. **typst** `compile --root <repo> --ignore-system-fonts --diagnostic-format short` with
   `SOURCE_DATE_EPOCH=0` into `_build/pdf/<doc>.pdf`. Every Typst `warning:` and every
   pandoc log warning fails the document.

Documents: overview, summary (the overview is its first chapter), exercises (hints and
solutions in appendices), exercises-blank, mc (answer key appendix), `<exam>` (cover,
„Seite x von y“, MC part, no solutions), `<exam>-solutions` (solutions with rubric),
cheatsheet and plan. A document whose sources do not exist is not built. The cheat sheet is
compiled at `--input density=0..4` until it fits its page limit (studykit.cheatsheet); when
even density 4 overflows, the build fails with the overflow measured and the previous
cheatsheet.pdf stays in place.

**Manifest** (`_build/pdf/manifest.json`, read by the site):

    {"schema": "studykit-pdf/1", "course": "<id>", "docs": [
      {"id": "mc", "kind": "mc", "file": "mc.pdf", "title": "…", "pages": 12, "bytes": 81234},
      {"id": "<exam>", "kind": "exam", "file": "<exam>.pdf", "exam": "<exam>", …},
      {"id": "cheatsheet", …, "max_pages": 2, "density": 0}]}

It lists the documents this run built (or found up to date) and, when only some documents
were requested, the untouched documents of the previous manifest whose PDF still exists. A
document that fails keeps its previous PDF on disk, so nothing that worked is lost, but it
leaves the manifest: the site then links no PDF that does not match the current sources.
Documents whose sources are gone leave the manifest and their PDF is deleted.

**Incremental builds:** a document is skipped when its PDF exists and the digest of its
inputs (assembled Markdown, the figures it uses, the index, the filter, the house library,
the studykit sources, the tool versions, the cheat sheet's page limit) equals the one
stored in `_build/typ/<doc>.digest` by its last successful build (the cheat sheet's
density goes on a second line).

`make()` returns the outcomes as objects, with each problem typed (filter finding, pandoc
or Typst diagnostic, overflow) for the PDF stage of validate; `build()` is its JSON form.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import time
import unicodedata
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from studykit import content, index, model, pandoc, tools, verify

SCHEMA = "studykit-pdf/1"
FORMAT_TAG = b"studykit-pdf/1"
PART_FENCE = "::::::"  # longer than any fence a course file may use (`::::` for mcq)
UNIT_FENCE = "::::::::"  # a unit holds a part
NBSP = "\u00a0"  # between a number and its unit

# --- text the assembler writes (filter labels live in pandoc/filters/lib/i18n.lua) ----------

TEXT: dict[str, dict[str, Any]] = {
    "de": {
        "summary": "Zusammenfassung",
        "exercises": "Übungen",
        "exercises-blank": "Übungsblatt",
        "exercises-sub": "Mit Hinweisen und Lösungen im Anhang",
        "exercises-blank-sub": "Aufgaben ohne Hinweise und Lösungen",
        "mc": "Multiple-Choice-Fragen",
        "mc-sub": "Mit Lösungsschlüssel und Begründungen im Anhang",
        "solutions-title": "{title} \u2013 Lösungen",
        "solutions-sub": "Musterlösungen mit Bewertungsschema",
        "cheatsheet": "Formelblatt",
        "plan": "Lernplan",
        "contents": "Inhalt",
        "task": "Aufgabe",
        "points": ("{n} Punkt", "{n} Punkte"),
        "points-dative": ("{n} Punkt", "{n} Punkten"),
        "questions": ("{n} Frage", "{n} Fragen"),
        "difficulty": "Schwierigkeit {n} von 4",
        "minutes": "etwa {n} Minuten",
        "exercise-kinds": {
            "compute": "Rechenaufgabe",
            "derive": "Herleitung",
            "concept": "Verständnisfrage",
            "sketch": "Skizze",
            "code": "Programmieraufgabe",
        },
        "sources": "Quellen",
        "page": "S.",
        "mc-part": "MC-Teil",
        "mc-part-meta": "{questions} zu je {points}",
        "scoring": {
            "all-or-nothing": "Eine Frage zählt nur, wenn sie vollständig richtig beantwortet ist.",
            "partial": "Bei Fragen mit mehreren richtigen Antworten gibt es Teilpunkte für "
            "richtig entschiedene Optionen.",
            "kprim": "Fragen mit mehreren richtigen Antworten werden wie Kprim bewertet: "
            "alles richtig gibt die volle, ein Fehler die halbe Punktzahl.",
        },
        "negative": "Falsche Antworten führen zu Abzügen; der MC-Teil insgesamt gibt nie "
        "weniger als 0 Punkte.",
        "no-negative": "Falsche Antworten führen nicht zu Abzügen.",
        "fields": ["Name", "Matrikelnummer"],
        "exam-date": "Klausurtermin",
        "duration": "Bearbeitungszeit",
        "duration-value": "{n} Minuten",
        "total-points": "Punkte",
        "pass": "{total}, bestanden ab {pass}",
        "aids": "Hilfsmittel",
        "no-aids": "keine",
        "notes-title": "Hinweise",
        "notes": [
            "Bearbeiten Sie die Aufgaben auf eigenem Papier und schreiben Sie Ihren Namen auf "
            "jedes Blatt.",
            "Geben Sie bei Rechenaufgaben den Lösungsweg an; ein Ergebnis ohne Weg bringt "
            "nicht die volle Punktzahl.",
        ],
        "mc-note": "Kreuzen Sie im MC-Teil die Kästchen an.",
        "table-title": "Punkteverteilung",
        "table-head": ["Aufgabe", "Thema", "Punkte", "erreicht"],
        "total": "Summe",
        "plan-head": ["", "Datum", "Dauer", "Art", "Ziel und Aufgaben"],
        "week": "Woche {n}",
        "exam-on": "Klausur am {date}",
        "exam-open": "Klausurtermin noch offen",
        "plan-sum": "{sessions} mit zusammen {hours}",
        "sessions": ("{n} Lerneinheit", "{n} Lerneinheiten"),
        "hours": ("{n} Stunde", "{n} Stunden"),
        "plan-generated": "Stand: {date}",
        "session-kinds": {
            "learn": "Lernen",
            "review": "Wiederholen",
            "mixed": "Gemischt",
            "mock-exam": "Probeklausur",
            "cheatsheet": "Formelblatt",
            "buffer": "Puffer",
        },
        "plan-tasks": {
            "read": "Lesen",
            "exercises": "Übungen",
            "mc": "MC",
            "exam": "Probeklausur",
            "review": "Wiederholen",
            "cheatsheet": "Formelblatt schreiben",
        },
        "mc-task": "MC ({count} Fragen)",
        "weekdays": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        "weekdays-long": [
            "Montag",
            "Dienstag",
            "Mittwoch",
            "Donnerstag",
            "Freitag",
            "Samstag",
            "Sonntag",
        ],
        "months": [
            "Januar",
            "Februar",
            "März",
            "April",
            "Mai",
            "Juni",
            "Juli",
            "August",
            "September",
            "Oktober",
            "November",
            "Dezember",
        ],
    },
    "en": {
        "summary": "Summary",
        "exercises": "Exercises",
        "exercises-blank": "Exercise sheet",
        "exercises-sub": "With hints and solutions in the appendix",
        "exercises-blank-sub": "Exercises without hints and solutions",
        "mc": "Multiple-choice questions",
        "mc-sub": "With the answer key and every reason in the appendix",
        "solutions-title": "{title} \u2013 Solutions",
        "solutions-sub": "Model solutions with the marking scheme",
        "cheatsheet": "Cheat sheet",
        "plan": "Study plan",
        "contents": "Contents",
        "task": "Task",
        "points": ("{n} point", "{n} points"),
        "points-dative": ("{n} point", "{n} points"),
        "questions": ("{n} question", "{n} questions"),
        "difficulty": "Difficulty {n} of 4",
        "minutes": "about {n} minutes",
        "exercise-kinds": {
            "compute": "Calculation",
            "derive": "Derivation",
            "concept": "Concept question",
            "sketch": "Sketch",
            "code": "Programming",
        },
        "sources": "Sources",
        "page": "p.",
        "mc-part": "Multiple-choice part",
        "mc-part-meta": "{questions}, {points} each",
        "scoring": {
            "all-or-nothing": "A question counts only when it is answered completely right.",
            "partial": "Questions with several correct answers give partial credit for "
            "options decided right.",
            "kprim": "Questions with several correct answers are marked like Kprim: all "
            "right gives full, one mistake half the points.",
        },
        "negative": "Wrong answers cost points; the part as a whole never goes below 0.",
        "no-negative": "Wrong answers cost no points.",
        "fields": ["Name", "Student ID"],
        "exam-date": "Exam date",
        "duration": "Time",
        "duration-value": "{n} minutes",
        "total-points": "Points",
        "pass": "{total}, pass mark {pass}",
        "aids": "Allowed aids",
        "no-aids": "none",
        "notes-title": "Notes",
        "notes": [
            "Work on your own paper and write your name on every sheet.",
            "Show your working in calculations; a result alone does not earn full marks.",
        ],
        "mc-note": "Tick the boxes in the multiple-choice part.",
        "table-title": "Points",
        "table-head": ["Task", "Topic", "Points", "Achieved"],
        "total": "Total",
        "plan-head": ["", "Date", "Time", "Kind", "Goal and tasks"],
        "week": "Week {n}",
        "exam-on": "Exam on {date}",
        "exam-open": "Exam date not known yet",
        "plan-sum": "{sessions}, {hours} in total",
        "sessions": ("{n} session", "{n} sessions"),
        "hours": ("{n} hour", "{n} hours"),
        "plan-generated": "As of {date}",
        "session-kinds": {
            "learn": "Learn",
            "review": "Review",
            "mixed": "Mixed",
            "mock-exam": "Mock exam",
            "cheatsheet": "Cheat sheet",
            "buffer": "Buffer",
        },
        "plan-tasks": {
            "read": "Read",
            "exercises": "Exercises",
            "mc": "MC",
            "exam": "Mock exam",
            "review": "Review",
            "cheatsheet": "Write the cheat sheet",
        },
        "mc-task": "MC ({count} questions)",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "weekdays-long": [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ],
        "months": [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
    },
}


class Text:
    """The assembler's words, numbers and dates in the course language."""

    def __init__(self, lang: str):
        self.lang = lang if lang in TEXT else "en"
        self.t = TEXT[self.lang]

    def __getitem__(self, key: str) -> Any:
        return self.t[key]

    def num(self, value: float | int) -> str:
        v = float(value)
        s = str(int(v)) if v.is_integer() and abs(v) < 1e15 else f"{v:.10g}"
        if self.lang == "de":
            s = s.replace(".", ",")
        return s.replace("-", "\u2212")

    def count(self, key: str, n: float | int) -> str:
        one, many = self.t[key]
        return (one if float(n) == 1 else many).format(n=self.num(n))

    def date(self, d: dt.date, weekday: bool = False) -> str:
        month = self.t["months"][d.month - 1]
        text = f"{d.day}. {month} {d.year}" if self.lang == "de" else f"{d.day} {month} {d.year}"
        if weekday:
            text = f"{self.t['weekdays-long'][d.weekday()]}, {text}"
        return text

    def short_date(self, d: dt.date) -> str:
        day = self.t["weekdays"][d.weekday()]
        if self.lang == "de":
            return f"{day}{NBSP}{d.day}.{d.month}."
        return f"{day}{NBSP}{d.day}{NBSP}{self.t['months'][d.month - 1][:3]}"

    def date_range(self, a: dt.date, b: dt.date) -> str:
        months = self.t["months"]
        de = self.lang == "de"
        if a.year == b.year and a.month == b.month:
            return (
                f"{a.day}.\u2013{b.day}. {months[a.month - 1]} {a.year}"
                if de
                else (f"{a.day}\u2013{b.day} {months[a.month - 1]} {a.year}")
            )
        if a.year == b.year:
            if de:
                return (
                    f"{a.day}. {months[a.month - 1]} \u2013 {b.day}. {months[b.month - 1]} {b.year}"
                )
            return f"{a.day} {months[a.month - 1]} \u2013 {b.day} {months[b.month - 1]} {b.year}"
        return f"{self.date(a)} \u2013 {self.date(b)}"


# --- Markdown helpers ---------------------------------------------------------------------------

_PUNCT = re.compile(r"([!-/:-@\[-`{-~])")
FIGURE_RE = re.compile(r"\(fig:([a-z0-9][a-z0-9-]*)\)")


def esc(text: str) -> str:
    """Plain text as Markdown that reads back as exactly this text (one line)."""
    return _PUNCT.sub(r"\\\1", " ".join(str(text).split()))


def _esc_spaced(text: str) -> str:
    """`esc`, keeping one space at either end where `text` had whitespace."""
    core = esc(text)
    if not core:
        return " " if text else ""
    lead = " " if text[:1].isspace() else ""
    trail = " " if text[-1:].isspace() else ""
    return lead + core + trail


def label_md(text: str) -> str:
    """A label (plain text plus inline `$…$` math, §2.5) as Markdown: text escaped, math kept."""
    out, last = [], 0
    for m in model.INLINE_MATH_RE.finditer(text):
        out += [_esc_spaced(text[last : m.start()]), m.group(0)]
        last = m.end()
    out.append(_esc_spaced(text[last:]))
    return "".join(out).strip()


def attr(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\\", "&#92;")
    )


class Markdown:
    """The assembled document, line by line (parts remember where their lines are)."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.files: list[str] = []  # course files whose bodies it holds, in order

    def gap(self) -> None:
        if self.lines and self.lines[-1] != "":
            self.lines.append("")

    def heading(self, level: int, text: str) -> None:
        self.gap()
        self.lines += ["#" * level + " " + esc(text), ""]

    def para(self, markdown: str) -> None:
        self.gap()
        self.lines += [markdown, ""]

    def div(self, name: str, body: Sequence[str], **attrs: str) -> None:
        self.gap()
        extra = "".join(f' {k}="{attr(v)}"' for k, v in attrs.items())
        head = f"::: {{.{name}{extra}}}" if extra else f"::: {name}"
        self.lines += [head, *body, ":::", ""]

    def gen(self, fn: str, data: dict[str, Any]) -> None:
        text = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
        self.div("sk-gen", ["```json", *text.splitlines(), "```"], fn=fn)

    def part(self, doc: content.Doc, **attrs: str | None) -> None:
        """A course file's body, frontmatter stripped, in a part the filter checks as that file."""
        body = doc.split.body.rstrip("\n").split("\n")
        self.files.append(doc.rel)
        self.gap()
        fence = len(self.lines) + 1  # 1-based line of the opening fence
        fields = {
            "file": doc.rel,
            "lines": f"{fence + 1}-{fence + len(body)}",
            "first": str(doc.split.body_line),
            **{k: v for k, v in attrs.items() if v is not None},
        }
        head = " ".join(f'{k}="{attr(v)}"' for k, v in fields.items())
        self.lines += [f"{PART_FENCE} {{.sk-part {head}}}", *body, "", PART_FENCE, ""]

    def open_unit(self) -> None:
        """Start blocks the PDF keeps on one page when they fit (lib/document.lua sk-unit)."""
        self.gap()
        self.lines += [f"{UNIT_FENCE} sk-unit", ""]

    def close_unit(self) -> None:
        self.gap()
        self.lines += [UNIT_FENCE, ""]

    def text(self) -> str:
        return "\n".join(self.lines).rstrip("\n") + "\n"


def bullets(items: Iterable[str]) -> list[str]:
    return [f"- {item}" for item in items]


# --- what to build --------------------------------------------------------------------------


@dataclass
class Plan:
    """One document to build: its id, kind and assembled Markdown."""

    id: str
    kind: str
    title: str
    markdown: str
    solutions: pandoc.Solutions = "none"
    exam: str | None = None
    max_pages: int | None = None  # the cheat sheet's limit (studykit.cheatsheet.limit)
    # course files it is built from (course.yaml first), and the one that defines it
    # (overview.md, cheatsheet.md, plan.yaml, exams/<e>/exam.yaml; None for collections)
    sources: list[str] = field(default_factory=list)
    primary: str | None = None
    # the cheat sheet's `##` headings as (file line, title), to name measured sections
    sections: list[tuple[int, str]] = field(default_factory=list)

    @property
    def file(self) -> str:
        return f"{self.id}.pdf"


class AssemblyError(Exception):
    pass


def _data(doc: content.Doc | None) -> dict[str, Any]:
    data = doc.data if doc is not None else None
    return data if isinstance(data, dict) else {}


def _sort_key(text: str) -> str:
    """Rough locale order for titles: accents fold to their base letter (Ä next to A)."""
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in folded if not unicodedata.combining(c))


class Assembler:
    """Turns a course tree into the Markdown of each PDF document."""

    def __init__(self, tree: content.CourseTree):
        self.tree = tree
        course = tree.model
        if course is None:
            raise AssemblyError("course.yaml does not validate; run `studykit validate` first")
        self.course = course
        self.tx = Text(course.lang)
        self.order = {t.id: i for i, t in enumerate(course.topics)}
        self.topic_titles = {t.id: t.title for t in course.topics}
        # quarantined items (§2.10) are left out; the filter drops quarantined questions
        self.hidden = set(verify.quarantined_ids(tree.root))

    def questions(self, doc: content.Doc) -> int:
        """The number of questions of an MC file that the document shows."""
        qs = doc.body.questions if doc.body else []
        return sum(1 for q in qs if q.id not in self.hidden)

    # -- shared pieces --

    def plan_of(
        self,
        id: str,
        kind: str,
        title: str,
        md: Markdown,
        *,
        extra: Sequence[str] = (),
        primary: str | None = None,
        **fields: Any,
    ) -> Plan:
        """A Plan with the course files it reads: course.yaml, `extra`, its parts and the
        scripts of the figures it shows."""
        text = md.text()
        figures = [
            f"figures/{slug}.py"
            for slug in dict.fromkeys(FIGURE_RE.findall(text))
            if self.tree.get(f"figures/{slug}.py") is not None
        ]
        sources = list(dict.fromkeys(["course.yaml", *extra, *md.files, *figures]))
        return Plan(id, kind, title, text, sources=sources, primary=primary, **fields)

    def info(self, md: Markdown, kind: str, title: str, **extra: Any) -> None:
        data = {"kind": kind, "title": title, "course": self.course.title}
        data.update({k: v for k, v in extra.items() if v is not None})
        md.gen("info", data)

    def answers(self, md: Markdown, answers: Any) -> None:
        rows = []
        for a in answers if isinstance(answers, list) else []:
            if not isinstance(a, dict) or not isinstance(a.get("label"), str):
                continue
            rows.append(f"- {label_md(a['label'])}")
            rows.append("")
            rows.append(f"  {self.value_md(a)}")
            rows.append("")
        if rows:
            md.div("sk-answers", rows[:-1])

    def value_md(self, answer: dict[str, Any]) -> str:
        if isinstance(answer.get("expr"), str):
            return "`" + answer["expr"].replace("`", "") + "`"
        value = answer.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return esc("?")
        unit = answer.get("unit") if isinstance(answer.get("unit"), str) else ""
        s = f"{float(value):.6g}"
        if "e" in s:
            mant, exp = s.split("e")
            mant = mant.replace(".", "{,}" if self.tx.lang == "de" else ".")
            number = f"${mant} \\cdot 10^{{{int(exp)}}}$"
        else:
            number = esc(self.tx.num(float(s)))
        if not unit:
            return number
        return number + ("" if unit == "°" else NBSP) + esc(unit)

    def sources_line(self, data: dict[str, Any]) -> str | None:
        out = []
        for src in data.get("sources") or []:
            if not isinstance(src, dict) or not isinstance(src.get("doc"), str):
                continue
            title = self.tree.sources.get(src["doc"], {}).get("title") or src["doc"]
            pages = src.get("pages")
            if pages:
                title += f", {self.tx['page']} {str(pages).replace('-', '\u2013')}"
            out.append(title)
        return f"{self.tx['sources']}: " + "; ".join(out) if out else None

    def topic_title(self, topic: str | None) -> str:
        return self.topic_titles.get(topic or "", topic or "")

    def by_topic(self, docs: Iterable[content.Doc]) -> list[tuple[str, list[content.Doc]]]:
        groups: dict[str, list[content.Doc]] = {}
        for doc in docs:
            topic = doc.parts.get("topic") or _data(doc).get("topic") or ""
            groups.setdefault(topic, []).append(doc)
        return sorted(groups.items(), key=lambda kv: (self.order.get(kv[0], 99), kv[0]))

    # -- documents --

    def overview(self) -> Plan | None:
        doc = self.tree.get("overview.md")
        if doc is None:
            return None
        title = _data(doc).get("title") or "Overview"
        md = Markdown()
        self.info(md, "overview", title)
        md.part(doc)
        return self.plan_of("overview", "overview", title, md, primary=doc.rel)

    def summary(self) -> Plan | None:
        chapters = sorted(
            self.tree.of_kind("summary"),
            key=lambda d: (d.parts.get("nn", ""), self.order.get(d.parts.get("topic", ""), 99)),
        )
        overview = self.tree.get("overview.md")
        if not chapters and overview is None:
            return None
        title = self.tx["summary"]
        md = Markdown()
        self.info(md, "summary", title, outline=self.tx["contents"], **{"outline-depth": 2})
        if overview is not None:
            md.heading(1, _data(overview).get("title") or "Overview")
            md.part(overview)
        for doc in chapters:
            data = _data(doc)
            md.heading(1, data.get("title") or self.topic_title(doc.parts.get("topic")))
            line = self.sources_line(data)
            if line:
                md.div("sk-meta", [esc(line)])
            objectives = [o for o in data.get("objectives") or [] if isinstance(o, str)]
            if objectives:
                md.div("sk-objectives", bullets(label_md(o) for o in objectives))
            md.part(doc)
        extra = ["sources/manifest.yaml"] if self.tree.get("sources/manifest.yaml") else []
        return self.plan_of("summary", "summary", title, md, extra=extra)

    def exercises(self, blank: bool) -> Plan | None:
        docs = [d for d in self.tree.of_kind("exercise") if not verify.hidden_file(d, self.hidden)]
        if not docs:
            return None
        kind = "exercises-blank" if blank else "exercises"
        title = self.tx[kind]
        md = Markdown()
        self.info(
            md,
            kind,
            title,
            subtitle=self.tx[f"{kind}-sub"],
            outline=self.tx["contents"],
            **{"outline-depth": 2},
        )
        mode = "none" if blank else "appendix"
        for i, (topic, group) in enumerate(self.by_topic(docs), start=1):
            md.heading(1, f"{i} {self.topic_title(topic)}")
            group.sort(
                key=lambda d: (
                    _data(d).get("difficulty") or 0,
                    _sort_key(str(_data(d).get("title") or "")),
                )
            )
            for j, doc in enumerate(group, start=1):
                data = _data(doc)
                ex_title = str(data.get("title") or doc.parts.get("id") or doc.rel)
                number = f"{i}.{j}"
                md.open_unit()
                md.heading(2, f"{number} {ex_title}")
                meta = []
                if isinstance(data.get("difficulty"), int):
                    meta.append(self.tx["difficulty"].format(n=data["difficulty"]))
                if isinstance(data.get("minutes"), int):
                    meta.append(self.tx["minutes"].format(n=data["minutes"]))
                kind_label = self.tx["exercise-kinds"].get(data.get("kind"))
                if kind_label:
                    meta.append(kind_label)
                if meta:
                    md.div("sk-meta", [esc(" · ".join(meta))])
                md.part(doc, number=number, title=ex_title, hints=mode, solution=mode)
                if not blank:
                    self.answers(md, data.get("answers"))
                md.close_unit()
        return self.plan_of(kind, kind, title, md, solutions=mode)

    def mc(self) -> Plan | None:
        banks = self.tree.of_kind("mc")
        if not banks:
            return None
        title = self.tx["mc"]
        md = Markdown()
        self.info(md, "mc", title, subtitle=self.tx["mc-sub"])
        for topic, group in self.by_topic(banks):
            for doc in group:
                n = self.questions(doc)
                md.heading(1, _data(doc).get("title") or self.topic_title(topic))
                md.div("sk-meta", [esc(self.tx.count("questions", n))])
                md.part(doc, solution="appendix")
        return self.plan_of("mc", "mc", title, md, solutions="appendix")

    def _exam_parts(self, exam_doc: content.Doc) -> tuple[dict[str, Any], list, Any]:
        data = verify.exam_without(self.tree, exam_doc, _data(exam_doc), self.hidden)
        exam_id = exam_doc.parts["exam"]
        tasks = []
        for name in data.get("tasks") or []:
            rel = f"exams/{exam_id}/{name}"
            doc = self.tree.get(rel)
            if doc is None:
                raise AssemblyError(f"{exam_doc.display}: task file {name} does not exist")
            tasks.append(doc)
        mc = None
        if isinstance(data.get("mc"), dict):
            mc = self.tree.get(f"exams/{exam_id}/{data['mc'].get('file') or 'mc.md'}")
            if mc is None:
                raise AssemblyError(f"{exam_doc.display}: the MC file does not exist")
        return data, tasks, mc

    def _mc_meta(self, data: dict[str, Any], mc: content.Doc) -> tuple[int, float, str]:
        n = self.questions(mc)
        each = float(data["mc"].get("points_each") or 0)
        meta = self.tx["mc-part-meta"].format(
            questions=self.tx.count("questions", n), points=self.tx.count("points-dative", each)
        )
        return n, n * each, meta

    def _rules(self) -> list[str]:
        mc = self.course.exam.mc
        if mc is None:
            return []
        return [
            self.tx["scoring"][mc.scoring],
            self.tx["negative"] if mc.negative_marking else self.tx["no-negative"],
        ]

    def exam(self, exam_doc: content.Doc) -> Plan:
        data, tasks, mc = self._exam_parts(exam_doc)
        exam_id = exam_doc.parts["exam"]
        title = str(data.get("title") or exam_id)
        tx = self.tx
        rows, total = [], 0.0
        for k, doc in enumerate(tasks, start=1):
            points = float(_data(doc).get("points") or 0)
            total += points
            rows.append([str(k), str(_data(doc).get("title") or doc.rel), tx.num(points)])
        if mc is not None:
            n, mc_points, _ = self._mc_meta(data, mc)
            total += mc_points
            rows.append(["MC", f"{tx['mc-part']} ({tx.count('questions', n)})", tx.num(mc_points)])
        aids = data.get("aids")
        aids = self.course.exam.aids if aids in (None, "inherit") else aids
        facts = []
        if self.course.exam.date:
            facts.append([tx["exam-date"], tx.date(self.course.exam.date)])
        if data.get("duration_min"):
            facts.append([tx["duration"], tx["duration-value"].format(n=data["duration_min"])])
        if data.get("points"):
            value = tx.num(data["points"])
            if data.get("pass_points"):
                value = tx["pass"].format(total=value, **{"pass": tx.num(data["pass_points"])})
            facts.append([tx["total-points"], value])
        facts.append([tx["aids"], [str(a) for a in aids] if aids else [tx["no-aids"]]])
        notes = list(tx["notes"])
        if mc is not None:
            notes.append(" ".join([tx["mc-note"], *self._rules()]))
        cover = {
            "title": title,
            "course": self.course.title,
            "fields": tx["fields"],
            "facts": facts,
            "notes-title": tx["notes-title"],
            "notes": notes,
            "table": {
                "title": tx["table-title"],
                "head": tx["table-head"],
                "rows": rows,
                "total": [tx["total"], tx.num(total)],
            },
        }
        md = Markdown()
        self.info(md, "exam", title)
        md.gen("cover", cover)
        for k, doc in enumerate(tasks, start=1):
            task = _data(doc)
            md.heading(1, f"{tx['task']} {k}: {task.get('title') or doc.rel}")
            md.div("sk-meta", [esc(tx.count("points", float(task.get("points") or 0)))])
            md.part(doc, hints="none", solution="none")
        if mc is not None:
            _, _, meta = self._mc_meta(data, mc)
            md.heading(1, tx["mc-part"])
            md.div("sk-meta", [esc(" ".join([meta + ".", *self._rules()]))])
            md.part(mc, solution="none")
        return self.plan_of(
            exam_id, "exam", title, md, extra=[exam_doc.rel], primary=exam_doc.rel, exam=exam_id
        )

    def exam_solutions(self, exam_doc: content.Doc) -> Plan:
        data, tasks, mc = self._exam_parts(exam_doc)
        exam_id = exam_doc.parts["exam"]
        tx = self.tx
        title = tx["solutions-title"].format(title=data.get("title") or exam_id)
        md = Markdown()
        self.info(md, "exam-solutions", title, subtitle=tx["solutions-sub"])
        for k, doc in enumerate(tasks, start=1):
            task = _data(doc)
            points = float(task.get("points") or 0)
            md.heading(1, f"{tx['task']} {k}: {task.get('title') or doc.rel}")
            md.div("sk-meta", [esc(tx.count("points", points))])
            md.part(doc, hints="none", solution="inline")
            rubric = [r for r in task.get("rubric") or [] if isinstance(r, dict)]
            if rubric:
                md.div(
                    "sk-rubric",
                    bullets(label_md(str(r.get("criterion") or "")) for r in rubric),
                    points=";".join(tx.num(float(r.get("points") or 0)) for r in rubric),
                    total=tx.num(points),
                )
            self.answers(md, task.get("answers"))
        if mc is not None:
            _, _, meta = self._mc_meta(data, mc)
            md.heading(1, tx["mc-part"])
            md.div("sk-meta", [esc(meta + ".")])
            md.part(mc, solution="inline")
        return self.plan_of(
            f"{exam_id}-solutions",
            "exam-solutions",
            title,
            md,
            extra=[exam_doc.rel],
            primary=exam_doc.rel,
            solutions="inline",
            exam=exam_id,
        )

    def cheatsheet(self) -> Plan | None:
        from studykit import cheatsheet

        doc = self.tree.get("cheatsheet.md")
        if doc is None or not self.course.cheatsheet.allowed:
            return None
        data = _data(doc)
        title = str(data.get("title") or self.tx["cheatsheet"])
        md = Markdown()
        self.info(md, "cheatsheet", title)
        md.part(doc)
        return self.plan_of(
            "cheatsheet",
            "cheatsheet",
            title,
            md,
            primary=doc.rel,
            max_pages=cheatsheet.limit(self.course, data),
            sections=doc.body.headings(2) if doc.body else [],
        )

    def plan(self) -> Plan | None:
        doc = self.tree.get("plan.yaml")
        if doc is None:
            return None
        tx = self.tx
        data = doc.model.model_dump() if doc.model is not None else None
        if data is None:
            raise AssemblyError(f"{doc.display} does not validate; run `studykit validate`")
        sessions = sorted(data["sessions"], key=lambda s: (s["date"], s["id"]))
        exam_date = data.get("exam_date") or self.course.exam.date
        minutes = sum(s["minutes"] for s in sessions)
        intro = [
            tx["exam-on"].format(date=tx.date(exam_date, weekday=True))
            if exam_date
            else tx["exam-open"],
            tx["plan-sum"].format(
                sessions=tx.count("sessions", len(sessions)),
                hours=tx.count("hours", round(minutes / 60, 1)),
            ),
            tx["plan-generated"].format(date=tx.date(data["generated"])),
        ]
        weeks: list[dict[str, Any]] = []
        first_monday = None
        for s in sessions:
            day: dt.date = s["date"]
            monday = day - dt.timedelta(days=day.weekday())
            first_monday = first_monday or monday
            n = (monday - first_monday).days // 7 + 1
            if not weeks or weeks[-1]["monday"] != monday:
                span = tx.date_range(monday, monday + dt.timedelta(days=6))
                weeks.append({"monday": monday, "title": f"{tx['week'].format(n=n)} · {span}"})
                weeks[-1]["sessions"] = []
            row = {
                "date": tx.short_date(day),
                "minutes": f"{s['minutes']}{NBSP}min",
                "kind": tx["session-kinds"].get(s["kind"], s["kind"]),
                "tasks": [self.plan_task(t) for t in s.get("tasks") or []],
            }
            if s.get("goal"):
                row["goal"] = s["goal"]
            topics = [self.topic_title(t) for t in s.get("topics") or []]
            if topics:
                row["topics"] = ", ".join(topics)
            weeks[-1]["sessions"].append(row)
        for week in weeks:
            del week["monday"]
        title = tx["plan"]
        md = Markdown()
        self.info(md, "plan", title)
        md.gen("plan", {"intro": intro, "head": tx["plan-head"], "weeks": weeks})
        return self.plan_of("plan", "plan", title, md, extra=[doc.rel], primary=doc.rel)

    def ref_title(self, ref: str) -> str:
        scheme, _, rest = ref.partition(":")
        if scheme == "topic":
            return self.topic_title(rest)
        if scheme == "exam":
            exam = self.tree.get(f"exams/{rest}/exam.yaml")
            return str(_data(exam).get("title") or rest)
        if scheme in ("ex", "mc"):
            for item in self.tree.items:
                if item.id == rest:
                    return item.title or rest
        if scheme == "src":
            doc = rest.split("#")[0]
            return self.tree.sources.get(doc, {}).get("title") or doc
        return rest

    def plan_task(self, task: dict[str, Any]) -> str:
        tx = self.tx
        label = tx["plan-tasks"].get(task["do"], task["do"])
        refs = [r for r in [task.get("ref"), *(task.get("refs") or [])] if r]
        if task["do"] == "mc" and task.get("topic"):
            label = tx["mc-task"].format(count=task.get("count") or "")
            what = self.topic_title(task["topic"])
        elif refs:
            what = "; ".join(self.ref_title(r) for r in refs)
        elif task.get("topic"):
            what = self.topic_title(task["topic"])
        else:
            return label
        return f"{label}: {what}"

    def builders(self) -> dict[str, Any]:
        """Document id -> function that assembles it, in manifest order."""
        out: dict[str, Any] = {
            "overview": self.overview,
            "summary": self.summary,
            "exercises": lambda: self.exercises(blank=False),
            "exercises-blank": lambda: self.exercises(blank=True),
            "mc": self.mc,
        }
        for exam_doc in sorted(self.tree.of_kind("exam"), key=lambda d: d.parts["exam"]):
            exam_id = exam_doc.parts["exam"]
            out[exam_id] = lambda d=exam_doc: self.exam(d)
            out[f"{exam_id}-solutions"] = lambda d=exam_doc: self.exam_solutions(d)
        out["cheatsheet"] = self.cheatsheet
        out["plan"] = self.plan
        return out


def available(tree: content.CourseTree) -> list[str]:
    """Ids of the documents a course can build (exam ids come from the exam directories)."""
    ids = []
    if tree.get("overview.md"):
        ids.append("overview")
    if tree.get("overview.md") or tree.of_kind("summary"):
        ids.append("summary")
    if tree.of_kind("exercise"):
        ids += ["exercises", "exercises-blank"]
    if tree.of_kind("mc"):
        ids.append("mc")
    for exam in sorted(d.parts["exam"] for d in tree.of_kind("exam")):
        ids += [exam, f"{exam}-solutions"]
    model_ = tree.model
    if tree.get("cheatsheet.md") and (model_ is None or model_.cheatsheet.allowed):
        ids.append("cheatsheet")
    if tree.get("plan.yaml"):
        ids.append("plan")
    return ids


SINGLE_KINDS = ("overview", "summary", "exercises", "exercises-blank", "mc", "cheatsheet", "plan")


def doc_kind(doc_id: str, ids: Sequence[str]) -> str:
    """The manifest kind of a document id (`ids`: the course's documents)."""
    if doc_id in SINGLE_KINDS:
        return doc_id
    if doc_id.endswith("-solutions") and doc_id.removesuffix("-solutions") in ids:
        return "exam-solutions"
    return "exam"


# --- building ----------------------------------------------------------------------------------

# `path:line:col: error: message` (typst --diagnostic-format short); without a position for
# problems that have none
TYPST_DIAG = re.compile(
    r"^(?:(?P<path>.+?):(?P<line>\d+):(?P<col>\d+): )?(?P<severity>error|warning): "
    r"(?P<message>.*)$"
)


@dataclass
class Problem:
    """Why a document failed, typed for the PDF stage of validate.

    kind: `finding` (a filter finding, `message` is the formatted line with the course file
    and line), `typst-error`, `typst-warning` (with the position Typst reported, its path
    relative to the repository), `pandoc-warning`, `pandoc` (pandoc failed without a
    finding), `assembly` (the course files do not make the document), `overflow` (the cheat
    sheet is longer than its limit even at the densest setting).
    """

    kind: str
    message: str
    path: str | None = None
    line: int = 0
    col: int = 0

    def text(self) -> str:
        if self.kind in ("typst-error", "typst-warning"):
            severity = "error" if self.kind == "typst-error" else "warning"
            where = f"{self.path}:{self.line}:{self.col}: " if self.path else ""
            return f"typst: {where}{severity}: {self.message}"
        if self.kind == "pandoc-warning":
            return f"pandoc warning: {self.message}"
        if self.kind == "pandoc":
            return f"pandoc: {self.message}"
        return self.message


def typst_problems(lines: Iterable[str]) -> list[Problem]:
    out = []
    for line in lines:
        m = TYPST_DIAG.match(line.strip())
        if m is None:
            continue
        out.append(
            Problem(
                f"typst-{m['severity']}",
                m["message"],
                m["path"],
                int(m["line"] or 0),
                int(m["col"] or 0),
            )
        )
    return out


@dataclass
class Outcome:
    id: str
    kind: str
    file: str
    title: str
    status: str  # built | cached | failed
    pages: int | None = None
    bytes: int | None = None
    exam: str | None = None
    max_pages: int | None = None
    density: int | None = None
    problems: list[Problem] = field(default_factory=list)
    seconds: float = 0.0
    sources: list[str] = field(default_factory=list)
    primary: str | None = None
    overflow: dict[str, Any] | None = None  # the cheat sheet's, when it does not fit

    @property
    def ok(self) -> bool:
        return self.status in ("built", "cached")

    @property
    def errors(self) -> list[str]:
        return [p.text() for p in self.problems]

    def entry(self) -> dict[str, Any]:
        """The manifest entry (§3.3 contract)."""
        out: dict[str, Any] = {"id": self.id, "kind": self.kind, "file": self.file}
        if self.exam is not None:
            out["exam"] = self.exam
        out |= {"title": self.title, "pages": self.pages, "bytes": self.bytes}
        if self.kind == "cheatsheet":
            out |= {"max_pages": self.max_pages, "density": self.density}
        return out

    def to_json(self) -> dict[str, Any]:
        out = {**self.entry(), "status": self.status, "errors": self.errors}
        if self.overflow is not None:
            out["overflow"] = self.overflow
        return out


def typst_bin() -> Path:
    return tools.bin_path(tools.repo_root(), "typst")


def tool_version(binary: Path) -> str:
    proc = subprocess.run(
        [str(binary), "--version"], capture_output=True, text=True, check=True, timeout=60
    )
    return proc.stdout.splitlines()[0].strip()


def source_digest(root: Path) -> str:
    """sha256 over everything besides the course that shapes a PDF: the filter, the house
    library and the studykit sources (figures excluded: their output is hashed per use)."""
    files = [p for d in ("pandoc", "typst") for p in sorted((root / d).rglob("*")) if p.is_file()]
    pkg = Path(__file__).parent
    files += sorted(p for p in pkg.rglob("*.py") if "figures" not in p.relative_to(pkg).parts)
    h = hashlib.sha256()
    for path in files:
        try:
            name = path.relative_to(root).as_posix()
        except ValueError:
            name = path.name
        h.update(name.encode() + b"\0" + path.read_bytes() + b"\0")
    return h.hexdigest()


def page_count(path: Path) -> int:
    import pypdfium2  # loads PDFium; only needed here

    pdf = pypdfium2.PdfDocument(str(path))
    try:
        return len(pdf)
    finally:
        pdf.close()


def pdf_text(path: Path) -> list[str]:
    """The text of every page (for checks and tests)."""
    import pypdfium2

    pdf = pypdfium2.PdfDocument(str(path))
    try:
        out = []
        for page in pdf:
            textpage = page.get_textpage()
            out.append(textpage.get_text_range())
            textpage.close()
            page.close()
        return out
    finally:
        pdf.close()


def _course_findings(course_dir: Path, lines: Iterable[str]) -> list[str]:
    """Filter findings with course-relative paths shown as display paths."""
    out = []
    for line in lines:
        m = pandoc.FINDING.match(line)
        if m and not Path(m["path"]).is_absolute() and (course_dir / m["path"]).exists():
            line = content.display_path(course_dir / m["path"]) + line[len(m["path"]) :]
        out.append(line)
    return out


def _log_warnings(log: Path) -> list[Problem]:
    if not log.is_file():
        return []
    try:
        entries = json.loads(log.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        return [Problem("pandoc", f"unreadable pandoc log {log}")]
    return [
        Problem("pandoc-warning", str(e.get("pretty") or e.get("type") or e))
        for e in entries
        if isinstance(e, dict) and str(e.get("verbosity", "")).upper() == "WARNING"
    ]


@dataclass
class Context:
    root: Path
    course_dir: Path
    pandoc_version: str
    typst_version: str
    sources: str
    force: bool = False

    @property
    def build(self) -> Path:
        return self.course_dir / "_build"


def _typst(ctx: Context, command: str, inputs: dict[str, str] | None) -> tuple[list[str], dict]:
    """The argv start and environment of every Typst run (§3.3)."""
    args = [
        str(typst_bin()),
        command,
        "--root",
        str(ctx.root),
        "--ignore-system-fonts",
        "--diagnostic-format",
        "short",
    ]
    for key, value in (inputs or {}).items():
        args += ["--input", f"{key}={value}"]
    # TYPST_FONT_PATHS and friends would bring fonts or packages from this machine in
    env = {k: v for k, v in os.environ.items() if not k.startswith("TYPST_")}
    env["SOURCE_DATE_EPOCH"] = "0"
    return args, env


def compile_typst(
    ctx: Context, typ: Path, out: Path, inputs: dict[str, str] | None = None
) -> list[Problem]:
    """`typst compile` as §3.3 runs it; returns the problems (errors and warnings)."""
    args, env = _typst(ctx, "compile", inputs)
    proc = subprocess.run(
        [*args, str(typ), str(out)],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
        env=env,
        cwd=ctx.root,
    )
    problems = typst_problems(proc.stderr.splitlines())
    if proc.returncode != 0 and not problems:
        problems = [
            Problem("typst-error", proc.stderr.strip() or f"typst exited with {proc.returncode}")
        ]
    return problems


def eval_typst(ctx: Context, typ: Path, expression: str, inputs: dict[str, str] | None = None):
    """`typst eval <expression> --in <typ>`: the value as JSON (introspects the layout)."""
    args, env = _typst(ctx, "eval", inputs)
    proc = subprocess.run(
        [*args, "--in", str(typ), expression],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
        env=env,
        cwd=ctx.root,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"typst eval exited with {proc.returncode}")
    return json.loads(proc.stdout)


def _stamp(path: Path) -> tuple[str, int | None] | None:
    """(digest, cheat-sheet density) of the last successful build, or None."""
    try:
        lines = path.read_text(encoding="utf-8").split()
    except OSError:
        return None
    if not lines:
        return None
    density = None
    if len(lines) >= 3 and lines[1] == "density" and lines[2].isdigit():
        density = int(lines[2])
    return lines[0], density


def _digest(ctx: Context, plan: Plan, index_bytes: bytes | None = None) -> str:
    figures = ctx.build / "figures"
    h = hashlib.sha256()
    for part in (
        FORMAT_TAG,
        ctx.pandoc_version.encode(),
        ctx.typst_version.encode(),
        ctx.sources.encode(),
        index_bytes if index_bytes is not None else (ctx.build / "index.json").read_bytes(),
        plan.kind.encode(),
        plan.solutions.encode(),
        str(plan.max_pages).encode(),
        plan.markdown.encode(),
    ):
        h.update(part + b"\0")
    for slug in sorted(set(FIGURE_RE.findall(plan.markdown))):
        svg = figures / f"{slug}.svg"
        h.update(
            slug.encode() + b"\0" + (svg.read_bytes() if svg.is_file() else b"missing") + b"\0"
        )
    return h.hexdigest()


def build_one(ctx: Context, plan: Plan) -> Outcome:
    started = time.monotonic()
    out = Outcome(
        plan.id,
        plan.kind,
        plan.file,
        plan.title,
        "failed",
        exam=plan.exam,
        max_pages=plan.max_pages,
        sources=plan.sources,
        primary=plan.primary,
    )
    typ_dir, pdf_dir, log_dir = ctx.build / "typ", ctx.build / "pdf", ctx.build / "logs"
    for d in (typ_dir, pdf_dir, log_dir):
        d.mkdir(parents=True, exist_ok=True)
    md_path = typ_dir / f"{plan.id}.md"
    if not md_path.is_file() or md_path.read_text(encoding="utf-8") != plan.markdown:
        md_path.write_text(plan.markdown, encoding="utf-8")

    digest = _digest(ctx, plan)
    digest_path = typ_dir / f"{plan.id}.digest"
    pdf_path = pdf_dir / plan.file
    stamp = _stamp(digest_path)
    fitted = plan.kind == "cheatsheet"
    if (
        not ctx.force
        and pdf_path.is_file()
        and stamp is not None
        and stamp[0] == digest
        and (not fitted or stamp[1] is not None)
    ):
        out.status = "cached"
        out.pages, out.bytes = page_count(pdf_path), pdf_path.stat().st_size
        out.density = stamp[1]
        out.seconds = time.monotonic() - started
        return out

    typ_path, log_path = typ_dir / f"{plan.id}.typ", log_dir / f"{plan.id}.json"
    doc = pandoc.course_document(
        ctx.course_dir,
        f"_build/typ/{plan.id}.md",
        solutions=plan.solutions,
        figdir=ctx.build / "figures",
        doc=plan.kind,
    )
    try:
        pandoc.run_file(md_path, doc, "typst", output=typ_path, log=log_path, root=ctx.root)
    except pandoc.FilterError as exc:
        lines = _course_findings(ctx.course_dir, exc.findings)
        out.problems = [Problem("finding", ln) for ln in lines] or [
            Problem("pandoc", exc.stderr.strip())
        ]
    except (pandoc.PandocError, OSError, subprocess.TimeoutExpired) as exc:
        out.problems = [Problem("pandoc", str(exc).strip())]
    out.problems += _log_warnings(log_path)
    if not out.problems:
        tmp = pdf_dir / f".{plan.id}.partial.pdf"
        tmp.unlink(missing_ok=True)
        if fitted:
            _fit_cheatsheet(ctx, plan, typ_path, tmp, out)
        else:
            out.problems = compile_typst(ctx, typ_path, tmp)
            if not out.problems:
                out.pages = page_count(tmp)
        if out.problems or out.pages is None:
            tmp.unlink(missing_ok=True)
        else:
            os.replace(tmp, pdf_path)
            out.bytes = pdf_path.stat().st_size
            line = digest if out.density is None else f"{digest}\ndensity {out.density}"
            digest_path.write_text(line + "\n", encoding="utf-8")
            out.status = "built"
    out.seconds = time.monotonic() - started
    return out


def _fit_cheatsheet(ctx: Context, plan: Plan, typ: Path, tmp: Path, out: Outcome) -> None:
    """Compile at densities 0 to 4 and keep the first that fits (studykit.cheatsheet)."""
    from studykit import cheatsheet  # it imports this module

    limit = plan.max_pages or cheatsheet.HARD_LIMIT
    result = cheatsheet.fit(
        lambda density: compile_typst(ctx, typ, tmp, {"density": str(density)}),
        lambda: page_count(tmp),
        limit,
    )
    out.density = result.density
    if result.problems:
        out.problems = result.problems
        return
    if result.fits:
        out.pages = result.pages
        return
    floor = cheatsheet.DENSITIES[-1]
    try:
        layout = eval_typst(ctx, typ, cheatsheet.MEASURE, {"density": str(floor)})
        out.overflow = cheatsheet.overflow(layout, limit, result.pages or 0, plan.sections)
    except (RuntimeError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        out.overflow = cheatsheet.overflow_unmeasured(limit, result.pages or 0, str(exc))
    out.problems = [Problem("overflow", cheatsheet.overflow_message(out.overflow))]
    out.pages = None


def freshness(course_dir: Path) -> dict[str, str]:
    """Per document the course can build: `fresh` (the manifest lists it and its PDF was
    built from the current inputs), `stale` or `missing`. Builds and writes nothing: the
    digest is computed as `build_one` would, with the index computed in memory. Raises
    FileNotFoundError when pandoc or typst is not installed."""
    root = tools.repo_root()
    course_dir = course_dir.resolve()
    tree = content.CourseTree(course_dir)
    ids = available(tree)
    previous = read_manifest(course_dir) or {}
    listed = {d.get("id") for d in previous.get("docs") or [] if isinstance(d, dict)}
    out = {d: "missing" for d in ids}
    present = [
        d for d in ids if d in listed and (course_dir / "_build" / "pdf" / f"{d}.pdf").is_file()
    ]
    if not present:
        return out
    for binary in (pandoc.pandoc_bin(), typst_bin()):
        if not Path(binary).exists():
            raise FileNotFoundError(f"{binary} is not installed (run `just setup`)")
    ctx = Context(
        root,
        course_dir,
        tool_version(pandoc.pandoc_bin()),
        tool_version(typst_bin()),
        source_digest(root),
    )
    index_bytes = index.dumps(index.build(tree)).encode()
    try:
        builders = Assembler(tree).builders()
    except AssemblyError:
        return {d: "stale" if d in present else "missing" for d in ids}
    for doc_id in present:
        try:
            plan = builders[doc_id]()
        except AssemblyError, KeyError:
            plan = None
        stamp = _stamp(ctx.build / "typ" / f"{doc_id}.digest")
        fresh = (
            plan is not None and stamp is not None and stamp[0] == _digest(ctx, plan, index_bytes)
        )
        out[doc_id] = "fresh" if fresh else "stale"
    return out


def manifest_path(course_dir: Path) -> Path:
    return course_dir / "_build" / "pdf" / "manifest.json"


def read_manifest(course_dir: Path) -> dict[str, Any] | None:
    path = manifest_path(course_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return None
    return data


def _merge(
    course_dir: Path,
    order: list[str],
    outcomes: list[Outcome],
    previous: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Manifest entries: this run's successes plus untouched previous entries, in order."""
    pdf_dir = course_dir / "_build" / "pdf"
    tried = {o.id for o in outcomes}
    entries = {o.id: o.entry() for o in outcomes if o.ok}
    for old in (previous or {}).get("docs") or []:
        if not isinstance(old, dict) or not isinstance(old.get("id"), str):
            continue
        oid = old["id"]
        if oid in tried or oid in entries:
            continue
        file = pdf_dir / str(old.get("file") or "")
        if oid not in order:
            # its sources are gone: the stale PDF goes too
            if old.get("file") and file.is_file() and file.parent == pdf_dir:
                file.unlink()
            continue
        if file.is_file():
            entries[oid] = old
    return [entries[i] for i in order if i in entries]


@dataclass
class Build:
    """One `studykit pdf` run over a course."""

    course: str
    manifest: Path
    outcomes: list[Outcome]
    notes: list[str]

    def to_json(self) -> dict[str, Any]:
        return {
            "course": self.course,
            "manifest": content.display_path(self.manifest),
            "docs": [o.to_json() for o in self.outcomes],
            "notes": self.notes,
        }


def make(
    course_dir: Path,
    docs: Sequence[str] | None = None,
    *,
    files: Iterable[str] | None = None,
    force: bool = False,
    figures: bool = True,
    jobs: int | None = None,
) -> Build:
    """Build the course's PDFs (all, or the ids in `docs`) and write the manifest.

    With `files` (course-relative paths) only the documents built from one of them are
    built. Raises ValueError for a document id the course cannot have.
    """
    root = tools.repo_root()
    course_dir = course_dir.resolve()
    tree = content.CourseTree(course_dir)
    index.write(tree)
    ids = available(tree)
    wanted = list(dict.fromkeys(docs)) if docs else list(ids)
    unknown = [d for d in wanted if d not in ids]
    if unknown:
        raise ValueError(
            f"no document {', '.join(unknown)} in {tree.id}; this course has: {', '.join(ids)}"
        )
    selected = set(files) if files is not None else None
    notes: list[str] = []
    if figures:
        from studykit.figures import runner  # imports Matplotlib; only needed here

        for o in runner.build_course(course_dir):
            if o.status == "failed":
                notes.append(f"figure {o.slug} failed: {'; '.join(o.problems)[:300]}")

    ctx = Context(
        root,
        course_dir,
        tool_version(pandoc.pandoc_bin()),
        tool_version(typst_bin()),
        source_digest(root),
        force,
    )
    outcomes: list[Outcome] = []
    plans: list[Plan] = []

    def failed(doc_id: str, message: str) -> Outcome:
        return Outcome(
            doc_id,
            doc_kind(doc_id, ids),
            f"{doc_id}.pdf",
            "",
            "failed",
            problems=[Problem("assembly", message)],
        )

    try:
        builders = Assembler(tree).builders()
    except AssemblyError as exc:
        builders = {}
        outcomes += [failed(d, str(exc)) for d in wanted]
    for doc_id, assemble in builders.items():
        if doc_id not in wanted:
            continue
        try:
            plan = assemble()
        except AssemblyError as exc:
            outcomes.append(failed(doc_id, str(exc)))
            continue
        if plan is not None and (selected is None or selected & set(plan.sources)):
            plans.append(plan)
    workers = max(1, min(len(plans) or 1, jobs or os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes += list(pool.map(lambda p: build_one(ctx, p), plans))
    rank = {d: i for i, d in enumerate(ids)}
    outcomes.sort(key=lambda o: rank.get(o.id, len(rank)))

    previous = read_manifest(course_dir)
    manifest = {
        "schema": SCHEMA,
        "course": tree.model.id if tree.model else tree.id,
        "docs": _merge(course_dir, ids, outcomes, previous),
    }
    path = manifest_path(course_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
    return Build(manifest["course"], path, outcomes, notes)


def build(
    course_dir: Path,
    docs: Sequence[str] | None = None,
    *,
    force: bool = False,
    figures: bool = True,
    jobs: int | None = None,
) -> dict[str, Any]:
    """`make` as JSON: {"course", "manifest", "docs": [outcome…], "notes": […]}."""
    return make(course_dir, docs, force=force, figures=figures, jobs=jobs).to_json()


# --- where a problem comes from -----------------------------------------------------------------

# Typst lines that name the course item the lines after them come from: a part's
# `#metadata("<id>") <id>`, a question's `id: "<id>"`, an appendix entry's `back: <id>`
ITEM_MARK = re.compile(
    r'^#metadata\("(?P<meta>[^"]+)"\) <(?P=meta)>$'
    r'|^\s*id: "(?P<id>[^"]+)",$'
    r"|back: <(?P<back>[^>]+)>"
)


def locate(tree: content.CourseTree, typ: Path, line: int) -> tuple[str, int] | None:
    """The course file and line of the item a line of an assembled document's .typ belongs
    to, or None when no item comes before it (generated text, the document's head)."""
    try:
        lines = typ.read_text(encoding="utf-8").splitlines()[:line]
    except OSError:
        return None
    items = {item.id: item for item in tree.items}
    for text in reversed(lines):
        for m in reversed(list(ITEM_MARK.finditer(text))):
            item = items.get(m["meta"] or m["id"] or m["back"])
            if item is not None:
                return item.rel, item.line
    return None


def format_text(result: dict[str, Any]) -> str:
    rows = result["docs"]
    counts = {s: sum(r["status"] == s for r in rows) for s in ("built", "cached", "failed")}
    lines = [
        f"pdf {result['course']}: {counts['built']} built, {counts['cached']} cached, "
        f"{counts['failed']} failed"
    ]
    width = max((len(r["file"]) for r in rows), default=0)
    for r in rows:
        if r["status"] == "failed":
            lines.append(f"  failed  {r['file']}")
            lines += [f"          {e}" for e in r["errors"]]
        else:
            pages = f"{r['pages']} page{'s' if r['pages'] != 1 else ''}"
            size = f"{(r['bytes'] or 0) / 1024:.0f} KB"
            limit = ""
            if r["kind"] == "cheatsheet":
                limit = f"  (limit {r['max_pages']}, density {r['density']})"
            lines.append(
                f"  {r['status']:<7} {r['file']:<{width}}  {pages:>9}  {size:>7}  {r['title']}"
                + limit
            )
    lines += [f"  note: {n}" for n in result.get("notes", [])]
    lines.append(f"wrote {result['manifest']}")
    return "\n".join(lines)
