# Preserve a selected appraisal-import history segment

`appraisal_transition_bundle.py` creates a deterministic offline ZIP holding exact
initial protocol, explicitly ordered appraisal intake applications and endpoint
protocol bytes. Each step uses the existing `appraisal_intake.verify` authority.
It packages previously supplied appraisals; it does not perform or renew one.

The format is separate from ordinary research, native-source, report, extraction
and work-transition bundles. None of those existing archive formats is changed.
A read-only appraisal source comparison is not a transition and cannot be supplied
as an application step.

## One imported batch, preserved as a portable segment

First complete the synthetic [appraisal intake rehearsal](MANUAL_APPRAISAL_INTAKE.md).
Keep its original input and generated application/endpoint files. Use the same new
existing `OUTPUT` directory outside this repository, then run:

```sh
python appraisal_transition_bundle.py create examples/synthesis-review.json OUTPUT/with-appraisals.json OUTPUT/appraisal-segment.zip --application OUTPUT/appraisal-application.json --text
python appraisal_transition_bundle.py verify OUTPUT/appraisal-segment.zip --text
```

Verification succeeds only with the recorded implementation bytes available.
The implementation itself is not embedded or executed from the ZIP. Preserve the
corresponding checkout separately. Moving the ZIP does not require its former host
paths or original sidecar files for replay. No source document or locator is opened.

For multiple consecutive imports, repeat `--application` in actual supplied order.
The previous step's canonical candidate must match the next step's original review
basis. Do not omit intervening changes or reinterpret a later application against
a new base. Supply the actual endpoint, not a guessed or regenerated replacement.
A selected prefix or suffix is valid when its actual endpoints are provided; that
does not prove earlier or later history was complete.

## Retained members and verification

The ZIP contains only:

- `protocols/initial.json` and `protocols/endpoint.json`, byte-for-byte originals.
- `applications/step-000000.json`, and consecutive numbered application originals.
- `chain.json`, with ordered receipt IDs, appraisal IDs and exact byte/canonical
  protocol hashes for each step.
- `summary.txt`, with consistency bounds and explicit nonverification statements.
- `manifest.json`, with member hashes, lengths and implementation fingerprints.

Raw whitespace, Unicode spelling and object-key order are retained. Connections
between protocol steps use canonical JSON equality, which distinguishes Boolean
values from numbers but permits different whitespace/key ordering. All original
opaque fields, appraisal prefix records, result/source snapshots, import-review
assertions and downstream status cues remain under their original exact replay.
Historical snapshots are not automatically applicable at the endpoint or later.

Imported appraisal IDs are reported per step. These are not independent reviewers,
independent studies, consensus votes or measures of evidence adequacy. Conflicting
positions remain distinct supplied records. Existing synthesis/planning/completion
hashes are not refreshed by packaging; original source-status changes remain visible
inside each retained application. Appraisal validity remains NOT_ASSESSED.

The verifier regenerates the whole canonical archive and compares every byte.
Unknown paths, duplicate entries, symlinks, encryption, compression, missing or
nonconsecutive steps, modified receipts, reordered imports, endpoint drift and
changed ZIP metadata are rejected. Rehashing a changed manifest alone cannot make
an altered payload replay. Byte-identical canonical repacking is accepted. This
is not authentication: consistently rewritten unsigned assertions can replay.

## Bounds and exclusions

One to twenty explicit application files are accepted. Retained payloads and final
ZIP bytes are bounded at 50 MB; each CLI input is read with that cap and rendered
output is checked before exclusive output creation. These are byte limits, not
hard CPU/memory ceilings. Existing output entries and observed dangling links are
refused. Failed writes can leave partial new files; no atomic ancestor-alias or
path-race defense is claimed.

The verifier works in memory, never extracts files, follows locators or makes
external/model calls. Only `detached_appraisal_intake` is supported as a step.
Search/collection, screening, report, extraction, correction, condition and work
operations need their own records/formats. This selected archive is not a complete
research history, PRISMA certification or source-document archive. Earlier/later
history stays NOT_ASSESSED, census NOT_ESTABLISHED and conclusions NOT_READY.

No appraisal method, domain judgement, quality score, consensus or development
recommendation is generated or validated. Reviewer identity, independence,
chronology, actual reading and source authenticity remain unverified. Supplied
private text and identities are retained without redaction. Use synthetic examples
here and keep real inputs and generated archives outside the public repository.
