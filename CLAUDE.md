# study-kit

Claude Code agents and skills plus a locally run website for engineering studies.
The full specification is `docs/architecture.md`; read the section you are working on
before changing that area, and keep code and spec in sync.

## Hard rules

- **Never commit anything under `courses/`** (except `courses/README.md`). The repository
  is public; course material and generated course content stay local. Never use
  `git add -f`.
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
- Never compute numbers in your head; use Python (SymPy, NumPy, SciPy; `studykit calc`
  comes with Phase 5).
- Run `studykit validate` (or the narrowest `just` recipe that covers your change) before
  finishing.
- Grep and Glob may skip the gitignored `courses/`; use `studykit ls` or explicit paths.
- Pin exact versions; `toolchain.toml`, `uv.lock` and `site/pnpm-lock.yaml` are the source
  of truth.
