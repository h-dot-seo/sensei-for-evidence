# Blank screening-position sheets

`screening_sheet.py export` is a spreadsheet-facing transcription scaffold built
on the existing `screening_review.template`. It does not perform screening,
import edited cells, adjudicate positions or write canonical decisions. Reviewed append-only edited-sheet intake is now available through the separate
[positions intake wrapper](SCREENING_SHEET_INTAKE.md). Existing [JSON review workflow](SCREENING_REVIEWS.md) remains
available and unchanged. Reviewer supersession is not implemented.

## Synthetic walkthrough

Run from the repository root. Replace `OUTPUT` with an existing empty directory
outside this checkout. The fixture is fictional, contains prior assertions and
has no retained title/abstract text. Even those prior assertion cells are not
copied into this new sheet. Missing requested display columns remain blank.

```sh
python screening_sheet.py export examples/screening-reviews.json --display-column title --output OUTPUT/screening.csv --text
```

Stop here to inspect the new blank sheet. This command did not screen any record
or import any assertion. JSON stdout (omit `--text`) describes the exact file SHA,
bytes, export-protocol SHA, row count, display mapping and negative claims. The
CSV is written directly as UTF-8/LF; avoid shell redirection, especially Windows
PowerShell 5. Existing files, directories and dangling final symlinks are refused.
A missing parent fails. Write failures can leave a partial new file; this is not
atomic publication or a guarantee against ancestor-path alias races.

## Column contract

- `record_id`: spreadsheet-escaped display of the original ID. Leading `=`, `+`,
  `-`, `@` or whitespace gains an apostrophe using `csv_safety.safe_csv_cell`.
- `source_basis_sha256`: unchanged existing per-record source hash, unique by
  source basis including record ID. Use this key, not the escaped display ID.
- `readonly_record_id_json`: exact literal ID encoded as a JSON string. A literal
  apostrophe ID and an escaped formula-like ID can look the same in `record_id`;
  the source hash and this exact value keep them distinct. Do not strip apostrophes
  heuristically. The separate intake compares the exported escaped form exactly.
- `readonly_export_protocol_sha256`: hash of supplied export-time protocol JSON,
  not authentication, currentness or approval.
- `readonly_retained_locators_json`: ordered literal values and source pointers
  from promoted bibliographic rows, or blank for manual records. URLs/attachments
  are inert and never opened.
- `readonly_display:NAME`: one column per explicit repeated `--display-column NAME`.
  Each cell is an ordered JSON list of original column values and source pointers.
  Repeated occurrences remain separate. These are literal, possibly incomplete
  selections, not inferred titles/abstracts or parsed RIS/NBIB/EFetch tags. Case
  and spelling must match exactly; absent selected values produce blank cells.
  Nothing is guessed as a fallback. JSON wrappers and CSV safety escaping keep
  formula-like supplied values as display text; spreadsheet settings still matter.
- `review_id`, `reviewer`, `reviewed_at`, `decision`, `rationale`, `source_locator`:
  all blank human assertion columns. In particular the human `source_locator` is
  never prefilled from retained locators. No prior identity, date or decision is
  recycled.

All supplied protocol state is validated before export. Rows follow the existing
template's record ordering; no record is selected by eligibility or review state.
No import target, receipt chain or archive payload is introduced by this view.
The export accepts at most 10,000 records, 16 unique display columns (128 characters
each, no controls), 50 MB input and 10 MB output. This is a bounded convenience,
not a claim of high-volume decision processing. The normal protocol validators
and their limits still apply. A zero-record protocol yields a header-only CSV.

## Stale context and future human work

Keep the original protocol and source material with the sheet outside this public
repository. Regenerating a sheet describes current supplied context; it never
refreshes old review assertions or establishes that a person read it. Changes to
source context can change `source_basis_sha256`. Never refill or replace old
hashes to make an old sheet appear current; inspect the changed material and make
a fresh human assertion. An unchanged source hash alone does not assert whole
protocol equality, since unrelated protocol state may differ.

Human dates must remain `YYYY-MM-DD`; prevent spreadsheet locale reformatting.
Human positions use the existing literal `include`, `exclude`, `unclear` values,
not a vendor label mapping. Do not treat a completed CSV as an accepted import or
an approved decision. It remains private working material until separately
reviewed intake succeeds. Real sheets may contain unredacted abstracts and must not
be committed here. No source reading, reviewer identity/independence, adjudication,
search completion or scientific validity is established by exporting this sheet.
