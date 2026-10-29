# Part: plan (`plan.yaml`)

The study plan is computed, never written by hand: `studykit plan` is deterministic
(docs/architecture.md §2.9). Only each session's `goal` and optional `note` are written
afterwards.

## Procedure

1. Preview: `uv run --frozen studykit plan <course> --dry-run`, optionally with
   `--from YYYY-MM-DD` (default today, never before `study.start`). Findings such as
   SK-PLAN-DATE (unknown exam date), SK-PLAN-STUDY or SK-PLAN-BUDGET (missing or too small
   weekly budget) go to the user; they are fixed in `course.yaml`, not in the plan.
2. Write it: `uv run --frozen studykit plan <course>` (add `--json` to read
   `goals_missing`, `kept`, `dropped`, `goals_kept`). Replanning keeps every session marked
   done in `progress/` and the goals of unchanged sessions.
3. For every session id in `goals_missing`, Edit its `goal:` in `plan.yaml`: one line in
   the course language, at most about 80 characters, saying what the student can do after
   the session ("Grenzfrequenz und Bode-Diagramm des Tiefpasses sicher bestimmen"), based
   on the session's kind, topics and tasks. A `note:` only for a concrete tip. Single-quote
   both. Change nothing else; the next `studykit plan` would undo it.
4. `uv run --frozen studykit validate <course> --paths plan.yaml` must be clean, then
   report the number of sessions, the mock exam dates and the first three sessions.

Template: the content-format skill's `templates/plan.yaml`.
