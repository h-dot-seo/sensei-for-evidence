# Scoped CLI error presentation

The remaining twelve ordinary first-stage review/intake views in roadmap #51 now
report a static tool prefix, category and argument label on stderr. This is not a
repository-wide error conversion or a change to scientific or mechanical gates.

Adopted scripts: appraisal_source_review, prisma_audit, readiness_review,
receipt_intake, report_review, report_study_inventory, report_study_inventory_review,
report_study_review, screening_review, search_manifest, synthesis_review and work_review
(all `.py`). Existing source readers, PubMed tools, engine CLI entry points and the
four previously hardened status/comparison/handoff/state views are not converted.

## Channels and categories

- Success remains exit0 with the existing JSON/text report.
- `receipt_intake.py check` retains a structurally valid negative report on stdout,
  empty stderr and exit1. A missing/invalid file is a different error channel.
- Caught errors remain exit1, empty stdout and one stderr line:
  `<tool> error: <category>: <static argument label>: "<quoted detail>"`.
- Usage remains argparse exit2. No exit3/4 or JSON-error mode is introduced.

Categories: `input-unreadable` for caught filesystem input errors;
`input-not-json` for JSON decoding or Unicode errors; `input-too-complex` for the
existing shared nesting exception; `input-invalid` for other caught input/validation
errors; `output-exists` for an existing destination and `output-error` for other
caught output/rendering errors. These tokens describe the observed stage, not an
authorization or machine-action recommendation. An unexpected error outside the
existing catch set is not newly swallowed.

Labels are code constants, never the supplied path/ID/value. Appraisal comparison
labels each of its three reads separately; receipt checking distinguishes protocol
and fixture reads. Combined validation labels describe the participating inputs,
not a diagnosis of which supplied assertion is scientifically wrong. Filesystem
exception text, arbitrary missing-key text and Unicode exception bytes are replaced
with fixed details. Other pre-existing validation detail is quoted and retained:
this is **not** a complete privacy redactor. Existing reports, usage errors and
validator details may contain supplied information. Do not publish private inputs,
paths, diagnostics or reports merely because these categories are present.

## Implementation and replay boundaries

`cli_errors.py` is a non-engine presentation leaf. It does not open files, read,
parse JSON, set byte limits or validate research. Read/parse/validation calls retain
their ordering and count in the adopted entry points. Existing rendering placement,
input limits, strict JSON, validators, gates and global ENGINE filenames are unchanged.
The twelve direct maps and nine manually composed downstream maps include the new
helper explicitly. The latter are views_export, protocol_scaffold, patent_links,
report_review_intake, report_study_review_intake, report_study_inventory_review_intake,
screening_sheet_intake, screening_position_intake and screening_decision_batch.
review_handoff, accounting_flow and records_csv inherit its digest from already
merged result maps; their product bytes are unchanged. No global ENGINE insertion
is used to avoid this transitive bookkeeping.

**Compatibility change:** parsers of former raw/quoted stderr strings must now
recognize the new prefix/category/label. Normal and negative reports retain their
meaning; implementation maps change. Exact prior/current subprocess comparisons
permit only named implementation digest fields and the added helper key; appraisal
text embeds that exact map as one display line. Derived receipts/targets which bind
these implementations can consequently change even though their gates do not.
Old pending reviews or retained replay artifacts may require their original code;
there is no automatic rebase/reseal or claim that current code can replay all old
artifacts. Only the fixed fictional examples are maintained after actual guide replay.

## Verification scope

Synthetic tests cover all twelve tools' missing-file/JSON/UTF-8/shape errors, usage,
all appraisal read positions, receipt fixture labels and negative reports, exclusive
output refusal, prior/current normal JSON/text and file bytes, real subprocess versus
in-process channels, read/parse call order, exact source inventories and transitive
helper fingerprints. Historical baseline JSON is preserved. Earlier newline/error
position fixtures execute their preserved previous entry point because current stderr
presentation intentionally differs; current presentation has separate tests. Source
reversal is an exact recorded test fixture, not a public implementation loader.

This does not establish external integration compatibility, scientific sufficiency,
reviewer authenticity, total CPU/memory safety, or confidentiality of every diagnostic.
