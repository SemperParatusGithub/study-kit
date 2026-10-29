---
name: verify
description: Blind re-verification of course items with the dispute loop - verifier agents check each item from its blind view, author agents fix disputed items for at most two rounds, whatever stays disputed is quarantined.
disable-model-invocation: true
argument-hint: <course> [id|topic|exam|all]
allowed-tools:
  - Bash(uv run --frozen studykit *)
---

# /verify $ARGUMENTS

Re-verify course items blind and settle every disagreement (docs/architecture.md §2.10,
§5.3). Arguments: the course `$0` (an id or a directory) and the target `$1`: an item id,
a topic, an exam id or `all` (the default when it is missing).

You are the orchestrator. You may read keys and solutions; the verifier agents must not.
Never put a key value, a solution or an item file path into a verifier's prompt.

## 1. Run what exists

1. `uv run --frozen studykit ls $0` must find the course; otherwise stop and say where
   courses are looked for.
2. `uv run --frozen studykit verify $0 <target>` re-runs every existing check of the
   target (stale entries are checked against the new content). Exit 1 only means some
   item is disputed or failed.
3. `uv run --frozen studykit verify $0 <target> --status --json` lists every item with its
   `status`, `outcome`, `check`, `confirmed` (a second method reproduced the dispute) and
   `confirmations`. Items to send to a verifier:
   - an explicit item id as target: always (a fresh blind check);
   - otherwise: every item that is `unverified` (no check, or a check that errored) and
     every `disputed` item that is not `confirmed`.

## 2. Verifier wave

Start one `verifier` agent per item, at most 6 at a time. Its prompt is only:

> Course: `<absolute course directory>`. Item: `<id>`. Verify it with your protocol and
> return the result JSON.

Wait for the wave, then read the truth from the ledger, not from the agents' reports:
`uv run --frozen studykit verify $0 <target> --status --json`. An agent that returned
without a check, or whose check still errors, gets one more attempt; after that the item
stays unverified and goes into the report.

**Items without answer keys** (a `review(…)` check): compare the verifier's `reason`
with the item's solution yourself. If they disagree, record it:
`uv run --frozen studykit verify $0 <id> --dispute --note "verifier: …; solution: …"`.

## 3. Dispute loop (at most 2 author rounds per item)

For each disputed item, with the ledger entry from
`uv run --frozen studykit verify $0 <id> --status --show-key --json` (in `results` the
verifier's `computed` values and the key's `expected`, `ok: false` for a mismatch; MC: the
letters; `confirmed` and `confirmations`):

1. Start an `author` agent: "Course `<dir>`. Fix round for `<id>` (`<file>`). The verifier
   computed: `<key>=<value> <unit>` for each mismatched key (MC: its letters), confirmed by
   a second method: yes/no. Follow the fix round of the authoring skill." Several items
   may run in parallel (at most 6), never two items of the same file at once.
2. Verdict `fixed`: `uv run --frozen studykit verify $0 <id>` runs the same check on the
   new version. Verified ends the loop; a new dispute starts the next round.
3. Verdict `key-correct`: start a fresh `verifier` for the item with the extra line "The
   author holds the key; check your method with an independent second method." If its
   second method now sides with the key, the item returns to unverified and the verifier
   fixes its check; run verify again. If both methods still disagree with the key, show the
   user the item, the key, the verifier's numbers and the author's reason, and ask with
   AskUserQuestion: quarantine it, or leave it disputed for a manual fix.
4. The ledger quarantines an item by itself when it is disputed after the second fix
   round. An item that is still not verified after two rounds is quarantined by hand:
   `uv run --frozen studykit verify $0 <id> --quarantine --note "<one-line reason>"`.

Quarantined items disappear from the site and the PDFs and are listed in the report.

## 4. Finish

1. `uv run --frozen studykit verify $0 <target> --report` (writes `state/verify/report.md`).
2. `uv run --frozen studykit validate $0` (the PDFs rebuild without quarantined items);
   route a content error to an author agent as in step 3, at most one round.
3. Report to the user: a table with counts (verified, fixed after a dispute, disputed,
   quarantined, unverified), then every item that is not verified with its reason, the
   files the authors changed, and the path of `state/verify/report.md`. Say so when the
   course has items no verifier could check.
