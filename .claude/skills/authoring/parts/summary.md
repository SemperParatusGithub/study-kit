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
  topics with `topic:`, lecture pages with `src:<doc>#p=<n>`. The PDF appends
  „(→ Quelle: Dokument, S. n)“ to every `src:` link, so keep it out of parentheses and give
  it short text (`[Folie 12](src:…)`, not `([Skript, S. 2](src:…))`).

## In a topic

In a topic (`kind: topic`, docs/architecture.md §5.6) the summary is the explanation, the heart
of the page, and the subject need not be technical:

- The inputs are the notes and `sources/outline.md`; there is no notation file and no MC bank
  or exercise to serve. Teach from the start: assume only the chapter's prerequisites and say
  what each new word means. A formula where it helps, not as the structure of every section.
- Every new term gets a `::: definition` box whose first paragraph is the bold term alone
  (`**Merkle tree**`): the glossary collects these (SK-COV-GLOSSARY), so use the term as a
  reader would look it up. Define a term once, in the chapter that introduces it, and link
  that chapter later (the glossary keeps only the first definition). An `example` box shows the idea on something concrete, with numbers
  from `studykit calc` where there are any; `warning` boxes hold real misconceptions.
- No links to exercises; the chapter page links the flash cards itself.

## Rules

- Derive the important formulas briefly; the cheat sheet later condenses them.
- Use the same symbols as the exercises and the notation file; units with every number.
- Length: 120-300 lines without the frontmatter; a chapter that grows longer is split into clearer sections, not
  cut short.
- Every chapter ends with the automatic "Test yourself" quiz from the MC bank; do not add
  your own quiz.
- Template: the content-format skill's `templates/summary.md`.
