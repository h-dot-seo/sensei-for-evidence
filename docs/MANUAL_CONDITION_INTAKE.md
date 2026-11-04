# Explicit intake of supplied condition descriptions

`condition_intake.py` appends already completed, human-supplied comparison-condition
records through a separate review and replay step. It connects the existing
[condition metadata contract](EXPERIMENT_CONDITIONS.md) to explicit report-document
selections without requiring a person to edit the protocol ledger directly.

This is source-description bookkeeping, **not experimental design or execution**.
It never generates conditions, amounts, timing, models, sample sizes or statistical
values. It does not inspect source content or decide that a causal or clinical
claim is supported. Every descriptive field and document choice is supplied by a
person; the existing validator checks structure and links, not scientific truth.

## Fictional example

The existing extraction-worksheet protocol has four fictional results and no
condition ledger. `examples/manual-condition-candidates.json` explicitly describes
two fictional comparison pairs. The first links study A's two result IDs; the
second links study C's one result. No real organism, material, dose, duration,
procedure, assay or actual observation is supplied.

```sh
python condition_intake.py target examples/extraction-worksheet-protocol.json examples/manual-condition-candidates.json --output /outside/new-condition-target.json --text
```

Inspect the complete condition records, linked existing results, source descriptors
and supplied extraction notes. Save the output's `review_document` as a separate
file and honestly fill its null fields: `receipt_id`,
`decision: "import_conditions"`, `reviewer`, `reviewed_at` and `rationale`.
Keep the target hash actually reviewed. No blank template, matching checksum or
fictional example constitutes human review or acceptance of scientific validity.

```sh
python condition_intake.py assemble examples/extraction-worksheet-protocol.json examples/manual-condition-candidates.json /outside/completed-condition-review.json --output /outside/new-condition-application.json --text
python condition_intake.py verify examples/extraction-worksheet-protocol.json /outside/new-condition-application.json --protocol-output /outside/new-condition-protocol.json --text
python research_status.py /outside/new-condition-protocol.json --text
python compare_runs.py examples/extraction-worksheet-protocol.json /outside/new-condition-protocol.json --text
python research_bundle.py create /outside/new-condition-protocol.json /outside/new-condition-bundle.zip
python research_bundle.py verify /outside/new-condition-bundle.zip
```

Use new paths in an existing directory. The resulting protocol still has four
result rows, one included report and three included study labels. It gains two
comparison-pair descriptions covering three result IDs; result B remains unlinked.
The previously absent condition stage becomes supplied. Before that stage existed,
its unlinked-result queue was null, not an observed zero.
`condition_pair_count` counts stored supplied records only: zero with an absent
stage does not assert that the source literature contains no conditions.

Pair counts are not biological replicates, independent experimental units, sample
sizes or evidence weights. Supplied missingness remains visible. A complete set
of fields, or a missing-link queue becoming smaller, is not complete extraction,
valid statistics, a scientifically adequate comparison or mechanistic evidence.

## Candidate document

The document has exactly integer `schema_version: 1` and `candidates`, a nonempty
ordered list of at most 100 objects. Each candidate has exactly:

- `report_id`: the included, retrieved report for the linked existing results.
- `experimental_unit`: one completed record under the existing strict condition
  contract, including its optional outcome sampling/statistics metadata if supplied.
- `source_references`: a nonempty list of exactly `source_id` and
  `extraction_locator` objects, with no repeated source ID within the candidate.
- `extracted_by`, `extracted_at`, `extraction_note`: explicit human metadata.

Human/source text is nonblank and retained literally. `extracted_at` is a real
`YYYY-MM-DD` date. No date, missingness status or scientific value is inferred.
The condition schema is unchanged: a condition has a unique `experiment_id`,
existing `evidence_ids`, source/limitation fields, model/comparison descriptions,
per-result observation times and explicit causal wording/limitations. Optional
sampling/statistics must satisfy their existing exact result-coverage contracts.

Every referenced result must have an existing **raw explicit** `evidence_id`.
A legacy record-based fallback is not accepted as an explicitly supplied extraction
ID. All linked results must share one exact record and study, belong to the
selected report, and use its declared membership. Existing and within-batch
condition-ID collisions or assignment of a result to more than one condition fail.
No aggregate result is automatically split and no result is duplicated, reassigned
or created to make a condition fit.

The existing reporting-state unions remain authoritative. Reported values and
units are text; explicit unknown/unreported/not-applicable states retain reasons
and locations without invented values. The tool does not coerce numbers, convert
units, calculate effects, infer denominators, or fill time anchors. A condition's
causal-basis label must match the linked results' supplied labels; matching labels
are a consistency check, not proof of causality or mechanism.

Every selected source descriptor must currently belong to that report. Null
digests remain unbound, and supplied digests remain unverified. Locations are
inert text and are never followed. These are **whole-condition source associations**,
not field-by-field provenance or proof that every linked document supports every
value. No source or preferred document version is chosen automatically.

## Preservation and provenance compatibility

Both the entire original and candidate undergo core and full report/evidence
validation, including legacy scalar report declarations and unrelated rows. The
supplied condition objects are appended unchanged and in order. An absent
`experimental_units` field is created; a supplied empty or nonempty list keeps its
existing prefix. Every other raw protocol field remains unchanged, including
results, reports, searches, source descriptors, version and human assertions.
Record/report flow is checked to remain equal.

CSV-import history is supported under its existing metadata-enrichment rules and
is preserved without rewriting. Unlike result-row intake, this operation also
supports **already valid mock-adapter provenance**, because that existing contract
permits condition metadata enrichment without altering accepted results.

Explicit reports and source descriptors must already be valid under the mock
adapter's base contract: they cannot be added afterward as a hidden enrichment.
The tool neither relaxes provenance checks nor removes a ledger to make an input
pass. A broken history or invalid original protocol fails before any candidate
is exported. Mock receipts remain synthetic, unverified provider assertions.

Existing appraisals, synthesis positions, planning decisions and completion
assertions are not rewritten or renewed. Adding condition metadata can make
existing source-bound assertions stale under the established engine rules while
leaving their recorded status unchanged. Not every assertion has such a binding;
the tool does not claim that all downstream consequences have been detected or
scientifically reassessed. Inspect those views separately.

## Review target and detached replay

The target binds the whole original protocol's canonical hash, complete ordered
candidate document, full linked raw evidence snapshots and input pointers,
selected report/record context, selected source descriptors and locations, and
implementation fingerprints. Pointers refer to the retained original input, not
stable identities across versions. Any input or candidate change, including
result wording or an unrelated version edit, requires a fresh explicit review.
Object-key order and formatting are ignored; list order, literal values and JSON
number types remain significant.

The review has exactly integer `schema_version: 1`, `receipt_id`, `target_sha256`,
`decision`, `reviewer`, `reviewed_at` and `rationale`. Only schema and target hash
are prefilled. The sole decision is `import_conditions`; the date must be real
`YYYY-MM-DD`, and all human fields must be supplied. There is no automatic approval,
rebase, reviewer authentication, vote or hash renewal.

The application record has schema 1, kind `detached_condition_intake`, `receipt`
and `protocol_candidate`. The receipt preserves the candidate document, human
assertion, target, before/after flow and condition summaries, whole-input/candidate
hashes, implementation hashes, negative verification states and its checksum.
Replay reconstructs the complete record from the actual original input and
embedded proposal/review, then compares every field. Tampered snapshots, hashes,
derived counts, unknown fields and altered implementation fail exact replay.

This is editable, unsigned bookkeeping. Consistently reauthored assertions can
replay, so success does not authenticate who reviewed what or when. Receipt IDs
provide no global uniqueness or chronological authority. Retain the original
input, application record and exact recorded code; this operation does not migrate
old receipts across implementation versions.

Document selections and extraction/review metadata stay in the separate record,
not a persistent source-association ledger inside the protocol. Ordinary bundles
retain the appended conditions but not this record or original input. Later
protocol edits or bundle verification do not validate these detached associations.
No original result-intake or correction record is edited or renewed.

## Files and limits

Python callers use `prepare(protocol, candidate_document)`,
`assemble(protocol, candidate_document, review_document)` and
`verify(original_protocol, application_record)`. Candidate/review documents are
limited to 10 MB; original/candidate protocols and application records to 50 MB.
Encoded CLI JSON/text output is also bounded to 50 MB. These are resource limits,
not scientific scope or completeness limits.

`target` and `assemble` each require one new JSON output. `verify` optionally
creates one candidate protocol after successful replay. `--text` affects stdout
only. Strict JSON/UTF-8 validation and encoding occur before exclusive file
creation; existing paths, inputs and symlinks are not overwritten. A later disk
error can leave a partial new file; this is not an atomic filesystem transaction.
Shell redirection has its own overwrite risks.

Only generic code and synthetic fixtures belong in this public repository. Keep
actual research inputs and outputs private: supplied information is retained
without redaction. No external calls or uploads occur. Document authenticity,
reading, clinical correctness, scientific validity, causality, independence,
statistical adequacy and exhaustive extraction remain unestablished or unassessed.
