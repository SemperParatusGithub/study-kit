# Part: cheatsheet (`cheatsheet.md`)

The formula sheet a student may take into the exam, within `max_pages` (the smallest of
10, `course.cheatsheet.max_pages` and the frontmatter's `max_pages`). Only when
`course.cheatsheet.allowed` is true.

## Writing it

- Frontmatter: `title`, `max_pages`, `priority` (topic ids, most important first: focus
  topics, then by weight).
- One `##` section per topic in teaching order: display formulas grouped on one line with
  `\qquad`, small tables, `definition`/`note`/`warning` boxes, at most one small figure per
  topic (size `'cs'`). No exercises, hints or derivations of standard results.
- Take formulas from the summaries with the same symbols; every formula states its
  conditions in a word or two.

## Fitting (`studykit cheatsheet fit`)

`uv run --frozen studykit cheatsheet fit <course> --json` compiles at densities 0-4
(9 pt down to 7 pt) and keeps the first that fits.

- Exit 0: it fits; report `pages` and `density`.
- Exit 3: even 7 pt overflows. The JSON has `overflow_pages`, `used_pages`, `max_pages` and
  `largest_sections: [{title, line, height_pages}]` (`line` is the `##` heading's line in
  `cheatsheet.md`). The previous valid PDF stays.
- Exit 1: it did not build; fix the findings first. Exit 2: the course has no cheat sheet.

**Condense procedure on exit 3**, at most 3 rounds, rebuilding after each:

1. Remove derivations and intermediate steps; keep results.
2. Remove duplicate examples and formulas that appear in two sections.
3. Shorten prose to keywords; merge boxes; turn lists into one line.
4. Only then drop content of the lowest-priority topics: lowest weight first, and among
   those the highest mastery (`progress/mastery.json`, `topics.<id>.mastery`), starting
   with the largest sections the JSON lists.

Cut at least `overflow_pages` worth of the sections it names (their `height_pages` are
estimates: cut about 20 % more). If it still overflows after the third round, stop and
return `{"part": "cheatsheet", "fits": false, "overflow_pages": …, "candidates": […]}`
listing what could go, so the user decides what to drop. Never raise `max_pages` above
the course limit.

Template: the content-format skill's `templates/cheatsheet.md`.
