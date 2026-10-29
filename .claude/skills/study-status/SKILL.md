---
name: study-status
description: Show where the student stands in a study-kit course - days to the exam, plan adherence, the next sessions, weak topics, reviews due and the last mock exam - from studykit status, with one recommended next step.
disable-model-invocation: true
argument-hint: <course>
allowed-tools:
  - Bash(uv run --frozen studykit *)
---

# /study-status $ARGUMENTS

The student's status in the course `$0` (docs/architecture.md §2.11). Read-only.

1. Run `uv run --frozen studykit status $0` and show its output unchanged in a code block.
   (For details: `--json`; a past or future day: `--today YYYY-MM-DD`.)
2. Below it, at most four lines:
   - how the plan is going (sessions done, how many past sessions are not done);
   - the weakest topic and its accuracy (or a topic not practised yet, which counts 0 in
     the mastery), and the reviews due today;
   - the most useful next step, one of: the next plan session; `/import-progress $0` when
     no browser progress was imported or the last import is old; `/examine $0 mc` when
     reviews are due; `/tutor $0 <weakest topic>`; `/regenerate $0 plan` (or
     `studykit plan $0`) when the plan is behind; a mock exam (`/examine $0 exam <id>`) in
     the last three weeks.
3. Do not change any file. If the course is not found, say where courses are looked for
   (`uv run --frozen studykit ls`).
