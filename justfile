# study-kit task runner. First run on a fresh clone:
#   uv run --frozen studykit tools install && .tools/bin/just setup

set shell := ["bash", "-euo", "pipefail", "-c"]

root := justfile_directory()
export PATH := root / ".tools/bin" + ":" + env("PATH")
export ASTRO_TELEMETRY_DISABLED := "1"
export STUDYKIT_COURSES_DIR := env("STUDYKIT_COURSES_DIR", root / "courses")

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

# python tests and the golden math corpus
test:
    uv run --frozen pytest -q
    {{sk}} golden

# lint and format check
lint:
    uv run --frozen ruff check src tests
    uv run --frozen ruff format --check src tests
