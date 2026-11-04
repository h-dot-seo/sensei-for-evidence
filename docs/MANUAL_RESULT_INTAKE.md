# Explicit manual result intake and replay

`result_intake.py` connects existing collected, screened and included reports to
manually supplied result rows. Unlike the mock adapter, it accepts an existing
CSV-import workflow. It never reads a document or creates a scientific extraction.
A person supplies every result, source selection and location, then explicitly
reviews that exact batch before a new protocol candidate is produced.

To start an unfinished candidate, use a [manual extraction worksheet](EXTRACTION_WORKSHEETS.md).
It joins exact report-study context and existing results while leaving scientific
fields, source choices and human metadata blank. Complete those fields before
requesting the intake target below.

This is append-only, **detached** intake. Source associations remain in its separate
application record, not a new persistent protocol ledger. Ordinary later views do
not validate those associations or detect their staleness after further edits.
Keep the original protocol, application record and recorded implementation.

## Fictional end-to-end journey

Use the existing candidate-review example as the original protocol. The supplied
result candidates are entirely fictional. They add one null-finding description
for study C and another result for study A, without creating reports or studies.
No source text, real paper, clinical fact or biological procedure is included.

```sh
python result_intake.py target examples/report-study-inventory-reviews.json examples/manual-result-candidates.json --output /outside/new-result-target.json --text
```

Inspect the target and source mappings. Save only its `review_document` object as
a separate review file, then fill all null human fields after actual inspection:
`receipt_id`, `decision: "import_results"`, `reviewer`, `reviewed_at` and `rationale`.
The target hash must remain the one actually reviewed. A blank template is not
acceptance. Do not renew a hash just to make a changed batch pass.

```sh
python result_intake.py assemble examples/report-study-inventory-reviews.json examples/manual-result-candidates.json /outside/completed-result-review.json --output /outside/new-result-application.json --text
python result_intake.py verify examples/report-study-inventory-reviews.json /outside/new-result-application.json --protocol-output /outside/new-results-protocol.json --text
python prisma_audit.py /outside/new-results-protocol.json --text
python research_bundle.py create /outside/new-results-protocol.json /outside/new-results-bundle.zip
python research_bundle.py verify /outside/new-results-bundle.zip
```

Choose new paths in an existing directory. Each command can create only one new
file and refuses overwrite, including inputs. `assemble` saves an application
record, not a bare protocol. `verify --protocol-output` exports the candidate only
after exact replay succeeds. `--text` affects stdout, while saved output stays
JSON. Validation and encoding precede output creation; a later disk/write error
can leave a partial newly created file. This is not an atomic filesystem commit.
Original files and objects are not edited. Shell redirection has separate risks.

The example changes result-row count from two to four. Study C's existing
report-specific membership gains a result; included report/study labels, searches,
all earlier evidence rows, human positions and work assertions remain unchanged.
A null finding is retained as supplied text, not dropped because it lacks a
positive direction. Any-result presence does not establish exhaustive extraction.

## Candidate document

The top-level object has exactly integer `schema_version: 1` and `candidates`, a
nonempty ordered list of at most 100 rows. Each candidate has exactly:

- `report_id`: the explicit existing report that owns the source record.
- `evidence`: one complete result object, with exactly `evidence_id`, `record_id`,
  `study_id`, `locator`, `model`, `intervention`, `comparator`, `endpoint`, `result`,
  `limitations` and `mechanism_basis`.
- `source_references`: a nonempty list of exactly `source_id` and
  `extraction_locator` objects. Source IDs must be unique within this candidate.
- `extracted_by`, `extracted_at`, `extraction_note`: supplied human metadata.

All text fields are nonblank literal strings. `extracted_at` is a real
`YYYY-MM-DD` date. `mechanism_basis` must be `association`, `intervention` or
`unknown`; none of these labels establishes causality. Source locations and
extraction notes are inert supplied text, not instructions to execute. No ID,
source, person, date, result, limitation or study label is inferred or normalized.

Every result needs an explicit new `evidence_id`, including when older rows use
implicit record-based IDs. Batch duplicates and collisions with either kind of
existing ID fail. The source record must already map to that exact retrieved,
included report, and the report must explicitly declare the study using its
existing scalar or plural membership rules. A candidate inventory label or human
include position does not substitute for an included membership.

Every selected source descriptor must exist and belong to the same report.
Multiple source descriptors and per-source page/section locations can be supplied;
none is selected automatically. Null document digests remain unbound, and nonnull
digests remain unverified. A location and digest do not establish that the source
contains or supports the result. No URL, path or locator is opened.

The tool validates the entire original and temporary appended candidate with both
core and full report/evidence reconciliation, including scalar-only report inputs.
Unknown extra candidate, result, source-reference or review fields fail. Do not
put a mock provenance assertion or arbitrary payload into this narrow schema.
A protocol containing `adapter_receipts` is explicitly unsupported here. It must
not be stripped or rewritten to bypass its provenance contract. CSV-import history
is supported under its existing evidence-enrichment rules and is preserved.

## Explicit acceptance target

The target binds the canonical hash of the entire original protocol, the full
ordered candidate document, selected report/record source context, selected
source descriptors with human locations, and implementation hashes. Mapped local
CSV provenance is included. The original protocol body is not embedded as a
replacement for retaining the actual input. Snapshots do not reconstruct it.

Any protocol change, even unrelated metadata or version changes, invalidates the
review target. Candidate edits, reordered candidates, changed source selections,
source descriptors and implementation drift likewise require a fresh explicit
review. Object-key order and JSON formatting are ignored; literal values, number
types and list order remain significant.

The review document has exactly integer `schema_version: 1`, `receipt_id`,
`target_sha256`, `decision`, `reviewer`, `reviewed_at` and `rationale`. Only the
schema and target hash are prefilled. All human fields must be supplied and
nonblank, the date real `YYYY-MM-DD`, and the hash 64 lowercase hexadecimal
characters. The only operation is `decision: "import_results"`. This states an
intention to append the supplied batch, not acceptance of scientific validity.
There is no automatic approval, reviewer authentication, independence test or vote.

Assembly appends the exact candidate evidence rows in supplied order. It does not
replace earlier results, change source/report identities, screening, report
eligibility, memberships, search completion, work status, contexts or version.
It neither writes extracted-person metadata into the result row nor injects a
new protocol provenance key. Those associations remain in the detached receipt.
Changes to derived missing-result queues are bookkeeping consequences, not newly
verified reading or evidence sufficiency.

## Detached application record and limits

The application record contains schema 1, `kind: "detached_result_intake"`,
`receipt` and `protocol_candidate`. Its receipt retains the candidate document,
explicit review assertion, target snapshots, before/after record/report counts,
whole input/candidate hashes, implementation fingerprints and its own checksum.

Replay rebuilds the entire record from the retained original protocol and recorded
candidate/review documents and compares every field. Modified candidates,
associations, reports, counts, hashes, engine map or unknown fields fail unless
someone constructs a new internally consistent record. This is not a signed or
immutable history. A consistently replaced human assertion can legitimately replay;
success proves reproducibility of supplied data, not who reviewed it or when.
Receipt IDs have no global uniqueness registry or chronological authority.

No source authenticity, document-byte match, reading, extraction correctness,
clinical applicability, scientific appraisal or census completeness is established.
An ordinary seven-file bundle retains the exported candidate, not this application
record or original input. Its later successful verification does not verify this
intake's separate document associations. Keep those files and code separately.

Limits are 10 MB for a candidate document, 50 MB for an original protocol and
50 MB for an application record. These bound resource use, not research scope or
scientific completeness. Real inputs and outputs may contain sensitive supplied
information and must stay outside this public repository. Nothing is uploaded.
The standalone tool does not change existing canonical engine files or output
shapes; previously produced artifacts still need their exact recorded engine.

A separate [result-source comparison](RESULT_SOURCE_REVIEW.md) can explicitly
replay this record and compare it with a later protocol. It reports literal
result/link/source changes without writing persistent bindings or renewing review.

For a transcription correction to an existing finding, use
[explicit result text correction](RESULT_CORRECTIONS.md) rather than assigning a
new ID and counting another result. Its narrow result/limitations changes require
a separate human review and never renew this intake's original associations.
