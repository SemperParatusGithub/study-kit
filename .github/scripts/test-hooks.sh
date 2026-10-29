#!/usr/bin/env bash
# Tests for the git hooks in .githooks. Every case runs in a throwaway repository, so the
# checkout that runs the tests is never touched. Usage: bash .github/scripts/test-hooks.sh
set -euo pipefail

root=$(cd "$(dirname "$0")/../.." && pwd)
hooks="$root/.githooks"

# Ignore the caller's git setup: no repository from the environment, no global or system
# config (hooks, signing, templates) and a fixed identity.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR \
  GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CEILING_DIRECTORIES
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=hooks-test GIT_AUTHOR_EMAIL=hooks-test@example.invalid
export GIT_COMMITTER_NAME=hooks-test GIT_COMMITTER_EMAIL=hooks-test@example.invalid

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

failures=0

# expect <pass|fail> <description> <command...>: the command succeeds (pass), or it fails
# (fail) and its output names the check that rejected it ($rejected_by), so a broken test
# setup cannot pass as a rejection
expect() {
  local want=$1 name=$2 got=pass
  shift 2
  "$@" >"$tmp/out" 2>&1 || got=fail
  if [ "$got" = fail ] && ! grep -qF -- "$rejected_by" "$tmp/out"; then
    got="fail without a message from $rejected_by"
  fi
  if [ "$got" = "$want" ]; then
    printf 'ok   %s\n' "$name"
  else
    printf 'FAIL %s (expected %s, got %s)\n' "$name" "$want" "$got"
    sed 's/^/       /' "$tmp/out"
    failures=$((failures + 1))
  fi
}

# new_repo: print the path of a new repository that runs this checkout's hooks
new_repo() {
  local repo
  repo=$(mktemp -d "$tmp/repo.XXXXXX")
  git init -q -b main "$repo"
  git -C "$repo" config core.hooksPath "$hooks"
  git -C "$repo" commit -q --allow-empty -m "chore: start"
  printf '%s\n' "$repo"
}

# commit_file <path>: stage a new file at <path> and commit it through the hooks
commit_file() {
  local repo
  repo=$(new_repo)
  mkdir -p "$repo/$(dirname "$1")"
  printf 'x\n' >"$repo/$1"
  git -C "$repo" add -- "$1"
  git -C "$repo" commit -q -m "test: add a file"
}

# literal_pathspecs <command...>: run <command> with git's pathspec magic switched off
literal_pathspecs() {
  GIT_LITERAL_PATHSPECS=1 "$@"
}

# commit_msg <message>: run the commit-msg hook on <message>
commit_msg() {
  printf '%s\n' "$1" >"$tmp/msg"
  sh "$hooks/commit-msg" "$tmp/msg"
}

echo "pre-commit"
rejected_by="pre-commit:"
expect fail "course file" commit_file "courses/et1/overview.md"
# git quotes names with non-ASCII characters or quotes in its path output
expect fail "course file with an umlaut and a space" commit_file "courses/et1/sources/Übung 3.md"
expect fail "course file with a double quote" commit_file 'courses/et1/sources/"draft".md'
expect pass "courses/README.md" commit_file "courses/README.md"
expect pass "ordinary file" commit_file "docs/notes.md"
expect pass "ordinary file with an umlaut" commit_file "docs/Übersicht.md"
expect fail "pdf" commit_file "docs/plain.pdf"
expect fail "upper-case pdf at the top level" commit_file "Skript.PDF"
expect fail "pdf with an umlaut and a space" commit_file "docs/Skript Ü.pdf"
expect pass "pdf under tests/fixtures" commit_file "tests/fixtures/sample.pdf"
expect pass "pdf with an umlaut under tests/fixtures" commit_file "tests/fixtures/Übung.pdf"
# with literal pathspecs from the environment, the PDF pattern would match nothing
expect fail "pdf with GIT_LITERAL_PATHSPECS set" literal_pathspecs commit_file "docs/plain.pdf"

echo "commit-msg"
rejected_by="commit-msg:"
trailer="Co-Authored-By: Claude <noreply@anthropic.com>"
expect pass "conventional subject" commit_msg "feat(site): add a tab"
expect pass "breaking change" commit_msg "feat!: drop the old format"
expect fail "subject without a type" commit_msg "Add a tab"
expect fail "unknown type" commit_msg "feature: add a tab"
expect fail "co-author trailer" commit_msg "feat: add a tab

$trailer"
expect fail "lower-case co-author trailer" commit_msg "feat: add a tab

co-authored-by: someone <someone@example.invalid>"
for subject in 'Merge branch '\''main'\'' into topic' 'Revert "feat: add a tab"' \
  'fixup! feat: add a tab' 'squash! feat: add a tab' 'amend! feat: add a tab'; do
  expect pass "git-generated subject: $subject" commit_msg "$subject"
done

if [ "$failures" -gt 0 ]; then
  echo "$failures hook test(s) failed" >&2
  exit 1
fi
echo "all hook tests passed"
