# Preserve an explicitly selected extraction-transition segment

`extraction_transition_bundle.py` packages exact initial/endpoint protocol files
and an explicitly ordered, contiguous set of already reviewed result/condition
applications. A final research ZIP retains the final protocol, but not detached
source selections, earlier result wording or import/correction review assertions.
This separate archive retains those supplied records and replays the existing
verifiers. It does not generate a review or change existing protocol/bundle formats.
Old receipts remain byte-for-byte unchanged, including their original snapshot-bundle
caveats; this separate archive adds preservation without rewriting those records.

## Three supported application kinds

- `detached_result_intake`: append explicitly reviewed result rows.
- `detached_result_correction`: explicitly reviewed edits to result/limitations text.
- `detached_condition_intake`: append reviewed descriptive condition metadata.

Supply one to 20 applications in their actual intended transition order. A kind
can repeat, and a segment can start or end with any supported kind. The tool does
not sort by dates, infer missing steps or authenticate chronological execution.
The initial protocol is the exact supplied start of this segment, not necessarily
the beginning of a project. Each existing verifier receives the preceding
candidate protocol, and the final candidate must match the separately supplied
endpoint by full canonical JSON equality. Unrelated/opaque fields and JSON scalar
types remain bound. JSON whitespace/key order may differ between equivalent
representations; the original bytes and byte hashes are retained separately.

Each application keeps its full candidate, supplied review and receipt target,
including explicitly selected source descriptors, source locations and the context
recorded at that step. Earlier selections do not automatically apply to the final
result text. A condition recorded before a later correction still retains its
earlier selected result snapshot. No prior review, appraisal, claim, planning
assertion or work-completion assertion is renewed or reassessed by this archive.
Use the separate [result-source comparison](RESULT_SOURCE_REVIEW.md) where needed;
a matching archive is neither current source approval nor complete extraction.

## Eleven-command synthetic rehearsal

Use a new outside `OUTPUT` directory. All input examples are fictional software
fixtures, not real observations, reading or scientific approval. Begin with the
supplied report/study inventory fixture, whose full-text memberships already
permit these example results. Do not use this fixture as a real research base.

```sh
python result_intake.py target examples/report-study-inventory-reviews.json examples/manual-result-candidates.json --output OUTPUT/result-target.json
```

Copy only `review_document` from that target to `OUTPUT/result-review.json`. Keep
`schema_version` and `target_sha256`, then supply every remaining field honestly:
`receipt_id`, `reviewer`, `reviewed_at` (YYYY-MM-DD), `rationale`, and
`decision: "import_results"`. For this rehearsal only, use clearly fictional
reviewer/receipt labels and rationale. A blank or stale review is rejected.

```sh
python result_intake.py assemble examples/report-study-inventory-reviews.json examples/manual-result-candidates.json OUTPUT/result-review.json --output OUTPUT/result-application.json
python result_intake.py verify examples/report-study-inventory-reviews.json OUTPUT/result-application.json --protocol-output OUTPUT/with-results.json
python result_correction.py target OUTPUT/with-results.json examples/manual-result-corrections.json --output OUTPUT/correction-target.json
```

Copy the new `review_document` to `OUTPUT/correction-review.json`, retaining its
new target hash. Supply the same human field names, with a distinct receipt and
`decision: "correct_result_text"`. This is a separate review of the exact supplied
correction, not reuse of the import review or a newly invented result ID.

```sh
python result_correction.py assemble OUTPUT/with-results.json examples/manual-result-corrections.json OUTPUT/correction-review.json --output OUTPUT/correction-application.json
python result_correction.py verify OUTPUT/with-results.json OUTPUT/correction-application.json --protocol-output OUTPUT/corrected.json
python condition_intake.py target OUTPUT/corrected.json examples/manual-condition-candidates.json --output OUTPUT/condition-target.json
```

Copy this target's `review_document` to `OUTPUT/condition-review.json` and complete
all human fields for a separate review, with `decision: "import_conditions"`.
These fixture descriptions contain only fictional labels and explicitly missing
information, not experimental instructions or inferred parameter values.

```sh
python condition_intake.py assemble OUTPUT/corrected.json examples/manual-condition-candidates.json OUTPUT/condition-review.json --output OUTPUT/condition-application.json
python condition_intake.py verify OUTPUT/corrected.json OUTPUT/condition-application.json --protocol-output OUTPUT/final.json
python extraction_transition_bundle.py create examples/report-study-inventory-reviews.json OUTPUT/final.json OUTPUT/extraction-transitions.zip --application OUTPUT/result-application.json --application OUTPUT/correction-application.json --application OUTPUT/condition-application.json
python extraction_transition_bundle.py verify OUTPUT/extraction-transitions.zip --text
```

The fixture begins with two result rows and ends with four, not six: the correction
changes two existing text fields without adding or renaming rows. Two descriptive
condition records are appended. Report/study membership and report-stage counts remain unchanged. Result intake
increases extraction counts (result rows 2 to 4; extracted study labels 2 to 3);
correction and condition intake add no results. Source selections and earlier wording remain in the applications;
they are not copied into protocol result rows or silently treated as final approval.

The [existing NBIB-to-evidence rehearsal](BATCH_TO_EVIDENCE.md) also supplies a
compatible two-step segment, without adding a correction:

```sh
python extraction_transition_bundle.py create OUTPUT/included.json OUTPUT/final.json OUTPUT/extraction-transitions.zip --application OUTPUT/result-application.json --application OUTPUT/condition-application.json
python extraction_transition_bundle.py verify OUTPUT/extraction-transitions.zip --text
```

Use the `OUTPUT` from that walkthrough for these two commands, not the different
fixture rehearsal above. Its [report archive](REPORT_TRANSITION_BUNDLES.md) ends
at the same included protocol where this extraction segment begins. The archives
remain separate; equal boundary fingerprints do not establish complete research
history. Collection/screening and other omitted operations are not added here.

## Contents and verification

Generated member paths never come from source IDs, report IDs or local filenames:

- `protocols/initial.json` and `protocols/endpoint.json`: exact supplied bytes.
- `applications/step-000000.json` and consecutive names: exact ordered applications.
- `chain.json`: per-step kind, generated path, byte length/hash, canonical input and
  candidate hashes, receipt ID/hash and existing verifier replay status.
- `summary.txt`: bounded scope, endpoint fingerprints and explicit negative claims.
- `manifest.json`: every payload size/hash and the recorded local implementation
  hashes, including the three verifiers and directly used JSON/output helpers.

The archive contains no code. Retain the recorded repository revision separately.
Verification never imports or executes anything from the ZIP. It checks closed
member paths, types and sizes, reruns the existing verifiers, rebuilds the complete
canonical ZIP and compares all bytes. Changed manifest/summary, resealed tampered
receipts, stale inputs, changed implementation and changed endpoint fail.
Omitted/reordered steps that break exact replay fail; a replay does not prove that
no unrecorded reversible changes occurred. Metadata or repacking that changes bytes also fails; byte-identical
canonical repacking remains valid. Consistently reauthored inputs can still replay:
these unsigned receipts do not establish authorship, execution or immutable history.

Move the archive to another location and verify using the recorded implementation;
original local input paths are unnecessary. Supplied locator strings are retained
but never followed. No files are extracted, sources read or network calls made.

## Limits and exclusions

At most 20 steps and 50,000,000 total archive bytes are supported. Input aggregates,
declared uncompressed sizes and serialized outputs are bounded; these are not
hard CPU/memory ceilings. Strict UTF-8 JSON rejects duplicate keys, non-finite
numbers and unpaired surrogates. Only stored regular ZIP members with fixed names
are accepted; duplicates, extra paths, symlinks and compressed members fail.

Output is serialized before creation. Existing final entries, including observed
dangling symlinks, are refused using inspection plus exclusive creation. This is
not an atomic path-race or parent-alias defense; a failed write can leave a partial
new file. Use a new destination and keep real inputs outside the public repository.
All supplied text, identities, locators and private data are retained without
redaction. These commands do not publish or share an archive.

Collection, screening, report transitions, inventory intake, source-work intake,
review-only edits, source updates and other operations are unsupported as steps.
Do not omit such an intervening mutation and call the chain contiguous. An
explicit shorter segment can begin after it, without claiming the missing history.
Existing ledgers remain subject to existing protocol validators. Use the separate
[native collection archive](NATIVE_COLLECTION_BUNDLES.md) for selected citation
bytes/import associations; source documents and ordinary research ZIPs are not
embedded in this extraction archive.

Earlier/later history is `NOT_ASSESSED`, complete history and extraction census
are `NOT_ESTABLISHED`, scientific acceptance is `NOT_ASSESSED`, review renewal and
downstream reassessment are `NOT_PERFORMED`, and conclusions remain `NOT_READY`.
No source authentication, verified reading, eligibility, independent-study count,
PRISMA compliance or clinical validity is established by replay success.
