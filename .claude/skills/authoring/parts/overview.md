# Part: overview (`overview.md`)

The first page a student sees: the big picture before any detail (§2.12). Written first in
an author wave so other parts can link to it; `/regenerate <course> overview` re-runs it.

## Inputs

`course.yaml` (topics, weights, prerequisites, focus, skip, exam), `analysis/exam-profile.yaml`
(format, duration, points, archetypes and their shares, MC part, aids, confidence),
`analysis/notation.yaml`, `sources/outline.md`, the "Course facts" of the notes in
`sources/notes/` (exam date, format and aids as the material states them) and the summary
chapters when they exist.

## Structure

Exactly six H2 sections, in this order (titles in the course language; English: Big
picture, Topic map, How the topics connect, Exam at a glance, How to study this subject,
Prerequisites). Lint checks them by position and count (SK-STRUCT-SECTIONS).

1. **Worum geht es? / Big picture** - one or two paragraphs: what the subject is for, how
   the topics build on each other; link each topic with `[title](topic:<id>)`.
2. **Themenkarte / Topic map** - only `![Caption](fig:topic-map)`; the figure is built
   from `course.yaml` automatically (no script).
3. **Wie die Themen zusammenhängen / How the topics connect** - the thread through the
   topics, with at most one or two key formulas that carry over.
4. **Die Klausur auf einen Blick / Exam at a glance** - date, duration, points, aids, a
   table of the parts with points (archetypes and their shares from the profile, the MC part
   with question count, types, scoring and negative marking), the time per point and what
   follows from it; link the mock exams with `exam:` once they exist. Say how sure the
   profile is (`confidence`, how many past exams).
5. **So lernst du dieses Fach / How to study this subject** - 3-6 concrete bullets: order,
   which exercises to start with (`ex:` links once they exist), when to do MC, the cheat
   sheet, mock exams.
6. **Voraussetzungen / Prerequisites** - bullets of what the course assumes.

## Rules

- Every topic that is not skipped is linked at least once with `topic:` (SK-COV-OVERVIEW).
- Link only ids that `uv run --frozen studykit index <course> --json` lists (anything else
  is SK-REF-MISSING). In an author wave the overview comes first, before any exercise or
  mock exam exists: name them in words without a link; /register-new-subject adds the
  links before it publishes (its step 13), `/regenerate <course> all` at its end, and
  `/regenerate <course> overview` links what exists by then.
- Numbers about the exam come from `course.yaml` and the profile, not from memory; compute
  shares, minutes per point and sums with `studykit calc`. When the notes' course facts
  differ from `course.yaml` (another exam date, say), give the `course.yaml` value and
  name what the material states, with its `src:` link.
- In the PDF a `topic:` link whose text is not the topic's title gets „(→ Thema: Titel)“
  appended; in running prose use the title itself as the link text, and keep a `src:` link
  out of parentheses (it gets its own).
- No exercises, hints or solutions here; 60-120 lines of Markdown.
- Template: the content-format skill's `templates/overview.md`.
