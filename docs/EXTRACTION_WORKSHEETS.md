# Prepare a manual extraction worksheet

`result_extraction.py` joins the supplied context for one explicitly selected
report, study and source record, then provides a deliberately unfinished candidate
for [manual result intake](MANUAL_RESULT_INTAKE.md). It helps a person start that
workflow without assembling its nested JSON schema from memory.

The command does not read documents, extract findings, choose a source, or fill
scientific fields. Only the report, study and record IDs explicitly selected by
the caller are prefilled. Existing results are shown separately, never copied
into the draft as another finding.

## Fictional example

The example is entirely synthetic. The selected study has one existing fictional
null-finding row and two report-level document declarations. One guideline context
explicitly references the selected record, and one development context links to
its existing result. Another study's context and a search-only context do not
become applicable merely because they share a report or search with the selection.

```sh
python result_extraction.py examples/extraction-worksheet-protocol.json --report-id report-one --study-id study-C --record-id record-one --text
python result_extraction.py examples/extraction-worksheet-protocol.json --report-id report-one --study-id study-C --record-id record-one --output /outside/new-extraction-worksheet.json
python result_extraction.py examples/extraction-worksheet-protocol.json --report-id report-one --study-id study-C --record-id record-one --candidate-output /outside/new-unfinished-candidates.json
```

Use new paths in an existing directory. `--output` saves the entire worksheet;
`--candidate-output` saves only its unfinished `candidate_document`. These options
are mutually exclusive, so a command creates at most one file. Stdout always shows
the whole worksheet, as JSON by default or quoted text with `--text`. Saved files
remain JSON even with `--text`.

The worksheet contains one existing pair-result, one selected-record result, and
two available document descriptors. These are separate counts. Existing result
presence does not establish that the study is exhaustively extracted, and two
descriptors do not establish that either document was obtained, read or verified.

## Explicit selection and scope

All three selectors are required, even when only one possible record or study is
declared. Exact literal strings are used without case, whitespace or similarity
matching. The report must already be retrieved and included; the selected record
must map to it, and the selected study must be explicitly declared by it. Scalar
and plural study declarations use the same membership rules. Candidate inventory
descriptions and human include positions do not substitute for membership.

The **entire protocol** is validated before filtering, including complete
report/evidence reconciliation. Invalid unrelated rows are not hidden by a narrow
selection. CSV-import provenance is validated and included through the existing
record targets. Mock `adapter_receipts` inputs are unsupported, matching manual
intake; do not remove them to bypass their provenance contract.

The worksheet includes:

- The question and criteria, selected report target and selected record target.
- The selected record's search occurrences and any mapped local CSV rows.
- All document declarations for the selected report, explicitly marked available
  rather than selected or verified.
- Existing result rows for the **entire exact report-study pair**, across all
  records mapped to that report, in their original input order.
- Explicitly linked source-record and existing-result contexts, kept separate.
- A blank candidate document, a blank source-reference shape and filling guidance.

Each existing result retains its complete raw object and input pointer, with a
`selected_record` marker. A separate `normalized_evidence_id` and
`evidence_id_origin` identify whether the established engine uses an explicit ID
or legacy record-based fallback. No missing ID is inserted into the raw row, and
the new draft's extraction ID stays null. Results from another report using the
same study label, or another study in this report, are not included in this list.
Equal study labels do not establish identity or independence.

Report targets and search contexts are complete existing context objects. They
can mention sibling studies, mapped records or search results outside the selected
pair. Only `existing_results` and its stated counts have the narrower pair scope;
the worksheet does not claim every embedded field is limited to the selected row.

## Available documents and linked contexts

`available_sources` lists the whole selected report's catalog. None is selected
automatically, associated with the new result, or preferred as the latest version.
Null digests remain unbound and nonnull digests unverified. No locator, URL or local
path is opened. Source descriptors are not evidence that a particular study or
result appears in a document.

Without any descriptors for the selected report, the worksheet still shows useful
context and the unfinished draft with `SOURCE_DESCRIPTORS_REQUIRED`. Add appropriate
supplied descriptors and regenerate the worksheet before trying to complete
intake. An absent `report_sources` field is distinguished from a supplied empty
catalog. With available descriptors the status is `DRAFT_REQUIRES_HUMAN_INPUT`,
not ready, reviewed, or approved.

`source_record_contexts` contains only source-scope contexts with an explicit typed
`record` reference to the selected record. A `planned_search` reference does not
inherit applicability through a record's search membership. A source context
remains source-scoped after results exist.

`existing_result_contexts` contains only evidence-scope contexts that explicitly
reference an existing result in the selected report-study pair. Each wrapper shows
the exact matched result IDs or source references and the full raw context,
including its other references, limitations and supplied review status. A context
can therefore include sibling or unrelated items in its full assertion without
claiming those are additional matches. Neither section extends context to the
unfinished new candidate, validates clinical applicability, or renews a review.
Missing context links are not generated from topic similarity or document content.

## Finish the candidate through explicit intake

The candidate has exactly the existing intake document shape, with one row. Only
its `report_id`, `evidence.record_id` and `evidence.study_id` are prefilled from
caller selections. All other evidence fields, including `evidence_id` and
`mechanism_basis`, are null. `extracted_by`, `extracted_at` and `extraction_note`
are null, and `source_references` is empty. The separate source-reference template
has null `source_id` and `extraction_locator` fields for a person to fill.

**The unfinished candidate is intentionally rejected by intake.** It is not a
completed extraction, a factual assertion or an approval template. No current
date, default mechanism label, new identifier, source location, observation,
limitation or reviewer is invented. A person must supply all those values and
explicitly select the source references after their own inspection. If the work
is a transcription correction to an existing finding, use
[result text correction](RESULT_CORRECTIONS.md) rather than adding a copy.

After saving a genuinely completed candidate document, use the actual current
protocol and existing intake workflow:

```sh
python result_intake.py target examples/extraction-worksheet-protocol.json /outside/completed-candidates.json --output /outside/new-intake-target.json --text
```

Then separately complete the intake's human review and use its `assemble` and
`verify` commands. The worksheet supplies no review document or acceptance hash.
Its protocol fingerprint describes the supplied snapshot, not permission to use
it after edits. Intake revalidates the current input, selected sources, identifiers
and completed candidate, then binds its own review target. A saved draft does not
carry stale approval forward.

## Reproducibility and limits

Python callers use `worksheet(protocol, report_id, study_id, record_id)`. Output
objects are detached from caller inputs. Existing canonical engines, intake,
correction and source-comparison code remain unchanged. This standalone view adds
no protocol field, provenance ledger, eligibility decision or work-state change.

Input and output bounds are 50 MB, including encoded CLI JSON/text. Strict JSON,
UTF-8, full validation and output encoding precede exclusive file creation.
Existing paths, including inputs and symlinks, are not overwritten. A later disk
error can leave a partial newly created file; writing is not an atomic filesystem
transaction. Shell redirection has its own overwrite behavior.

Supplied data is retained without redaction. Keep real research inputs, source
material and outputs private and outside this public repository. No external
service is contacted. Source authenticity, document bytes, reading, scientific or
clinical correctness, complete extraction and a complete literature census remain
unestablished or unperformed. No biological experiment or clinical action is
designed or executed by this worksheet.

## Inspect selected verbatim passages

After completing a manual candidate, use [source passage checking](RESULT_PASSAGE_CHECK.md)
to inspect explicitly mapped UTF-8 source files and compare selected byte ranges
with verbatim quotes beside the candidate fields. This separate local check neither
fills result values nor establishes that a quote supports them. Its observation is
not embedded or automatically verified by intake; retain both records and use the
ordinary independent human review before importing a result.
