# study-kit

Agents and skills for Claude Code and Codex plus a locally run website for engineering
studies. The full specification is `docs/architecture.md`; read the section you are
working on before changing that area, and keep code and spec in sync. `CLAUDE.md` holds
the same rules for Claude Code; change both together.

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
- `rg` skips the gitignored `courses/`; use `studykit ls` (files),
  `studykit index <course> --json` (ids), `rg --no-ignore` or explicit paths.
- Pin exact versions; `toolchain.toml`, `uv.lock` and `site/pnpm-lock.yaml` are the source
  of truth.
- Ledger files (`state/verify/`) are written only by `studykit verify`, `progress/` only
  by `studykit progress import|log|report`, and `plan.yaml` only by `studykit plan`, except
  each session's goal and note. Never edit them by hand.

## Codex (docs/architecture.md §5.5)

The commands, skills and agents are written once, for Claude Code, in `.claude/`; Codex
uses the same files:

- **Skills:** `.agents/skills` links to `.claude/skills`. The user commands
  (`register-new-subject`, `add-material`, `regenerate`, `verify`, `tutor`, `examine`,
  `import-progress`, `study-status`) run only when typed, as `$register-new-subject <folder>`
  instead of `/register-new-subject <folder>`; their `agents/openai.yaml` turns off implicit
  invocation. The internal skills `ingest`, `content-format`, `authoring`, `figures` and
  `verify-protocol` are read by the agents.
- **Agents:** `.codex/agents/{ingester,exam-analyst,author,verifier}.toml` are generated from
  `.claude/agents/*.md` by `uv run --frozen studykit codex agents` (`just codex-agents`;
  `just test` checks they are current). Never edit them by hand. When a command says to
  start agents, spawn these subagents by name, at most 6 at a time
  (`.codex/config.toml`). The tutor and the examiner are the main thread:
  `STUDYKIT_AGENT=codex just tutor <course>` and `STUDYKIT_AGENT=codex just examine <course>`.
- **Hooks and rules** (`.codex/hooks.json`, `.codex/rules/`, loaded once you trust the
  project): every `apply_patch` of a course file runs `studykit lint --hook` (fix what it
  prints at once), `studykit hook pre-git` blocks git commands that would commit course
  files, and `git add -f` is forbidden.
- **The verifier is blind only by its instructions under Codex:** no hook stops it from
  reading keys. Prefer Claude Code for `$verify` and the verifier waves of
  `$register-new-subject` and `$regenerate` when you can.

Reading skills and agents written for Claude Code:

| Claude Code | Codex |
|---|---|
| `/name args` | `$name args`; `$ARGUMENTS` is the text after the skill name, `$0`, `$1`, … its words |
| start the `author` (or other) agent | spawn the custom agent of that name with the same prompt |
| Read, Write, Edit | read with the shell (`sed -n`, `cat`), write with `apply_patch` |
| Glob, Grep | `studykit ls`, `rg --no-ignore`, `find` |
| Read a PDF with `pages` | `uv run --frozen studykit ingest page <course> <doc> <pages>`, then view the PNGs it prints |
| Read a PNG | view the image |
| AskUserQuestion | `request_user_input` when available, otherwise ask in chat with lettered options and wait for the answer |
| `allowed-tools`, `permissions` | your approval policy; `.codex/rules/` |
| `${CLAUDE_PROJECT_DIR}` | the repository root (`git rev-parse --show-toplevel`) |

When you change a skill or an agent, run `uv run --frozen studykit codex agents` and
`uv run --frozen pytest -q tests/py/test_claude.py`: it checks frontmatter, referenced
files, `studykit` commands, `just` recipes and the Codex files.
