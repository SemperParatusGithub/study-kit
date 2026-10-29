# Part: summary (`summary/<nn>-<topic>.md`)

One chapter per topic, `nn` = the topic's position in `course.yaml` (01, 02, …). The
chapter teaches the topic so that its exercises and MC questions can be solved from it.

## Inputs

The topic's notes in `sources/notes/`, `sources/outline.md`, the lecture text pages they
cite, `notation.yaml`, the chapters of the prerequisite topics (link, do not repeat them).

## Structure

- Frontmatter: `topic`, `title` (the topic title), 3-6 `objectives` (what the student can
  do afterwards, starting with a verb), `sources: [{doc, pages}]` when sources exist.
- 3-7 H2 sections in teaching order, each: the idea in prose, the key formula as display
  math, a figure where a picture explains more than text, then a box.
- Boxes: `definition` for each new term, `theorem` for a rule with conditions, `example`
  for one worked numeric example per main formula (values computed in Python), `warning`
  for each common mistake (from the misconception catalogue in [mc.md](mc.md)), `note`
  for side remarks, and one `takeaways` box at the end (3-6 bullets).
- Link exercises where they fit (`Übung: [Titel](ex:<id>)`) once they exist, prerequisite
  topics with `topic:`, lecture pages with `src:<doc>#p=<n>`.

## Rules

- Derive the important formulas briefly; the cheat sheet later condenses them.
- Use the same symbols as the exercises and the notation file; units with every number.
- Length: 120-300 lines; a chapter that grows longer is split into clearer sections, not
  cut short.
- Every chapter ends with the automatic "Test yourself" quiz from the MC bank; do not add
  your own quiz.
- Template: the content-format skill's `templates/summary.md`.
