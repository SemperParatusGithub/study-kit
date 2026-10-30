---
name: ingest
description: How study-kit reads a course's lecture material - the chunk digest procedure (page text first, the PDF page as an image only for flagged pages, scanned pages transcribed into sources/text), the notes file of one chunk, the exam profile and notation of the exam analysis, and the gates each must pass. Use when writing sources/notes/<chunk>.md, a page transcription, analysis/exam-profile.yaml or analysis/notation.yaml.
user-invocable: false
---

# Reading the lecture material

`/register-new-subject` (docs/architecture.md §5.4) turns a folder of lecture PDFs into a
course. `studykit ingest init` and `extract` have already copied the PDFs, extracted their
page text and cut them into chunks; you turn one chunk into notes (the `ingester`) or all
past exams into the exam profile (the `exam-analyst`). The main thread merges the notes into topics
afterwards, so notes are faithful digests, not course content.

## What is there

```
<course>/sources/manifest.yaml               documents: id, title, kind, pages, sha256; answers.round1
<course>/sources/chunks.yaml                 chunks: id, doc, kind, first, last, flagged, scanned, sha256
<course>/sources/raw/<doc>.pdf               the PDF (page n of the chunk = page n of the PDF)
<course>/sources/text/<doc>/p0001.txt        page text from the PDF's text layer (4-digit page number)
<course>/sources/text/<doc>/index.json       per page: chars, garbled, graphics, shapes, visual, scanned, reasons
<course>/sources/text/<doc>/p0001.vision.md  your transcription of a scanned page
<course>/sources/notes/<chunk>.md            your notes of one chunk
<course>/analysis/exam-profile.yaml          the exam profile (exam-analyst)
<course>/analysis/notation.yaml              the notation (exam-analyst)
```

The course directory is gitignored: Grep and Glob may skip it. Read files by their
explicit path (`uv run --frozen studykit ls <course>` lists the course files; the chunk
plan names every page), and search page texts with `grep -rn '<pattern>' <course>/sources/text`
in Bash. Never change `manifest.yaml`, `chunks.yaml`, `sources/raw/`, a `p0001.txt` or
`index.json`: only `studykit ingest extract|add` writes them.

## Chunk digest procedure (ingester)

Your assignment names the course directory and one chunk id.

1. **Find the chunk** in `sources/chunks.yaml`: `doc`, `kind`, `first`-`last`, `flagged`,
   `scanned`, `sha256`. Read the document's entry in `sources/manifest.yaml` (title, kind)
   and `answers.round1.lang` (the course language).
2. **Text first.** Read `sources/text/<doc>/pNNNN.txt` for every page of the chunk, in
   order. Most pages need nothing more: the text layer has the words, and formulas come
   out as Unicode italics (`𝑈𝑒` is $U_\mathrm{e}$) with fractions split over lines.
3. **Images only for flagged pages.** For each page in `flagged`, Read the PDF page:
   Read `<course>/sources/raw/<doc>.pdf` with `pages: "<n>"` (one page or a short range
   such as `"5-6"`, never the whole document; an agent that cannot read PDFs, such as
   Codex, runs `uv run --frozen studykit ingest page <course> <doc> <n>` and looks at the
   PNG it prints). `index.json` says why a page is flagged
   (little text, garbled glyphs, large images, many drawn shapes): look at the circuit,
   plot or table and describe it in the notes. Do not open pages that are not flagged
   unless the text is unusable (then list them in `visual_pages` too).
4. **Transcribe scanned pages.** A page in `scanned` has no text layer. Read it as an
   image and Write `sources/text/<doc>/pNNNN.vision.md` (same 4-digit number): the full
   page as Markdown in the source language, formulas as `$…$` in the math subset of the
   content-format skill, figures as one bracketed line (`[Schaltbild: …]`), illegible
   parts as `[unleserlich]` (English material: `[illegible]`). Never invent what you cannot
   read. Then digest the page like any other.
5. **Write the notes** `sources/notes/<chunk>.md` from
   [templates/notes.md](templates/notes.md) (rules below).
6. **Gate:** `uv run --frozen studykit validate <course> --paths sources/notes/<chunk>.md`
   reports no error. The lint hook already checks every Write; fix what it prints at once.
   Every scanned page of the chunk has its `.vision.md`.
7. **Return** one compact JSON object as your final message, nothing else:

```json
{"chunk": "vl-03-c01", "notes": "sources/notes/vl-03-c01.md",
 "topics": ["invertierender-verstaerker", "integrierer"], "visual_pages": [5, 8],
 "transcribed": [], "validate": "ok", "notes_on_quality": "one line, optional"}
```

The caller judges success from the files and `studykit pipeline status`, not from this
report.

## Notes rules

**Frontmatter** (`studykit.model.ChunkNotes`, `schemas/notes.schema.json`; every field is
checked, unknown fields are errors):

| Field | Value |
|---|---|
| `chunk` | the chunk id, equal to the file name |
| `doc` | the chunk's `doc` |
| `pages` | `'<first>-<last>'` of the chunk, single-quoted (`'1-1'` for one page) |
| `source_sha256` | the chunk's `sha256` from `sources/chunks.yaml`, single-quoted |
| `kind` | the chunk's `kind` |
| `title` | what the chunk covers, in the course language, one line |
| `topics` | 1 to 5 candidate topic slugs (below) |
| `visual_pages` | the pages you Read as images, `[]` if none |

**Candidate topics** are kebab-case ASCII slugs in the course language (ä → ae, ö → oe,
ü → ue, ß → ss): `invertierender-verstaerker`, `komplexe-wechselstromrechnung`,
`bode-diagramm`. Name a chapter-sized concept as the material names it, not a single
formula and not the whole subject. Other ingesters work on other chunks at the same time;
the main thread maps everyone's slugs to the 6 to 15 course topics.

**Body:** the sections of the template, in this order, headings in English (the main
thread reads them by name), content in the course language with the source's terms and
symbols. Leave a section with "–" when the chunk has nothing for it; never drop it.

- `## Summary`: three to eight sentences on what the chunk teaches and how.
- `## Course facts`: what the material states about the course itself, word for word where
  it matters: course title, semester, lecturer, exam date, duration, points, allowed aids,
  MC rules. Only what is written; "–" otherwise.
- `## Topics`: one line per candidate slug with its pages.
- `## Formulas`: every formula a student must know, as display math, each followed by one
  line with its meaning, conditions and the page link. Transcribe faithfully, in the math
  subset (`\mathrm{j}`, `\underline{U}`, `{,}` for a German decimal comma, no denied
  macros).
- `## Definitions`: term and definition, with the page.
- `## Examples`: worked examples with their given values and results as the source states
  them. Do not recompute them in your head; when a result looks wrong, check it with
  `uv run --frozen studykit calc "<expr>"` and note the difference under Open questions.
- `## Exercise archetypes`: the kinds of tasks the chunk poses or prepares for, one line
  each: a kebab id, what is given and asked, the method, the pages (exercise sheets and
  exams: every task; slides and scripts: the tasks the examples prepare).
- `## Notation`: the conventions you saw: imaginary unit `j` or `i`, unit step `ε(t)`,
  `σ(t)` or `u(t)`, phasors underlined, bold or with a hat, RMS or peak phasors, decimal
  comma or point, index style. Only what the chunk shows.
- `## Figures`: for every visual page, what the figure shows: circuit topology with
  component values and reference arrows, plot axes and key points, table contents.
- `## Open questions`: unreadable parts, contradictions, apparent errors in the source.

**Page links** are `[S. 5](src:<doc>#p=5)` (English material: `[p. 5]`); the page is the
PDF page, between 1 and the document's page count (SK-REF-SRC). Every formula, definition,
example and archetype carries one, so authors can cite the lecture later.

**Format:** the content-format dialect without container blocks (notes allow none), no
H1, no raw HTML, math in the subset (the Math stage checks notes; SK-MATH codes name the
replacement). Inline code is fine for archetype ids.

## Exam analysis (exam-analyst)

The procedure is in [exam-analysis.md](exam-analysis.md); the files it writes:

| File | Template | Model and schema |
|---|---|---|
| `analysis/exam-profile.yaml` with past exams | [templates/exam-profile.yaml](templates/exam-profile.yaml) | `ExamProfile`, `schemas/exam-profile.schema.json` |
| `analysis/exam-profile.yaml` without past exams | [templates/exam-profile-no-exams.yaml](templates/exam-profile-no-exams.yaml) | the same |
| `analysis/notation.yaml` | [templates/notation.yaml](templates/notation.yaml) | `Notation`, `schemas/notation.schema.json` |

Rules both files share:

- Shares (`archetypes[].share`, `mc.type_mix`, `topic_weights`) each add up to 1 within
  0.02 (SK-SCHEMA-SHARES). Compute them with `uv run --frozen studykit calc`, round to two
  decimals and put the rounding remainder on the largest share.
- `topic` fields and `topic_weights` keys are candidate topic slugs while `course.yaml`
  still has only the placeholder topic `draft`; the main thread maps them to the course
  topics in the synthesis step. Once real topics exist they must be course topics
  (SK-REF-MISSING).
- `exams` lists the document ids of the analysed past exams (kind `exam`; their solutions
  count as sources, not as exams). `basis: past-exams` needs at least one.
- No double quotes in YAML; single-quote values with a backslash, a colon or a `$`.

## Outline (main thread)

The synthesis step writes `sources/outline.md` from [templates/outline.md](templates/outline.md):
one section per course topic with its id, weight, prerequisites, the chunks and pages it
draws on, the key formulas and archetypes, and a chunk table that names every chunk id.
`studykit pipeline status` checks that the outline names every topic id and every chunk
id; authors read the outline to find the notes of their topic.

## Gates

| Step | Passes when |
|---|---|
| a chunk's notes | `uv run --frozen studykit validate <course> --paths sources/notes/<chunk>.md` has no error; `doc`, `pages` and `source_sha256` equal the chunk's (SK-REF-CHUNK); every scanned page has its `.vision.md` |
| the exam analysis | `uv run --frozen studykit validate <course> --paths analysis` has no error |
| the reading step | `uv run --frozen studykit pipeline status <course> --json`: step 4 (`read`) is `done`; its `todo` lists `chunks_without_notes`, `notes_invalid`, `notes_stale`, `lint_errors`, `exam_profile`, `notation` and `transcriptions_missing` otherwise |

SK codes you may meet: SK-SCHEMA-MISSING, SK-SCHEMA-UNKNOWN, SK-SCHEMA-VALUE (frontmatter
and YAML fields), SK-SCHEMA-SHARES (shares), SK-YAML-DQUOTE and SK-YAML-BACKSLASH (quoting),
SK-STRUCT-PATH (notes file name and `chunk` differ), SK-REF-CHUNK (notes and chunk plan
disagree), SK-REF-SRC (a page link outside the document), SK-REF-MISSING (an unknown
document or topic), SK-MATH-DENIED and SK-MATH-BLOCKMARK (math subset). Each is explained
with its fix in `docs/content-format/errors.md`.
