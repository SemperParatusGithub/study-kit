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
| `course.yaml` | `/register-new-subject` scaffold and synthesis (main thread); `retired_ids` also by `/regenerate` |
| `overview.md`, `summary/`, `exercises/`, `mc/`, `exams/`, `cheatsheet.md`, `figures/` | `author` (one agent per topic and part, started by `/regenerate` and `/verify`) |
| `plan.yaml` | `studykit plan` (only `goal` and `note` are written by Claude afterwards) |
| `analysis/exam-profile.yaml`, `analysis/notation.yaml` | `exam-analyst` |
| `sources/manifest.yaml`, `sources/chunks.yaml`, `sources/raw/`, `sources/text/` | `studykit ingest` |
| `sources/notes/<chunk>.md` | `ingester` (one agent per chunk) |
| `sources/outline.md` | `/register-new-subject` synthesis (main thread) |
| `checks/`, `state/verify/` | `verifier` (blind) and `studykit verify` |
| `progress/` | `studykit progress import`, `log` and `report` |

The `author` and `verifier` agents and the `studykit plan`, `verify` and `progress` commands
come from Phase 5; `studykit ingest`, `studykit pipeline`, the `ingester` and
`exam-analyst` agents, `/register-new-subject` and `/add-material` from Phase 6.

Stages: Structure, Schema, Fences, MC, Math and Pandoc run in `studykit lint` and
`validate --quick`; References, Figures, Verification and PDF run in `validate`; Site and
Coverage only with `validate --release`. A stage is reported as skipped when its tools are
missing (pandoc or typst in `.tools/bin`, `site/node_modules`).

The Pandoc stage runs the Lua filter set that builds the site and the PDFs on every file
the earlier stages left without errors (at file scope in `lint` and `--quick`, where targets
missing from the course are not reported). Its findings use the codes below: a rule that
both the filter and a stage check has one code (e.g. `SK-REF-FIGURE`, `SK-BLOCK-FENCE`,
`SK-MCQ-KEY`), and the rules only the filter sees have their own (`SK-BLOCK-RAW`,
`SK-BLOCK-MARKDOWN`, `SK-REF-LINK`, `SK-MATH-TYPST`). The website shows the same findings as
an error card on the page.

## Structure (SK-STRUCT)

### `SK-STRUCT-MISSING`
**error.** A required file is missing: `course.yaml` in a course directory, `exam.yaml`
in an `exams/<exam-id>/` directory, or a file given to `lint`. A missing `overview.md`,
`plan.yaml` or (when the exam allows one) `cheatsheet.md` is a warning while the course is
being authored and an error with `--release`.
Fix: create the file from its schema in `schemas/`, or remove the stray directory;
`plan.yaml` comes from `studykit plan <course>` (then write the session goals).

### `SK-STRUCT-PATH`
**error.** A file is not where the layout (§2.1) expects it, its path disagrees with its
`topic`, an exam task file is not listed in `exam.yaml`, `mc.md` exists without an `mc:`
part, the `chunk` of `sources/notes/<chunk>.md` is not its file name, or a linted file is
not inside a course. The filter reports it too when it cannot tell
the file kind from the path it was given.
Fix: move or rename it, e.g. `summary/rc-filter.md` → `summary/03-rc-filter.md`,
`exercises/<topic>/<ex-id>.md`, `mc/<topic>.md`, `exams/<exam-id>/NN-<task-id>.md`.

### `SK-STRUCT-ID`
**error.** An id does not match its pattern (`ex-…`, `mc-<topic>-NNN`, exam tasks
`<prefix>-tN` with any kebab prefix such as `pk1-t1`,
kebab-case topics, docs, slugs and exams; course ids `^[a-z0-9][a-z0-9-]{1,39}$`) or does
not match its file or directory name (also the `course` of `sources/manifest.yaml`).
Fix: keep the file name and the `id` equal. Ids are never renamed once published; rename
the file instead, or retire the old id in `course.yaml: retired_ids`.

### `SK-STRUCT-DUP`
**error.** An id is used twice in the course (exercise, MC question, exam task, exam,
topic, plan session, exam task file; a source document's id, file or sha256, a chunk, an
archetype), or a topic has two summary chapters.
Every occurrence is reported and names the others, so `lint` flags the file that
introduced the duplicate. Fix: give the newer item a fresh id; existing ids are never
renamed.

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

### `SK-STRUCT-PLAN`
**error** (a session) or **warning** (the exam date). `plan.yaml` no longer fits the exam in
`course.yaml`: a session is on or after the exam day (error), or the plan's `exam_date` is
not the exam date (warning: the plan was made for another date).
Fix: `studykit plan <course>` replans from today; done sessions and the goals of unchanged
sessions are kept.

### `SK-STRUCT-DRAFT`
**error.** `course.yaml` has `status: ready` but still lists the placeholder topic `draft`
that `studykit ingest init` writes into a draft course.
Fix: write the real topics (the synthesis step of `/register-new-subject`), or keep
`status: draft` until the course is complete.

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

### `SK-SCHEMA-SHARES`
**error.** Shares in `analysis/exam-profile.yaml` do not add up to 1 (within 0.02): the
archetypes' `share` of the exam's points, `mc.type_mix` or `topic_weights`.
Fix: recompute the shares from the past exams' points (`studykit calc`) so each list adds
up to 1.

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
**error.** A double-quoted scalar without a backslash. Double quotes are never allowed
(architecture §2.1): the scalar turns into `SK-YAML-ESCAPE` as soon as someone adds math.
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
YAML parser (for `course.yaml` and `plan.yaml`) rejects the file.
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
**error.** A block is nested in another one, or (reported by the filter) sits inside a
list. The only allowed nesting is `explanation` inside `mcq`.
Fix: close the outer block before opening the next one.

### `SK-BLOCK-HINTS`
**error.** An exercise or exam task has fewer than 1 or more than 3 hints.
Fix: 1–3 hints, ordered principle → set-up → key intermediate result.

### `SK-BLOCK-SOLUTION`
**error.** An exercise or exam task does not have exactly one `solution`, or something
follows it.
Fix: one `::: solution` block as the last thing in the file.

### `SK-BLOCK-CODE`
**error.** A fenced code block has no language or one outside
`python matlab octave c cpp vhdl verilog systemverilog julia text`, or is never closed.
Fix: ```` ```python ````, or ```` ```text ```` for anything else.

### `SK-BLOCK-TABLE`
**error.** A `|` inside inline math or inline code on a pipe-table row (the header row or
a row below the `|---|` delimiter). Pandoc splits a row at every `|` before it reads math
or code, and nothing warns: `| $|\underline{Z}|$ | 1 |` becomes the cells `$` and
`\underline{Z}`, and in the header row the whole table becomes a paragraph. `\|` is an
escaped cell border there, so `$\|x\|$` turns into `|x|`. Tables in block quotes and list
items count too; lines right after a paragraph line (no blank line between) are no table
for pandoc and are not reported.
Fix: in math `\lvert\underline{Z}\rvert` (absolute value), `\lVert x \rVert` (norm),
`P(A \mid B)`; in code escape it, `` `a\|b` ``, which shows `a|b`.

### `SK-BLOCK-HYPHEN`
**warning.** A line ends in a letter and a hyphen and the next line of the paragraph
starts with a letter: `[RC-` / `Tiefpass](topic:rc-filter)`. Markdown joins the lines with a
space, so the page shows „RC- Tiefpass“. A next line starting with „und“, „oder“ (also
„und/oder“), „u.“, „sowie“, „bis“, „wie“, „noch“, „als“, „bzw.“, „beziehungsweise“,
„resp.“, „respektive“, „versus“, „vs.“, „and“, „or“, „nor“ or „to“ is a suspended compound
(„Ein- und Ausgang“, „sowohl Ein- als auch Ausgang“) and not reported.
Fix: keep the hyphenated word on one line, e.g. move `[RC-Tiefpass](topic:rc-filter)` to
the next line as a whole.

### `SK-BLOCK-RAW`
**error.** Raw HTML (`<br>`, `<span …>`, an `<!-- … -->` comment) or another raw block or
inline in the body. pandoc 3.13 still reads raw HTML although the dialect turns it off, so
the filter rejects it on every target (§2.3); it is reported by the Pandoc stage.
Fix: use Markdown, math or a container block; delete HTML comments.

### `SK-BLOCK-MARKDOWN`
**error.** Markdown the dialect does not allow (§2.3): an H1 heading in the body, a heading
with attributes, a footnote, or `{…}` attributes on a span (`[text]{.x}`), on inline code
(`` `a`{.x} ``) or on a table (a `{…}` line above it). The HTML writer copies attributes onto
the element, so an `onclick` would reach the page; `mcq` is the only block with attributes.
Reported by the Pandoc stage.
Fix: start the body at `##` (the title comes from the frontmatter), say a footnote in the
text or a `::: note` box, and remove the `{…}`.

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
the strictly longest in more than half of them, so length gives the answer away; or, after
the deterministic PDF shuffle (seeded by the question id, as in `mcq.lua`), one letter is
the correct answer in more than half of them.
Fix: make distractors as long and as specific as the correct option; for a skewed letter,
move the correct option to another place in the source of some of the listed questions.

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
command, a syntax error, or Unicode letters outside `\text{…}`. The KaTeX check runs only
when `site/node_modules` is installed (otherwise Math reports an info note); the filter
reports non-ASCII characters outside `\text{…}` under this code too, so they show up
without KaTeX. The website reports a formula KaTeX rejects in the body or in a frontmatter
label under this code.
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

### `SK-MATH-THINSPACE`
**error.** A space command stands between two digits: `10\,000` as a thousands separator
or `1\,5` as a mistyped decimal comma. The same holds for `\:` `\;` `\>` `\ ` `~`
`\thinspace` `\medspace` `\thickspace`, also in a group (`10{\,}000`). Both engines set a
gap, so the number reads as two („1 5 V“), and the Typst decimal-comma fix-up only
rewrites `{,}`. Reported by the Math stage and, with the same code and token rule, by
`math.lua`.
Fix: write `10000`, `10^4`, or `{,}` for a decimal comma (`1{,}5\,\mathrm{V}`).

### `SK-MATH-HINT-LEAK`
**warning.** A hint contains a number that matches an answer within its tolerance (also
with an SI prefix, e.g. `1,59 kHz` for `1591.55 Hz`).
Fix: give the method or an intermediate result in the hint, never the final value.

### `SK-MATH-TYPST`
**error.** pandoc cannot convert the formula to Typst without a warning, so the PDF would
fail on it. `math.lua` converts every formula on its own, also in the lint's json run, and
reports the first warning. Reported by the Pandoc stage.
Fix: stay within the math subset of `docs/architecture.md` §2.3 (allowed environments,
no denied constructs); rewrite the part the message names.

## Pandoc filters (SK-PANDOC)

### `SK-PANDOC-FAIL`
**error.** The pandoc run failed without a structured finding (pandoc itself failed, or
the filter crashed), or the filter ran without the metadata `studykit.pandoc` passes:
no `-M sk-file` or `sk-index`, an index it cannot read, an unsupported language, a bad
`sk-scope` or `sk-solutions`, an `sk-figdir` outside the working directory, or no
`pandoc/math-denylist.json`. Filter findings use the same codes as the stages, with the
course-relative file and source line.
Fix: run `studykit lint <file>`; if the file is clean, run pandoc through `studykit.pandoc`
(or `studykit render`); otherwise the filter itself has a bug.

## References (SK-REF)

The References stage runs in `validate`. The filter checks links, images and figures in
`lint` and `validate --quick` as well, with the same codes; a missing target is reported
there only in a full run.

### `SK-REF-MISSING`
**error.** A reference target does not exist: `ex:`, `mc:` (practice-bank questions
only), `topic:`, `exam:`, `src:<doc>` (in `sources/manifest.yaml`), `fig:<slug>`
(`figures/<slug>.py`, or the built-in `topic-map`), plan refs, exam task files and the
MC file in `exam.yaml`, `modeled_on` documents, frontmatter `source`/`sources`
documents, exam-task archetypes (in `analysis/exam-profile.yaml`; without a profile
the archetypes are not checked), the documents of `sources/chunks.yaml` and the profile's
`exams`, and the profile's archetype topics and `topic_weights` (course topics; not
checked while `course.yaml` has only the placeholder topic `draft`).
Fix: use an existing id (`studykit ls <course> --json` lists them) or create the target.

### `SK-REF-SCHEME`
**error.** A link target is not a study-kit reference (a relative path, an unknown
scheme, `fig:` as a link), or a plan ref cannot be resolved. External `https://` and
`mailto:` links are allowed (see `SK-REF-LINK`).
Fix: `[…](ex:<id>)`, `(mc:<id>)`, `(topic:<id>)`, `(exam:<id>)`, `(src:<doc>#p=<n>)`.

### `SK-REF-LINK`
**error.** A bare URL: a URL or `www.…` in the text, an autolink `<https://…>`, or a link
whose text is its own URL (or e-mail address); or a link with `{…}` attributes. Reported by
the Pandoc stage.
Fix: `[descriptive text](https://…)`, and no `{…}` after the link.

### `SK-REF-IMAGE`
**error.** An image is not a `fig:` reference. Figures are code (§3.4).
Fix: write `figures/<slug>.py` and embed `![Caption](fig:<slug>)`.

### `SK-REF-FIGURE`
**error.** A figure is not alone in its paragraph, has attributes such as `{width=…}`, or
has an empty caption (the caption doubles as alt text). Inline math in the caption is
fine: the page and the PDF render it, and the PDF's alt text reads it as plain text
(`$\underline{U}_C$` → U_C, `$1{,}5\,\mathrm{k\Omega}$` → 1,5 kΩ).
Fix: `![Bode-Diagramm des RC-Tiefpasses](fig:rc-bode)` on its own line between blank
lines; the size comes from the figure script.

### `SK-REF-SRC`
**error.** A source link is malformed or its page is outside the document.
Fix: `src:<doc>#p=<page>` with a page from 1 to the document's page count.

### `SK-REF-CHUNK`
**error** or **warning.** The ingest files disagree. Errors: `sources/notes/<chunk>.md`
names a chunk that `sources/chunks.yaml` does not have, or its `doc` or `pages` differ from
the chunk's. Warnings: the notes were written for another version of the document
(`source_sha256` is not the chunk's `sha256`), or a chunk was planned from an older version
than `sources/manifest.yaml` lists (the PDF changed since).
Fix: copy `doc`, `pages` (`first-last`) and `sha256` (as `source_sha256`) from the chunk in
`sources/chunks.yaml`; for a changed document run `studykit ingest extract <course>` and
read its chunks again (`studykit pipeline status <course>` lists them).

## Figures (SK-FIG)

### `SK-FIG-BUILD`
**error.** A figure script (or a builtin such as the topic map) does not build: it raises,
runs longer than 60 s, has no alt text, or its SVG fails validation (colours outside the
palette, text not converted to paths, text drawn in a colour below 4.5:1 on the page, too
large). Only `fg`, `muted` and `c1` are readable as text; draw labels in `fg` and let a
coloured line or marker be the key.
Fix: run `studykit fig build <course> --only <slug>`, fix the script and look at the PNG.

### `SK-FIG-UNUSED`
**warning.** A figure script is never embedded.
Fix: embed it with `![Caption](fig:<slug>)` or delete the script.

## Verification (SK-VER)

The stage reads the verification ledger `state/verify/<id>.json` of every exercise, exam
task and MC question (`docs/architecture.md` §2.10); it runs no checks itself
(`studykit verify` does). Findings point at the item's file and line. Without
`--release` it reports only what needs attention (disputed, quarantined, stale, broken or
orphaned entries) and notes how many items are verified; `--release` adds every item that
is not verified and every numeric question without a check script.

### `SK-VER-DISPUTED`
**warning; error with `--release`.** The verifier's check disagrees with the item's key
(a number outside its tolerance, a different MC key, a Kprim statement judged the other
way, a distractor that does not follow from its mistake, an ambiguous question).
Fix: the author fixes the item with the verifier's numbers from the ledger
(`studykit verify <course> <id> --status --show-key` shows them), then
`studykit verify <course> <id>` runs the check again. A dispute on the second fix quarantines
the item.

### `SK-VER-QUARANTINED`
**warning.** The item stayed disputed after two author fix rounds (or was quarantined by
hand with `--quarantine`). It is hidden from the website and the PDFs and listed in
`state/verify/report.md`.
Fix: rewrite the item and run `studykit verify <course> <id>`; it shows again once its
check passes.

### `SK-VER-STALE`
**warning.** The item changed since it was checked: the content hash in its ledger entry
no longer matches the file (an exercise or exam task) or the question's lines.
Fix: run `studykit verify <course> <id>` again (the check is reused).

### `SK-VER-UNVERIFIED`
**warning, `--release` only.** The item has no ledger entry, or its last check did not run
to a result (the script failed, a key is missing) or two methods disagree.
Fix: `studykit blind <course> <id>`, let the verifier write `checks/<id>.py` or `.json`,
then `studykit verify <course> <id>`.

### `SK-VER-CHECK`
**warning, `--release` only.** A numeric MC question (single or multi, every option a
number with an optional unit) has no `checks/<id>.py`. Numeric questions are checked with
`mc_numeric` (§2.6), which also proves that every distractor follows from its mistake.
Fix: the verifier writes `checks/<id>.py` ending with `mc_numeric(correct=…, options=…,
mistakes=…)`.

### `SK-VER-LEDGER`
**error.** A ledger file under `state/verify/` is not valid JSON or does not match
`schemas/verify.schema.json`. Ledger files are written by `studykit verify` only.
Fix: delete it with `studykit verify <course> <id> --clear` and run verify again.

### `SK-VER-ORPHAN`
**warning.** A ledger entry or a check file names an id the course does not have (an item
was renamed or deleted). Second methods `checks/<id>.<tag>.py` and the planned formula
audits `checks/sum-<topic>.py` are not orphans.
Fix: `studykit verify <course> orphans --clear` removes the ledger entries; rename or
delete the check file.

## PDF (SK-PDF)

Every full `validate` builds the course's PDFs as `studykit pdf` does, into `_build/pdf`
with its manifest, using the figures the Figures stage built; `validate --quick` and `lint`
never do. It runs in every full validate
rather than only with `--release` because it is cheap and finds what only Typst sees while
the author is still on the file: a document whose inputs did not change is reused by its
digest, so after an edit only the documents that contain the file are rebuilt (Typst
compiles all nine PDFs of the sample course in about a second), and a formula Typst cannot
set, a warning or a cheat sheet over its page limit shows up at once instead of at release
time. With `--paths` only the documents built from those files are built. The stage is
skipped with a note when pandoc or typst is missing from `.tools/bin`, when the course lies
outside the repository (Typst reads only files below it) and while earlier stages report
errors (the PDFs are built from checked files). A document that fails keeps its previous PDF
but leaves the manifest, so the site links no PDF that does not match the course.

A problem is reported at the course file it comes from where that can be known: for a Typst
diagnostic in the assembled `_build/typ/<doc>.typ`, the file and line of the exercise,
question, task or chapter it sits in; otherwise the file that defines the document
(`overview.md`, `cheatsheet.md`, `plan.yaml`, `exams/<exam>/exam.yaml`), else `course.yaml`.
A finding of the filter set in the PDF's pandoc run keeps its own code.

### `SK-PDF-COMPILE`
**error.** Typst cannot compile a document. The message names the PDF, Typst's error and
its position in `_build/typ/<doc>.typ` (or in `typst/studykit.typ`). Typical causes are a
figure whose SVG was never built (`file not found`) and math that converts to Typst but
does not compile there.
Fix: look at that line of the `.typ` file and rewrite the construct in the course file; run
`studykit fig build <course>` for a missing figure. An error inside `typst/studykit.typ` is a
bug in the house library, not in the course.

### `SK-PDF-WARNING`
**error.** Typst or pandoc printed a warning while building a document. Every warning fails
the PDF (`docs/architecture.md` §3.3), so no document ships with a formula pandoc could not
convert or a font Typst had to replace.
Fix: change the construct the warning names; pandoc's messages are in
`_build/logs/<doc>.json`.

### `SK-PDF-CHEATSHEET`
**error.** The cheat sheet has more pages than its limit even at density 4 (7 pt). The limit
is `min(3, course.yaml cheatsheet.max_pages, max_pages)`, so more than 3 pages is never
allowed. Reported at the `max_pages` line of `cheatsheet.md`, with how far it overflows and
its largest sections; the previous `cheatsheet.pdf` stays in place.
Fix: condense it, in this order: derivations, duplicate examples, prose, then the
lowest-priority topics. `studykit cheatsheet fit <course> --json` measures the overflow and
the height of each section in pages (exit code 3 while it does not fit).

### `SK-PDF-BUILD`
**error.** A document could not be built for another reason: the course files do not
assemble into it (an exam task file is missing), pandoc failed without a finding, or the
build itself stopped.
Fix: run `studykit pdf <course> <doc>` and fix the first error it prints.

## Site (SK-SITE, `--release` only)

With `--release`, validate builds the website as `just build` does (`STUDYKIT_STRICT=1`)
for this course alone: `STUDYKIT_COURSES_DIR` is a temporary directory with a link to the
course, so other courses next to it never fail its run. The build goes into a temporary
`--outDir` (so `site/dist` and `site/public` stay untouched); then Pagefind runs over it,
`pnpm -C site check` checks the site's types, and the link check runs. Content problems that
only the build finds keep their own codes (`SK-FIG-BUILD`, `SK-MATH-KATEX`, …) at the
course's files. The stage is skipped with a note when `pnpm`, `node` or `site/node_modules`
is missing, for `--paths`, and while earlier stages report errors (the strict build would
stop on them).

### `SK-SITE-BUILD`
**error.** The strict `astro build` (or Pagefind after it) failed without printing a
content finding: a broken page template, a loader crash, a missing tool. Reported at the
course's `course.yaml`, with the last lines of the build output.
Fix: run `STUDYKIT_COURSES_DIR=<dir> just build <course>` and fix the first error it
prints; a site bug goes to the site code, not the course.

### `SK-SITE-CHECK`
**error.** `astro check` reports a type error in the site code (path under `site/`), or
fails without one while the build passed (reported at `site`, with the last output lines).
It runs without `STUDYKIT_STRICT`, so a content problem shows as the build's finding, not
here; this is a bug in `site/src`.
Fix: `pnpm -C site check` shows the context.

### `SK-SITE-LINK`
**error** (warning for a lecture PDF under `/c/<course>/src/` or `/pdf/` that the site
serves from course files). A link or `#anchor` in a built page points nowhere. The path
names the page in the built site: `dist/c/<course>/summary/<topic>/index.html` is the page
`/c/<course>/summary/<topic>/`. `studykit check-links site/dist` reports the same after
`just build`.
Fix: fix the link in the source file of that page (`ex:`, `mc:`, `topic:`, `exam:`,
heading anchors), or build the page it points to.

## Coverage (SK-COV, `--release` only)

### `SK-COV-OVERVIEW`
**error.** `overview.md` never links a (non-skipped) topic with `topic:`.
Fix: link every topic at least once.

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
exam uses: a type with a share in `analysis/exam-profile.yaml` `mc.type_mix` (without a
profile mix, every type), limited to `course.yaml` `exam.mc.types`.
Fix: `/regenerate <course> mc --topic <topic> --add <n>`.

### `SK-COV-EXAM`
**error.** Fewer mock exams than `targets.mock_exams`, or a mock exam whose `points` or
`duration_min` is more than 10 % away from the real exam in `course.yaml: exam`.
Fix: `/regenerate <course> exams`, or lower the target; scale the mock exam's tasks to the
real exam's points and time.

## Progress (SK-PROGRESS, `studykit progress`)

These codes are not validate stages: `studykit progress import` reports them for a browser
export (and for `progress/state.json`, the merged state it keeps), `progress log` for an
examiner result, and `progress report` and `studykit status` when the files under
`progress/` do not read. Nothing is written while any is reported. For an import the
position is the line of the entry's key in the file; for `progress log` it is the
`--json-line` argument or the stdin line.

### `SK-PROGRESS-FILE`
**error.** The file cannot be read, is not JSON, or has no `items` object, so it is not a
study-kit progress export.
Fix: use the file the site's Export button downloads (progress page),
`studykit-progress-<course>-<date>.json`.

### `SK-PROGRESS-SCHEMA`
**error.** The export's `schema` is not `studykit-progress/1`: a newer site wrote it (update
study-kit), or it is an unversioned document from before the schema (import it on the site
once and export it again; the site migrates it).
Fix: `git pull && uv sync`, or re-export from the site.

### `SK-PROGRESS-COURSE`
**error.** The export names no course, or another course than the one it is imported into.
Fix: import it into the course it names, or export the right course's progress page.

### `SK-PROGRESS-ENTRY`
**error.** An entry does not validate against `schemas/progress.schema.json`
(`studykit.model.Progress`), or a timestamp is not ISO 8601 in the form the site writes
(`Date.toISOString()`). The site drops such entries when it reads or imports a document, so
an export it wrote never has one.
Fix: export the progress again on the site instead of editing the file by hand.

### `SK-PROGRESS-EXAMINER`
**error.** An examiner result is not one JSON object per line, does not validate against
`schemas/examiner.schema.json` (`studykit.model.ExaminerResult`: an MC result needs the
question id, `conf` and `chosen`; a task or exercise its id; `points` come with
`max_points`), names an item the course does not have, or a topic the item does not belong
to; or an MC result's `chosen` names a letter the question does not have, or its `score`
differs from the score the site gives `chosen` (`lib/scoring.ts` with
`course.exam.mc.scoring`).
Fix: `studykit progress log <course> --json-line '{"mode": "mc", "kind": "mc", "topic":
"rc-filter", "item": "mc-rc-filter-003", "chosen": ["B"], "conf": "sure"}'`; `chosen` is in
source letters (A = the first option in the file; Kprim: the statements judged true), and
a left-out `score` is computed.

## Ingest (SK-INGEST, `studykit ingest`)

`studykit ingest scan|init|add` report these at the file of the user's folder they concern
(line 1, column 1). They are not validate stages. Only `SK-INGEST-FOLDER` and
`SK-INGEST-COURSE` are errors, which stop the command before it writes anything; the
warnings name files that are left out.

### `SK-INGEST-FOLDER`
**error.** The folder does not exist, or it (or the file given) holds no PDF at all.
Fix: give the folder with the lecture material; export slides, scripts, sheets and exams
as PDF first.

### `SK-INGEST-UNSUPPORTED`
**warning.** An office file (`.pptx`, `.docx`, `.odp`, `.key`, …) or an image (`.png`,
`.jpg`, `.heic`, …) is not read.
Fix: export the document as PDF (photos and scans: combine them into one PDF) and run
`studykit ingest add <course> <file>`.

### `SK-INGEST-DUPLICATE`
**warning.** The PDF has the same content (sha256) as another one in the folder or a
document the course already has; it is read once.
Fix: nothing to do; delete the copy from the folder if it is not needed.

### `SK-INGEST-PDF`
**warning.** pypdfium2 cannot open the PDF: it is encrypted, damaged or not a PDF.
Fix: remove the password or print the document to a new PDF, then add it again.

### `SK-INGEST-COURSE`
**error.** The draft `course.yaml` that `ingest init` would write does not validate, for
example because of an empty title or a non-positive exam duration.
Fix: correct the flag that feeds it (`--title`, `--exam-minutes`, `--exam-points`,
`--hours-per-week`) and run `ingest init` again.

## Plan (SK-PLAN, `studykit plan`)

`studykit plan` reports these at `course.yaml`; errors write no plan. A plan it writes is
read back and checked like validate checks it (schema, references), so the Structure and
References codes never come from a fresh plan.

### `SK-PLAN-STUDY`
**error.** The plan has no time budget: `course.yaml` has no `study` settings, or
`study.hours_per_week` is less than 15 minutes a week.
Fix: `study: {start: YYYY-MM-DD, hours_per_week: 6, blocked: ['YYYY-MM-DD..YYYY-MM-DD']}`.

### `SK-PLAN-DATE`
**error** or **warning.** The first day to plan (`--from`, else today) is not before the
exam, or there is no free study day left before it (error); or the exam date is unknown, so
the plan runs 12 weeks and writes `exam_date: null` (warning).
Fix: plan from an earlier day (`--from YYYY-MM-DD`), set `exam.date`, or shorten
`study.blocked`.

### `SK-PLAN-BUDGET`
**warning.** The time does not cover the plan: too few sessions to learn every topic, a mock
exam longer than the weekly budget, no session left for a mock exam, fewer mock exams than
`targets.mock_exams`, or done sessions that already fill a week.
Fix: start earlier, raise `study.hours_per_week`, skip topics, or write the missing mock
exams; then plan again.
