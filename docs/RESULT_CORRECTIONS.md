# Explicit correction of existing result text

`result_correction.py` applies separately reviewed, human-supplied transcription
corrections to existing `result` and/or `limitations` text. A correction is not
another finding: the existing extraction ID, row position and result count stay
the same. The tool never decides what the corrected wording should say.

Use ordinary [manual result intake](MANUAL_RESULT_INTAKE.md) for genuinely new
result rows. Do not give a corrected copy a new ID merely to get around an intake
collision: doing so retains the old row and counts another result.

## Fictional journey

The starting `examples/result-source-current.json` has four fictional result rows.
`examples/manual-result-corrections.json` supplies two narrow corrections: study
C's null-finding wording and the limitation on study A's second result. Neither
contains real observations, full text or biological execution instructions.

```sh
python result_correction.py target examples/result-source-current.json examples/manual-result-corrections.json --output /outside/new-correction-target.json --text
```

Inspect the before/after rows, exact selected sources and human correction notes.
Save the output's `review_document` as a separate file, then honestly fill its null
human fields: `receipt_id`, `decision: "correct_result_text"`, `reviewer`,
`reviewed_at` and `rationale`. Keep the target hash actually reviewed. A template
or a hash is not a person's review; do not refresh the hash just to pass a changed
proposal. These examples only rehearse software bookkeeping.

```sh
python result_correction.py assemble examples/result-source-current.json examples/manual-result-corrections.json /outside/completed-correction-review.json --output /outside/new-correction-application.json --text
python result_correction.py verify examples/result-source-current.json /outside/new-correction-application.json --protocol-output /outside/new-corrected-protocol.json --text
python compare_runs.py examples/result-source-current.json /outside/new-corrected-protocol.json --text
python research_bundle.py create /outside/new-corrected-protocol.json /outside/new-corrected-bundle.zip
python research_bundle.py verify /outside/new-corrected-bundle.zip
```

Use new paths in an existing directory. `assemble` writes a detached application
record, not a bare protocol. `verify --protocol-output` exports its candidate only
after the complete record replays against the original input. The example still
has four results, one included report and three included study labels. Original
input files and objects remain unchanged; the new candidate's version label is
also unchanged. Version changes or other edits require a separate explicit step.

## Deliberately narrow correction contract

The correction document has exactly integer `schema_version: 1` and `corrections`,
an ordered nonempty list of at most 100 rows. Each row has exactly:

- `evidence_id`: an existing **explicit raw** extraction ID.
- `report_id`: the exact existing report owning the result's source record.
- `changes`: a nonempty object containing only `result`, `limitations`, or both.
- `source_references`: a nonempty list of exactly `source_id` and
  `extraction_locator` objects, without repeated source IDs within that correction.
- `corrected_by`, `corrected_at`, `correction_note`: explicit human metadata.

All text is nonblank and preserved literally, including significant whitespace.
`corrected_at` is a real `YYYY-MM-DD` date. Every field listed in `changes` must
actually differ from the original raw value; no-op fields fail even if another
field changes. Repeated target IDs in a batch fail. A legacy implicit record-based
ID is not accepted as an explicitly supplied extraction ID. Similar spelling,
case or whitespace is never normalized into a match.

The report must already be retrieved and included, map the existing record and
explicitly declare its study. Every selected source descriptor must currently
belong to that report. Sources are never chosen from a prior intake automatically.
Null document digests remain unbound; supplied digests remain unverified. Locations
are inert text, never opened or fetched. Selecting a source does not establish
that it supports either the old or corrected wording.

The tool cannot change result IDs, record/study/report identity, eligibility,
source descriptors, endpoints, model/comparison metadata, mechanism labels, or
any other field. It cannot delete or append results. Those broader changes need a
separately designed workflow; this command is not a general protocol patch tool.
It preserves opaque metadata and all untouched fields rather than reconstructing
rows from a smaller normalized schema.

Both the complete original and candidate undergo core and full report/evidence
validation, including legacy scalar report declarations. Invalid unrelated input
fails too. CSV-import provenance remains supported under its existing evidence
enrichment rules, and is neither rewritten nor discarded. Mock `adapter_receipts`
inputs are unsupported and must not be stripped to bypass that contract. A
correction cannot be used to repair an already structurally invalid protocol.

## Review target and detached replay

The target binds the entire original protocol's canonical hash, full ordered
correction document, before/after result rows and changed fields, report/record
context, explicitly selected sources and locations, and implementation hashes.
Result pointers identify positions in the original protocol, preserved in the
candidate. Source pointers also refer to that original input. They are navigation
within this operation, not persistent cross-version identities.

The review has exactly integer `schema_version: 1`, `receipt_id`, `target_sha256`,
`decision`, `reviewer`, `reviewed_at` and `rationale`. Only schema and target hash
are prefilled. The decision must be `correct_result_text`, the date a real
`YYYY-MM-DD`, and other human fields nonblank literal text. Changes anywhere in
the original input, proposal, selected sources or implementation invalidate this
review. There is no automatic rebase, approval, vote or hash renewal. Object-key
order and JSON formatting are ignored; list order, literal values and JSON number
types remain significant.

The application has schema 1, kind `detached_result_correction`, `receipt` and
`protocol_candidate`. The receipt retains the proposal, human assertion, target,
before/after counts, whole-input/candidate hashes, implementation fingerprints,
negative verification states and its own checksum. Replay rebuilds and compares
the **entire** record, not just its checksum. Tampered snapshots, candidates,
unknown fields or implementation drift fail. Retain the original input, application
and exact recorded code. This does not migrate old receipts between code versions.

This is an editable, unsigned record, not authenticated chronology or proof of
who inspected a source. A consistently reauthored assertion can replay. Receipt
IDs have no global uniqueness or time-order authority. Success proves mechanical
reproducibility of the supplied operation, not that the correction is true.

## Existing assertions and downstream limits

Earlier intake records and source associations are not edited or renewed.
[Result-source comparison](RESULT_SOURCE_REVIEW.md), when given an earlier intake
and its actual original input, still reports the corrected raw row as `CHANGED`.
A source descriptor can remain unchanged while result wording changes. The new
correction's selected sources are separate supplied associations, confined to its
detached record; the protocol gains no persistent correction or source ledger.

All ID-linked appraisals, condition/statistics metadata, synthesis statements,
planning assertions and work completion fields remain literally unchanged.
Existing engine rules can expose stale source-bound reviews after a correction,
but **not all downstream assertions have such bindings**. The tool neither
reassesses attached metadata nor claims every affected assertion was detected or
invalidated. A recorded `COMPLETE` task remains `COMPLETE`, even if an existing
completion-source check now says `STALE_SOURCE`. Review these consequences
separately; no task or scientific judgment is automatically reopened or approved.

Ordinary research bundles retain the corrected protocol, not this application
record or its original input. Bundle verification therefore does not verify the
correction's detached source associations or human review. Source authenticity,
document bytes, reading, scientific/clinical correctness, reviewer/corrector
identity, extraction completeness and downstream reassessment remain unestablished
or unperformed. Corrected wording is still supplied evidence, not validated fact.

## Files and bounds

Python callers use `prepare(protocol, correction_document)`,
`assemble(protocol, correction_document, review_document)` and
`verify(original_protocol, application_record)`. Outputs are detached from caller
objects. The standalone command leaves existing canonical engines and older
intake/source-comparison implementations unchanged.

Correction/review documents are limited to 10 MB, original/candidate protocols and
application records to 50 MB. Encoded CLI JSON/text output is also bounded to 50 MB.
Strict JSON/UTF-8 validation and output encoding precede file creation. Every
command can exclusively create at most one file and refuses overwrite, including
input paths and existing symlinks. A disk/write failure can still leave a partial
new file; this is not an atomic filesystem transaction. `--text` changes stdout,
while saved files stay JSON. Shell redirection has its own overwrite risks.

Keep real/private inputs and outputs outside this public repository. They retain
all supplied information without redaction. Nothing is uploaded or sent externally.
