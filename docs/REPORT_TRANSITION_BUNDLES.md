# Preserve an explicitly selected report-transition segment

`report_transition_bundle.py` creates a separate portable archive for an ordered,
contiguous segment of existing report-registration, retrieval-update and full-text
applications. It closes a handoff gap: a final research/collection ZIP preserves
the protocol, but not these detached reviews and prior retrieval values.

The wrapper retains exact file bytes and calls each existing application verifier.
It does not change protocol schemas, produce a new review, repair stale records,
renew hashes or alter existing bundle formats. A successful archive verifies
supplied-data consistency, not who performed a review or whether any research
operation actually happened.

## Scope: three existing application types

Supported `kind` values are exactly:

- `detached_report_intake`: explicit new report registration.
- `detached_report_retrieval_update`: supplied retrieval-state transitions.
- `detached_report_decision`: supplied full-text eligibility/membership choice.

Supply one to 20 application files in their explicitly supplied transition order.
Order is a caller assertion, not authenticated chronology. A segment may start or
end at any supported operation, and the same kind can occur more than once. The
initial protocol need not be the start of the research project.

For each step, its existing verifier receives the preceding candidate protocol as
its original input. The first step uses the retained initial protocol. The final
candidate must match the separately supplied endpoint protocol by complete
canonical JSON equality. Different whitespace/key order is permitted between
equivalent JSON representations, but each supplied file's original bytes and byte
hash remain separately preserved. Missing steps, reordered applications and stale
whole-input hashes are refused when they break that exact chain. A claimed final
protocol with later evidence additions is not this segment's endpoint.

## Continue the NBIB-to-evidence rehearsal

First execute the [30-command synthetic walkthrough](BATCH_TO_EVIDENCE.md), keeping
its external `OUTPUT` directory. Its report segment starts at `screened.json` and
ends at `included.json`, before result and condition intake. Use a new archive path:

```sh
python report_transition_bundle.py create OUTPUT/screened.json OUTPUT/included.json OUTPUT/report-transitions.zip --application OUTPUT/report-application.json --application OUTPUT/retrieval-application.json --application OUTPUT/full-text-application.json
python report_transition_bundle.py verify OUTPUT/report-transitions.zip --text
```

These are prewritten fictional assertions, not actual acquisition, reading or
review. The segment covers three supplied transitions: registration, a retrieval
update and one full-text choice. Its endpoint has two retrieved reports, one
included report with one declared study, one report awaiting assessment, and no
result rows. The later `final.json` with two results is deliberately **not** accepted
as this segment's endpoint. Do not describe this ZIP as the complete evidence run.

This archive can be copied to another location and verified with the recorded
implementation without the original input paths. The implementation is not
embedded. Changed verifier/wrapper bytes require the separately retained recorded
revision; no archive-supplied script is loaded or executed.

## Archive contents and binding

All member names are generated, never derived from report IDs or local paths:

- `protocols/initial.json`: exact supplied initial-protocol bytes.
- `protocols/endpoint.json`: exact supplied endpoint-protocol bytes.
- `applications/step-000000.json`, and consecutive names: exact ordered application
  bytes, including the full existing receipt and its candidate protocol.
- `chain.json`: per-step kind, generated path, exact raw size/hash, canonical input
  and candidate hashes, receipt ID/hash, and the supported verifier's replay status.
  It also distinguishes initial/endpoint raw hashes from canonical protocol hashes.
- `summary.txt`: bounded scope, endpoint fingerprints and negative claims.
- `manifest.json`: payload sizes/hashes and the existing verifier/wrapper code hashes.

The entire archive is deterministic stored ZIP with fixed member metadata and
ordering. Verification checks paths/types/size bounds, invokes the existing replay
functions, rebuilds the archive, then compares complete bytes. Rewriting the
manifest, changing summary text, re-zipping, altering metadata or merely resealing
a changed receipt does not repair an inconsistency. A consistently reauthored
complete set of inputs can still replay: this is not an authenticated or immutable
history service.

## What remains outside the segment

Earlier and later history are explicitly `NOT_ASSESSED`, and complete history is
`NOT_ESTABLISHED`. This wrapper does not accept collection, screening, result,
condition, correction or source-work applications as steps. Existing ledgers
inside the protocols remain checked by their existing protocol validators, which
does not reconstruct all omitted operations or prove execution.

The archive does not add original NBIB files, document files, source-code files or
the ordinary research bundle. Keep the separate
[batch-native collection archive](BATCH_COLLECTION_BUNDLES.md) for selected native
source bytes and historical import association. Its endpoint may be a later stage;
that does not extend this segment's coverage. Keep result/condition applications
and their originals separately. No preferred document version, source identity,
reviewer authority, eligibility correctness, census or scientific readiness is
established by either archive.

This tool never opens a source locator, downloads a paper, extracts ZIP members,
transmits data or performs a biological experiment. The only local inputs read
are the explicitly named protocol/application/archive files and implementation
files needed for fingerprints.

## Limits, output behavior and privacy

At most 20 steps and 50,000,000 total archive bytes are supported. The aggregate
retained payloads, declared uncompressed ZIP sizes and serialized output are
bounded. Inputs are strict UTF-8 JSON; duplicate keys, non-finite numbers, unpaired
surrogates, unknown application types and invalid prior protocols are rejected.
Generated paths, duplicate-member refusal, stored-only regular files and exact
canonical rebuild prevent traversal, symlink, compressed-payload and metadata
substitution from being accepted. Nothing is extracted during verification.

Serialization is preflighted before output creation. Existing final entries,
including dangling symlinks, are refused using final-entry inspection and
exclusive creation. This is not race-proof or a parent-alias security boundary;
a failed write can leave a partial new file. Use a new path rather than overwriting
real work to rerun an example.

All supplied private text, human labels, locators and candidate data are retained
without redaction. Keep real inputs/archives outside the public repository and
check permissions before sharing. No sharing or publishing occurs through these
commands. Verification remains `NOT_ESTABLISHED` for census/complete history and
`NOT_READY` for conclusions, even when every selected step replays successfully.
