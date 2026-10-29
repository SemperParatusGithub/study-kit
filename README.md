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
| `just doctor` | Checks every tool against `toolchain.toml` and reports how to fix mismatches |
| `just validate [course]` | Checks a course (or all) against the content format; `--release` adds coverage |
| `just lint <files>` | Quick check of edited course files, as the Claude Code hook runs it |
| `just figures [course]` | Renders the figure scripts of a course |
| `just test` | Python tests, schema drift and the golden math corpus (KaTeX and pandoc → Typst) |
| `just lint-code` | ruff lint and format check of the Python code |

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
