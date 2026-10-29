# Walkthrough: register a subject and study it

This guide follows one subject from a folder of lecture PDFs to a course you study with
the website and Claude Code. The examples come from a real run on the sample materials in
`examples/sample-materials` (op-amp basic circuits, in German), which produced the course
`opamp-grundlagen`. The specification behind every step is
[architecture.md §5.4](architecture.md#54-register-new-subject-folder-course-id).

Your course stays on your machine: everything under `courses/` is gitignored, and the
hooks refuse to commit it (see the README).

## Before you start

- Set up the repository once (`uv run --frozen studykit tools install`, then
  `.tools/bin/just setup`), and have Claude Code (`claude`) installed.
- Put the subject's material in one folder, anywhere on your disk: slides, the lecture
  script, exercise sheets and their solutions, and above all **past exams** with their
  solutions. Only PDFs are read. Export PowerPoint, Word or Keynote files as PDF first;
  photos of handwritten sheets work best combined into one PDF. A scan without a text layer
  is fine: it is transcribed.
- File names help: `Klausur_WS2025-26.pdf`, `Uebung03_..._Loesung.pdf` or
  `VL03_Folien.pdf` tell the inventory what each document is. Otherwise it looks at the
  cover page and the page shape, and asks you about the ones it is unsure of.

To try everything without your own material, build the sample materials first:

```bash
just sample-materials        # PDFs into examples/sample-materials/_build/materials (gitignored)
```

They are seven PDFs: 14 slides, a 2-page script excerpt, exercise sheet 3 with solutions,
a past exam with its model solution, and a rasterised scan of an old exercise sheet.

## Register the subject

Open Claude Code in the repository and run:

```
/register-new-subject ~/Studium/Elektronik1 [course-id]
```

For the sample: `/register-new-subject examples/sample-materials/_build/materials
opamp-grundlagen`. Without a course id the command proposes one from the folder name
(`ä` becomes `ae`, and so on) and asks you to confirm it.

The command runs fifteen steps (0–14). You answer two short rounds of questions; the rest
runs on its own, with up to six agents at a time. After every step it reads
`studykit pipeline status <course>`, which works out from the files what is done, so a
step is judged by what it wrote, never by what an agent says it did.

### Step 0: inventory

The command checks the tools (`just doctor --quick`) and reads the folder with
`studykit ingest scan <folder> --dry-run`. Nothing is copied yet. You see a table like
this (from the sample run):

```
  id                                           kind           pages  text  visual  origin
  altes-uebungsblatt02-scan                    exercises          1    0%  1       Altes_Uebungsblatt02_Scan.pdf
  klausur-ws2025-26                            exam               2  100%  1       Klausur_WS2025-26.pdf
  klausur-ws2025-26-loesung                    exam-solutions     1  100%  -       Klausur_WS2025-26_Loesung.pdf
  ...
  vl03-operationsverstaerker-grundschaltungen  slides            14  100%  1,5,8,11  VL03_Operationsverstaerker_Grundschaltungen.pdf
22 pages, 8 visual (1 without text layer), 7 chunk(s); language de
possible exam date 2027-02-17 (vl03-operationsverstaerker-grundschaltungen p. 14): …
```

- **kind** comes from the file name, else from the cover page, else from the page shape
  (landscape pages look like slides). A `?` marks a guess you will be asked about.
- **text** is the share of pages with a text layer; the scan has none.
- **visual** pages are those with little text, garbled glyphs, large images or many drawn
  shapes (the three circuit slides 5, 8 and 11). Only these pages are later looked at as
  images; everything else is read as text, which keeps the run cheap.
- Duplicates (same content, another name) are read once; office files and images are
  listed with "export as PDF".
- Dates near "Klausur" or "exam" become choices for the first question.

### Step 1: four questions

One question block, with four questions:

| Question | Options |
|---|---|
| Exam date | the dates found in the material, "Unknown yet", or type one |
| Format | Written, Written + MC part, MC only, Oral |
| Cheat sheet | Not allowed, 1, 2 or 3 pages |
| Hours/week | 4, 6, 8, 10, or type one |

A second block asks only what is still open: which uncertain documents are past exams or
their solutions, and whether to write the course in the detected language. In the sample
run the slides said 17.02.2027; the answer was a different date typed in (2027-02-20),
written with an MC part, a 2-page cheat sheet and 6 hours a week. An unknown exam date is
fine: the plan then covers 12 weeks and you set the date later.

### Steps 2 and 3: copy and extract

`studykit ingest init` copies every PDF to `courses/<id>/sources/raw/<doc>.pdf`, writes
`sources/manifest.yaml` (each document's id, kind, pages and sha256, and your answers)
and a draft `course.yaml` with one placeholder topic. Your folder is only read, never
changed, and only by `studykit ingest`; every agent reads the copies.

`studykit ingest extract` writes the page text to `sources/text/<doc>/p0001.txt` and cuts
the material into chunks of at most 20 pages (`sources/chunks.yaml`). A chunk never spans
two documents, and a past exam stays in one piece. The sample gave seven chunks, one per
document; the slides' chunk lists its flagged pages:

```yaml
- {id: vl03-operationsverstaerker-grundschaltungen-c01, doc: vl03-operationsverstaerker-grundschaltungen,
   kind: slides, first: 1, last: 14, flagged: [1, 5, 8, 11], scanned: [], sha256: '28a6…'}
```

### Step 4: reading

One `ingester` agent per chunk reads the page text, looks at the flagged pages as images
and writes a digest, `sources/notes/<chunk>.md`: summary, course facts, candidate topics,
formulas, definitions, examples, exercise archetypes, notation and figures, each with a
`src:` link to its page. A scanned page is first transcribed to
`sources/text/<doc>/p0001.vision.md` (the old exercise sheet in the sample).

Alongside, the `exam-analyst` reads the past exams and writes
`analysis/exam-profile.yaml` (task archetypes with points and minutes, the MC part with its
types and scoring, topic weights, and a confidence) and `analysis/notation.yaml` (j or i,
phasor style, decimal sign, symbols). The sample's single past exam gave a profile of
medium confidence: 90 minutes, 60 points, six MC questions at 2 points, three tasks.
Without past exams the profile is built from your answers and marked low confidence.

### Step 5: topics

Claude merges the candidate topics of all notes into the course's topics (6 to 15 for a
full lecture), with prerequisites and weights. With past exams, the weights are each
topic's share of the exam points; otherwise they follow how much of the lecture covers it.
The result is `sources/outline.md` (every topic with its sources, formulas and archetypes)
and the topics in `course.yaml`. The sample material is small, so it gave three topics:

| # | Topic | Weight |
|---|---|---|
| 1 | Idealer Operationsverstärker und Gegenkopplung | 0.03 |
| 2 | Invertierender und nichtinvertierender Verstärker, Spannungsfolger und Summierer | 0.63 |
| 3 | Integrierer | 0.34 |

### Step 6: confirm the topics and start

You see the numbered topic table and the exam as the course now assumes it. Reply in one
line, as often as you like:

```
focus 3,5; skip 9; merge 6+7; weight 2=0.3; exam 120 min 100 pts; ok
```

Then one more question block: how many mock exams (1–3), the scope, and whether to start.
With the start question comes an estimate of the agent runs and time for both scopes.

- **Full** builds everything now.
- **Core first** builds the summary, the MC bank and the plan now, and defers the
  exercises, the mock exams and the cheat sheet; run the command again later to finish
  them.
- **Not now** stops here; the next run continues with this question.

The sample run chose one mock exam (the profile is based on one past exam), full scope.

### Steps 7–13: the course is written

None of these steps needs you, unless something fails twice.

| Step | What happens | Sample run |
|---|---|---|
| 7 Author | `author` agents write the overview, then one summary chapter per topic, then the exercises and the MC bank per topic, following the notes and the notation | an overview, 3 chapters, 21 exercises, 37 MC questions |
| 8 Figures | the figure scripts are rendered and every PNG is looked at | 19 figures |
| 9 Verify | `verifier` agents recompute every exercise and MC question **blind**, from a view without key or solution; disagreements go back to the author for at most two rounds, and what stays wrong is quarantined (hidden) | 58 of 58 verified |
| 10 Mock exams | one author per mock exam, modelled on the profile's archetypes with new values, then verified | `probeklausur-1`: 3 tasks and 6 MC questions, 60 points, 90 minutes |
| 11 Cheat sheet | written from the summaries, fitted into the page limit, every formula checked against its summary chapter | 1 of 2 pages at 9 pt |
| 12 Plan | `studykit plan` schedules the sessions up to the exam; Claude writes each session's goal | 49 sessions, the mock exam a week before the exam |
| 13 Publish | links to exercises and mock exams added, PDFs built, `validate --release`, then `status: ready` and the website build | 9 PDFs, 0 errors |

### Step 14: the report

`studykit pipeline report` writes `courses/<id>/state/pipeline/report.md`, and Claude sums
it up: the counts per part, how much was verified, fixed or quarantined and why, the cheat
sheet's size, what was assumed (for the sample: the exam format and MC rules come from a
single past exam), and the next steps below.

## Resume an interrupted run

Run the same command again. It reads `studykit pipeline status <course>` and continues at
the first step that is not done; finished steps are never redone. You can look yourself:

```bash
just pipeline opamp-grundlagen          # or: uv run --frozen studykit pipeline status opamp-grundlagen
```

```
   0 preflight   done
   ...
   8 figures     done
   9 verify      pending   …
  10 mock-exams  pending
  ...
resume at step 9 (verify)
```

Each step's line says what is missing (`--json` lists it per step as `todo`). The sample
run was itself done over several sessions; the last one started at step 9. Typical
reasons to resume: you said "Not now" in round 2, the session ended, or a step stopped
with findings you fixed. If you changed files in your folder before the topics were made
(step 5), the next run copies and reads the changes first; after that, use
`/add-material`.

## Add material later

New slides, a new exercise sheet or another past exam:

```
/add-material opamp-grundlagen ~/Studium/Elektronik1/VL04_Folien.pdf
```

A folder works too; only what is new or changed is copied (the sample folder again gives
"0 added, 0 changed, 7 unchanged"). The command saves the current `course.yaml`, outline
and exam profile to `_history/<timestamp>/`, reads the new chunks, runs the exam analysis
again when an exam was added, and shows how the topics would change (weights before and
after, new topics). You choose to apply the change, apply it without new topics, or keep
the topics. It then lists the `/regenerate` commands that bring the content up to date,
for example `/regenerate opamp-grundlagen summary --topic integrierer`, without running
them.

## Study

### The website

```bash
just dev
```

Open http://localhost:4321/c/opamp-grundlagen/. The tabs are the overview (topic map and
the exam at a glance), the plan, the summary, exercises with a hint ladder and an answer
check, the MC bank with practice, test and review modes, the mock exams under time, the
cheat sheet and your progress. Each tab links its PDF. Your progress lives in the
browser for this address, which is why the site always runs on port 4321.

### Claude Code commands

| When | Command | What it does |
|---|---|---|
| right after registering | `/examine opamp-grundlagen diagnostic` | 15 MC questions over all topics; seeds the review schedule, and a replan puts your weak topics first |
| stuck on a topic or exercise | `/tutor opamp-grundlagen integrierer` | Socratic tutoring: questions instead of answers, every number checked |
| a solution looks wrong | `/verify opamp-grundlagen <id>` | blind re-verification of one item, a topic, a mock exam or `all` |
| a part should be better or bigger | `/regenerate opamp-grundlagen mc --topic integrierer --add 5` | rewrites one part and everything downstream (old files go to `_history/`) |
| after studying on the website | `/import-progress opamp-grundlagen` | imports the progress you exported on the Progress page and offers a replan |
| any time | `/study-status opamp-grundlagen` | days to the exam, plan adherence, weakest topics, reviews due and one next step |

`/tutor` and `/examine` work best from the shell, where the persona has the session to
itself: `just tutor opamp-grundlagen integrierer`, `just examine opamp-grundlagen
diagnostic`.

A typical week: work through the plan's sessions on the website; export your progress and
run `/import-progress`; `/study-status` names the next step; `/examine <course> mc` for
due reviews, `/tutor <course> <topic>` for the weakest topic. In the last weeks, write the
mock exam under time on the website or with `/examine <course> exam probeklausur-1`.
