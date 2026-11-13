# Blank human-decision sheets

`screening_decision_sheet.py export` creates a bounded CSV scaffold for explicitly
human-authored future decisions. It does not screen, select a winner, infer a vote,
create a receipt or modify canonical screening. This is **export only**; edited
batch decision target/assemble/verify intake is not implemented yet. The existing
[single-record decisions](SCREENING_DECISIONS.md) remain available and unchanged.

This sheet is distinct from [reviewer-position sheets](SCREENING_SHEETS.md) and
[positions intake](SCREENING_SHEET_INTAKE.md). Do not pass a decision sheet to the
positions intake, which rejects its different headers. Do not turn reviewer
positions, even unanimous ones, into a decision automatically.

## Synthetic walkthrough

From the repository root, replace `OUTPUT` with an existing empty directory
outside this checkout. This fictional fixture includes prior assertions; none
are copied into human decision cells. Stop after export and inspect the scaffold.

```sh
python screening_decision_sheet.py export examples/screening-reviews.json --display-column title --output OUTPUT/decisions.csv --text
```

Omit `--text` for a detached JSON export report with file bytes/hash, protocol hash,
selection scope and negative claims. No review approval or decision application is
created. Outputs are UTF-8/LF and exclusively created: existing files, directories
and dangling final symlinks are refused. Missing parents fail; write failures may
leave a partial new file. This is not atomic publication or an ancestor-alias/race
security boundary. No shell redirection is needed on Windows PowerShell.

## Selection and column contract

By default all enumerated records are exported, capped at 100. Repeat
`--record-id ID` to select an explicit subset in the exact requested order; unknown,
blank and duplicate IDs fail. No eligibility, prior screening or review state
selects records implicitly. IDs are literal, including leading whitespace or
formula-like characters. For a CLI value starting with `-`, use `--record-id=-id`.
A valid empty protocol produces a header-only scaffold, not a completion claim.
The entire protocol, including unselected assertions, is validated.

The existing source-sheet export supplies source targets and literal retained
`--display-column NAME` values without guessing titles/abstracts. The base columns
are unchanged: escaped `record_id`, exact `readonly_record_id_json`,
`source_basis_sha256`, `readonly_export_protocol_sha256` and read-only retained
locators/display values. Source hashes plus literal JSON IDs distinguish an
escaped formula ID from an actual apostrophe-prefixed ID with the same display.

Additional read-only columns:
- `readonly_prior_screening_json`: the exact current canonical row or JSON `null`.
- `readonly_review_context_json`: supplied review stage, full per-record assertion
  ledger (including stale status) and existing comparison cues. Conflicts remain
  visible. These are supplied snapshots, not verified identity, reading or evidence.
- `readonly_export_review_context_sha256`: hash of that exact JSON context.

Human columns `receipt_id`, `decision`, `reason`, `adjudicator`, `decided_at`,
`rationale`, `source_locator` are **all empty**, even if prior screening and reviews
exist. Dates in future human assertions must remain `YYYY-MM-DD`, and canonical
choices are `include`/`exclude`, not the reviewer-position value `unclear`. This
export neither validates edited human cells nor supplies any such choice.

## Binding and limits

Preserve the original protocol with the sheet. Export-time hashes bind supplied
context only, not currentness, authenticity or approval. Any protocol/reviewer
change requires fresh context and fresh human review; never refill old hashes.
These hashes are **not sequential per-record target hashes**. Future batch intake
must bind the human-reviewed exact sheet in a separate import review, then compute
ordinary chained targets internally and replay against the unchanged original.
No canonical receipt schema is changed here. Retain positions before preparing a
future decisions batch; appended positions change its review context.

This is a convenience for tens to at most 100 records, not high-volume processing.
The existing engine's 1,000-receipt lifetime limit remains unchanged; export does
not reserve receipt capacity or promise a later import will fit. This wrapper
accepts a 50 MB protocol, 10 MB CSV and at most 16 retained display columns. Its
reused source exporter additionally limits the whole source catalog to 10,000 rows
and 10 MB before selection; the strict parser's existing field/physical-line limits
also apply. All locators and retained text are inert and never opened. Keep real
sheets, abstracts and source material outside this public repository. No source
reading, reviewer authenticity, adjudication or conclusion readiness is established.
