---
name: regenerate
description: Regenerate one part of a course (overview, plan, summary, exercises, mc, figures, exams, cheatsheet or all) and everything downstream - saves the old files to _history/, runs author agents, verification, validation and the PDFs, and keeps the ids of surviving items.
disable-model-invocation: true
argument-hint: <course> <overview|plan|summary|exercises|mc|figures|exams|cheatsheet|all> [--topic t] [--add n] [--replace] [note]
allowed-tools:
  - Bash(uv run --frozen studykit *)
  - Bash(mkdir -p *)
  - Bash(cp -p *)
---

# /regenerate $ARGUMENTS

Re-run one authoring step of a course and everything that depends on it
(docs/architecture.md §5.2, §5.4). Arguments: the course `$0`, the part `$1`, then
optional `--topic <t>`, `--add <n>`, `--replace` and a free-text note for the authors.

## 1. Understand the request

1. `uv run --frozen studykit ls $0` finds the course (otherwise stop);
   `uv run --frozen studykit index $0 --json` gives topics, items and exams.
2. The part must be one of `overview`, `plan`, `summary`, `exercises`, `mc`, `figures`,
   `exams`, `cheatsheet`, `all`. `--topic` must be a topic of `course.yaml`; without it a
   per-topic part (summary, exercises, mc) covers every topic that is not skipped.
3. Mode: `--add n` adds n items and keeps everything else; `--replace` rewrites the part
   (items that survive keep their ids, the others are removed); neither means "improve in
   place" (fix what is weak, keep ids, add only what the targets require).
4. **`--replace` (and `all`) needs a yes first:** list the files and item counts that will
   be rewritten and ask with AskUserQuestion; stop on no.

## 2. Save what will change

Take a UTC timestamp (`date -u +%Y%m%dT%H%M%SZ`) and copy every file this run may
overwrite, including the downstream files below, to
`<course>/_history/<timestamp>/<same relative path>` (`mkdir -p`, then `cp -p`). Nothing
is deleted from `_history/`; discovery and validation never read it.

## 3. Write the part

| Part | Who | Scope |
|---|---|---|
| overview | one `author` | `overview.md` |
| summary, exercises, mc | one `author` per topic, at most 6 in parallel | the topic's files |
| exams | one `author` per mock exam, at most 3 in parallel | `exams/<id>/` (`--add n` = n new mock exams) |
| cheatsheet | one `author` | `cheatsheet.md`, then the fit loop of its procedure |
| figures | you: `uv run --frozen studykit fig build $0 --force`; an `author` per failing or flawed figure | `figures/*.py` |
| plan | you, with `.claude/skills/authoring/parts/plan.md` | `plan.yaml` |
| all | overview first, then summary, exercises and mc per topic, then exams, cheatsheet, plan | everything |

Each author prompt names the course directory, the part, the topic, the mode with `n`,
the ids to keep (from the index) and the user's note. Authors return JSON with `added`,
`changed`, `removed`; judge the result by the files and validate, not by the report. Look
at the figures an author built when the part has new ones.

**Removed ids** go into `course.yaml: retired_ids` (you edit it; append, keep the order).

## 4. Downstream

| Changed | Then |
|---|---|
| overview | validate, PDF |
| summary | cheatsheet (an author updates the formulas of the changed topics, then `uv run --frozen studykit cheatsheet fit $0`), validate, PDF |
| exercises | verify, `studykit plan` (it references exercises), validate, PDF; with `--replace` ask whether the mock exams should be regenerated too |
| mc | verify, validate, PDF |
| exams | verify, `studykit plan` (mock exam sessions), validate, PDF |
| cheatsheet | validate, PDF |
| plan | validate, PDF |
| figures | validate, PDF |

- **Verify** the items in `added` and `changed`: follow `.claude/skills/verify/SKILL.md`
  from step 2 with exactly those ids (verifier wave, dispute loop, quarantine). Unchanged
  items keep their ledger entries.
- **Plan:** `uv run --frozen studykit plan $0`, then write the missing goals as in
  `.claude/skills/authoring/parts/plan.md`. Sessions marked done are kept.
- **Validate:** `uv run --frozen studykit validate $0` (it also builds the PDFs). Route
  errors by file to the owning author (`docs/content-format/errors.md` has the owners),
  at most 3 rounds.
- **PDF:** `uv run --frozen studykit pdf $0`; it must report no failed document.

## 5. Report

Per part: items added, changed, removed (and retired), figures written; verification
counts (verified, fixed, quarantined with reasons); validate result; the PDFs built; the
`_history/<timestamp>/` directory with the old files. If something is still red, say what
and which step owns it.
