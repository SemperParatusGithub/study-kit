# Part: exam (`exams/<exam-id>/`)

A mock exam modelled on the real one: same format, length and archetype mix, new items.

## Inputs

`analysis/exam-profile.yaml` (archetypes with topic and share, points, minutes per point,
MC share, type mix, scoring, negative marking), `course.yaml: exam` (date, duration,
points, aids, MC part), the exercises of each topic (difficulty reference) and the
existing mock exams (do not repeat their items).

## Building it

1. Id `probeklausur-<n>` (next free n); task prefix `pk<n>`; files `NN-pk<n>-tM.md`.
2. Points and time within ±10 % of `course.yaml: exam` (SK-COV-EXAM with `--release`);
   `pass_points` 50 % of the points unless the course says otherwise; `aids: inherit`;
   `modeled_on` lists the past-exam document ids it follows.
3. Tasks: one per archetype share, points ≈ share × task points, `minutes` ≈ points ×
   minutes per point, `difficulty` mostly 2-3 with one 4. Each task is an exercise with
   `kind: exam-task`, `points`, `archetype` (an id from the profile), `answers` and a
   `rubric` whose points add up to the task's points (SK-SCHEMA-RUBRIC): one criterion per
   gradable step, phrased as what earns the points.
4. MC part, only when `course.exam.mc.present`: `mc.md` with questions numbered in a range
   no bank uses (`mc-<topic>-101`, … for exam 1, `201` for exam 2), the profile's type mix,
   `mc: {file: mc.md, points_each: …}` so that tasks + questions × points_each = `points`
   (SK-STRUCT-POINTS). Questions follow [mc.md](mc.md).
5. Values and circuits are new; never copy a past-exam task or a practice exercise.

## Checks

- `uv run --frozen studykit validate <course> --paths exams/<exam-id>/*` clean.
- Sum of task points + MC points equals `points`; sum of `minutes` ≤ `duration_min`.
- Every task has a solution with the rubric's steps visible.

Template: the content-format skill's `templates/exam/`.
