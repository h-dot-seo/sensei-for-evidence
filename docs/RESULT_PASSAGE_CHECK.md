# Check selected source passages beside manual result fields

`result_passage_check.py` closes the local reading-to-extraction gap: it compares
human-selected verbatim quotations with exact byte ranges in explicitly mapped
UTF-8 source files, then displays them beside the supplied extraction field values.
It does **not** generate findings, infer which passages matter or determine whether
a quotation supports a paraphrase or mechanism label.

The completed result candidates remain unchanged. Their separate human intake
review is still required. Text matching is location/transcription consistency,
not scientific acceptance, source authenticity, causal evidence or completeness.

## Fictional source-to-intake rehearsal

All fixtures below are invented software examples. The source is a small UTF-8
text file, not a real paper or an experimental procedure. Use new output paths in
an existing directory outside the public checkout:

```sh
python result_passage_check.py template examples/result-passage-protocol.json examples/result-passage-candidates.json --output OUTPUT/passage-template.json
python result_passage_check.py catalog examples/result-passage-protocol.json examples/result-passage-candidates.json examples/result-passage-manifest.json --root examples --output OUTPUT/source-catalog.json --text
python result_passage_check.py check examples/result-passage-protocol.json examples/result-passage-candidates.json examples/result-passage-manifest.json --root examples --output OUTPUT/passage-check.json --text
python result_intake.py target examples/result-passage-protocol.json examples/result-passage-candidates.json --output OUTPUT/result-target.json --text
```

The template supplies no source path, byte count, selected field, range, quote or
review decision. It lists the available candidate/source context separately so a
person can make those selections. The fictional manifest supplies explicit choices
for this rehearsal; it is not reusable evidence for another source.

For real use, first map only intended sources to a dedicated, trusted, quiescent
local directory. The catalog shows their verified UTF-8 physical lines and byte
boundaries. Choose the actual passage and candidate field yourself, then run the
check. Matching text cannot establish that the whole paper was read or that an
unselected field is absent from it. Unanchored fields remain visible as gaps in
this selected checking scope, not negative scientific findings.

Inspect both the supplied field value and its selected quote. Complete the separate
intake review only after the actual human assessment. Save the target's
`review_document` as a separate file and fill its reviewer, date, rationale,
receipt ID and `import_results` decision honestly:

```sh
python result_intake.py assemble examples/result-passage-protocol.json examples/result-passage-candidates.json OUTPUT/completed-result-review.json --output OUTPUT/result-application.json --text
python result_intake.py verify examples/result-passage-protocol.json OUTPUT/result-application.json --protocol-output OUTPUT/results-protocol.json --text
```

The `check` command exits nonzero for an unmatched or uncheckable passage while
retaining a valid observation. Catalog success concerns source bytes and readable
text, not successful passage comparisons; use `check` for the selected quotations.

The passage checker does not fill or refresh that review. Intake continues to
report its own source-byte-check scope as not performed: it does not independently
run this checker or embed its observation. Keep the source files, manifest, passage
observation, original protocol/candidates and recorded implementation together.
Do not change receipt flags or hashes merely to imply that an external check ran.

## Exact source and candidate binding

The manifest binds the exact original protocol and completed candidate document.
Each source mapping identifies an already-selected candidate source reference and
its report, current descriptor fingerprint, relative path and expected byte count.
The declaration must already contain a nonnull document SHA-256. This tool does not
create or replace that declaration or turn a supplied checksum into authentic
publication identity.

The checksum must describe the **actual UTF-8 text representation** being checked.
A PDF checksum cannot validate an independently converted text file. If text was
converted elsewhere, retain its conversion provenance and explicitly declare that
representation as a separate source through the existing source-declaration path.
This tool does not parse PDF, run OCR, repair text or normalize line endings.

Every passage identifies a candidate index, a field, an already-selected source,
zero-based inclusive `byte_start`, exclusive `byte_end` and an expected verbatim
quote. Byte offsets are not character offsets. A multibyte UTF-8 character must not
be split. BOM bytes and CR/LF/CRLF terminators count toward positions; repeated
identical wording at another location remains a different passage.

Allowed field labels cover `model`, `intervention`, `comparator`, `endpoint`,
`result`, `limitations` and `mechanism_basis`. These are human-supplied associations,
not automated evidence classifications. Even a matching quotation beside
`mechanism_basis` does not validate the chosen association/intervention/unknown
label or establish causation.

## Observations, not approval

Source byte mismatches, missing/unsafe files and changed-during-read observations
prevent passage checking against that source. Unsupported text and invalid UTF-8
boundaries remain distinct from a quote mismatch. An exact match means only that
the expected quote occurs at the selected byte range in the compared representation.
A quote mismatch should prompt inspection of the actual source and chosen offsets,
not automatic replacement of the supplied quote.

The whole protocol, completed candidate batch and every later manifest entry are
validated before any source directory is opened. A malformed later selection must
not cause earlier files to be read. No locator, URL or path from a report descriptor
is opened automatically. Only the explicit manifest-relative paths are inspected.
No protocol, result value, report membership, screening decision, work state or
scientific review is changed.

## Filesystem and privacy limits

Local source inspection requires descriptor-relative no-follow file support.
Native Windows source checks fail closed rather than falling back to an unsafe
reader; template generation remains offline. Use a supported POSIX environment
for the actual source-file rehearsal. Symlinks, hard-linked/nonregular sources,
parent traversal and protected metadata paths are refused. Existing or dangling
output paths are refused before source reads. An output-write failure may leave a
partial new file; no atomic filesystem transaction is promised.

The checker permits at most 20 sources, 1 MB per source and 5 MB total, with
200 passages and 32,768 bytes for each quote and selected span. The catalog permits
5,000 physical lines per source and 20,000 total, counted before line objects are
created. Manifest and output limits are 10 MB and 50 MB. Repeated field/text output
expansion is checked before source access; an oversized catalog fails without
silently truncating a successful view. These are bounded input/output checks, not
hard CPU or memory isolation.

Use a dedicated, trusted, quiescent source directory. Stable-read checks are not a
security boundary against a privileged concurrent filesystem attacker. Supplied
text is untrusted content, never instructions to execute. Human-readable output
quotes control/format characters so they cannot spoof labels.

The catalog explicitly exposes selected source text; the passage observation
retains selected quotes and field values. Neither is redacted. Keep real/private
sources and outputs outside public repositories and share them only with suitable
permission. No network request, data transmission, model call or expenditure occurs.

Re-run the same check with the original inputs, files and recorded implementation
to reproduce the comparison. The detached observation is unsigned and can be
reauthored; hashes do not authenticate execution, reviewers, source authorship or
scientific correctness. Ordinary research bundles do not automatically retain these
files or validate their passage associations.
