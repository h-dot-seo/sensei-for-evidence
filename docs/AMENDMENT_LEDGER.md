# Persist a supplied amendment without closing a gate

This is the recording and comparison part of roadmap #43 adjustments (a), (b) and
(d), not the proposed gate-closing rule (c). The existing `OPEN_AMENDMENT` status,
challenge/readiness rules, open items and all gates remain unchanged. Recording a
reason does not establish that a gap was resolved or that a change was approved.

The author supplies a valid BEFORE and a separately human-edited AFTER. A two-input
intake binds those exact snapshots and a supplied amendment row for separate review.
Only after a complete supplied review does it produce an append-only candidate
protocol and detached application. `verify` replays the same two inputs; it does not
fetch history, authenticate a reviewer, perform research or infer authorization.

## Row and history contract

Optional `amendments` is a list of at most 100 exact-field rows:
`amendment_id`, `before_protocol_sha256`, `from_version`, `to_version`, `reason`,
`authored_by`, `authored_at`, `scope_fields`, `triggered_by`.
IDs are unique; author, reason and version labels are nonblank supplied strings;
dates are calendar-valid supplied dates, not verified event times. Scope is at most
100 unique top-level names. `amendments` itself is implicit, not a supplied scope name.
`triggered_by` is at most 100 unique `{kind, ref_id}` pairs. Only `CHALLENGE` and
`READINESS_ASSERTION` are supported, and recording requires those IDs to exist in
BEFORE. This is a one-way historical reference. Question/stop-rule/other motivations
can be explained in the supplied reason, not invented as validated entities.

The template fills only the mechanical before hash and two version labels. ID,
reason, scope, references, author and date remain null. That worksheet is deliberately
not a valid candidate. Target preparation produces a separate review worksheet with
only its schema and target hash filled. The person must supply receipt ID, exact
`record_supplied_amendment` decision, reviewer/date and rationale. These labels are
not authenticated approval or a scientific judgment.

All older amendment rows must be preserved exactly between BEFORE and the human-edited
AFTER. The intake appends one new ID and changes no other AFTER value. It recomputes
research results to require that the append itself changes only the optional amendment
observations. A human change between BEFORE and AFTER can still make existing bindings
STALE or alter existing gates under existing rules; this is not hidden or repaired.
No actual review or prior record is automatically resealed.

Rows have no DECLARED/ENACTED status and no embedded after hash. An embedded after hash
would include itself. Instead, the row retains the actual BEFORE canonical hash and
version labels; the separate target/application binds the complete human-edited AFTER
and the complete appended candidate. Canonical hashes preserve JSON types and list
order, not file formatting. Sequential v1→v2→v3 recording retains the earlier row:
its current observation becomes `NOT_CURRENT_VERSION`, not invalid. A repeated version
label can still match; this does not establish chronological order or current approval.

## Single snapshot versus actual paired verification

The engine/status/handoff/bundle display supplied rows and `CURRENT_VERSION` or
`NOT_CURRENT_VERSION`. Both `before_hash_verification` and
`historical_reference_verification` stay `NOT_VERIFIED_IN_PLACE`. A historical referenced
challenge may no longer exist in the current snapshot. A single snapshot must not
pretend it inspected the original BEFORE or authenticated a historical event.

`compare_runs.py BEFORE AFTER --amendment-id ID` selects one row from AFTER. It is
mutually exclusive with the existing `--amendment` external-note option. It checks the
actual BEFORE hash, both version labels, exact changed top-level scope other than the
implicit amendment field, and historical reference existence in BEFORE. Its distinct
binding label is `RECORDED_BEFORE_AND_SCOPE_MATCH` or `MISMATCH`;
`after_hash_verification` is `NOT_APPLICABLE_EMBEDDED`. It must not reuse the external
note's stronger two-input-hash label. This comparison is not detached-review replay;
retain the exact BEFORE, pre-append AFTER and application for `amendment_intake verify`.
A comparison against a later snapshot may mismatch an earlier row, as it should.

Existing external notes and default comparison fields remain supported. The new ledger
is not a signed, complete or regulatory change history. Hash-consistently reauthored
unsigned inputs/reviews can replay. Version labels and supplied HUMAN identities are
not authentication, and no scientific, clinical or legal conclusion follows.

## Fictional recording and retained-bundle rehearsal

Create an empty `WORK` directory. The fixtures are fictional, not real research.
After `target`, a person supplies `WORK/review.json` using its `review_document`, fills
all null human fields and retains the exact target hash. The guide test supplies a
fictional reviewer only for rehearsal; the product never fills those fields.

```sh
python amendment_intake.py template examples/amendment-before.json examples/amendment-after.json --output WORK/template.json
python amendment_intake.py target examples/amendment-before.json examples/amendment-after.json examples/manual-amendment.json --output WORK/target.json
python amendment_intake.py assemble examples/amendment-before.json examples/amendment-after.json examples/manual-amendment.json WORK/review.json --output WORK/application.json
python amendment_intake.py verify examples/amendment-before.json examples/amendment-after.json WORK/application.json --protocol-output WORK/recorded.json
python compare_runs.py examples/amendment-before.json WORK/recorded.json --amendment-id fictional-amendment --text
python research_status.py WORK/recorded.json --text
python review_handoff.py WORK/recorded.json --text
python research_bundle.py create WORK/recorded.json WORK/recorded.zip
python research_bundle.py verify WORK/recorded.zip
```

## Compatibility, errors and limits

Absent `amendments`, existing run/gate values and CLI outputs are preserved apart from
explicit implementation fingerprints. Adding the optional stage changes protocol and
bundle identity. New engine bytes and the new engine module change implementation
maps; older bound targets/applications/bundles may require their original implementation.
This release maintains only the fixed fictional examples by actual replay. It does not
update real reviews or provide an automatic resealer. Old versions do not promise to
interpret new amendment rows. Existing adapters/native provenance still enforce their
own immutable context; admitting the `amendments` field does not permit arbitrary edits.

Intake protocols and applications are bounded to 50,000,000 canonical UTF-8 bytes;
CLI input files are bounded to the same byte limit before parsing. Candidate/review
files use 10,000,000 bytes. Existing strict JSON and depth rules apply. Outputs are
exclusive; existing files/links are refused. Multi-file output is not atomic and a later
failure can leave an earlier or partial file. No whole-process CPU/memory guarantee is
made. Supplied text is not a privacy redactor; review it before sharing.

Caught intake errors use fixed stderr, empty stdout and exit 1; usage uses exit 2.
Successful exact intake replay exits 0. A structurally valid mismatching embedded
comparison produces its comparison JSON/text with exit 1, like an external-note
mismatch. Invalid ID or incompatible options fail without a report. Supplied dates,
reasons and links are recorded, never judged adequate.
