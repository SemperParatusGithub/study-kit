---
name: authoring
description: How study-kit writes course content - the shared quality rules for every part, id handling, the fix round after a verifier dispute, and the result JSON an author returns. Each part (overview, summary, exercises, mc, exam, cheatsheet, plan) has its own procedure under parts/; read the one you were given. Use when writing, extending, replacing or fixing course content.
user-invocable: false
---

# Authoring course content

One author call covers one (topic, part), or the overview, a mock exam, the cheat sheet or
the plan. Read the procedure of your part before writing anything:

| Part | Procedure | Files |
|---|---|---|
| overview | [parts/overview.md](parts/overview.md) | `overview.md` |
| summary | [parts/summary.md](parts/summary.md) | `summary/<nn>-<topic>.md` and its figures |
| exercises | [parts/exercises.md](parts/exercises.md) | `exercises/<topic>/*.md` and their figures |
| mc | [parts/mc.md](parts/mc.md) | `mc/<topic>.md` |
| exam | [parts/exam.md](parts/exam.md) | `exams/<exam-id>/` |
| cheatsheet | [parts/cheatsheet.md](parts/cheatsheet.md) | `cheatsheet.md` |
| plan | [parts/plan.md](parts/plan.md) | `plan.yaml` (goals and notes only) |

The file format is in the content-format skill; figures follow the figures skill.

## Before writing

1. Read `course.yaml` (language, topics, weights, focus, skip, exam format, targets) and,
   when they exist, `analysis/exam-profile.yaml` (archetypes, MC mix, scoring),
   `analysis/notation.yaml` (j or i, phasor style), `sources/outline.md` and the notes in
   `sources/notes/` of the chunks the outline lists for your topic (formulas, examples,
   exercise archetypes and `src:` page links to cite). List files with
   `uv run --frozen studykit ls <course>` and ids with
   `uv run --frozen studykit index <course> --json`.
2. Read what the part already has. Existing items whose id survives keep their id and file
   name; only their content may change.
3. Read the summary chapter of your topic (and of its prerequisites) so names, symbols and
   conventions match across parts.

## Quality rules (every part)

- **Language:** all course text in `course.lang`; field names, ids and code in English.
  Notation follows `notation.yaml` and the summary of the topic (the same symbol for the
  same quantity everywhere).
- **Numbers are computed, never guessed.** Every value in a statement, solution, answer
  key or distractor comes from Python: `uv run --frozen studykit calc "<expr>"`
  (`--subs R=2.2e3`, `--units`) or a short `uv run --frozen python -c "…"` with
  NumPy/SymPy. Round answer values to 4-5 significant digits; numeric keys get
  `rtol: 5.0e-3`, dB and degree keys an `atol`.
- **Self-contained:** a student can solve each item from its statement and the summary;
  every given value has a unit; every asked quantity has an answer key (or is a sketch or
  derivation without one).
- **Solutions** show every step a grader expects: the approach, the formula, the numbers
  inserted, the result with unit, one sentence of interpretation where it helps.
- **Hints** form a ladder (principle → set-up → key intermediate result), never contain an
  answer value (SK-MATH-HINT-LEAK) and never the full solution.
- **Original work:** when past exams or exercise sheets are the source, change values,
  circuits and wording; model the archetype, not the item. Cite the source document in
  `source: {doc, page, relation}` and link lecture pages with `src:<doc>#p=<n>`.
- **Figures are code:** every circuit, plot and phasor diagram is a `figures/<slug>.py`
  script; render it and look at the PNG (figures skill). No figure is decoration only.
- **Ids:** never rename one; new items take the next free number or a new descriptive id
  that is not in `retired_ids`; an item you delete is reported in `removed` so its id is
  retired in `course.yaml`.
- **Scope:** write only the files of your part and their figure scripts. Never edit
  `course.yaml`, `checks/`, `state/`, `progress/`, `_build/` or `_history/`, nor another
  part's files.

## Finishing

1. `uv run --frozen studykit fig build <course> --only <slug>` for each figure you wrote,
   then look at `<course>/_build/figures/<slug>.png`.
2. `uv run --frozen studykit validate <course> --paths <your files…>` must report no error
   in your files; fix your warnings too unless the warning is expected (say why).
3. Return one compact JSON object as your final message, nothing else:

```json
{"part": "mc", "topic": "rc-filter", "files": ["mc/rc-filter.md"],
 "added": ["mc-rc-filter-011"], "changed": ["mc-rc-filter-004"], "removed": [],
 "figures": [], "validate": "ok", "warnings": [], "notes": "one line, optional"}
```

`validate` is `ok` or the remaining finding lines. The caller judges success from the
files and from validate, not from this report.

## Fix round (after a verifier dispute)

You get an item id and the verifier's computed values (never its check script).

1. Re-derive the item yourself from its statement, in Python, without looking at the
   verifier's numbers first; then compare all three: your result, the key, the verifier.
2. If the key or solution is wrong: fix the answer value, the solution and every place that
   uses the value (another subtask, a distractor's `why`, the explanation). If the
   statement is ambiguous or under-specified: fix the statement. Keep the id.
3. If the key is right and the verifier is wrong, change nothing and return
   `{"item": "<id>", "verdict": "key-correct", "reason": "…the step the verifier got wrong…"}`.
4. Otherwise return `{"item": "<id>", "verdict": "fixed", "files": […], "what": "…"}` after
   `studykit validate <course> --paths <file>` is clean.
