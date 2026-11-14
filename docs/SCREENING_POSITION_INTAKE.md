# Explicit long-form CSV screening positions

Use this offline path for an operator-prepared UTF-8 CSV with one row per exact
record ID and reviewer label. Unlike the fixed-header [screening sheet intake](SCREENING_SHEET_INTAKE.md),
this accepts explicit column and literal label mappings and multiple reviewers of
the same record. It is not tested Rayyan, Covidence, EndNote or other product
compatibility. No product-specific parsing, fuzzy matching or external connection.

These are supplied title/abstract **positions**, not canonical `screening` decisions.
The existing [separate decision workflow](SCREENING_DECISIONS.md) is unchanged.
No vote, majority, consensus, eligibility or reviewer identity is inferred. Even
`Consensus` in a reviewer cell is only a label. Keep real/private files and generated
outputs outside this public repository. Retained text and hashes do not grant rights.

## Preserve the basis actually reviewed

Supply a template exported **before** review with `screening_review.py --template`.
Preview copies each exact record's source hash from this template, checks its internal
hash/ID consistency and records its protocol hash. It does not require the template's
old implementation hashes to match today's checkout. Target compares selected source
hashes with current source targets and rejects stale sources. It never substitutes
fresh hashes. A stale import requires regenerating the template and re-examining the
changed sources, not editing hashes merely to clear the cue.

The claim that reviewers saw the supplied template, or that it actually preceded
review, remains the operator's assertion. Unsigned templates cannot prove chronology
or authenticity. A protocol version-only change can leave the source basis equal;
the earlier template protocol hash remains recorded. Unselected template records are
retained, but current-source matching is required only for the positions imported.

## Synthetic rehearsal, first block

The checked-in CSV is entirely fictional, including two opposing readers of one
record. This rehearsal creates a fresh basis for those fictional assertions only;
it is not evidence about a real person's review timing. Choose new filenames in an
existing local directory. Every input and all existing assertions remain unchanged.

```sh
python screening_review.py examples/screening-reviews.json --template --output /outside/positions-basis.json
python screening_position_intake.py preview examples/screening-reviews.json examples/screening-positions-export.csv --basis-template /outside/positions-basis.json --record-id-column Record --decision-column Position --reviewer-column Reader --reviewed-at-column Date --rationale-column Why --source-locator-column Locator --label include=Included --label exclude=Excluded --output /outside/positions-candidates.json
python screening_position_intake.py target examples/screening-reviews.json /outside/positions-candidates.json --output /outside/positions-target.json
```

Inspect all retained raw cells and `blocked_rows` in the preview. Unmapped labels,
unknown IDs, absent template records, invalid dates, blank required fields and
existing/new duplicate IDs or record/reviewer pairs prevent target. Empty ID/locator
cells, malformed CSV or mappings fail preview outright. No incomplete row is silently
skipped and no placeholder fills missing human assertions. A repeated record ID with
a different reviewer is expected, not a duplicate record to merge.

Copy `review_document` from the target to a new `positions-review.json`, preserving
its `schema_version`, `target_sha256` and `decision: import_screening_positions`.
A human supplies nonblank `receipt_id`, `reviewer`, `reviewed_at` (YYYY-MM-DD) and
`rationale`. The import review authorizes recording only, not endorsement of the
positions. The automated rehearsal supplies fictional values between these blocks;
no completed approval is checked into the repository.

## Apply and replay, second block

```sh
python screening_position_intake.py assemble examples/screening-reviews.json /outside/positions-candidates.json /outside/positions-review.json --output /outside/positions-application.json
python screening_position_intake.py verify examples/screening-reviews.json /outside/positions-application.json --output /outside/positions-verification.json
python screening_position_intake.py verify examples/screening-reviews.json /outside/positions-application.json --protocol-output /outside/positions-protocol.json
```

Verify reconstructs the entire application from its retained original CSV bytes,
compact basis template, exact mappings and separate assertion. The old template file
is not needed. Candidate edits that disagree with that replay fail. The protocol
candidate only appends `screening_reviews`; prior assertions, canonical screening,
counts and scientific conclusions are not changed. A consistent reauthoring of all
unsigned inputs is not detectable authenticity fraud prevention.

## Literal contracts and limits

- Required distinct columns: record ID, decision, reviewer, reviewed date, rationale,
  source locator. Optional `--review-id-column` supplies exact stable IDs.
- Each repeatable `--label DECISION=LITERAL` maps one exact string to `include`,
  `exclude` or `unclear`. Duplicate canonical keys or literal labels fail. No trim,
  case conversion, timestamp conversion or escape removal. Extra CSV columns are
  retained but not interpreted. Multiline quoted cells and UTF-8 BOM are supported
  by the existing strict CSV parser; original byte spans remain in the receipt.
- Without an explicit review-ID column, IDs are `csv-row-NNNNNN@<export sha256>`.
  They label this exact export, not an identity preserved across re-exports. Reimport
  collisions fail rather than replace old assertions. Reviewer supersession is absent.
- This first CSV path does not accept hand-authored candidate JSON without retained
  CSV provenance or a separate ID-mapping file. Prepare exact sensei record IDs in the
  source CSV. Existing manual/own-sheet workflows remain available.
- 1 to 100 rows; 10MB CSV/template/import-review limit, 50MB protocol/candidate/application
  limits. Shared parser limits also apply. Processing and serialization are in memory.
- Only one output per command, exclusive creation; existing entries including final
  symlinks fail. OS write failures may leave a partial new file. Hostile ancestor/path
  races are not a sandbox or transactional filesystem guarantee.
- JSON is the only renderer. Formula-looking cell text is retained literally in JSON,
  never evaluated or automatically unescaped. This is not spreadsheet-safe re-export.

[Command reference](COMMANDS.md) · [Reviewer positions](SCREENING_REVIEWS.md)
