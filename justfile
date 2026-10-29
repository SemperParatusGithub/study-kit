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

# strict site build with search index and link check (all courses; validates `course`)
build course="": (figures course) (validate course)
    STUDYKIT_STRICT=1 pnpm -C site build
    {{sk}} check-links site/dist

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

# python and node unit tests, schema drift and the golden math corpus
test:
    uv run --frozen pytest -q
    pnpm -C site run test:unit
    {{sk}} schema export --check
    {{sk}} golden

# The e2e suite runs against site/dist, so build the sample course first:
#   STUDYKIT_COURSES_DIR=examples just build sample-course
# Playwright fetches its Chromium on first use; args go to `playwright test`.
# browser tests of the built sample course (site/tests/e2e)
e2e *args:
    pnpm -C site exec playwright install chromium
    pnpm -C site run e2e {{args}}

# ruff lint and format check of the python code
lint-code:
    uv run --frozen ruff check src tests
    uv run --frozen ruff format --check src tests
