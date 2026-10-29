# study-kit task runner. First run on a fresh clone:
#   uv run --frozen studykit tools install && .tools/bin/just setup

set shell := ["bash", "-euo", "pipefail", "-c"]

root := justfile_directory()
export PATH := root / ".tools/bin" + ":" + env("PATH")
export ASTRO_TELEMETRY_DISABLED := "1"
# absolute, so python (run from the repo root) and the site (run from site/) agree on a
# relative value: it is relative to the repo root
export STUDYKIT_COURSES_DIR := absolute_path(env("STUDYKIT_COURSES_DIR", root / "courses"))

sk := "uv run --frozen studykit"
# recipes that run other recipes call this very just with this justfile
just := quote(just_executable()) + " --justfile " + quote(justfile())

# list recipes
default:
    @just --list

# install everything (idempotent)
setup:
    uv sync --frozen
    {{sk}} tools install
    pnpm -C site install --frozen-lockfile
    git config core.hooksPath .githooks
    {{sk}} doctor

# check that every tool matches toolchain.toml
doctor *flags:
    {{sk}} doctor {{flags}}

# render the figure scripts of one course (or all)
figures course="":
    {{sk}} fig build {{course}}

# website at http://localhost:4321 (strictPort: progress is tied to the origin)
dev: (figures "")
    pnpm -C site dev

# Figures, validation and PDFs cover `course` (or every course); the site is built for all
# courses and reads each course's PDF manifest.
# figures, validation and PDFs, then the strict site build with search index and link check
build course="": (figures course) (validate course) (pdf course)
    STUDYKIT_STRICT=1 pnpm -C site build
    {{sk}} check-links site/dist

# PDFs of one course (or all) into <course>/_build/pdf, with manifest.json for the site
pdf course="":
    {{sk}} pdf {{course}}

# cheat sheet within its page limit; exits 3 with the overflow when even 7 pt is too long
cheatsheet course:
    {{sk}} cheatsheet fit {{course}}

# every internal link and #anchor of the built site resolves
check-links dist="site/dist":
    {{sk}} check-links {{dist}}

# quick check of edited course files (what the Claude Code hook runs)
lint +files:
    {{sk}} lint {{files}}

# full check of one course (or all); flags: --quick, --release, --paths, --json
validate course="" *flags:
    {{sk}} validate {{course}} {{flags}}

# regenerate schemas/*.schema.json from the pydantic models
schema:
    {{sk}} schema export

# python and node unit tests, the git hooks, schema drift and the golden math corpus
test:
    uv run --frozen pytest -q
    pnpm -C site run test:unit
    bash .github/scripts/test-hooks.sh
    {{sk}} schema export --check
    {{sk}} golden

# The e2e suite runs against site/dist, so build the sample course first:
#   STUDYKIT_COURSES_DIR=examples just build sample-course
# Playwright fetches its Chromium on first use; args go to `playwright test`.
# browser tests of the built sample course (site/tests/e2e)
[positional-arguments]
e2e *args:
    pnpm -C site exec playwright install chromium
    pnpm -C site run e2e "$@"

# `test` includes `schema export --check`; the sample course comes from examples/. CI then
# runs the browser suites too: `pnpm -C site run test:elements` and `just e2e`.
# CI checks before the browser tests: doctor, tests, sample-course build and validation
ci:
    {{just}} doctor
    {{just}} test
    STUDYKIT_COURSES_DIR={{quote(root / "examples")}} {{just}} build sample-course
    STUDYKIT_COURSES_DIR={{quote(root / "examples")}} {{just}} validate sample-course --release

# ruff lint and format check of the python code
lint-code:
    uv run --frozen ruff check src tests
    uv run --frozen ruff format --check src tests
