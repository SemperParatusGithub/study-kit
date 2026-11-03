#!/usr/bin/env bash
# The checks of the guard workflow (.github/workflows/guard.yml); they run in the checkout.
# Usage: bash .github/scripts/guard.sh commits|courses|pdfs
#   commits  every commit of the push or pull request passes .githooks/commit-msg; reads
#            EVENT, PR_BASE, PR_HEAD, PUSH_BEFORE, PUSH_REF and DEFAULT_BRANCH from the
#            environment
#   courses  under courses/ only what starter-courses.txt lists is tracked: the README and the
#            two starter courses, which one commit added once; they may go, nothing may join
#   pdfs     no PDFs are tracked outside tests/fixtures/
set -euo pipefail
# The pathspec settings from the environment would change what the patterns below mean.
unset GIT_LITERAL_PATHSPECS GIT_GLOB_PATHSPECS GIT_NOGLOB_PATHSPECS GIT_ICASE_PATHSPECS

hooks="$(cd "$(dirname "$0")/../.." && pwd)/.githooks"

commits() {
  local range shas msg sha status=0
  if [ "$EVENT" = pull_request ]; then
    range="$PR_BASE..$PR_HEAD"
  elif git cat-file -e "$PUSH_BEFORE^{commit}" 2>/dev/null; then
    range="$PUSH_BEFORE..HEAD"
  elif [ "$PUSH_REF" != "refs/heads/$DEFAULT_BRANCH" ]; then
    # A new branch (before is all zeros), or a force push whose old tip no branch reaches
    # any more, so the checkout lacks it: check what the branch adds to the default branch.
    range="origin/$DEFAULT_BRANCH..HEAD"
  elif [ "$PUSH_BEFORE" = 0000000000000000000000000000000000000000 ]; then
    # The default branch was created: every commit on it is new.
    range=HEAD
  else
    echo "::error::the push rewrote the history of $DEFAULT_BRANCH, so the commits it added" \
      "are unknown; check them by hand"
    return 1
  fi
  echo "checking $range"
  # Not in the loop's word list, where a failure would go unnoticed and check nothing.
  if ! shas=$(git rev-list --no-merges "$range"); then
    echo "::error::cannot list the commits of $range"
    return 1
  fi
  msg=$(mktemp)
  for sha in $shas; do
    git log -1 --format=%B "$sha" >"$msg"
    if ! sh "$hooks/commit-msg" "$msg"; then
      echo "::error::commit $sha violates the commit rules"
      status=1
    fi
  done
  rm -f "$msg"
  return $status
}

courses() {
  local allowed extra
  allowed="$(dirname "$0")/starter-courses.txt"
  extra=$(LC_ALL=C comm -23 <(git -c core.quotePath=false ls-files courses | LC_ALL=C sort) \
    <(LC_ALL=C sort "$allowed"))
  if [ -n "$extra" ]; then
    echo "::error::only the files of .github/scripts/starter-courses.txt may be tracked under courses/"
    printf '%s\n' "$extra"
    return 1
  fi
}

pdfs() {
  local pdfs
  # git matches the paths itself, as in .githooks/pre-commit: its path output quotes names
  # with non-ASCII characters, and the extension may be in any case.
  pdfs=$(git -c core.quotePath=false ls-files -- ':(glob,icase)**/*.pdf' \
    ':(exclude,glob)tests/fixtures/**')
  if [ -n "$pdfs" ]; then
    echo "::error::PDFs may only be tracked under tests/fixtures/"
    printf '%s\n' "$pdfs"
    return 1
  fi
}

case "${1:-}" in
  commits | courses | pdfs) "$1" ;;
  *)
    echo "usage: $0 commits|courses|pdfs" >&2
    exit 2
    ;;
esac
