# Record independent challenges without adjudicating statements

`challenge_intake.py` appends human-authored independent challenges to existing
synthesis statements through a separate exact-input import review. It binds each
challenge to the challenged statements' current bases, exposes statements that
have no recorded challenge and challenges whose material gaps are still open, and
preserves every other record unchanged. It does not generate a challenge, judge
whether an alternative explanation is plausible, verify citations against sources,
verify independence, or uphold or refute any statement.

This is the executable form of the workflow's step 8. A challenge examines four
things, all supplied by the challenger as literal text: the strongest alternative
explanation, the discriminating evidence that is missing, citation-integrity
findings on the cited result rows, and whether the statement's conclusion stays
within the cited evidence. The outcome is one of three labels.

| Outcome | Meaning recorded | Reopening |
|---|---|---|
| `SURVIVES` | The challenger found no material gap at this time | Must be `null` |
| `MATERIAL_GAP` | A gap material to the conclusion was found | Must name an existing `work_package_id` or an `amendment_note` |
| `UNRESOLVED` | The challenge could not be resolved either way | Optional |

An unresolved outcome is a legitimate result, not a defect. A surviving outcome is
a recorded assertion, not proof. A material gap reopens targeted work; it does
not change the statement, its review, its citations or any appraisal.

## Independence as a mechanical check only

The engine rejects a challenge whose `challenger` label equals a label already
recorded on the challenged statements: the statement `reviewer`, any evidence
position `recorded_by`, or the `reviewer` of an appraisal on the cited results.
The template lists those labels. A distinct label is the only check performed;
it does not establish that a different person, an uninvolved person or a competent
person made the challenge. Every output labels this `LABEL_DISTINCT_ONLY`.

## Blank drafting and explicit candidate records

A reference document has exactly integer schema_version: 1 and a nonempty unique
list of existing statement_ids. The template copies the selection, computes the
current `basis_sha256` of those statements, lists the recorded labels, and leaves
every other field null. Lists start empty. No blank is interpreted as agreement,
disagreement or completed review.

The candidate document has exactly schema_version and a nonempty challenges list
of at most 100 rows. Each row has exactly:

- challenge_id, challenger, challenged_at (a real YYYY-MM-DD), statement_ids,
  alternative_explanation, limitations and independence_declaration as supplied
  nonblank text or IDs.
- missing_discriminating_evidence: a list of at most 100 nonblank strings; may be empty.
- citation_integrity_findings: a list of at most 100 objects with exactly
  evidence_id and finding. Each evidence_id must be cited by a challenged statement.
- conclusion_width: WITHIN_CITED_EVIDENCE, BROADER_THAN_CITED_EVIDENCE or NOT_ASSESSED.
- outcome and reopening as in the table above.
- basis_sha256: the template's current basis for exactly these statement_ids.

Target preparation fails if the basis no longer matches the statements, because a
challenge recorded against changed statements would bind to text the challenger
did not examine. Regenerate the template and re-examine instead of copying hashes.
New IDs must be unique across the existing ledger and the batch; existing records
cannot be replaced or merged. Identical challenger labels across rows do not make
them one challenge or independent of each other.

## Eleven-command synthetic challenge-to-review rehearsal

Use a new existing `OUTPUT` directory outside this repository. All fixture
explanations, findings, labels and outcomes are fictional software data, not a
scientific assessment of any real statement.

```sh
python challenge_intake.py template examples/synthesis-review.json examples/challenge-references.json --candidate-output OUTPUT/challenge-draft.json
python challenge_intake.py target examples/synthesis-review.json examples/manual-challenge-candidates.json --output OUTPUT/challenge-target.json
```

Keep the unfinished draft separate. The completed fictional candidate records one
`MATERIAL_GAP` on statement-1 that reopens the existing `WP-MECHANISM` work and one
`UNRESOLVED` challenge on statement-2 with an amendment note. Copy the target's
review_document to `OUTPUT/challenge-review.json`, retain schema and hash, and
explicitly fill receipt_id, reviewer, reviewed_at, rationale and
`decision: "import_challenges"`. This separate review records the supplied rows; it
is not agreement with the challenges. Use fictional labels only for this rehearsal.

```sh
python challenge_intake.py assemble examples/synthesis-review.json examples/manual-challenge-candidates.json OUTPUT/challenge-review.json --output OUTPUT/challenge-application.json
python challenge_intake.py verify examples/synthesis-review.json OUTPUT/challenge-application.json --protocol-output OUTPUT/with-challenges.json
python research_status.py OUTPUT/with-challenges.json --text
python synthesis_review.py OUTPUT/with-challenges.json --text
python review_handoff.py OUTPUT/with-challenges.json --text
python compare_runs.py examples/synthesis-review.json OUTPUT/with-challenges.json
python research_bundle.py create OUTPUT/with-challenges.json OUTPUT/research.zip
python research_bundle.py verify OUTPUT/research.zip
```

Before the import, both statements are listed without a recorded challenge. After
it, that queue is empty, one challenge has an open material gap pointing at
`WP-MECHANISM`, and one challenge is unresolved. Both challenges bind to the current
statement bases. Statement-1 keeps its reviewed status and hash; statement-2 stays
pending. Record flow, report counts, work packages, planning and appraisals are
unchanged. Census remains `NOT_ESTABLISHED` and conclusions `NOT_READY`.

## Bindings, staleness and downstream views

The basis of a challenge is the sorted set of challenged statement IDs with each
statement's current review-target basis hash. That hash already covers the
statement text, limitations, citations, cited result rows, contexts, intersecting
appraisals and supplied positions. If any of those change later, for example when a
new appraisal is imported for a cited result, the challenge is listed under stale
statement bindings. Nothing is renewed automatically; the challenger must re-examine.
A challenge without a basis is accepted as `UNBOUND_CHALLENGE` and never becomes
current by itself.

Statements without a recorded challenge, open material gaps, unresolved challenges
and stale bindings appear as queues in `research_status.py` and as handoff steps
with their input rows in `review_handoff.py`. The synthesis snapshot shows each
statement's challenges beside its citations. Bundles record the challenge stage in
the summary and keep challenge rows in `protocol.json`. Version comparison lists
added, removed and changed challenges and their binding/reopening transitions.

## Replay, preservation and limits

Verification regenerates the entire application against its actual original and
recorded implementation. Unrelated original changes, candidate changes and
resealed output changes fail replay. This is not authentication: consistently
reauthored unsigned labels can replay, and dates are checked for calendar syntax,
not chronology. Keep the original, the detached application and the recorded
implementation together.

Reference/candidate/review inputs are limited to 10 MB; protocols/applications to
50 MB; 100 challenges per batch and 100 items per list. Strict JSON, exact row
schemas and whole-protocol validation apply. Output is prepared before exclusive
creation; existing entries and observed dangling links are refused. This is not an
atomic path-race defense, and a failed write may leave a partial new file.

No external call, model call, source reading or experimental procedure is
performed. Supplied private text is retained without redaction; keep real inputs
and generated records outside this public repository. Neither a recorded challenge
nor a matching hash establishes evidence sufficiency, conclusion readiness,
scientific acceptance or clinical applicability.
