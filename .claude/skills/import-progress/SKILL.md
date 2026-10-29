---
name: import-progress
description: Import a browser progress export of a study-kit course - finds the newest studykit-progress-<course>-*.json in ~/Downloads (after confirmation) or takes the given file, validates and merges it with studykit progress import, writes the mastery report and offers a replan.
disable-model-invocation: true
argument-hint: <course> [file]
allowed-tools:
  - Bash(uv run --frozen studykit *)
  - Bash(ls *)
---

# /import-progress $ARGUMENTS

Bring the progress the student made on the website (stored in the browser) into the
course, so that `studykit status`, `studykit plan` and the examiner see it
(docs/architecture.md §2.11). Arguments: the course `$0`, optionally the export file `$1`.

## 1. Find the file

1. `uv run --frozen studykit ls $0` must find the course; its id is the directory name.
   Note the weakest topics before the import from `uv run --frozen studykit status $0 --json`
   (`weak_topics`); step 4 compares them.
2. With a file argument, use that file. Without one, find the newest export of this course:
   `ls -t ~/Downloads/studykit-progress-<course-id>-*.json | head -n 1`. None found: tell
   the student to use "Export" on the site's progress page
   (`http://localhost:4321/c/<course-id>/progress/`) and stop.
3. Show the file name, its date and size (`ls -l <file>`) and ask with AskUserQuestion
   whether to import it (Import / Cancel). Only the file the student confirms is read.

## 2. Import

1. Preview: `uv run --frozen studykit progress import $0 <file> --dry-run`. It validates
   the export and lists what would change (new entries, MC attempts, ratings, mock exam
   attempts, sessions newly done).
2. Findings stop the import; explain them in one line each: SK-PROGRESS-FILE (not JSON or
   unreadable), SK-PROGRESS-SCHEMA (another schema version), SK-PROGRESS-COURSE (the export
   belongs to another course or names none), SK-PROGRESS-ENTRY (an entry that does not
   validate; the rest is fine). `docs/content-format/errors.md` has the fixes.
3. Import: `uv run --frozen studykit progress import $0 <file>`. It merges into
   `progress/state.json` (the site's union merge: nothing is lost by importing twice) and
   keeps a copy in `progress/browser/`.

## 3. Report

1. `uv run --frozen studykit progress report $0` writes `progress/mastery.json` and
   `progress/report.md`; show the mastery, the reviews due and the misconceptions.
2. `uv run --frozen studykit status $0` shows the plan adherence. Summarise in three lines:
   what was imported, where the student stands, the weakest topic.

## 4. Offer a replan

When the status shows past sessions not done (`plan.behind` in `--json`), or the weakest
topics differ from those noted in step 1, ask with AskUserQuestion whether to replan from
today (Replan / Keep the plan). On yes:

1. `uv run --frozen studykit plan $0` (done sessions and unchanged goals are kept), then
   write the missing goals as `.claude/skills/authoring/parts/plan.md` describes.
2. `uv run --frozen studykit validate $0 --paths plan.yaml` and
   `uv run --frozen studykit pdf $0 plan`.
3. Tell the student that the site shows the new plan after the next build (`just build`)
   or at once in `just dev`.
