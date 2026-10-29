---
name: content-format
description: The study-kit course file format - directory layout, ids, YAML rules, the Markdown dialect (container blocks, MC questions, math subset, links, figures), frontmatter fields per file kind, copy-ready templates and the SK error codes. Use before writing or fixing any file under a course directory.
user-invocable: false
---

# Course content format

The full specification is `docs/architecture.md` §2 (content schema) and §2.3 (dialect).
Every SK code, what triggers it and its fix is in `docs/content-format/errors.md`. The
pydantic models in `src/studykit/model.py` are the schema; their JSON export is in
`schemas/` (`course.schema.json`, `exercise.schema.json`, …). The sample course
`examples/sample-course/` uses every feature and is always valid.

## Finding and checking files

- Courses live in `courses/<id>/` (gitignored) or wherever `STUDYKIT_COURSES_DIR` points;
  CI uses `examples/`. A `<course>` argument is a course id or a directory.
- Grep and Glob may skip gitignored paths. List course files with
  `uv run --frozen studykit ls <course>` (`--kind exercise`, `--json`) and the ids with
  `uv run --frozen studykit index <course> --json` (topics, items with their file, exams,
  figures, quarantined ids). Read files by their explicit path.
- Every Write or Edit of a course file runs the lint hook; it prints findings as
  `path:line:col SK-CODE message (fix: …)`. Fix them at once.
- Check a set of files: `uv run --frozen studykit lint <files…>`; your own files in their
  course context: `uv run --frozen studykit validate <course> --paths <files…>`; the
  whole course: `uv run --frozen studykit validate <course>` (also builds its PDFs).

## Layout

```
<course>/course.yaml  overview.md  cheatsheet.md  plan.yaml
<course>/summary/<nn>-<topic>.md           one chapter per topic, nn = teaching order
<course>/exercises/<topic>/<ex-id>.md      one exercise per file
<course>/mc/<topic>.md                     one MC bank per topic
<course>/exams/<exam-id>/exam.yaml  NN-<task-id>.md  mc.md
<course>/figures/<slug>.py                 figure scripts (figures skill)
<course>/analysis/exam-profile.yaml        archetypes, MC mix (exam analysis)
<course>/checks/  state/  progress/  _history/  _build/   tool output, never hand-edited
```

Any other file in the course is SK-STRUCT-PATH.

## Ids

- Kebab-case ASCII, unique in the course: exercises `ex-…`, MC questions
  `mc-<topic>-NNN` (practice banks count from 001; exam MC uses its own range such as
  101, 201), exam tasks `<prefix>-tN` (`pk1-t1` in `probeklausur-1`), exams
  `probeklausur-N`, figures `<slug>`.
- Ids are never renamed. A deleted item's id goes into `course.yaml: retired_ids`, and a
  retired id is never used again (SK-STRUCT-RETIRED).

## YAML (frontmatter, course.yaml, exam.yaml, plan.yaml)

- No double-quoted scalars (`"\frac"` becomes a form feed): SK-YAML-DQUOTE.
- A value with a backslash is single-quoted or a `|-` block: SK-YAML-BACKSLASH.
- Single-quote a value with `: ` or a leading special character; double a `'` inside.
- `course.yaml` holds no LaTeX at all (SK-YAML-LATEX); no control characters.
- `label`, `objectives` and rubric `criterion` are plain text plus inline `$…$` only.

## Frontmatter per kind

| Kind | Fields (required in bold) |
|---|---|
| summary | **topic**, **title**, objectives (labels), sources `[{doc, pages}]` |
| overview | **title** |
| exercise | **id**, **title**, **topic**, **difficulty** 1-4, **kind** compute/derive/concept/sketch/code, **minutes**, source `{doc, page, relation}`, answers |
| exam task | the exercise fields with **kind: exam-task**, **points**, **archetype**, **rubric** `[{points, criterion}]` summing to points; difficulty and minutes optional |
| MC bank | **topic**, **title** |
| exam MC | **title**, topic optional |
| cheat sheet | **title**, **max_pages** (≤ course limit ≤ 3), priority (topic ids) |
| exam.yaml | **schema: 1**, **id**, **title**, **duration_min**, **points**, **pass_points**, aids (`inherit`), modeled_on, **tasks** (file names), mc `{file: mc.md, points_each}` |

**Answers** (the machine-checkable key, read by the site's answer check and by
`studykit verify`):

- numeric: `{key, label, value, unit, rtol | atol}`; units are plain text (`Hz`, `kHz`,
  `µs`, `Ω`, `°`, `dB`); use `rtol: 5.0e-3` for computed values, `atol` for dB and degrees.
- symbolic: `{key, label, expr: 'U0*R2/(R1 + R2)', symbols: [U0, R1, R2]}` in SymPy syntax.
- Every number a student is asked for gets an answer key; a derivation without a number
  gets none.

## Markdown dialect

pandoc `commonmark_x` without smart quotes, raw HTML or attributes. Write „…" directly.

**Container blocks**, a closed list; a blank line before and after every fence:

| Block | Fence | Allowed in | Rule |
|---|---|---|---|
| hint | `::: hint` | exercise, exam task | 1-3, ordered principle → set-up → key intermediate result; no answer value in a hint (SK-MATH-HINT-LEAK) |
| solution | `::: solution` | exercise, exam task | exactly one, the last block |
| definition, theorem, example, note, warning, takeaways | `::: definition` … | summary (cheat sheet: definition, note, warning) | a first paragraph that is one bold span is the box title |
| mcq | `:::: {.mcq #mc-<topic>-NNN type="single" difficulty="2"}` | `mc/*.md`, `exams/*/mc.md` | exactly 4 colons; the only block with attributes |
| explanation | `::: explanation` | inside mcq | exactly one |

**MC question** (§2.6): the stem, then a loose task list; every option has exactly two
paragraphs, the option text and its `why` (indented two spaces), separated by blank lines:

```markdown
:::: {.mcq #mc-rc-filter-001 type="single" difficulty="1"}
Stem with $math$?

- [x] Correct option

  Why it is right.

- [ ] Distractor

  The mistake that produces it.

::: explanation
Short worked reasoning. Never refer to an option by letter (options are shuffled).
:::
::::
```

- `single`: 3-5 options, exactly one `[x]`. `multi`: 4-6 options, at least one `[x]` and one
  `[ ]`. `kprim`: exactly 4 statements, `[x]` = true.
- Optional attributes: `tags="a,b"`, `source="doc:page"`, `pin-last="true"` (only for a
  final "none of these" option). Never "all of the above" (SK-MCQ-ALL-ABOVE).

**Math** (the subset KaTeX and pandoc → Typst both render):

- Inline `$x$` with no space inside the dollars and no digit right after the closing `$`.
- Display math: `$$` alone on its line, no blank line inside; no line inside may start with
  `=`, `-`, `+`, `*`, `#`, `>` or `1.` (keep `=` at the end of the previous line).
- Units and numbers: `3{,}3\,\mathrm{k\Omega}`, decimal comma `{,}` in German, imaginary
  unit `\mathrm{j}`, phasors `\underline{U}`, subscripts in `\mathrm{…}` (`f_\mathrm{g}`),
  words in `\text{…}`. A course's `analysis/notation.yaml` overrides these defaults
  (`decimal: point`, `imaginary_unit: i`, its symbols). No space command between two
  digits (`10000` or `10^4`, never `10\,000`).
- Environments: `aligned`, `gathered`, `cases`, `pmatrix`, `bmatrix`, `Bmatrix` only.
- Denied (the lint prints the replacement; list in `pandoc/math-denylist.json`):
  `\overset`, `\stackrel`, `\xrightarrow`, `\underset`, `\color`, `\textcolor`, `\tag`,
  `\label`, `\ref`, `\eqref`, `vmatrix`, `array`, bare `matrix`, `\big` and friends, `\|`,
  `\mathsf`, `\operatorname*`, `\limits`, `\SI`, `\qty`, `\si`, `\pu`, `\R`, `\N`, `\ce`,
  `\def`, `\newcommand` and other macros. Non-ASCII letters only inside `\text{…}`.
- A Laplace correspondence is `\;\circ\!-\!\bullet\;`; an evaluation bar
  `\left.…\right|_{t=0}`; a norm `\lVert x \rVert`.

**Links and figures:**

- Course links `[text](ex:<id>)`, `(mc:<id>)` (practice banks only), `(topic:<id>)`,
  `(exam:<id>)`, `(src:<doc>#p=12)`; every target must exist. External `https://` links
  need descriptive text; no bare URLs.
- Figures: `![Caption that doubles as alt text](fig:<slug>)` alone in its paragraph, no
  attributes. `fig:topic-map` exists in every course without a script.

**Other rules:** subtasks are `**a)**` paragraphs; code blocks are fenced with exactly one
language of `python matlab octave c cpp vhdl verilog systemverilog julia text`; no H1 in a
body, no footnotes, no `{…}` attributes, no raw HTML; in a pipe table no `|` inside inline
math (`\lvert … \rvert`, `\mid`); keep a hyphenated word on one line.

## Templates

Copy-ready files taken from the sample course; each passes `studykit lint` in the sample
course. Change ids, topics and values, keep the structure.

| Template | File it becomes |
|---|---|
| [course.yaml](templates/course.yaml) | `course.yaml` |
| [overview.md](templates/overview.md) | `overview.md` (the six H2 sections in this order) |
| [summary.md](templates/summary.md) | `summary/<nn>-<topic>.md` |
| [exercise.md](templates/exercise.md) | `exercises/<topic>/<ex-id>.md`, numeric answers |
| [exercise-symbolic.md](templates/exercise-symbolic.md) | `exercises/<topic>/<ex-id>.md`, a symbolic answer |
| [mc-bank.md](templates/mc-bank.md) | `mc/<topic>.md` (single, multi with pin-last, Kprim) |
| [exam/exam.yaml](templates/exam/exam.yaml) | `exams/<exam-id>/exam.yaml` |
| [exam/01-pk2-t1.md](templates/exam/01-pk2-t1.md) | `exams/<exam-id>/NN-<task-id>.md` |
| [exam/mc.md](templates/exam/mc.md) | `exams/<exam-id>/mc.md` |
| [cheatsheet.md](templates/cheatsheet.md) | `cheatsheet.md` |
| [plan.yaml](templates/plan.yaml) | `plan.yaml` (written by `studykit plan`; edit only goal and note) |
| [figure.py](templates/figure.py) | `figures/<slug>.py` |
| [exam-profile.yaml](templates/exam-profile.yaml) | `analysis/exam-profile.yaml` |

## SK codes

The prefix names the validation stage: SK-STRUCT (layout, ids, points), SK-SCHEMA and
SK-YAML (frontmatter), SK-BLOCK (fences), SK-MCQ (MC rules), SK-MATH (math subset),
SK-REF (links, figures, sources), SK-PANDOC, SK-FIG, SK-VER (verification ledger), SK-PDF,
SK-SITE, SK-COV (coverage, `--release`), SK-PROGRESS and SK-PLAN. Look up the code in
`docs/content-format/errors.md` before fixing; the fix line names the remedy. Common ones:

| Code | Usual fix |
|---|---|
| SK-BLOCK-FENCE, SK-BLOCK-BLANK | exact fence form; blank lines around every fence |
| SK-MCQ-WHY | every option needs its second paragraph |
| SK-MCQ-LETTER | the explanation names the option's content, never its letter |
| SK-MATH-DENIED | use the replacement the message names |
| SK-MATH-BLOCKMARK | move a leading `=` or `-` to the end of the previous line |
| SK-YAML-BACKSLASH | single-quote the value |
| SK-REF-MISSING | link only ids that exist (`studykit index <course> --json`) |
| SK-STRUCT-POINTS | task and MC points must add up to `points` in exam.yaml |
| SK-SCHEMA-RUBRIC | rubric points sum to the task's points |
