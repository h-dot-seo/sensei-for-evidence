# Supplied title/abstract reviewer positions

Local CSV collection ends with records awaiting screening, not eligibility
decisions. The optional `screening_reviews` ledger records separate human-supplied
positions before or alongside the canonical `screening` ledger. It preserves
disagreement and the supplied source context without choosing an outcome.

This tool does not read a title/abstract, check a medical fact, authenticate a
reviewer or adjudicate eligibility. All checked-in examples are fictional. Keep
real/private material and generated outputs outside this public repository.

## Reproduce the fictional review

```sh
python screening_review.py examples/screening-reviews.json --text
python screening_review.py examples/screening-reviews.json --record-id=record-alpha --text
python screening_review.py examples/screening-reviews.json --record-id=record-alpha --template --output /outside/new-screening-template.json
python prisma_audit.py examples/screening-reviews.json --text
python review_handoff.py examples/screening-reviews.json --text
python research_bundle.py create examples/screening-reviews.json /outside/new-screening-bundle.zip
python research_bundle.py verify /outside/new-screening-bundle.zip
```

Choose new output paths in an existing local directory. `--output` writes a JSON
review report or template, never a modified protocol, and refuses overwrite.
`--text` changes stdout only. Without `--output`, these review commands write only
stdout. Input files are not changed; source locators are never opened or executed.

The example has four records and five fictional reviewer assertions:

- Alpha has opposing current include/exclude positions but no canonical decision.
- Beta has a current include position and a separately recorded exclusion.
- Gamma has an unclear current position and an earlier-question stale position.
- Delta has no supplied review.

The PRISMA record counts stay at four enumerated, one screened/excluded and three
pending. No report or result row is created. The earlier-question hash in the
example is a synthetic demonstration, not authenticated review history.

## Record an assertion after actual human review

1. Inspect the exact record's source target and containing source context with
   the review command. For imported CSV data, mapped original rows, columns and
   source pointers remain available in the target. Supplied data is not proof
   that a source is authentic or that the title/abstract is complete.
2. Generate a separate blank template. Its `screening_reviews` field is a scaffold:
   only the exact record ID and current source-basis hash are filled. Review ID,
   reviewer label, date, decision, rationale and source locator remain null.
   Existing assertions remain visible for inspection but are not copied into
   the new scaffold or renewed.
3. After a person reviews the intended material and criteria, supply those
   fields honestly. Copy the completed assertion rows, not the entire template
   report, into `screening_reviews` in a separate working protocol. Rerun the
   commands. Never copy a fresh hash just to clear a stale-review cue.
4. If a canonical eligibility decision is appropriate, a human supplies it
   separately with its own reason. `screening_review.py` remains read-only. The
   separate [explicit decision workflow](SCREENING_DECISIONS.md) can apply only a
   completed supplied document to a new candidate and retain decision receipts.
   It never votes or adjudicates eligibility. Preserve earlier protocol snapshots
   when changing reviewer assertions; reviewer supersession is not implemented.

Each review requires exactly these fields:

```json
{
  "review_id": "a-stable-supplied-review-id",
  "record_id": "an-exact-enumerated-record-id",
  "reviewer": "a-supplied-reviewer-label",
  "reviewed_at": "2026-11-04",
  "decision": "unclear",
  "rationale": "The supplied source leaves the criterion unresolved.",
  "source_locator": "an-inert-source-location-description",
  "source_basis_sha256": "use-the-exact-source-target-actually-reviewed"
}
```

The example hash text above is deliberately invalid, not a reusable approval.
Actual hashes must contain 64 lowercase hexadecimal characters. All fields are
nonblank literal strings; dates must be valid `YYYY-MM-DD`. Decisions are
`include`, `exclude` or `unclear`. Unknown fields, unknown records, duplicate
review IDs and duplicate exact `(record_id, reviewer)` pairs are rejected. One
active assertion per exact reviewer label is supported in this increment.
Different labels do not prove different people or independent review. No names
or IDs are trimmed, merged or matched by similarity. Unscreened and excluded
records can both have review assertions.

## What the source hash binds

Each record target binds its exact ID, question, inclusion/exclusion criteria,
ordered search occurrence references and retained mapped bibliographic rows.
Each occurrence references the digest of its **complete containing search
assertion**, available once in the source-context catalog. CSV receipt context
includes its retained export hash. Full searches are not copied into every
record target, avoiding a quadratic source-catalog expansion.

This is deliberately conservative: changing any field or record membership in
a containing search, or reordering search/record occurrences, can stale a review.
Changing the criteria, mapped CSV source rows or source receipts also changes the
target. Unrelated work, protocol version, canonical screening decisions and the
current review ledger are excluded from the target, avoiding circular review
binding and allowing a later manual eligibility decision.

`CURRENT_SOURCE` means only that supplied hash and current supplied context
match. `STALE_SOURCE` preserves an assertion whose hash no longer matches. The
tool does not retain or reconstruct every earlier source snapshot. Archive the
actual working protocol/bundle when recording reviews. The hash is not a
signature, proof of authorship, proof that the source was read, or a check of
remote full-text bytes. A review's source locator and rationale remain separate
unverified assertions, not fetched or authenticated source contents.

## Read disagreements without inventing consensus

Every record lists all supplied review IDs, current/stale subsets, distinct
current decision labels, reviewer labels and the separate canonical screening
row, if any. A stale position is retained but excluded from current-position
comparisons. Different current labels, including an `unclear` label alongside
another label, produce a difference cue. Unclear, missing-current, stale and
canonical-label differences are shown explicitly.

`matches_recorded_decision` compares only the literal include/exclude label,
including for an assertion separately marked stale. It does not compare rationale
or establish valid adjudication. It is null for unclear or absent canonical
decisions. Matching positions are not called consensus; no minimum reviewer
count or required independence is configured. An empty cue list does not prove
that screening or source review is complete.

## PRISMA, comparison and compatibility

Core output, report ledgers, PRISMA audit and synthesis snapshots retain the
optional `screening_review` projection. Status/handoff add
`records_with_screening_review_cues`, with exact record IDs and original review,
screening and search row locations. Handoff links to the detailed review command.
Queues remain protocol-wide even when one work package is selected.

Run-to-run comparison adds `screening_review_changes` only when either snapshot
opts in. It compares stable supplied review IDs, keeps before/after assertions
and recomputed source-match labels, and shows changed record review projections.
An unchanged assertion can therefore be visibly stale after criteria change.
The comparator does not renew it or decide whether its judgment is correct.

Omitting `screening_reviews` retains legacy output shapes and CSV bytes. An
explicit empty list opts in and records the absence of current review assertions;
null is invalid. The key is now reserved rather than opaque unrelated metadata.
The CSV import history permits this new enrichment while retaining all original
source integrity checks. The bundle retains the raw assertions and fingerprints
their validator; its existing seven-file structure is unchanged.
Use the recorded code revision to verify older engine-bound intake artifacts or
bundles; a new implementation fingerprint is not automatic reapproval.

Informational reviewer assertions do not change existing planning, completion or
synthesis source bases. Canonical screening remains the operational input to
those workflows. No new work dependency is created, and work completion does not
resolve reviewer positions. Full-text review, per-study eligibility, reviewer
supersession history, source authenticity and medical/scientific correctness remain separate.
