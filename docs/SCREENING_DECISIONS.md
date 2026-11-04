# Explicit supplied screening decisions and retained receipts

Separate reviewer positions do not choose the canonical screening outcome. This
workflow records a **human-supplied** include/exclude choice, applies that exact
choice to a new protocol candidate and retains the supplied context of the change.
It performs no majority vote, eligibility assessment, medical fact check, source
reading or authentication of the person named in the decision.

All checked-in material is fictional. Keep actual private protocols, source data
and generated files outside this public repository. Source locators are inert
text and are never opened or executed.

## Reproduce the fictional application

```sh
python screening_decision.py target examples/screening-reviews.json --record-id=record-alpha --output /outside/new-decision-target.json --text
python screening_decision.py assemble examples/screening-reviews.json examples/screening-decision-document.json --protocol-output /outside/new-decided-protocol.json --text
python screening_decision.py inspect /outside/new-decided-protocol.json --text
python compare_runs.py examples/screening-reviews.json /outside/new-decided-protocol.json --text
python prisma_audit.py /outside/new-decided-protocol.json --text
python research_bundle.py create /outside/new-decided-protocol.json /outside/new-decided-bundle.zip
python research_bundle.py verify /outside/new-decided-bundle.zip
```

Use new paths in an existing output directory. The first command writes a target
report containing a blank `decision_document`. The second uses a separately
authored fictional completed document; it does not fill or approve that template.
Its exact hash is tied to the bundled input, not reusable with real material.
`--output` saves the target report. `--protocol-output` saves only the candidate
protocol. Both refuse overwrite; `--text` affects stdout, not saved JSON.

Alpha becomes canonically included only because the supplied document explicitly
chooses inclusion. The opposing reviewer positions remain unchanged and visible.
No source authenticity, independent adjudication or scientific correctness has
been established.

To inspect an already assembled two-step fictional history:

```sh
python screening_decision.py inspect examples/screening-decisions.json --record-id=record-alpha --text
python research_status.py examples/screening-decisions.json --text
python review_handoff.py examples/screening-decisions.json --text
```

That fixture records an initial inclusion followed by an explicit exclusion. The
second supplied calendar date is deliberately earlier: dates do not order or
select decisions. The explicit receipt chain records application order. The first
result row differs from current screening; this is an expected retrospective
comparison, not a finding that the earlier decision was invalid or unfinished.

## Human input and concurrency

`target` fills only the exact record ID, schema version and target hash. Every
human field remains null until supplied:

- `receipt_id`: a unique literal ID for this recorded application.
- `decision`: `include` or `exclude`; no default or inferred winner.
- `reason`: the exact reason to store in canonical screening.
- `adjudicator`, `decided_at`, `rationale`, `source_locator`: supplied identity
  label, valid `YYYY-MM-DD`, explanation of the choice and inert note/source locator.

The document has exactly these fields plus `schema_version: 1`, `record_id` and
`target_sha256`. Strings must be nonblank and hashes lowercase SHA-256 hex. The
target report is not itself a completed document or protocol. After an actual
human decision, save just its completed `decision_document` object separately
and provide that object to `assemble`.

The target binds the **entire current protocol hash**, prior canonical row or
null, current record source/criteria target, referenced source contexts, all
supplied reviewer positions for that record, and the explicit preceding receipt.
Any intervening protocol change, even unrelated work/version edits, requires a
fresh target and an honestly supplied decision document. There is no automatic
rebase, hash renewal or reuse of an old decision with new input.
Canonical JSON ignores object-key order and file whitespace, but retains list
order and JSON value types; this is not an original-file byte hash.

Stale or unclear reviewer positions remain in the snapshot. A supplied decision
can disagree with every position; no reviewer threshold, independence or consensus
is inferred. Assembly never changes reviewer hashes, labels or assertions.

## Exactly what assembly changes

Before and after construction, the entire protocol and optional report ledger
are validated. A new decision is appended to `screening` if the record was
unscreened. Otherwise only that row's decision and reason are replaced; row order,
record ID and other metadata remain intact. One receipt is appended and any new
source-catalog bodies are retained. There is no automatic version change.

All reports, evidence, work, contexts, import receipts and other existing fields
remain unchanged. Excluding a record that still has a linked report or extracted
result fails, including the legacy scalar-report path. The tool does not delete
those rows, fabricate replacement data or bypass their linkage rules. These are
structural checks, not judgments about a paper's contents.

Structural failure or an existing output destination produces no successful
candidate report or partial structurally invalid protocol file. Existing files
and input objects remain unchanged. If saving fails, the command reports the
failure rather than claiming delivery.

## Retained history and its limits

The optional `screening_decision_history` contains `schema_version`, a shared
source-context catalog and ordered receipts. Each exact canonical search body is
stored once by its digest, while receipt references retain the original search
indices and occurrence pointers. The catalog is content addressing, not publication
identity deduplication. Repeated decisions do not recursively embed previous
protocols or entire import/decision histories.

Receipts retain the human document, previous canonical row, resulting canonical
row, source/criteria target and raw reviewer snapshots. Explicit indices and
previous-receipt hashes must form one consistent chain. Duplicate receipt IDs,
missing links, inconsistent hashes, invalid source memberships and unused or
duplicate catalog bodies fail validation. The history is bounded to 1,000 receipts
and 50 MB of canonical JSON. Retained fragments cannot embed whole protocol histories.

Hashes prove internal consistency of supplied snapshots, not authorship,
chronology, immutable append-only storage or proof of execution. Complete historical
protocols are intentionally not retained: `historical_protocol_reconstruction`
remains `NOT_PERFORMED`. The whole-input hash is enforced when assembling a new
candidate, but its historical contents cannot be independently reconstructed from
these receipts alone. Keep the original protocol/bundle snapshots for that purpose.

Mapped bibliographic rows are retained source fragments, not reverified original
CSV exports. Source authenticity, actual full-text bytes, the completeness of
historical context and medical/scientific correctness remain unestablished. Use
the recorded implementation revision when verifying older engine-bound artifacts.

## Inspect changes without selecting an authoritative receipt

Every receipt is compared separately with current supplied inputs:

- `current_source_match_status` and nullable `current_source_basis_sha256`
  distinguish matching context, changed context and a record no longer enumerated.
- `review_snapshot_match_status` compares the retained raw reviewer assertions
  with the current assertions, not whether any judgment was valid.
- `matches_current_screening` compares the entire resulting row, including its
  reason and metadata, with the current canonical row. Matching just a verdict
  is insufficient, and multiple matching receipts do not establish authority.
- `prior_row_matches_preceding_record_result` exposes an intervening unrecorded
  canonical edit. It does not assume that this ledger captures every change.

Removed records can still be inspected through retained receipts. No receipt is
inferred active by date, list position or agreement. The operational decision is
always the separate canonical `screening` row.

## Other views and compatibility

PRISMA audit, report output and synthesis snapshots retain the optional history.
Status and handoff show it as **retrospective information outside pending queues**;
older mismatches are not automatically new tasks. Existing reviewer-position
cues remain visible even after an explicit decision. Handoff includes the detailed
history inspection command without executing it.

Run comparison adds `screening_decision_changes` only on opt-in: raw receipt and
catalog changes, record-history changes, and before/after current-context labels.
Unchanged retained receipts remain visible when current sources or canonical
reasons change. There is no automated scientific interpretation of those changes.

Omitting the history preserves legacy shapes and CSV bytes. An explicit empty
history object is distinct from absence; null is invalid. The new top-level key
is reserved and permitted as CSV-import enrichment. Later CSV imports can retain
prior decision history without placing recursive histories inside new receipts.
Seven-file bundles include the receipt data and fingerprint both the validator
and operational decision API. History metadata alone does not renew or stale
existing review/work/synthesis bases; an actual canonical screening edit has its
normal downstream source-binding effects.

Full-text review, per-study eligibility, reviewer-assertion supersession and
independent factual adjudication remain separate, unimplemented tasks.
