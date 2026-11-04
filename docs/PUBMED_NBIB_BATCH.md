# Multiple local NBIB files, one explicit collection review

`nbib_batch_intake.py` prepares several explicitly selected files for **one
declared search** without concatenating or replacing their native provenance.
It creates one unreviewed CSV intake for the existing human reconciliation path.
The [single-file parser contract](PUBMED_NBIB_INTAKE.md) remains unchanged. Neither
tool downloads literature, discovers files, infers pagination or authenticates
the relationship between a file and a query.

This addresses splitting a supplied citation export across local files. The
operator must decide whether the selected files belong to the same declared
search. Different queries or search occasions should remain separately declared
searches, not be silently joined under one timestamp. The grouping, labels, order
and timestamp here are supplied assertions, not verified facts.

## Prepare the entire group before collection review

The following two exports are entirely fictional. Their repeated identifier
strings are not verified publication IDs. Use a new existing output directory
outside the public checkout. `--export` is repeated in the caller's chosen order;
the part before the first `=` is an explicit source label, not a path or filename
inferred by the software. Paths may contain further `=` characters.

```sh
python nbib_batch_intake.py preview examples/bibliographic-base.json --export first=examples/pubmed-export.nbib --export second=examples/pubmed-export-additional.nbib --search-id local-primary --searched-at 2026-11-04T00:00:00Z --output /outside/new-batch.json --text
python nbib_batch_intake.py verify /outside/new-batch.json --intake-output /outside/new-intake.json --text
python bibliographic_review.py template /outside/new-intake.json --review-output /outside/new-choices.json --text
```

Five native occurrences remain five unreviewed CSV rows. Every identity or
withholding choice and rationale is intentionally blank. Repeated identifiers
within and across files are visible, but no `same_record` choice is inferred.
Identical file bytes supplied under two distinct source labels also remain two
input occurrences. Withholding a row is collection triage, not a screening
exclusion. Title similarity never creates record, report or study identity.

Inspect both native files and supply all row choices. Keep `review: null` while
preparing the separate review target:

```sh
python bibliographic_review.py target examples/bibliographic-base.json /outside/new-intake.json /outside/new-choices.json --review-output /outside/new-review.json --text
```

Supply reviewer, calendar date, rationale and `import_for_screening` only after
reviewing that exact target, then assemble:

```sh
python bibliographic_review.py assemble examples/bibliographic-base.json /outside/new-intake.json /outside/new-review.json --protocol-output /outside/new-protocol.json --text
python research_status.py /outside/new-protocol.json --text
python prisma_audit.py /outside/new-protocol.json --text
python research_bundle.py create /outside/new-protocol.json /outside/new-research.zip
python research_bundle.py verify /outside/new-research.zip
```

The result is **one incomplete search**, with unknown total and no screening,
report, study or evidence decisions. The other planned source in this example
remains missing. Successful file parsing and EOF are not complete coverage.

Preparation, review targeting and verification are distinct operations. A new
file, changed byte, changed label, reordered source or changed timestamp changes
the exact intake/review target. Do not copy an earlier review onto a changed
batch. Assemble all intended files before importing: the existing reconciler
refuses to append a second import for an already used planned search and does not
replace an existing search. No automatic rebase, late-file append or review
renewal is provided. Later independent searches use the same ledger-free common
base and their own unused plan entries, as in [CSV reconciliation](BIBLIOGRAPHIC_REVIEW.md).

## Separate original files, one derivative

The wrapper's ordered `source_exports` retains each exact caller label, zero-based
source index, original UTF-8 text, size and SHA-256, plus the complete parsed
record list and blank spans. BOMs, line endings, missing final newlines, repeated
tags and source-specific native spans remain intact. Files are never joined into
a synthetic native file. The same original file can appear twice without being
silently removed or mistaken for two verified downloads.

Each CSV row retains the original single-file NBIB columns and adds:

- `nbib_source_id`: the exact supplied source label.
- `nbib_source_index`: zero-based input order, serialized as decimal text.
- `nbib_batch_occurrence_id`: a positional label such as
  `source-000002/nbib-record-000001`, unique in this preparation only.

`nbib_occurrence_id` remains local to its individual file. Native record and field
spans are always relative to that file, while the inner intake's CSV spans are
relative to the derivative. `nbib_original_export_sha256` is each row's original
file hash. The source grouping lists all repeated literal PMID occurrences with
their file-specific references; it neither deduplicates them nor declares them
the same publication. Input order is not acquisition chronology.

The unchanged CSV review ledger, screening source snapshots, PRISMA accounting
and ordinary bundle retain all original-value columns. They do not run the native
batch verifier. **Keep `new-batch.json` with the protocol and ordinary bundle.**
It is required for complete native-file provenance, including separators, and
native-conversion replay. The existing `collection_bundle.py --nbib` accepts
single-file wrappers only; a batch wrapper cannot be substituted for one. This
increment does not add a portable batch-native collection archive.

`verify` reparses every retained native file and rebuilds the complete grouping,
CSV and intake using the recorded protocol, source order, labels, timestamp and
current implementation. It rejects inconsistent edits, extra fields, type
substitutions and implementation drift even when editable outer hashes were
resealed. A person able to change all inputs and rebuild everything can make a
different internally consistent artifact. Hash equality is not a signature,
source authentication, reviewer authentication or scientific review.

For a separate machine-readable inspection copy of the derivative:

```sh
python nbib_batch_intake.py verify /outside/new-batch.json --csv-output /outside/new-derived.csv --text
```

The derivative is lossless interchange, **not spreadsheet-safe CSV**. Exact source
labels can begin with formula-like characters or whitespace. CSV quoting does
not neutralize spreadsheet formulas. Inspect it as text/JSON or import every
column explicitly as text with formula execution disabled; do not open untrusted
derivatives directly in a spreadsheet. Labels are not silently escaped because
that would change the retained source values.

## Bounds and local output behavior

- One to 100 explicitly selected files; source labels must be nonblank, unique
  exact strings of at most 128 characters and contain no NUL or unpaired surrogate.
  Labels are not normalized or resolved as paths. The API accepts `=` within a
  label; the CLI uses the first `=` as its label/path delimiter.
- Each file must satisfy the unchanged strict NBIB grammar and be nonempty with
  at least one record. Empty files do not establish zero-hit searches.
- At most 10,000,000 combined native bytes, 100,000 combined records and 200,000
  combined physical lines. Existing individual parser limits still apply.
- The derived CSV must satisfy the unchanged CSV parser's byte, row, physical-line
  and interpreter field-size limits. Native inputs within their bounds can still
  exceed the derivative limits because retained fields and escaping expand them.
- Serialized artifacts and rendered CLI output are limited to 50,000,000 bytes.
  All validation and output serialization finish before an output path is opened.

`--intake-output` and `--csv-output` are mutually exclusive. Output creation rejects
observed existing final directory entries, including dangling symlinks, and uses
exclusive open. This is not atomic protection against concurrent path replacement
or parent-directory aliases. A write failure may leave a partial new file. Without
an output flag, the commands are read-only; stdout defaults to JSON and `--text`
quotes supplied labels and other values. Shell redirection has its own behavior.

Native files may contain abstracts, affiliations or other private/copyrighted text.
No redaction or rights determination is performed. Keep real input/output outside
this public repository and inspect redistribution rights before sharing. This
workflow performs no full-text retrieval, scientific extraction, clinical advice
or experimental execution.
