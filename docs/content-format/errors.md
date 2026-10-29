# Content errors (SK-codes)

Every check in `studykit lint` and `studykit validate` reports one line:

```
path:line:col SK-CODE message (fix: …)
```

Warnings keep the shape and start the message with `warning:`; they do not fail
`validate` (exit code 0) but the lint hook still shows them. Notes such as a skipped
stage print as `info: …` and are never findings. `--json` gives the same data as
`{path, line, col, code, message, fix, severity}`.

The prefix is the family and names the validation stage
(`docs/architecture.md` §4.3); the suffix names the rule. Route a failure to the step
that owns the file:

| File | Owner |
|---|---|
| `course.yaml` | `/register-new-subject` scaffold and synthesis (main thread) |
| `overview.md`, `summary/`, `exercises/`, `mc/`, `exams/`, `cheatsheet.md`, `figures/` | `author` (one agent per topic and part) |
| `plan.yaml` | `studykit plan` (only `goal` and `note` are hand-written) |
| `analysis/exam-profile.yaml` | `exam-analyst` |
| `sources/manifest.yaml` | `studykit ingest` |

Stages: Structure, Schema, Fences, MC and Math run in `studykit lint` and
`validate --quick`; References, Figures and the later stages run in `validate`;
Coverage only with `validate --release`. Stages whose tools are not there yet
(pandoc filters, figure build, verification, PDF, site) are reported as skipped.

## Structure (SK-STRUCT)

### `SK-STRUCT-MISSING`
**error.** A required file is missing: `course.yaml` in a course directory, `exam.yaml`
in an `exams/<exam-id>/` directory, or a file given to `lint`.
Fix: create the file from its schema in `schemas/`, or remove the stray directory.

### `SK-STRUCT-PATH`
**error.** A file is not where the layout (§2.1) expects it, its path disagrees with its
`topic`, an exam task file is not listed in `exam.yaml`, `mc.md` exists without an `mc:`
part, or a linted file is not inside a course.
Fix: move or rename it, e.g. `summary/rc-filter.md` → `summary/03-rc-filter.md`,
`exercises/<topic>/<ex-id>.md`, `mc/<topic>.md`, `exams/<exam-id>/NN-<task-id>.md`.

### `SK-STRUCT-ID`
**error.** An id does not match its pattern (`ex-…`, `mc-<topic>-NNN`, `<exam>-tN`,
kebab-case topics, docs, slugs and exams; course ids `^[a-z0-9][a-z0-9-]{1,39}$`) or does
not match its file or directory name.
Fix: keep the file name and the `id` equal. Ids are never renamed once published; rename
the file instead, or retire the old id in `course.yaml: retired_ids`.

### `SK-STRUCT-DUP`
**error.** An id is used twice in the course (exercise, MC question, exam task, exam,
topic, plan session, exam task file), or a topic has two summary chapters.
Fix: give the newer item a fresh id; the message names the first occurrence.

### `SK-STRUCT-RETIRED`
**error.** An item uses an id listed in `course.yaml: retired_ids`.
Fix: choose a new id; retired ids are never reused because browser progress is keyed
by id.

### `SK-STRUCT-CYCLE`
**error.** Topic prerequisites in `course.yaml` form a cycle; the message prints it.
Fix: remove one `prereq` entry so the topics can be taught in order.

### `SK-STRUCT-TOPIC`
**error.** A topic id is not one of the course topics: an item's `topic`, a `prereq`,
`focus`, `skip`, `priority` or plan entry, or the topic encoded in an MC id
(`mc-<topic>-NNN`, which must equal the bank's topic in `mc/<topic>.md`).
Fix: use an id from `course.yaml: topics` (the message lists them) or add the topic there.

### `SK-STRUCT-SECTIONS`
**error.** `overview.md` does not have exactly six `##` sections (§2.12). Only position
and count are checked, so the titles may be localised.
Fix: use the six sections in order: big picture, topic map, how the topics connect, exam
at a glance, how to study, prerequisites.

### `SK-STRUCT-POINTS`
**error.** In `exam.yaml`, task points plus MC questions × `points_each` do not add up to
`points`.
Fix: adjust task `points`, the number of questions in `mc.md`, `points_each` or the total.

## Schema (SK-SCHEMA, SK-YAML)

### `SK-SCHEMA-FRONTMATTER`
**error.** A Markdown file does not start with a `---` frontmatter block, or the block is
not closed by a second `---` line.
Fix: start the file with `---`, the YAML fields, and `---`; then the body.

### `SK-SCHEMA-MISSING`
**error.** A required field is missing; the message gives its dotted path.
Fix: add it; `schemas/<kind>.schema.json` lists every field.

### `SK-SCHEMA-UNKNOWN`
**error.** A field is not part of the schema (every model forbids unknown fields, which
also catches typos such as `dificulty`).
Fix: remove it or fix its spelling.

### `SK-SCHEMA-VALUE`
**error.** A value has the wrong type or range. The models are strict: `'10'` is not a
number, `no` is not a boolean (write `false`), dates are `YYYY-MM-DD`, enums accept only
their listed values. Also used for `max_pages` above the course limit, `pass_points`
above `points`, an incomplete plan task and an invalid blocked period.
Fix: follow the hint, which names the allowed values or bounds.

### `SK-SCHEMA-ANSWER`
**error.** An entry in `answers` is neither numeric with a tolerance
(`value` plus `rtol` or `atol`) nor symbolic (`expr` plus `symbols`, no tolerance), or two
answers share a `key`.
Fix:
```yaml
- {key: fg, label: '$f_\mathrm{g}$', value: 1591.55, unit: Hz, rtol: 1.0e-3}
- {key: H, label: '$\underline{H}(s)$', expr: '1/(1+s*R*C)', symbols: [s, R, C]}
```

### `SK-SCHEMA-RUBRIC`
**error.** The rubric points of an exam task do not add up to the task's `points`.
Fix: make `sum(rubric[].points) == points`.

### `SK-SCHEMA-LABEL`
**error.** An answer `label`, rubric `criterion` or summary objective is not plain text
plus inline math: it has Markdown (`*`, `_`, backticks, brackets), TeX outside `$…$`,
display math, an unbalanced `$`, or a line break. These strings are rendered by a small
splitter, not by pandoc.
Fix: `'$|\underline{H}(f_\mathrm{g})|$ in dB'`.

### `SK-YAML-SYNTAX`
**error.** The YAML does not parse (or uses a tag). The position is where the parser
stopped, which can be one line after the real mistake.
Fix: check indentation and quoting; values containing `: ` or ` #`, or starting with
`{`, `[`, `*`, `&`, `!`, `%` or `@`, need single quotes.

### `SK-YAML-ESCAPE`
**error.** A double-quoted scalar contains a backslash. YAML treats it as an escape:
`"\frac"` becomes a form feed plus `rac`.
Fix: single quotes keep backslashes literal: `label: '$\frac{1}{2}$'`.

### `SK-YAML-DQUOTE`
**warning.** A double-quoted scalar without a backslash. It is harmless today but turns
into `SK-YAML-ESCAPE` as soon as someone adds math.
Fix: use single quotes (`'…'`, a literal `'` is written `''`).

### `SK-YAML-BACKSLASH`
**error.** A plain, folded (`>`) or clipping literal (`|`) scalar contains a backslash.
Only single-quoted and `|-` block scalars are allowed to carry TeX.
Fix: `title: '$\omega_\mathrm{g}$ bestimmen'`, or a `|-` block for long text.

### `SK-YAML-CONTROL`
**error.** A control character (C0 except tab and newlines, DEL, C1) in a YAML file or
frontmatter. These usually come from copy and paste and break both parsers.
Fix: delete it.

### `SK-YAML-LATEX`
**error.** `course.yaml` contains LaTeX (a backslash or `$…$`). Course metadata is shown
in places that never render math.
Fix: plain text, e.g. `Ohm` instead of `\Omega`.

### `SK-YAML-DUPKEY`
**error.** A mapping repeats a key. PyYAML would silently keep the last value; the site's
YAML 1.2 parser rejects the file.
Fix: keep one entry per key.

## Fences (SK-BLOCK)

### `SK-BLOCK-UNKNOWN`
**error.** A `:::` block name is not in the closed list: `hint`, `solution`,
`definition`, `theorem`, `example`, `note`, `warning`, `takeaways`, `mcq`,
`explanation`.
Fix: use one of these, or write plain Markdown.

### `SK-BLOCK-FENCE`
**error.** A fence is malformed: wrong colon count (blocks use exactly `:::`, `mcq` uses
exactly `::::` with attributes), no space after the colons, extra words, attributes on a
non-mcq block, an indented fence, a closing fence that does not match its opening, a
closing fence without an open block, or a block that is never closed.
Fix: `::: note` … `:::`; `:::: {.mcq #mc-rc-filter-003 type="single" difficulty="2"}` …
`::::`.

### `SK-BLOCK-BLANK`
**error.** No blank line before an opening fence or after a closing fence (a fence
directly next to another fence is fine).
Fix: insert the empty line.

### `SK-BLOCK-PLACEMENT`
**error.** A block is used in a file kind that does not allow it: `hint` and `solution`
only in exercises and exam tasks; `definition`, `theorem`, `example`, `note`, `warning`,
`takeaways` only in summaries (the cheat sheet allows `definition`, `note`, `warning`);
`mcq` only in MC banks; `explanation` only inside `mcq`. The overview uses no blocks.
Fix: move the content or turn it into plain Markdown.

### `SK-BLOCK-NESTING`
**error.** A block is nested in another one. The only allowed nesting is `explanation`
inside `mcq`.
Fix: close the outer block before opening the next one.

### `SK-BLOCK-HINTS`
**error.** An exercise has fewer than 1 or more than 3 hints (an exam task 0 to 3).
Fix: 1–3 hints, ordered principle → set-up → key intermediate result.

### `SK-BLOCK-SOLUTION`
**error.** An exercise or exam task does not have exactly one `solution`, or something
follows it.
Fix: one `::: solution` block as the last thing in the file.

### `SK-BLOCK-CODE`
**error.** A fenced code block has no language or one outside
`python matlab octave c cpp vhdl verilog systemverilog julia text`, or is never closed.
Fix: ```` ```python ````, or ```` ```text ```` for anything else.

## MC (SK-MCQ)

### `SK-MCQ-ATTR`
**error.** An `mcq` block's attributes are wrong: the id is not `mc-<topic>-NNN`, `type`
is not `single`/`multi`/`kprim`, `difficulty` is not 1–4, `pin-last` is not
`true`/`false`, `source` is not `doc:page`, or there are unknown attributes or classes.
Fix: `:::: {.mcq #mc-rc-filter-003 type="single" difficulty="2" source="uebung-04:2"}`.

### `SK-MCQ-COUNT`
**error.** Wrong number of options: single 3–5, multi 4–6, kprim exactly 4.
Fix: add or remove options.

### `SK-MCQ-KEY`
**error.** The `[x]` marks do not fit the type: single needs exactly one, multi at least
one `[x]` and at least one `[ ]`. (Kprim marks each statement true or false freely.)
Fix: correct the marks; the verifier re-checks the key later.

### `SK-MCQ-WHY`
**error.** An option does not have exactly two paragraphs: the option text, then the
`why` (indented two spaces after a blank line). For a distractor the why names the
mistake it models.
Fix:
```markdown
- [ ] $10\,\mathrm{kHz}$

  Das ist $1/(RC)$: Faktor $2\pi$ vergessen.
```

### `SK-MCQ-EXPLANATION`
**error.** A question has no `::: explanation` block, more than one, or an empty one.
Fix: exactly one explanation after the options, before the closing `::::`.

### `SK-MCQ-ALL-ABOVE`
**error.** An option reads like "all of the above" / „Alle Aussagen sind richtig“.
Options are shuffled, so it cannot work; it also leaks the answer.
Fix: make it a `multi` question.

### `SK-MCQ-PIN-LAST`
**error.** `pin-last="true"` is set, but the last option is not a "none of these" option.
Fix: drop `pin-last`, or make the last option „Keine der Aussagen ist richtig.“

### `SK-MCQ-LETTER`
**error.** A why or the explanation refers to an option by letter („Antwort A“, „Option
(B)“). Letters change with every shuffle.
Fix: name the statement or the quantity instead.

### `SK-MCQ-FORMAT`
**error.** The question does not follow stem → options → explanation: text outside any
`mcq` block in a bank, a malformed option marker (`* [x]`, `-[x]`), unindented text after
an option, the explanation before the options, or text after the explanation.
Fix: options are `- [x] text` / `- [ ] text` in column 1; whys are indented two spaces;
general remarks go into the explanation.

### `SK-MCQ-BIAS`
**warning.** In a bank with at least four single-choice questions, the correct option is
the strictly longest in more than half of them, so length gives the answer away.
Fix: make distractors as long and as specific as the correct option.

## Math (SK-MATH)

### `SK-MATH-DENIED`
**error.** The formula uses a construct from `pandoc/math-denylist.json`: it either fails
in KaTeX or Typst, or converts silently wrong in the PDF (`\tag`, `\color`, `\overset`,
`vmatrix`, `\SI`, …; §2.3). The fix hint is the denylist's replacement. Tokens match
whole control words, so `\R` never matches `\Rightarrow`. Formulas with a denied
construct are not sent to KaTeX.
Fix: use the named replacement.

### `SK-MATH-ENV`
**error.** An environment outside `aligned`, `gathered`, `cases`, `pmatrix`, `bmatrix`,
`Bmatrix` (a `matrix` directly inside `\left…\right` is the allowed determinant form).
Fix: `\begin{aligned}` instead of `align`; a determinant is
`\left|\begin{matrix} a & b \\ c & d \end{matrix}\right|`.

### `SK-MATH-KATEX`
**error.** KaTeX in strict mode (the site's renderer) rejects the formula: an unknown
command, a syntax error, or Unicode letters outside `\text{…}`. Runs only when
`site/node_modules` is installed; otherwise Math reports an info note.
Fix: follow the KaTeX message; words go in `\text{…}`, units in `\mathrm{…}`.

### `SK-MATH-BLOCKMARK`
**error.** A line inside `$$ … $$` starts with `=`, `-`, `+`, `*`, `#`, `>` or `1.`.
Pandoc then reads a heading, list or quote instead of math, on the site and in the PDF.
Fix: keep the operator at the end of the previous line, or start the line with `{}`.

### `SK-MATH-INLINE`
**error.** Inline math is malformed: a space just inside the dollars (`$ x $`), a digit
right after the closing `$` (`$x$5`), or an unmatched `$`. Pandoc would print dollars.
Fix: `$x$`; write a literal dollar as `\$`.

### `SK-MATH-DISPLAY`
**error.** Display math is malformed: `$$` not alone on its line, a blank line inside,
an empty block, or a block that is never closed.
Fix:
```markdown
$$
U_2 = U \cdot \frac{R_2}{R_1 + R_2}
$$
```

### `SK-MATH-HINT-LEAK`
**warning.** A hint contains a number that matches an answer within its tolerance (also
with an SI prefix, e.g. `1,59 kHz` for `1591.55 Hz`).
Fix: give the method or an intermediate result in the hint, never the final value.

## Pandoc filters (SK-PANDOC)

### `SK-PANDOC-FAIL`
**error.** The pandoc filter run failed without a structured finding. Structured
findings from the Lua filters (`guard`, `mcq`, `math`, `refs`) appear under their own
SK-codes in the same format, with the course-relative file and source line.
Fix: run `studykit lint <file>`; if the file is clean, the filter itself has a bug.

## References (SK-REF)

### `SK-REF-MISSING`
**error.** A reference target does not exist: `ex:`, `mc:` (practice-bank questions
only), `topic:`, `exam:`, `src:<doc>` (in `sources/manifest.yaml`), `fig:<slug>`
(`figures/<slug>.py`, or the built-in `topic-map`), plan refs, exam task files and the
MC file in `exam.yaml`, `modeled_on` documents, frontmatter `source`/`sources`
documents, and exam-task archetypes (in `analysis/exam-profile.yaml`).
Fix: use an existing id (`studykit ls <course> --json` lists them) or create the target.

### `SK-REF-SCHEME`
**error.** A link target is not a study-kit reference (a relative path, an unknown
scheme), or a plan ref cannot be resolved. External `https://` and `mailto:` links are
allowed.
Fix: `[…](ex:<id>)`, `(mc:<id>)`, `(topic:<id>)`, `(exam:<id>)`, `(src:<doc>#p=<n>)`.

### `SK-REF-IMAGE`
**error.** An image is not a `fig:` reference. Figures are code (§3.4).
Fix: write `figures/<slug>.py` and embed `![Caption](fig:<slug>)`.

### `SK-REF-FIGURE`
**error.** A figure is not alone in its paragraph, has attributes such as `{width=…}`, or
has an empty caption (the caption doubles as alt text).
Fix: `![Bode-Diagramm des RC-Tiefpasses](fig:rc-bode)` on its own line between blank
lines; the size comes from the figure script.

### `SK-REF-SRC`
**error.** A source link is malformed or its page is outside the document.
Fix: `src:<doc>#p=<page>` with a page from 1 to the document's page count.

## Figures (SK-FIG)

### `SK-FIG-UNUSED`
**warning.** A figure script is never embedded.
Fix: embed it with `![Caption](fig:<slug>)` or delete the script.

## Coverage (SK-COV, `--release` only)

### `SK-COV-OVERVIEW`
**error.** `overview.md` is missing, or it never links a (non-skipped) topic with
`topic:`.
Fix: author the overview (§2.12) and link every topic at least once.

### `SK-COV-SUMMARY`
**error.** A topic has no summary chapter.
Fix: `/regenerate <course> summary --topic <topic>`.

### `SK-COV-EXERCISES`
**error.** A topic has fewer exercises than `targets.exercises_per_topic` (4 when
`auto`) or they all share one difficulty level.
Fix: `/regenerate <course> exercises --topic <topic> --add <n>`.

### `SK-COV-MC`
**error** (count) or **warning** (type mix). A topic's practice bank has fewer questions
than `targets.mc_per_topic` (with `auto`: 10–25 by weight), or lacks a question type the
exam uses.
Fix: `/regenerate <course> mc --topic <topic> --add <n>`.

### `SK-COV-CHEATSHEET`
**error.** The exam allows a cheat sheet, but `cheatsheet.md` is missing.
Fix: `/regenerate <course> cheatsheet`.

### `SK-COV-PLAN`
**error.** `plan.yaml` is missing.
Fix: `studykit plan <course>`.

### `SK-COV-EXAM`
**error.** Fewer mock exams than `targets.mock_exams`.
Fix: `/regenerate <course> exams`, or lower the target.
