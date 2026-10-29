# study-kit

Claude Code agents and skills plus a locally run website for engineering studies.
The full specification is `docs/architecture.md`; read the section you are working on
before changing that area, and keep code and spec in sync.

## Hard rules

- **Never commit anything under `courses/`** (except `courses/README.md`). The repository
  is public; course material and generated course content stay local. Never use
  `git add -f`.
- **Never commit PDFs** outside `tests/fixtures/`. Course PDFs are built into
  `<course>/_build/pdf` (`just pdf`), and tests generate theirs; the pre-commit hook and the
  guard workflow reject the rest.
- **Commits:** Conventional Commits v1.0.0, one logical change per commit,
  `<type>(<scope>): <description>` in lowercase imperative. **Never add a
  `Co-Authored-By` trailer** or any other AI attribution. `.githooks/commit-msg` enforces this.
- Work on a branch per phase or feature; push and merge only when the user asks.
- Code, comments, skills, agents and UI are in English. Generated course content follows
  `course.lang`.

## How to work here

- Entry points: `just <recipe>`, `uv run --frozen studykit …`, `pnpm -C site …`.
  Run `just doctor` if a tool behaves unexpectedly.
- Figures are code: write a script against `studykit.figures`, never hand-written SVG.
- Never compute numbers in your head; use Python (SymPy, NumPy, SciPy) or
  `uv run --frozen studykit calc "<expr>"`.
- Run `studykit validate` (or the narrowest `just` recipe that covers your change) before
  finishing; a full validate also builds the course's PDFs.
- After changing how PDFs look (`typst/`, `pdf.py`, the filter's Typst branch), build the
  sample course's PDFs and look at the pages (render them to PNG with pypdfium2).
- Grep and Glob may skip the gitignored `courses/`; use `studykit ls` or explicit paths.
- Pin exact versions; `toolchain.toml`, `uv.lock` and `site/pnpm-lock.yaml` are the source
  of truth.

## Claude Code layer (`.claude/`, docs/architecture.md §5)

- Commands: `/regenerate`, `/verify`, `/tutor`, `/examine`, `/import-progress`,
  `/study-status` (`.claude/skills/<name>/SKILL.md`). Internal skills the agents preload:
  `content-format`, `authoring`, `figures`, `verify-protocol`.
- Agents: `author`, `verifier`, `tutor`, `examiner` (`.claude/agents/`). No agent has the
  Agent tool, none has memory. The verifier works blind: its hook
  (`studykit hook verifier-guard`) denies it item files, keys and solutions; it works from
  `studykit blind`.
- `just tutor <course>` and `just examine <course> [mode]` start the tutor and the examiner
  as the main thread; `just verify` and `just status` wrap the CLI.
- Hooks in `.claude/settings.json`: every Write or Edit of a course file runs
  `studykit lint --hook` (fix what it prints at once); `studykit hook pre-git` blocks git
  commands that would commit course files.
- When you change a skill or an agent, run `uv run --frozen pytest -q tests/py/test_claude.py`:
  it checks frontmatter, referenced files, `studykit` commands and `just` recipes.
