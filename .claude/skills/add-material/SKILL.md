---
name: add-material
description: Add new or changed lecture PDFs to an existing study-kit course - incremental copy and extract, ingester agents for the new chunks, the exam analysis again when exams changed, a topic-map diff applied after confirmation, and the /regenerate commands that bring the course up to date.
disable-model-invocation: true
argument-hint: <course> <file|folder>
allowed-tools:
  - Bash(uv run --frozen studykit *)
  - Bash(date -u *)
  - Bash(mkdir -p *)
  - Bash(cp -p *)
---

# /add-material $ARGUMENTS

Bring new lecture material into a course that `/register-new-subject` built
(docs/architecture.md §5.4). Arguments: the course `$0` and a PDF or a folder `$1` (quote a
path with spaces). The file or folder is only read, and only by `studykit ingest add`
(Bash); agents read the copies in `<course>/sources/raw/`. Never Read, Write or list it
yourself.
This command changes the sources, the notes and the topic map; it regenerates no content
itself but says which `/regenerate` runs bring the course up to date.

Judge every step from files and `studykit` commands, not from agents' reports; start at
most 6 agents at a time; compute every number with `uv run --frozen studykit calc`. Grep
and Glob may skip the gitignored `courses/`: read course files by explicit path.

## 1. Preview

1. `uv run --frozen studykit pipeline status $0 --json` must find the course with a
   manifest (step 0 `done`); otherwise stop and point to `/register-new-subject`. Note the
   resume point: a course whose registration is unfinished is finished by running
   `/register-new-subject` again after this command.
2. `uv run --frozen studykit ingest add $0 "$1" --dry-run --json`. Exit 1
   (SK-INGEST-FOLDER) stops. Show `added`, `changed` (same origin, new content: its chunks
   are planned again and their notes go stale), `known` (nothing to do) and `skipped`
   with the reason (SK-INGEST-UNSUPPORTED: export as PDF; SK-INGEST-DUPLICATE: the
   content is already there; SK-INGEST-PDF: encrypted or damaged).
3. Nothing added or changed: say so and stop.
4. Uncertain kinds (`scan.documents[].uncertain` of the new documents): one AskUserQuestion
   call, a multi-select question "Which of these are past exams or their solutions?" per
   four documents, mapped to `--kind <doc>=exam` or `exam-solutions` as in
   `/register-new-subject` round 1.

## 2. Copy and extract

1. Save the topic map before it changes: take a UTC timestamp (`date -u +%Y%m%dT%H%M%SZ`)
   and copy `course.yaml`, `sources/outline.md` and `analysis/exam-profile.yaml` to
   `<course>/_history/<timestamp>/` with the same relative paths (`mkdir -p`, `cp -p`).
2. `uv run --frozen studykit ingest add $0 "$1" [--kind <doc>=<kind> …] --json`. It
   copies what is new or changed, extracts it and lists in `read` the chunks to digest
   (`chunks.new`, `chunks.replanned`; `chunks.removed` are gone with their old version).

**Gate:** pipeline step 2 (`scaffold`) and step 3 (`extract`) are `done`.

## 3. Read

Start, at most 6 at a time:
- one `ingester` per chunk of `read` and of step 4's `todo` (`chunks_without_notes`,
  `notes_stale`, `notes_invalid`, and the chunk holding each `transcriptions_missing`
  page, given as `<doc> p. <n>`), prompt: "Course: `<dir>`. Chunk: `<chunk-id>`. Digest it
  with the ingest skill and return the result JSON.";
- one `exam-analyst` when an added or changed document has kind `exam` or
  `exam-solutions`, or step 4's `todo` has `exam_profile` or `notation`: "Course: `<dir>`.
  Write the exam profile and the notation again; new or changed documents: `<ids>`." It
  writes candidate slugs where a task fits no course topic.

Notes of a removed chunk (`chunks.removed`) are stale files: list them for the user; the
References stage reports them (SK-REF-CHUNK).

**Gate:** pipeline step 4 (`read`) is `done`; route notes findings to the chunk's
ingester and analysis findings to the exam-analyst, at most 2 rounds each.

## 4. Topic-map diff

1. Read the new and stale chunks' notes, the profile and the current outline. Map each new
   candidate slug to an existing course topic where it fits; collect the rest as proposed
   new topics.
2. Compute the proposed weights with `studykit calc` as the synthesis step does (exam
   point shares from a profile of medium or high confidence, else lecture coverage); ids of
   existing topics never change.
3. Show the diff as a table: topic, weight before → after, chunks added or replanned,
   archetypes added; then proposed new topics (id, title, prerequisites, sources) and
   topics whose sources changed.
4. Ask with AskUserQuestion: apply the topic changes, apply without new topics (map their
   chunks to the nearest topic), or keep the topics as they are (only the outline gains
   the new chunks).
5. Apply the choice: Edit `course.yaml` topics (new topics appended in teaching order,
   weights summing to 1), `sources/outline.md` (every chunk id named, the new sources per
   topic) and the profile's candidate slugs mapped to course topics.

**Gate:** pipeline step 5 (`synthesize`) is `done`, and
`uv run --frozen studykit validate $0 --paths course.yaml analysis sources` reports no
error.

## 5. What to regenerate

Use the rebuild dependencies (docs/architecture.md §5.4):

```
sources → notes → {topics, exam-profile} → plan
topics + exam-profile → overview
topics → summary → cheatsheet
topics → exercises
topics → mc
exam-profile + exercises → exams
any content → figures → verify → pdf
```

Suggest, do not run, one line each with its reason:

| What changed | Suggest |
|---|---|
| a topic's sources (new or replanned chunks mapped to it) | `/regenerate <c> summary --topic <t>`, then `/regenerate <c> exercises --topic <t> --add <n>` and `/regenerate <c> mc --topic <t> --add <n>` when the new material adds examples or archetypes |
| a new topic | `/regenerate <c> summary --topic <t>`, `exercises --topic <t>`, `mc --topic <t>` |
| topics added, merged or reweighted, or the exam profile | `/regenerate <c> overview` |
| the exam profile (new archetypes, MC rules, duration) | `/regenerate <c> exams` |
| any summary regenerated | the cheat sheet follows inside that run |
| topics, exercises or exams changed | `/regenerate <c> plan` (the others run it themselves) |

`/regenerate` saves what it overwrites, verifies the changed items and rebuilds the PDFs.

## 6. Report

What was added, changed, skipped (with the reason) and read; the topic changes applied
and the `_history/<timestamp>/` copy; the `/regenerate` commands in the order to run them;
and `uv run --frozen studykit pipeline status $0` (the steps now stale or partial show what
is out of date until those runs).
