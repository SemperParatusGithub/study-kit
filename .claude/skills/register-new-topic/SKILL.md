---
name: register-new-topic
description: Turn a folder, single files (PDF, text, images) or text pasted in the chat into a study-kit topic - a slim learning page without exam, MC or plan - with an explanation in chapters and, as chosen, flash cards, a glossary and a concept map. Resumable - every run continues at the first unfinished step that studykit pipeline status reports.
disable-model-invocation: true
argument-hint: <path> [path…] [--id <id>]
allowed-tools:
  - Bash(uv run --frozen studykit *)
  - Bash(just *)
---

# /register-new-topic $ARGUMENTS

Build a topic from the material given (docs/architecture.md §5.6). Arguments: any number of
folders and files (quote a path with spaces), and optionally `--id <id>`. Text the user
pasted into the chat counts as material too, so a topic may have no path at all. The user's
files are only read, and only by `studykit ingest scan|topic|add` (Bash); every agent reads
the copies in `<course>/sources/raw/`. Never Read, Write or list the user's files yourself.

You are the orchestrator in the main thread: you ask the user, start the agents and judge
every step. `<c>` below is the topic's id and `<dir>` its absolute directory (the `dir` of
`studykit pipeline status`). A topic is a course with `kind: topic`, so it lives in
`courses/`, and its "topics" in `course.yaml` are its chapters.

## Rules

- **State lives in the files.** After every step, and at the start of every run,
  `uv run --frozen studykit pipeline status <c> --json` says which steps are `done`,
  `pending`, `partial` or `stale`; what only a course has is `n/a`. `resume` is the first
  step that is not finished: continue there and never redo a step that is `done`.
- **Gates are judged from files and `studykit` commands, never from an agent's report.** A
  step that fails its gate twice stops the run with the findings and how to continue.
- **At most 6 agents at a time**, of all kinds together. Give each agent the absolute
  directory and its one assignment.
- **Numbers** come from `uv run --frozen studykit calc`, never from your head.
- **Ask only where this procedure asks.** Step 1 is the one round of questions.
- Grep and Glob may skip the gitignored `courses/`: list files with
  `uv run --frozen studykit ls <c>` and read them by explicit path.

Findings route as in `/register-new-subject`: `sources/notes/` to the chunk's `ingester`,
`course.yaml` and `sources/outline.md` to you, `overview.md`, `summary/`, `cards/` and
`figures/` to the `author` of that part and chapter in mode `fix` with the finding lines,
SK-INGEST-CONVERT and SK-INGEST-UNSUPPORTED to the user. Each gets at most 2 rounds.

## 0. Preflight

1. `just doctor --quick`; stop on a failure (it names the fix).
2. The id: `--id`, else one proposed from the subject (lower case, ä → ae, ö → oe, ü → ue,
   ß → ss, other characters → `-`, at most 40 characters, `^[a-z0-9][a-z0-9-]{1,39}$`).
3. `uv run --frozen studykit pipeline status <c> --json`. If `exists` is true: when `kind`
   is `course`, stop and point to `/add-material`; otherwise resume at `resume.step`, and
   when `complete` is true say so and stop. New material for a finished topic is
   `/add-material`'s job.
4. Text pasted in the chat: Write each piece, unchanged, to
   `<dir>/_build/inbox/pasted-<n>.txt` and treat that file as one more path. Links are no
   material unless the user's request says to fetch them.
5. Inventory: `uv run --frozen studykit ingest scan <path>… --topic --dry-run --json`. Exit
   1 (SK-INGEST-FOLDER) stops the run. Show a table of id, pages, text share, visual pages
   and origin, then the skipped files with their reason.

## 1. Ask

One AskUserQuestion call:

| Header | Question | Options |
|---|---|---|
| Contents | What should the topic have besides its explanation? (multi-select) | Flash cards, Glossary, Concept map; all three recommended |
| Name | Call it "<title from the subject>"? | that title, a shorter one (only when the request does not name the subject) |
| Language | Write it in <detected language>? | the detected `lang` first, the other of `de`, `en` (only when the material is mixed or the detection failed) |

Map them to `--contents cards,glossary,concept-map` (the names chosen, `none` for none).

## 2. Scaffold and extract

```
uv run --frozen studykit ingest topic <c> <path>… --title <title> --lang <de|en> --contents <names> --json
uv run --frozen studykit ingest extract <c> --json
```

Text files and images become PDFs in `sources/raw/`; everything after that treats them
alike. Report SK-INGEST-CONVERT warnings to the user: those files or characters are missing.

**Gate:** pipeline steps 2 (`scaffold`) and 3 (`extract`) are `done`.

## 3. Read

Start one `ingester` per chunk in step 4's `todo` (`chunks_without_notes`, `notes_invalid`,
`notes_stale`; for `transcriptions_missing`, given as `<doc> p. <n>`, the chunk with that
page), at most 6 at a time, prompt: "Course: `<dir>`. Chunk: `<chunk-id>`. Digest it with the
ingest skill and return the result JSON." (add the finding lines on a retry). There is no
exam analysis.

**Gate:** pipeline step 4 (`read`) is `done`.

## 4. Chapters (you)

1. Read every note (`sources/notes/<chunk>.md`, ids from `sources/chunks.yaml`).
2. Merge the candidate topics of the notes into **2 to 6 chapters** in teaching order: one
   chapter only when the material is too small to split, and then without a concept map.
   Kebab ids in the course language (ASCII), titles in the course language, `prereq` acyclic
   and only on earlier chapters. Weights: pages of material per chapter, computed with
   `uv run --frozen studykit calc`, rounded to two decimals, remainder on the largest, sum 1.
3. Write `sources/outline.md` from `.claude/skills/ingest/templates/outline.md`, without its
   past-exam column and archetypes: the chapter table, one section per chapter (sources with
   pages, merged slugs, key formulas) and the chunk table naming **every** chunk id.
4. Edit `course.yaml`: replace the placeholder `draft` with the chapters; set
   `contents.concept_map: false` for a single chapter and tell the user. Keep `status: draft`.

**Gate:** pipeline step 5 (`synthesize`) is `done`, and
`uv run --frozen studykit validate <c> --paths course.yaml sources` reports no error.

## 5. Author

`todo` of step 7 names what is missing. Authors (`author` agent, at most 6 at a time), each
prompt: "Course: `<dir>`. Part: `<part>`. Topic: `<chapter>`. Mode: new. This is a topic: read
the section 'In a topic' of your part. The notes of this chapter are the chunks
`sources/outline.md` lists for it."

1. First one author for `overview` (no chapter; the notes are all chunks of the outline);
   wait for it.
2. Then one author per chapter for `summary`, in teaching order.
3. Then, when `contents.cards` is true, one author per chapter for `cards`, each after its
   chapter's summary exists.

**Gate:** pipeline step 7 (`author`) is `done`. A chapter's flash cards are not checked by
the blind verifier; say so in the report.

## 6. Figures

`uv run --frozen studykit fig build <c>`. Look at the concept map
`<dir>/_build/figures/topic-map.png` and at every figure the authors made; send a flawed one
back to its author. Check the map's labels against the chapter titles.

**Gate:** pipeline step 8 (`figures`) is `done`.

## 7. Publish and report

1. `uv run --frozen studykit validate <c> --release`, findings routed as above. Then Edit
   `course.yaml` to `status: ready`, and `just build <c>`.
2. `uv run --frozen studykit pipeline report <c>`.
3. Tell the user what the topic has (chapters, cards, terms, whether a concept map), what was
   left out of the material and why, and the next steps: `just dev`, then
   `http://localhost:4321/c/<c>/`; `/tutor <c>` to work through a chapter.

**Gate:** pipeline steps 13 (`publish`) and 14 (`report`) are `done` and `complete` is true.
