---
name: register-new-subject
description: Turn a folder of lecture PDFs into a complete study-kit course - inventory, two short rounds of questions, ingest, chunk reading by ingester agents, exam analysis, topic synthesis, author and verifier waves, mock exams, cheat sheet, plan, PDFs, site and a report. Resumable - every run continues at the first unfinished step that studykit pipeline status reports.
disable-model-invocation: true
argument-hint: <folder> [course-id]
allowed-tools:
  - Bash(uv run --frozen studykit *)
  - Bash(just *)
---

# /register-new-subject $ARGUMENTS

Build a course from the lecture material in a folder (docs/architecture.md §5.4).
Arguments: the folder (`$0`; quote a path with spaces) and optionally the course id as the
second argument. The user's folder is only read, and only by
`studykit ingest scan|init|add` (Bash); every agent reads the copies in
`<course>/sources/raw/`. Never Read, Write or list the user's folder yourself.

You are the orchestrator in the main thread: you ask the user, start the agents and judge
every step. `<c>` below is the course id and `<dir>` its absolute directory (the `dir` of
`studykit pipeline status`).

## Rules

- **State lives in the files.** There is no state file. After every step, and at the start
  of every run, `uv run --frozen studykit pipeline status <c> --json` says which steps are
  `done`, `pending`, `partial` or `stale`, with `details` and a machine-readable `todo`;
  `resume` is the first step that is not done (deferred steps aside). Continue at
  `resume.step`; never redo a step that is `done`. A `stale` step is redone; the steps after
  it then show what they must redo.
- **Gates are judged from files and `studykit` commands, never from an agent's report.**
  An agent's JSON only tells you what it claims; the gate of each step below decides. A step
  that fails its gate twice stops the run with the findings, what owns them and how to
  continue (run the command again after fixing).
- **At most 6 agents at a time**, of all kinds together (3 for mock exams). Give each agent
  the absolute course directory and its one assignment; never paste keys or solutions into
  a verifier's prompt.
- **Numbers** (weights, shares, estimates) come from `uv run --frozen studykit calc`, never
  from your head.
- **Ask only where this procedure asks.** Round 1 and round 2 are the two rounds of
  questions; everything else runs without interrupting the user, unless a step stops.
- Grep and Glob may skip the gitignored `courses/`: list course files with
  `uv run --frozen studykit ls <c>` and read them by explicit path.

## Failure routing

A failed gate names findings as `path:line:col SK-CODE message (fix: …)`. Route each by
its file and code (`docs/content-format/errors.md` has the fix and the owner):

| Findings | Go to |
|---|---|
| `sources/notes/<chunk>.md`: SK-REF-CHUNK, SK-STRUCT-PATH, schema, YAML, fence, math or SK-REF-SRC codes | the `ingester` of that chunk, with the finding lines |
| `analysis/*.yaml`: SK-SCHEMA-SHARES, schema, YAML codes, SK-REF-MISSING on a past exam | the `exam-analyst`, with the finding lines |
| `analysis/exam-profile.yaml`: SK-REF-MISSING on a topic | you: map the slug to a course topic (step 5) |
| `sources/chunks.yaml` SK-REF-CHUNK warning, pipeline `todo.replan` or `not_extracted` | `uv run --frozen studykit ingest extract <c>` |
| SK-INGEST-UNSUPPORTED, SK-INGEST-PDF | the user: export as PDF or remove the password, then `/add-material <c> <file>` |
| SK-INGEST-FOLDER, SK-INGEST-COURSE | you: fix the folder or the flag and run `ingest init` again |
| `course.yaml` (SK-STRUCT-TOPIC, SK-STRUCT-CYCLE, SK-STRUCT-DRAFT, SK-YAML-LATEX, schema codes), `sources/outline.md` | you |
| `overview.md`, `summary/`, `exercises/`, `mc/`, `exams/`, `cheatsheet.md`, `figures/` (structure, schema, block, MC, math, reference, Pandoc, SK-FIG-BUILD, SK-PDF-COMPILE, SK-PDF-WARNING, SK-COV codes) | the `author` of that part and topic, mode `fix` with the finding lines |
| SK-PDF-CHEATSHEET | the cheat-sheet `author`, its condense loop |
| SK-VER-DISPUTED, SK-VER-UNVERIFIED, SK-VER-STALE, SK-VER-CHECK | the `/verify` procedure for those items |
| `plan.yaml`, SK-STRUCT-PLAN | `uv run --frozen studykit plan <c>`, then the goals (step 12) |
| SK-PLAN-STUDY, SK-PLAN-BUDGET, SK-PLAN-DATE | the user (budget or exam date), then you edit `course.yaml` |
| SK-PDF-BUILD, SK-SITE-BUILD without a course file, a tool missing | stop: `just doctor`, then run the command again |

Publish (step 13) routes for at most 3 rounds; every other step for at most 2 per agent.

## 0. Preflight

1. `just doctor --quick`; stop on a failure (it names the fix).
2. The course id: the second argument, else one proposed from the folder name (lower case,
   ä → ae, ö → oe, ü → ue, ß → ss, other characters → `-`, at most 40 characters,
   `^[a-z0-9][a-z0-9-]{1,39}$`). When the id was proposed, confirm it with one
   AskUserQuestion (the proposal, a shorter variant; Other for a free id).
3. `uv run --frozen studykit pipeline status <c> --json`. If `exists` is true, show the
   one-line state of each step and ask with AskUserQuestion: resume this course, or choose
   another id. On resume, jump to `resume.step`. When step 2's `todo` has
   `folder_changed` or `folder_new` (the folder changed since the copy): before synthesis
   (step 5 not done) run `uv run --frozen studykit ingest add <c> "$0" --json` and continue
   at the new resume point; after it, that is `/add-material`'s job: suggest
   `/add-material <c> <folder>` and stop. When `complete` is true, say so and stop; when
   only `deferred` steps remain, offer to finish them (round 2 again with scope full).
4. Inventory: `uv run --frozen studykit ingest scan "$0" --dry-run --json`. Exit 1
   (SK-INGEST-FOLDER) stops the run. Show a table: id, kind (a `?` when `uncertain`),
   pages, text share, visual and scanned pages, origin; then the totals (PDFs, pages,
   visual pages, chunks, past exams), the skipped files with their reason
   (`unsupported`: "export as PDF"; `duplicate`: of which), the detected language and the
   exam dates found.

## 1. Ask, round 1

One AskUserQuestion call with exactly these four questions (headers at most 12
characters, 2-4 options each; Other is always offered):

| Header | Question | Options |
|---|---|---|
| Exam date | When is the exam? | each date of `exam_dates` (at most two, with document and page), "Unknown yet" |
| Format | What is the exam format? | Written, Written + MC part, MC only, Oral |
| Cheat sheet | Is a cheat sheet allowed? | Not allowed, 1 page, 2 pages, 3 pages (Other: up to 10) |
| Hours/week | How many hours a week can you study? | 4, 6, 8, 10 |

A second call covers what the inventory left open, at most four questions:
- per four uncertain documents one multi-select question "Which of these are past exams or
  their solutions?" (`totals.uncertain_kinds`); a selected document becomes `exam`, or
  `exam-solutions` when its title or file name says solution (Lösung, Musterlösung); an
  unselected one that was guessed `exam` or `exam-solutions` becomes `other`;
- "Write the course in <detected language>?" with the detected `lang` first and the other
  of `de`, `en`.

Map the answers to flags: the date as `YYYY-MM-DD` or `unknown` (convert a typed date; ask
again only if it cannot be read), `written | written-mc | mc | oral`, an integer from `0` to `10`, the
hours as a number.

## 2. Scaffold

```
uv run --frozen studykit ingest init "$0" <c> --exam-date <date|unknown> --exam-format <format>
    --cheatsheet <pages> --hours-per-week <h> --lang <de|en> [--kind <doc>=<kind> …] --json
```

Add `--exam-minutes` and `--exam-points` only when the context of a found exam date states
them ("90 Minuten"), also when the user typed another date for the same exam. It copies the PDFs to `sources/raw/`, writes `sources/manifest.yaml`
with the round-1 answers and a draft `course.yaml`. Exit 1 stops with the findings.

**Gate:** pipeline step 2 (`scaffold`) is `done`, and
`uv run --frozen studykit validate <c> --paths course.yaml sources/manifest.yaml` reports
no error.

## 3. Extract

`uv run --frozen studykit ingest extract <c> --json`: page text into `sources/text/`, the
chunk plan `sources/chunks.yaml` (at most 20 pages, never across documents, past exams
whole, flagged and scanned pages per chunk).

**Gate:** pipeline step 3 (`extract`) is `done`.

## 4. Read

Start, at most 6 at a time:
- one `ingester` per chunk in step 4's `todo` (`chunks_without_notes`, `notes_invalid`,
  `notes_stale`; for `transcriptions_missing`, given as `<doc> p. <n>`, the chunk of
  `sources/chunks.yaml` with that `doc` and page; for `lint_errors`, the chunk whose notes
  file the finding names), prompt:
  "Course: `<dir>`. Chunk: `<chunk-id>`. Digest it with the ingest skill and return the
  result JSON." (add the finding lines on a retry);
- alongside, one `exam-analyst` when `todo` has `exam_profile` or `notation`: "Course:
  `<dir>`. Write the exam profile and the notation." It reads the past exams itself; with
  none it writes a low-confidence profile from the round-1 answers.

Start the next ingester as soon as one returns; read the longest chunks first.

**Gate:** pipeline step 4 (`read`) is `done`: the notes schema holds, every chunk has notes
at its document's sha256, every scanned page has its transcription, and there are no lint
errors in notes or analysis, so formulas pass the math lint. A chunk that fails twice stops
the run with its findings.

## 5. Synthesize (you)

1. Read every note (`sources/notes/<chunk>.md`, ids from `sources/chunks.yaml`), the exam
   profile and the notation.
2. Merge the candidate topics of all notes into **6 to 15 course topics** (fewer only for
   a very small course): kebab ids in the course language (ASCII), titles in the course
   language, teaching order, `prereq` acyclic and only on earlier topics.
3. **Weights:** with a profile of `confidence` medium or high, each topic's share of the
   exam points: the profile's `topic_weights` (they already count the MC part) added up
   over the slugs merged into the topic, so the course weights equal the mapped profile
   of item 6; archetype shares (task points only) only when the profile has no
   `topic_weights`. Otherwise the lecture coverage (pages of slides and script per
   topic). Compute with
   `uv run --frozen studykit calc`, round to two decimals, remainder on the largest, sum 1.
4. Write `sources/outline.md` from `.claude/skills/ingest/templates/outline.md`: the topic
   table (number, id, title, weight, prerequisites, chunks, past-exam frequency), one
   section per topic (sources with pages, merged slugs, key formulas, archetypes) and the
   chunk table naming **every** chunk id.
5. Edit `course.yaml` (keep its flow-form lines, `targets:` on one line, `status: draft`):
   the `topics` replace the placeholder `draft`; `title`, `short` and `semester` from the
   notes' course facts; `exam.duration_min`, `points` and `aids`, and the MC rules from the
   profile (past exams) or the course facts. No LaTeX in `course.yaml`.
6. Map the profile's candidate slugs to course topics: Edit each archetype `topic` and the
   `topic_weights` keys of `analysis/exam-profile.yaml` (weights of merged slugs added with
   `studykit calc`); change nothing else.

**Gate:** pipeline step 5 (`synthesize`) is `done`, and
`uv run --frozen studykit validate <c> --paths course.yaml analysis sources` reports no
error (the References stage now checks the profile's topics).

## 6. Ask, round 2

1. Show the numbered topic table: number, title (id), weight, sources (chunks and pages),
   past-exam frequency; below it the exam as `course.yaml` now has it (date, duration,
   points, MC part, aids; say which values are assumptions).
2. Ask for one line in chat, for example `focus 3,5; skip 9; merge 6+7; ok`. Commands:
   `focus <n,…>`, `skip <n,…>`, `merge <a>+<b>` (keeps the first id, adds the weights,
   joins sources and prerequisites), `weight <n>=<w>` (the others scale to keep the sum 1),
   `exam <minutes> min <points> pts`, `ok`. Apply them to `course.yaml`, the outline and
   the profile mapping (validate as in step 5), show the table again, and repeat until the
   line is `ok`.
3. Estimate with `studykit calc`, for both scopes: authors = 1 (overview) + topics × 3,
   plus the mock exams and 1 cheat sheet when allowed (core: topics × 2, no mock exams, no
   cheat sheet); items ≈ topics × 4 exercises plus the MC targets (per topic
   `min(25, max(10, ceil(25 * weight)))`, the Coverage stage's rule), plus 8 per mock exam
   (core: no exercises); opus agent runs ≈ (authors and items) × 1.2 for fix rounds;
   time ≈ authors / 6 × 15 min and items / 6 × 5 min. The estimate comes before the
   mock-exam answer, so count the default number of mock exams (next item) and say so.
   Give each as a range (× 0.7 to × 1.5) and say it is an estimate.
4. One AskUserQuestion call with three questions: "How many mock exams?" (1, 2, 3; the
   default, marked in its description: the number of past exams in the profile, at most
   3, else 2), "Which scope?" (Full: everything now; Core first: summary, MC and plan,
   the exercises, mock exams and cheat sheet later), "Start the generation?" (Go, with the
   estimate in the option's description; Not now).
5. Record the answers (`--no-go` for Not now); with no-go, stop: running the command
   again resumes here.

   ```
   uv run --frozen studykit ingest round2 <c> --mock-exams <n> --scope <full|core> [--no-go] --json
   ```

**Gate:** pipeline step 6 (`ask-2`) is `done`.

## 7. Author wave

`todo` of step 7 names what is missing (`overview`, `summary`, `exercises`, `mc`,
`overview_links`, `schema_errors`). Authors (`author` agent, at most 6 at a time), each
prompt: "Course: `<dir>`. Part: `<part>`. Topic: `<t>`. Mode: new. Follow `notation.yaml`;
the notes of this topic are the chunks `sources/outline.md` lists for it." When the part
exists but falls short of its target (a resumed run; the Coverage message names the
counts), the mode is `add <n>` instead.
1. First one author for `overview`, prompt: "Course: `<dir>`. Part: `overview`. Mode: new.
   Follow `notation.yaml`; the notes are all chunks of `sources/outline.md`." (no topic; it
   writes the topic map section and "exam at a glance" from the profile); wait for it.
   `overview_links` (topics the overview does not link) and `schema_errors` in
   `overview.md` go to this author with mode `fix` and the finding lines.
2. Then one author per topic for `summary` (topics in teaching order).
3. Then one author per (topic, part) for `mc`, and for `exercises` unless the scope is
   core, each after its topic's summary exists.

**Gate:** `uv run --frozen studykit validate <c> --quick --paths <the new files>` reports
no error, and pipeline step 7 (`author`) is `done`. Route findings to the owning author
(mode `fix`). The quick run checks neither references nor figures (step 8 does), and the
Coverage stage runs only with `--release`: the counts per topic come from step 7's
`todo` and details.

## 8. Figures

`just figures <c>`, then Read the PNG of every new figure in `<dir>/_build/figures/`:
overlapping labels, clipped text, wrong values or a missing component go back to the
author who references the figure (`fig:<slug>`), with the problem; build failures too. At
most 2 rounds. Then `uv run --frozen studykit validate <c> --paths <step 7's files>`
without `--quick`: the References and Figures stages catch `ex:`, `fig:` and `src:` links
the quick gate let through; route them like step 7's findings.

**Gate:** pipeline step 8 (`figures`) is `done`, and that validate reports no error.

## 9. Verify wave

Follow `.claude/skills/verify/SKILL.md` from its step 1 for each topic not skipped, in
teaching order (its `$0` is `<c>`, the target the topic id): verifier agents one item each, at most 6 at a time,
the dispute loop with at most 2 author fix rounds, quarantine of what stays disputed.

**Gate:** pipeline step 9 (`verify`) is `done`: every exercise and MC question of the
topics is verified or quarantined, none stale.

## 10. Mock exams (deferred with scope core)

`targets.mock_exams` exams, one `author` each with part `exam` (at most 3 in parallel),
each told its number (`probeklausur-<n>`) and the profile's archetypes; with
`exam.mc.present` it writes `mc.md`. Then the verify procedure with the exam id as target.

**Gate:** pipeline step 10 (`mock-exams`) is `done`: count, points and time within the
Coverage stage's ±10 %, the MC part, archetypes of the profile, every item verified or
quarantined.

## 11. Cheat sheet (deferred with scope core; done when not allowed)

One `author` with part `cheatsheet`; it runs the fit loop (`studykit cheatsheet fit`) and,
on overflow after three condense rounds, returns the candidates to drop: ask the user with
AskUserQuestion which to drop, then let the author fit again. Then audit the formulas: every
display formula of `cheatsheet.md` must appear with the same symbols in the summary chapter
of its topic; a formula that differs or has no source goes back to the author.

**Gate:** pipeline step 11 (`cheatsheet`) is `done`: a fresh `cheatsheet.pdf` within
`max_pages`.

## 12. Plan

`uv run --frozen studykit plan <c> --json`, then write the goal of every session in
`goals_missing` as `.claude/skills/authoring/parts/plan.md` describes. SK-PLAN findings go
to the user (exam date, weekly budget).

**Gate:** pipeline step 12 (`plan`) is `done`.

## 13. Publish

1. The overview and the summaries were written before any exercise or mock exam existed,
   so they could not link them. When `overview.md` has no `exam:` link although `exams/`
   has a mock exam, or no `ex:` link although exercises exist, start one `author`:
   "Course: `<dir>`. Part: `overview`. Mode: replace. Link the mock exams (`exam:`) and the
   first exercises to start with (`ex:`) that now exist." For each summary chapter that
   does not link every exercise of its topic (`studykit index <c> --json` lists them),
   start one `author` alongside: "Course: `<dir>`. Part: `summary`. Topic: `<t>`. Mode:
   fix. Link each exercise of the topic once (`Übung: [title](ex:<id>)`) after the
   section it practises; change nothing else." Their gate is step 7's.
2. `just pdf <c>`; a failed document is routed by its findings.
3. `uv run --frozen studykit validate <c> --release`; route every error (table above), at
   most 3 rounds, re-running the step whose files changed (figures, verify, plan).
4. Only when it is green: Edit `course.yaml` `status: draft` → `status: ready`, then
   `just build <c>` (figures, validate, PDFs, the strict site build, links). If the build
   fails, set `status: draft` again and route its findings (a round of the 3).
5. With scope core the Coverage stage still wants exercises, mock exams and the cheat
   sheet: skip `--release`, run `just build <c>` with `status: draft`, and say that the
   course becomes ready after the deferred steps.

**Gate:** pipeline step 13 (`publish`) is `done` (with scope core: `partial` only for
`status`).

## 14. Report

`uv run --frozen studykit pipeline report <c>` writes `state/pipeline/report.md`. Then
tell the user, briefly:
- counts per part: topics, summary chapters, exercises by difficulty, MC questions by type,
  mock exams, figures;
- verification: the share verified, fixed after a dispute and quarantined, each
  quarantined or disputed item with its reason;
- the cheat sheet's pages and font size;
- what was assumed (exam duration, points, MC rules from a low-confidence profile) and the
  deferred steps with how to finish them (run this command again, scope full);
- next steps: `just dev` → `http://localhost:4321/c/<c>/`, `/examine <c> diagnostic` (15
  MC questions seed the Leitner boxes and the plan), `/tutor <c> <topic>`.

**Gate:** pipeline step 14 (`report`) is `done`, and `complete` is true; with scope core,
`resume` stays at step 13 (`status: draft`) until the deferred steps are done.
