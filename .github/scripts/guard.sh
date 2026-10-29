#!/usr/bin/env bash
# The checks of the guard workflow (.github/workflows/guard.yml); they run in the checkout.
# Usage: bash .github/scripts/guard.sh commits|courses|pdfs
#   commits  every commit of the push or pull request passes .githooks/commit-msg; reads
#            EVENT, PR_BASE, PR_HEAD, PUSH_BEFORE and DEFAULT_BRANCH from the environment
#   courses  only courses/README.md is tracked under courses/
#   pdfs     no PDFs are tracked outside tests/fixtures/
set -euo pipefail

hooks="$(cd "$(dirname "$0")/../.." && pwd)/.githooks"

commits() {
  local range msg sha status=0
  if [ "$EVENT" = pull_request ]; then
    range="$PR_BASE..$PR_HEAD"
  elif [ -z "$PUSH_BEFORE" ] || [ "$PUSH_BEFORE" = 0000000000000000000000000000000000000000 ]; then
    range="origin/$DEFAULT_BRANCH..HEAD"
  else
    range="$PUSH_BEFORE..HEAD"
  fi
  echo "checking $range"
  msg=$(mktemp)
  for sha in $(git rev-list --no-merges "$range"); do
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
