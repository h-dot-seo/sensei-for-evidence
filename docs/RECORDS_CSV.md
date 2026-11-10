# Detached supplied-record CSV

`views_export.py records` flattens the existing `prisma_audit.export_audit()`
record, occurrence, report and evidence ledgers. One row represents one exact
supplied record ID, never a verified publication or independent study. No join,
screening decision or review position is adjudicated. This is a detached artifact;
the research bundle's seven-file entry set and all engine bytes remain unchanged.

## Synthetic rehearsal

Run from the repository root. Replace `OUTPUT` with an existing directory outside
the public checkout; both filenames must be new. This fixture is entirely fictional.

```sh
python views_export.py records examples/prisma-audit.json --output OUTPUT/records.csv
python views_export.py records examples/prisma-audit.json --output OUTPUT/records-text.csv --text
```

Both CSV files are byte-identical. JSON is the default stdout receipt; `--text`
changes only that receipt to quoted text. It records output bytes/SHA-256, canonical
protocol SHA-256, implementation hashes, columns, row count, stage availability and
the full accounting boundary. Keep the receipt with the CSV. The CSV contains only
header/data rows, no boundary comment or synthetic data row. Census remains
`NOT_ESTABLISHED`; conclusion readiness remains `NOT_READY`. Hashes authenticate
neither sources nor reviewer identity.

## Columns and missing values

- `record_id`, `retained_occurrence_id`, `occurrence_ids`: existing exact-ID
  accounting, preserving the first supplied occurrence and all occurrence pointers.
- `search_indices`: authoritative zero-based input indices, aligned one-for-one
  with `occurrence_ids`. Repeated indices are preserved for repeated occurrences.
  `search_ids` is the aligned display-only list, retaining absent labels as JSON
  `null` and duplicated labels. Never use it as the authoritative join key.
- `screening_decision`, `screening_reason`, `screening_input_pointer`: existing
  recorded decision/reason/pointer. No screening row means `pending` and two blank
  cells; pending is a bookkeeping label, not a supplied decision.
- `report_stage`: `NOT_SUPPLIED` versus `SUPPLIED`, even for an empty report stage.
  `report_id`, `report_retrieval`, `report_decision` refer only to the mapped report;
  no mapping leaves these cells blank. An omitted mapped report decision is pending,
  as in the audit. `report_study_ids` uses the existing `report_study_ids` helper;
  only an included report supplies these memberships. No mapped report gives `[]`.
- `result_ids` and `result_study_ids`: aligned lists from existing evidence links,
  ordered by the audit's result IDs. Repeated study IDs are retained. They are
  deliberately separate from report memberships; no results gives `[]`.
- `screening_review_stage`: `NOT_SUPPLIED` versus `SUPPLIED`. Only a supplied
  review stage adds `screening_review_cues`, copied from the existing per-record
  comparison cues. An explicitly empty review stage can still carry the engine's
  `NO_CURRENT_SOURCE_REVIEW` cue; cues are not adjudications or new decisions.
- `bibliographic_row_pointers` appears only when bibliographic collection data was
  supplied, copied directly from the audit. An available empty list remains `[]`.

Lists use JSON inside CSV cells, not delimiter-separated guesses. Every header and
cell string passes through `csv_safety.safe_csv_cell`: leading formula characters
or whitespace gain an apostrophe, preserving the rest. All cells are quoted so
commas, quotes, CR and LF in supplied scalars round-trip. JSON list contents escape
controls; a scalar NUL is rejected consistently across supported Python runtimes.
This is conservative spreadsheet protection, not a guarantee about every importer;
do not remove the apostrophe automatically or execute supplied text.

## Bounds, output and privacy

The input, complete UTF-8 CSV and complete stdout receipt are each bounded to
16 MiB before any output file is created. Strict JSON rejects duplicate keys,
nonfinite values, invalid UTF-8 and lone surrogates. Key order does not affect
bytes; supplied list order remains meaningful. CSV serialization errors fail
closed with no output. Output encoding is UTF-8 without BOM and record terminators
are LF (embedded supplied CR/LF are preserved inside quoted cells).

The parent directory must exist. `lstat` plus exclusive binary creation refuses
existing files, directories and dangling links. A failed new CSV write is removed
on stable paths; if OS cleanup itself fails, an incomplete new file can remain
and no success receipt is printed. This is not atomic publication or protection
against concurrent path/ancestor replacement. Status/flow retain their existing
writer behavior. No output overwrites the protocol or an existing artifact.

Files and receipts are unredacted and may expose private research. Keep real
outputs outside the public repository and share only with authorization. No model,
network request, clock read, source retrieval, identity authentication, scientific
judgement or PRISMA-standard interchange compatibility is provided.
