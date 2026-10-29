# Exam analysis

The `exam-analyst` writes `analysis/exam-profile.yaml` and `analysis/notation.yaml` once
per course (docs/architecture.md §5.3, §5.4 step 4). It runs alongside the ingesters, so
it reads the sources itself and never waits for their notes. Mock exams are modelled on
the profile (the authoring skill's `parts/exam.md`), the overview's "exam at a glance"
quotes it, and every author follows the notation.

## 1. Inputs

1. `sources/manifest.yaml`: `answers.round1` (`exam_date`, `exam_format`,
   `cheatsheet_pages`, `hours_per_week`, `lang`) and the documents with their `kind`.
   Past exams have kind `exam`, their model solutions `exam-solutions`; exercise sheets
   `exercises` and `solutions`.
2. `sources/chunks.yaml`: the pages of each document and which are `flagged` or `scanned`.
3. `course.yaml`: `exam` as the draft has it, and whether `topics` is still the
   placeholder `draft` (then `topic` fields hold candidate slugs).
4. The page texts `sources/text/<doc>/pNNNN.txt` (and `pNNNN.vision.md` where an ingester
   transcribed a scanned page; if a scanned exam page has no transcription yet, Read the
   PDF page yourself, but do not write the transcription: that is the ingester's file).

Search all page texts with Bash, e.g.
`grep -rn -i -E 'klausur|prüfung|punkte|minuten|hilfsmittel' <course>/sources/text`;
Grep and Glob may skip the gitignored course directory.

## 2. With past exams

For every document of kind `exam` (pair it with its `exam-solutions` by title or file
name):

1. Read its page texts; Read the flagged PDF pages (`pages: "<n>"`) to see circuits,
   tables and the points table of the cover page.
2. From the cover page and the instructions: duration, total points, pass mark, allowed
   aids, the MC rules (how many questions, points each, single or multiple answers, Kprim,
   all-or-nothing or partial credit, negative marking).
3. Per task: what is given and asked, the method, its points (the solution's points per
   step add up to them), and the candidate topic (a kebab slug in the course language, the
   way the ingesters name topics).
4. Group the tasks of all exams into **archetypes**: the same kind of task with other
   values or a varied circuit is one archetype. Per archetype: a kebab `id`, a `title` in
   the course language, the `topic`, `share` = its task points over all task points of all
   exams (the MC part excluded), `frequency` = the share of exams that have it, the mean
   `points`, `minutes` = points × `minutes_per_point`, a `description` and its `sources`
   (`{doc, pages}`).
5. Totals: `duration_min`, `points`, `pass_points` (the latest exam's), `minutes_per_point`
   = duration over points, `mc` (`present`, `share` of all points, `count`, `types`,
   `type_mix` over the MC questions, `scoring`, `negative_marking`), `aids`.
6. `topic_weights`: each candidate topic's share of all exam points, MC questions counted
   for their topic.
7. `confidence`: `high` with three or more past exams, `medium` with one or two, `low`
   when the exams are incomplete (pages missing, no points). `basis: past-exams`, `exams`:
   the analysed exam document ids.

Compute every share, mean and ratio with `uv run --frozen studykit calc "<expr>"`; round
shares to two decimals and put the rounding remainder on the largest share so each list
adds up to 1.

## 3. Without past exams

Write a low-confidence profile from the round-1 answers
([templates/exam-profile-no-exams.yaml](templates/exam-profile-no-exams.yaml)):

- `confidence: low`, `basis: user-answers` (`course-description` when the course facts of
  the material describe the exam in detail), no `exams`.
- `format` from `exam_format`: `written` → `written`, `written-mc` → `mixed`, `mc` → `mc`,
  `oral` → `oral`.
- `mc` when the format has an MC part: `present: true`, `share` 0.2 for `written-mc` and 1
  for `mc`, `types: [single, multi, kprim]`, `type_mix` single 0.6, multi 0.25, kprim
  0.15, `scoring: all-or-nothing`, `negative_marking: false` (docs/architecture.md §0),
  unless the material states other rules. `oral` and `written`: `mc: {present: false}`.
- `duration_min`, `points` and `aids` only when the material states them (search the page
  texts for the exam's duration and aids); never guess them.
- Archetypes from the exercise sheets (kinds `exercises`, `solutions`): one per recurring
  kind of task, `share` = its tasks over all tasks; without sheets, from the worked
  examples of the scripts and slides, `share` by pages. At least one archetype.
- `topic_weights` only when the sheets cover the topics evenly enough to say so; else
  leave them out (synthesis falls back to lecture coverage).
- Say in `notes` what is assumed.

## 4. Notation

From all page texts (exams, scripts, slides, sheets), and the flagged pages where a symbol
is drawn rather than typed (underlined phasors are invisible in the text layer):

| Field | Look for |
|---|---|
| `imaginary_unit` | `j` (`jω`, `𝑗`, `1 + j`) or `i` in complex numbers |
| `phasor` | underlined (`\underline{U}`), bold, hat, arrow or plain capitals |
| `phasor_magnitude` | RMS (`U = 230 V` with `u(t) = √2·U·cos…`) or peak phasors |
| `step` | `ε(t)`, `σ(t)`, `u(t)` or `θ(t)` for the unit step |
| `decimal` | `4,7` (comma) or `4.7` (point) |

Add `symbols` for quantities whose letter is not obvious (in the math subset, single-quoted)
and `notes` for index and case conventions. Copy the rules into the profile's `notation`
too. Write `analysis/notation.yaml` from [templates/notation.yaml](templates/notation.yaml);
leave out a rule the material does not show.

## 5. Finish

1. `uv run --frozen studykit validate <course> --paths analysis` reports no error (the lint
   hook already checks each Write; fix SK-SCHEMA-SHARES by recomputing, not by nudging).
2. Return one compact JSON object as your final message, nothing else:

```json
{"profile": "analysis/exam-profile.yaml", "notation": "analysis/notation.yaml",
 "confidence": "medium", "basis": "past-exams", "exams": ["klausur-ws2526"],
 "archetypes": 3, "mc": true, "validate": "ok", "assumptions": "one line, optional"}
```

The synthesis step of /register-new-subject later maps the candidate slugs of `topic` and
`topic_weights` to the course topics; nothing else in the two files changes then.
