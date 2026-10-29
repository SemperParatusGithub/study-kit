#!/usr/bin/env bash
# Tests for the git hooks in .githooks and the guard workflow's checks (guard.sh). Every
# case runs in a throwaway repository, so the checkout that runs the tests is never touched.
# Usage: bash .github/scripts/test-hooks.sh
set -euo pipefail

root=$(cd "$(dirname "$0")/../.." && pwd)
hooks="$root/.githooks"
guard="$root/.github/scripts/guard.sh"

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

# guard_in <checkout> <check> [NAME=value...]: run a guard check in <checkout> with the
# given environment, as the guard workflow runs it
guard_in() {
  local checkout=$1 check=$2
  shift 2
  (cd "$checkout" && env "$@" bash "$guard" "$check")
}

# tracked <path...>: print the path of a new repository whose index holds <path...>
tracked() {
  local repo path
  repo=$(mktemp -d "$tmp/tracked.XXXXXX")
  git init -q -b main "$repo"
  for path in "$@"; do
    mkdir -p "$repo/$(dirname "$path")"
    printf 'x\n' >"$repo/$path"
  done
  git -C "$repo" add -A
  printf '%s\n' "$repo"
}

# new_remote: print the path of a directory with a bare repository origin.git and a clone
# of it, work, whose commits skip the hooks (it has none)
new_remote() {
  local dir
  dir=$(mktemp -d "$tmp/remote.XXXXXX")
  git init -q --bare -b main "$dir/origin.git"
  git clone -q "$dir/origin.git" "$dir/work" 2>/dev/null
  printf '%s\n' "$dir"
}

# commit_in <work> <subject> [body]: an empty commit in <work>; print its sha
commit_in() {
  git -C "$1" commit -q --allow-empty -m "$2" ${3:+-m "$3"}
  git -C "$1" rev-parse HEAD
}

# checkout <remote> <branch>: print the path of a fresh clone of <remote>/origin.git at
# <branch>, as actions/checkout with fetch-depth 0 makes it: it holds every branch, but no
# commit that no branch reaches any more
checkout() {
  local dir
  dir=$(mktemp -d "$tmp/checkout.XXXXXX")
  git clone -q --no-local "$1/origin.git" "$dir"
  git -C "$dir" checkout -q --detach "origin/$2"
  printf '%s\n' "$dir"
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
  expect fail "git-generated subject with a co-author trailer: $subject" commit_msg "$subject

$trailer"
done

echo "guard: commits"
rejected_by="violates the commit rules"
zero=0000000000000000000000000000000000000000
remote=$(new_remote)
work="$remote/work"
a=$(commit_in "$work" "feat: add a")
git -C "$work" push -q origin main
b=$(commit_in "$work" "feat: add b")
git -C "$work" push -q origin main
expect pass "push of conventional commits" guard_in "$(checkout "$remote" main)" commits \
  EVENT=push PUSH_BEFORE="$a" PUSH_REF=refs/heads/main DEFAULT_BRANCH=main
c=$(commit_in "$work" "feat: add c" "$trailer")
git -C "$work" push -q origin main
expect fail "push of a commit with a co-author trailer" guard_in "$(checkout "$remote" main)" \
  commits EVENT=push PUSH_BEFORE="$b" PUSH_REF=refs/heads/main DEFAULT_BRANCH=main
git -C "$work" checkout -q -b topic "$b"
d=$(commit_in "$work" "fix: add d")
git -C "$work" push -q origin topic
expect pass "new branch of conventional commits" guard_in "$(checkout "$remote" topic)" \
  commits EVENT=push PUSH_BEFORE="$zero" PUSH_REF=refs/heads/topic DEFAULT_BRANCH=main
expect pass "pull request of conventional commits" guard_in "$(checkout "$remote" topic)" \
  commits EVENT=pull_request PR_BASE="$b" PR_HEAD="$d" DEFAULT_BRANCH=main
expect fail "pull request with a co-author trailer" guard_in "$(checkout "$remote" main)" \
  commits EVENT=pull_request PR_BASE="$a" PR_HEAD="$c" DEFAULT_BRANCH=main
rejected_by="cannot list the commits"
expect fail "pull request from an unknown base" guard_in "$(checkout "$remote" topic)" \
  commits EVENT=pull_request PR_BASE=1234567890123456789012345678901234567890 PR_HEAD="$d" \
  DEFAULT_BRANCH=main
rejected_by="violates the commit rules"
# A force push leaves the old tip (github.event.before) out of the checkout.
git -C "$work" reset -q --hard "$b"
e=$(commit_in "$work" "fix: add e")
git -C "$work" push -q --force origin topic
expect pass "force push of conventional commits to a branch" \
  guard_in "$(checkout "$remote" topic)" commits \
  EVENT=push PUSH_BEFORE="$d" PUSH_REF=refs/heads/topic DEFAULT_BRANCH=main
git -C "$work" reset -q --hard "$b"
commit_in "$work" "fix: add f" "$trailer" >/dev/null
git -C "$work" push -q --force origin topic
expect fail "force push of a co-author trailer to a branch" \
  guard_in "$(checkout "$remote" topic)" commits \
  EVENT=push PUSH_BEFORE="$e" PUSH_REF=refs/heads/topic DEFAULT_BRANCH=main
# No branch tells which commits of a rewritten default branch are new, so the check fails.
git -C "$work" checkout -q main
git -C "$work" reset -q --hard "$a"
commit_in "$work" "feat: add g" >/dev/null
git -C "$work" push -q --force origin main
rejected_by="rewrote the history of main"
expect fail "force push to the default branch" guard_in "$(checkout "$remote" main)" commits \
  EVENT=push PUSH_BEFORE="$c" PUSH_REF=refs/heads/main DEFAULT_BRANCH=main
rejected_by="violates the commit rules"
# When the default branch is created, all of its commits are new.
remote=$(new_remote)
commit_in "$remote/work" "feat: start" >/dev/null
git -C "$remote/work" push -q origin main
expect pass "first push of the default branch" guard_in "$(checkout "$remote" main)" commits \
  EVENT=push PUSH_BEFORE="$zero" PUSH_REF=refs/heads/main DEFAULT_BRANCH=main
remote=$(new_remote)
commit_in "$remote/work" "feat: start" "$trailer" >/dev/null
commit_in "$remote/work" "feat: add a" >/dev/null
git -C "$remote/work" push -q origin main
expect fail "first push of the default branch with a co-author trailer" \
  guard_in "$(checkout "$remote" main)" commits \
  EVENT=push PUSH_BEFORE="$zero" PUSH_REF=refs/heads/main DEFAULT_BRANCH=main

echo "guard: courses"
rejected_by="::error::"
expect pass "only courses/README.md" guard_in "$(tracked courses/README.md docs/a.md)" courses
expect fail "course file" guard_in "$(tracked courses/README.md courses/et1/a.md)" courses
expect fail "course file with an umlaut" \
  guard_in "$(tracked courses/README.md "courses/et1/Übung 3.md")" courses

echo "guard: pdfs"
expect pass "pdf under tests/fixtures" guard_in "$(tracked tests/fixtures/a.pdf)" pdfs
expect fail "pdf" guard_in "$(tracked docs/a.pdf)" pdfs
expect fail "upper-case pdf" guard_in "$(tracked docs/A.PDF)" pdfs
expect fail "mixed-case pdf" guard_in "$(tracked docs/a.Pdf)" pdfs
expect fail "pdf with an umlaut and a space" guard_in "$(tracked "docs/Skript Ü.pdf")" pdfs
expect pass "pdf with an umlaut under tests/fixtures" \
  guard_in "$(tracked "tests/fixtures/Übung.pdf")" pdfs

if [ "$failures" -gt 0 ]; then
  echo "$failures hook test(s) failed" >&2
  exit 1
fi
echo "all hook tests passed"
