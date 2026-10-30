# study-kit

Claude Code and Codex agents and skills plus a locally run website for engineering studies.
Point it at a folder of lecture material and it builds, per subject, an overview, a study
plan, a summary, exercises with hints and verified solutions, a multiple-choice bank, a
cheat sheet of at most three pages and mock exams modelled on past exams, all readable in
the browser and exportable as PDF.

> Status: everything in the design works (Phases 0–6): building a course from a folder of
> lecture PDFs (`/register-new-subject`), the website, the PDFs, and the Claude Code
> commands for verifying, regenerating, tutoring and examining. The full design is in
> [docs/architecture.md](docs/architecture.md); [docs/walkthrough.md](docs/walkthrough.md)
> follows one subject from its PDFs to studying it.

## Requirements

macOS on Apple silicon or Linux x86_64 with:

- [uv](https://docs.astral.sh/uv/) ≥ 0.11.30 (manages Python 3.14 itself)
- Node.js ≥ 24.17 and pnpm ≥ 11.22 (`corepack enable pnpm`)
- git and curl
- [Claude Code](https://github.com/anthropics/claude-code) (`claude`) or
  [Codex](https://github.com/openai/codex) (`codex`) for the commands, agents and skills in
  `.claude/` (see [Using Codex](#using-codex)); everything else works without them

pandoc, Typst and just are **not** installed system-wide: `studykit tools install` downloads
the exact versions pinned in [toolchain.toml](toolchain.toml), verifies their sha256 and puts
them in `.tools/bin`.

## Setup

```bash
uv run --frozen studykit tools install
.tools/bin/just setup
```

`just setup` is idempotent: it syncs the Python environment, installs the pinned tools and
the site dependencies, activates the git hooks and runs `just doctor`. Add `.tools/bin` to
your `PATH` (or use `.tools/bin/just`) to call `just` directly.

## Quick start: register a subject

Put the subject's PDFs in one folder (slides, script, exercise sheets, solutions and, most
important, past exams; export office files as PDF first), open Claude Code in the
repository and run:

```
/register-new-subject ~/Studium/Elektronik1
```

It shows an inventory of the folder and asks four questions (exam date, format, cheat
sheet, hours per week), reads the material with agents, proposes the topics, and asks
once more (focus and skip topics, number of mock exams, full or core scope, go). Then it
writes and verifies the course and builds its PDFs and website pages; finally:

```bash
just dev        # http://localhost:4321/c/<course>/
```

The command copies your PDFs into `courses/<course>/sources/raw/` and never changes your
folder. Run it again to resume an interrupted run (`just pipeline <course>` shows where
it stands); `/add-material <course> <file|folder>` adds material later. To try it without
your own material, `just sample-materials` builds a set of German lecture PDFs on op-amp
circuits into `examples/sample-materials/_build/materials`. The
[walkthrough](docs/walkthrough.md) explains every step.

## Everyday commands

| Command | What it does |
|---|---|
| `just dev` | Renders the figures and serves the website at http://localhost:4321 |
| `just build [course]` | Figures, validation, PDFs, strict site build with search index, link check of `site/dist` |
| `just pdf [course]` | Builds a course's PDFs (or every course's) into `<course>/_build/pdf/`; only documents whose sources changed are rebuilt |
| `just cheatsheet <course>` | Fits the cheat sheet into its page limit (9 pt down to 7 pt); exits 3 with the longest sections when even 7 pt is too long |
| `just doctor` | Checks every tool against `toolchain.toml` and reports how to fix mismatches |
| `just validate [course]` | Checks a course (or all) against the content format and builds its PDFs (`--quick` skips them); `--release` adds the site check (strict build, search index, type check, link check) and coverage |
| `just lint <files>` | Quick check of edited course files, as the Claude Code hook runs it |
| `just status <course>` | Study status: days to the exam, plan adherence, weakest topics, reviews due, last mock exam (`--today YYYY-MM-DD`, `--json`) |
| `just verify <course> [target]` | Runs the verifier's existing checks for an item, topic, exam or `all` and updates the ledger `state/verify/`; `--status` only shows it, `--report` writes `state/verify/report.md` |
| `just tutor <course> [topic]` | Starts Claude Code as the Socratic tutor (`/tutor`; an exercise id works too) |
| `just examine <course> [mode]` | Starts Claude Code as the examiner (`/examine`) |
| `just figures [course]` | Renders the figure scripts of a course |
| `just pipeline <course>` | Where `/register-new-subject` stands: each step's status and the step a new run resumes at (`--json`) |
| `just ingest <action> …` | `studykit ingest scan\|init\|extract\|add\|round2\|page`, the Python side of registering a subject |
| `just sample-materials` | Builds the sample lecture PDFs (`examples/sample-materials`) into its gitignored `_build/materials` |
| `just test` | Python and Node unit tests, the git hooks, schema drift and the golden math corpus (KaTeX and pandoc → Typst) |
| `just e2e` | Playwright tests of the built sample course in Chromium (build it first, see below) |
| `just ci` | `doctor`, `test`, a strict build of the sample course with its PDFs and its release validation (CI also runs `lint-code` and the browser tests) |
| `just lint-code` | ruff lint and format check of the Python code |

The website always runs on port 4321: progress lives in the browser's storage for that
origin. Search uses the index of the last `just build`.

### PDFs

`just pdf <course>` writes, in the course language, `overview.pdf`, `summary.pdf`,
`exercises.pdf` (hints and solutions in the appendix), `exercises-blank.pdf`, `mc.pdf`
(answer key in the appendix), `<exam>.pdf` and `<exam>-solutions.pdf` per mock exam,
`cheatsheet.pdf` and `plan.pdf` to `courses/<course>/_build/pdf/`, together with
`manifest.json` (page count and size of each). The website links each PDF from its tab and
serves it at `/c/<course>/pdf/<file>`; a document that is not built or failed has no link.
PDFs built while `just dev` runs appear on the next page load. Every Typst or pandoc
warning fails a document, and a document that fails keeps its previous PDF. Generated PDFs
are never committed.

### The sample course

`examples/sample-course` is a complete German course (three topics, exercises, an MC bank,
a mock exam, a cheat sheet and a plan). To look at it, point the recipes at `examples/`:

```bash
STUDYKIT_COURSES_DIR=examples just build sample-course   # once, for the search index and PDFs
STUDYKIT_COURSES_DIR=examples just dev
```

Its PDFs land in `examples/sample-course/_build/pdf/`; `STUDYKIT_COURSES_DIR=examples just
pdf sample-course` rebuilds them on their own. CI uploads them as the `sample-course-pdfs`
artifact on every run.

There are two sets of browser tests, both in Chromium through Playwright:

```bash
just e2e                         # the built sample course: build it first, as above
pnpm -C site run test:elements   # the custom elements in their own harness, no build needed
```

`just e2e` downloads Chromium on first use (the harness needs it too) and passes extra
arguments to `playwright test`, for example `just e2e --repeat-each 3`. `SK_E2E_PORT` moves
the suite off port 4321 while a dev server holds it. Reports and traces are written to
`site/node_modules/.cache/sk-e2e/`.

CI runs `just lint-code` and `just ci`, then both browser suites, so the full local
equivalent is:

```bash
just lint-code && just ci && pnpm -C site run test:elements && just e2e
```

## Studying with Claude Code

Open Claude Code in the repository (`claude`). The commands take a course id from
`courses/` (or a course directory): one you registered, or the sample course copied into
`courses/`, which stays local:

```bash
cp -R examples/sample-course courses/
```

| Command | What it does |
|---|---|
| `/register-new-subject <folder> [course-id]` | Builds a course from a folder of lecture PDFs (see the quick start above); resumes where it stopped. |
| `/add-material <course> <file\|folder>` | Copies and reads new or changed PDFs, proposes how the topics change (applied after you confirm) and lists the `/regenerate` runs that bring the content up to date. |
| `/study-status <course>` | Where you stand: days to the exam, plan adherence, weakest topics, reviews due, the last mock exam, and one recommended next step. Read-only. |
| `/tutor <course> [topic\|ex-id]` | Socratic tutoring: works through a topic or one exercise by asking rather than lecturing, checks every number with `studykit calc` and writes nothing. |
| `/examine <course> [mode]` | Strict examiner. Modes: `diagnostic` (15 questions over all topics), `topic <t>`, `mc` (the default: due reviews, then weak topics), `weak`, `misconceptions`, `exam <id>` (a mock exam under time) and `oral`. It asks for your confidence before revealing anything and logs every graded item to `progress/examiner.jsonl`. |
| `/import-progress <course> [file]` | Brings the progress from the website into the course: export it on the Progress page ("Export progress"), and the command finds the newest `studykit-progress-<course>-*.json` in `~/Downloads`, asks before importing, merges it, writes the mastery report and offers a replan. |
| `/verify <course> [id\|topic\|exam\|all]` | Blind re-verification: verifier agents recompute each item from a view without key or solution, author agents fix disputed items for at most two rounds, and what stays disputed is quarantined (hidden from the website and the PDFs). The report is `state/verify/report.md`. |
| `/regenerate <course> <part> [--topic t] [--add n] [--replace] [note]` | Rewrites one part (`overview`, `plan`, `summary`, `exercises`, `mc`, `figures`, `exams`, `cheatsheet` or `all`) and everything downstream: verification, plan, validation and PDFs. Old files go to `<course>/_history/`, surviving items keep their ids, and `--replace` and `all` ask first. Example: `/regenerate sample-course mc --topic rc-filter --add 3`. |

`/tutor` and `/examine` are best started from the shell, so the persona has the session to
itself: `just tutor sample-course rc-filter`, `just examine sample-course diagnostic`.

A typical week: work through the plan on the website; export your progress and run
`/import-progress`; `/study-status` names the next step; `/examine <course> mc` for due
reviews or `/tutor <course> <topic>` for the weakest topic. The examiner's results update
`progress/mastery.json`, which the course cards show until the browser has answers of its
own, and `studykit plan` uses them when it replans (`/regenerate <course> plan`).

Inside Claude Code, every edit of a course file is linted at once, git commands that would
commit course files are blocked, and the verifier cannot read keys or solutions
(docs/architecture.md §5).

## Using Codex

Codex uses the same commands, skills and agents. Open `codex` in the repository and trust
the project, so it loads `.codex/` (the agents, hooks and rules); `/hooks` asks you to
trust the lint and git hooks once. Then type the commands with `$` instead of `/`:

```
$register-new-subject ~/Studium/Elektronik1
$study-status sample-course
```

`STUDYKIT_AGENT=codex just tutor sample-course rc-filter` and
`STUDYKIT_AGENT=codex just examine sample-course diagnostic` start the tutor and the
examiner in Codex. [AGENTS.md](AGENTS.md) holds the rules Codex follows here and how it
reads the skills; `.codex/agents/` is generated from `.claude/agents/` (`just codex-agents`).
One difference: under Codex no hook stops the verifier from reading keys, so it stays blind
only by its instructions; prefer Claude Code for `/verify` when you have both.

## Your course data stays local

Everything under `courses/` is gitignored. A pre-commit hook, a CI guard and Claude Code
hooks make sure lecture material and generated content are never committed to this public
repository.

## Contributing

Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), one
logical change each; the `commit-msg` hook enforces it. See [CLAUDE.md](CLAUDE.md) and
[AGENTS.md](AGENTS.md) for the rules Claude Code and Codex follow in this repository.

## License

[MIT](LICENSE)
