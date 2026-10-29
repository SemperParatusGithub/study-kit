# study-kit

Claude Code agents and skills plus a locally run website for engineering studies.
Point it at a folder of lecture material and it builds, per subject, an overview, a study
plan, a summary, exercises with hints and verified solutions, a multiple-choice bank, a
cheat sheet of at most three pages and mock exams modelled on past exams, all readable in
the browser and exportable as PDF.

> Status: under construction. The full design is in [docs/architecture.md](docs/architecture.md).

## Requirements

macOS on Apple silicon or Linux x86_64 with:

- [uv](https://docs.astral.sh/uv/) ≥ 0.11.30 (manages Python 3.14 itself)
- Node.js ≥ 24.17 and pnpm ≥ 11.22 (`corepack enable pnpm`)
- git and curl

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
| `just figures [course]` | Renders the figure scripts of a course |
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

## Your course data stays local

Everything under `courses/` is gitignored. A pre-commit hook, a CI guard and Claude Code
hooks make sure lecture material and generated content are never committed to this public
repository.

## Contributing

Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), one
logical change each; the `commit-msg` hook enforces it. See [CLAUDE.md](CLAUDE.md) for the
rules Claude Code follows in this repository.

## License

[MIT](LICENSE)
