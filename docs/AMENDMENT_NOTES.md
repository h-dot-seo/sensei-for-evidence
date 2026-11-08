# Bind a supplied amendment note to a protocol comparison

`compare_runs.py` already compares supplied protocol snapshots. Optional
`--amendment` adds the missing link between a person's stated reason/scope and the
exact two snapshots being compared. It does not add protocol fields or a second
comparison engine, and does not approve the change.

```sh
python compare_runs.py examples/first-run-enriched.json examples/first-run-note-complete.json --amendment examples/work-note-amendment.json
```

This entirely synthetic note says a fictional receipt-review note was marked
complete. It does not claim missing searches were performed, an artifact exists,
a reviewer is authenticated or scientific evidence was accepted.

## External note contract

The JSON object has exactly these fields:

- schema_version: integer 1 (not boolean).
- before_sha256 / after_sha256: lowercase canonical-input SHA-256 hashes. The
  existing comparison reports these for the actual inputs; object key order is
  ignored, list order and JSON types are retained. These are not file-byte hashes.
- from_version / to_version: nonempty supplied version strings, compared exactly
  to the corresponding protocol values. They do not authenticate amendment history.
  Legacy non-string protocol versions still work without a note, but cannot match
  this string-version note contract.
- reason / authored_by: nonempty human-supplied text; no reason is generated.
- authored_at: a supplied ISO calendar date, not a verified event timestamp.
- scope_fields: unique top-level protocol field names said to have changed.
  Include version when it changes. An empty list is permitted for identical
  snapshots; it is not proof that a meaningful amendment occurred.

Read the comparison before recording a reason and scope. Never change hashes or
scope merely to hide a mismatch. The tool checks bookkeeping, not whether the
reason is adequate, authority exists or the declared scope is semantically honest.
Existing protocol validation runs on both inputs before reporting any comparison.

## Result and exit behavior

`amendment_review` contains the copied assertion and its canonical hash, per-input
hash/version matches, actual changed fields, undeclared changed fields and declared
but unchanged fields. Binding is RECORDED_INPUTS_AND_SCOPE_MATCH only when all these
checks match; otherwise it is MISMATCH. Absent --amendment produces NOT_SUPPLIED;
explicit null or malformed note data is rejected.

The report also shows changes in derived planning source-match/current-rank state,
synthesis source-match/support state and work status/blocked_by, plus before/after
search-plan status and missing/incomplete IDs. These come from the **actual input
snapshots**, even if the note mismatches. They are observed transitions, not proof
that the supplied reason caused them. No planning or synthesis review is renewed.
Unchanged search summaries can still contain missing sources.

CLI behavior:
- No note, or a structurally valid matching note: comparison JSON (or `--text` summary), exit 0.
- Structurally valid mismatching note: comparison JSON (or `--text` summary) including MISMATCH, exit 1.
- Invalid note/protocol/read error: error on stderr, exit 1, no comparison report.

Other comparison fields remain unchanged. The note does not become embedded in
protocols, work CSV or research bundles; retain it separately if authorized. This
is a pairwise check, not a signed log, complete amendment history or regulatory
change-control system. It makes no medical, clinical, scientific or legal decision.

The standalone [completion comparison](COMPLETION_COMPARISON.md) is also produced
without a note. It separates changed work/source scope, own artifact locators and
direct prerequisite source labels. A matching note does not approve those changes
or prove that a retained COMPLETE status was actually reassessed.
