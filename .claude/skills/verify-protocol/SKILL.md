---
name: verify-protocol
description: The blind verification protocol of study-kit - work only from `studykit blind`, compute every result in Python, write checks/<id>.py or .json, run `studykit verify`, confirm a disagreement with a second independent method before it stands, and the dispute, fix and quarantine loop. Includes check-script recipes for nodal analysis, phasors, Laplace and stability margins. Use when verifying exercises, exam tasks or MC questions.
user-invocable: false
---

# Verification protocol

The verifier checks an item without ever seeing its key, solution, hints, rubric or MC
marks, so a wrong key cannot bias it. The spec is `docs/architecture.md` §2.10 (ledger)
and §5.3 (verifier); the check API is `src/studykit/check.py`; recipes are in
[recipes.md](recipes.md).

## Blindness

A guard hook (`studykit hook verifier-guard`) denies the verifier every path that holds a
key: the course's `exercises/`, `mc/`, `exams/`, `state/`, `_history/`, `_build/` (except
`_build/blind/` and the figure images), figure facts, the built site and `.cache/`; Grep
and Glob over a tree with a course; Bash that names those paths unless it is `studykit`
(`blind`, `calc`, `verify` without `--json`/`--show-key`, `ls`, `lint`, `validate`, `fig`,
`index`, `doctor`) or `python checks/…`; writes outside the course's `checks/`. A denial
is the protocol working: never look for another way to the file. Everything you need is in
the blind view.

## Procedure for one item

1. **Blind view:** `uv run --frozen studykit blind <course> <id>`, then Read
   `<course>/_build/blind/<id>.md`. It has the statement, the results to compute (key,
   label, unit or symbols) or the MC options in source order A-F, and the figure PNGs
   (build a missing one with `uv run --frozen studykit fig build <course> --only <slug>`,
   then Read the PNG).
2. **Compute in Python.** Never compute in your head. Quick values:
   `uv run --frozen studykit calc "1/(2*pi*R*C)" --subs R=2.2e3 C=47e-9`
   (`--units` for unit arithmetic); anything longer goes into the check script.
3. **Write the check:** `<course>/checks/<id>.py` that imports from `studykit.check` and
   ends with exactly one call:
   - `answers(key=value, …)`: an exercise or exam task, one value per key, in the key's
     unit (or `quantity(x, "kHz")`), SymPy expressions for symbolic keys;
   - `mc_numeric(correct=…, options={…}, mistakes={…})`: an MC question whose options are
     all numbers (the blind view says so; a JSON answer does not count there, SK-VER-CHECK);
   - `mc_answer([...], reason=…)` or `checks/<id>.json` `{"answer": […], "confidence":
     "high", "ambiguous": false, "reason": "…"}`: a conceptual MC question;
   - `review(agree, reason)`: an item without keys (see recipes).
   Pass `method="…"` naming the method. The script reads nothing from the course; all
   data comes from the statement, written as constants with units in comments.
4. **Run it:** `uv run --frozen studykit verify <course> <id>`. The output shows the
   status (`verified`, `disputed`, `unverified`) and problems without the key values.
   `unverified` with an error means your script failed: fix it and run again.
5. **Two-method rule.** Before a disagreement stands, confirm it with an independent
   second method in `<course>/checks/<id>.<tag>.py` (tag: `mesh`, `sympy`, `sim`, …):
   nodal vs. mesh analysis, numeric vs. symbolic, closed form vs. simulation, python-control
   vs. brentq on the frequency response. Then
   `uv run --frozen studykit verify <course> <id> --confirm checks/<id>.<tag>.py --method "mesh currents"`.
   - The second method reproduces your result: the dispute is confirmed.
   - The second method sides with the key: the item goes back to unverified; find the
     mistake in your first check (units, RMS vs. amplitude, sign convention, a misread
     value), fix `checks/<id>.py` and run `studykit verify` again.
   An MC answer needs no second script: re-read the blind view, reason once more by
   another route (a limit case, a sign check, the definition), write the answer as
   `<course>/checks/<id>.recheck.json` and `--confirm` it the same way; mark `ambiguous`
   instead of guessing. A review needs no second method.
6. **Report** one compact JSON object as your final message:

```json
{"item": "pk1-t2", "status": "disputed", "check": "checks/pk1-t2.py",
 "second": "checks/pk1-t2.sympy.py", "computed": {"Xc": 723.43}, "note": "one line"}
```

`computed` holds your values for the keys the run reported as mismatched (for MC: your
letters). Never claim a status the `studykit verify` output did not show.

## Dispute, fix and quarantine loop

Run by the `/verify` command; the verifier only does steps 1-6 above.

- A mismatch writes a dispute into the ledger `state/verify/<id>.json` automatically
  (SK-VER-DISPUTED). The author gets the item id and the verifier's computed values and
  fixes the item (or answers that the key is right, with the step the check got wrong).
- After a fix the item's content hash changes, the entry is stale, and
  `studykit verify <course> <id>` runs the same check on the new version. Each dispute on
  a new version counts one author fix round (`rounds`).
- The dispute after the second fix round quarantines the item automatically: it is hidden
  from the site and the PDFs and listed in `state/verify/report.md`. An item that cannot be
  settled otherwise is quarantined by hand:
  `uv run --frozen studykit verify <course> <id> --quarantine --note "reason"`.
- A disagreement that no check script can express (a review whose result contradicts the
  solution) is recorded with
  `uv run --frozen studykit verify <course> <id> --dispute --note "reason" --computed key=value`.
- `uv run --frozen studykit verify <course> <target> --status` shows the ledger;
  `--report` also writes `state/verify/report.md`; `--clear` removes entries (`stale`,
  `orphans`). Ledger files are written by `studykit verify` only, never by hand.
