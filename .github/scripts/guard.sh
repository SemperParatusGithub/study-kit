#!/usr/bin/env bash
# The checks of the guard workflow (.github/workflows/guard.yml); they run in the checkout.
# Usage: bash .github/scripts/guard.sh commits|courses|pdfs
#   commits  every commit of the push or pull request passes .githooks/commit-msg; reads
#            EVENT, PR_BASE, PR_HEAD, PUSH_BEFORE, PUSH_REF and DEFAULT_BRANCH from the
#            environment
#   courses  only courses/README.md is tracked under courses/
#   pdfs     no PDFs are tracked outside tests/fixtures/
set -euo pipefail

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
  local tracked
  tracked=$(git ls-files courses)
  if [ "$tracked" != "courses/README.md" ]; then
    echo "::error::only courses/README.md may be tracked under courses/"
    printf '%s\n' "$tracked"
    return 1
  fi
}

pdfs() {
  local pdfs
  pdfs=$(git ls-files '*.pdf' '*.PDF' | grep -v '^tests/fixtures/' || true)
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
