# Part: exercises (`exercises/<topic>/<ex-id>.md`)

Practice exercises of one topic, one file each, with a machine-checkable answer key.

## How many

- `targets.exercises_per_topic: auto` means at least 4 per topic (more for heavy or focus
  topics: about 4 + 8 × weight, focus × 1.5); a number means that many. `--add n` adds
  n to what exists.
- At least two difficulties per topic (SK-COV-EXERCISES). A good spread for six exercises:
  one at 1, two at 2, two at 3, one at 4 (exam level).
- Mix the kinds: mostly `compute`, some `derive` (symbolic answer), `concept` or `sketch`
  where the topic needs them; each exam archetype of the topic gets at least one exercise.

## Each exercise

1. Choose the values first and compute every result in Python
   (`uv run --frozen studykit calc …`); pick values that give unambiguous, not round-trip
   trivial results (avoid answers that equal a given value).
2. Statement: the situation, the given values with units, a figure for every circuit or
   diagram (figure script), subtasks as `**a)**` paragraphs, each asking for one result.
3. `answers`: one key per asked quantity with `label` naming the quantity (plain text and
   inline math), `value` in the stated `unit`, a tolerance; symbolic results as `expr` with
   `symbols`. Keys are short (`fg`, `Hdb`, `phi`, `U2`).
4. 1-3 hints (principle → set-up → key intermediate result), no answer values.
5. One `solution` block, the last block, with every subtask: formula, numbers inserted,
   result rounded as a student would write it (decimal comma in German).
6. Frontmatter: `difficulty`, `kind`, `minutes` (realistic working time),
   `source: {doc, page, relation}` when adapted from course material.

## Ids and files

`ex-<topic-short>-<slug>`, e.g. `ex-rc-tp-grenzfrequenz`; the file name is the id. Never
reuse an id from `retired_ids`.

Template: the content-format skill's `templates/exercise.md` and
`templates/exercise-symbolic.md`.
