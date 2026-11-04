# Append reviewed descriptive study inventory without editing the protocol by hand

`inventory_intake.py` connects completed human descriptions to the existing
[report-study inventory](REPORT_STUDY_INVENTORY.md). It replaces the manual copy
step with a separate exact-input review and replayable application. It does not
read a report, discover its studies, write descriptions or decide inclusion.

The selected report must already be retrieved and have supplied document-source
descriptors. It may be pending, included or excluded at full text. Do not mark it
included just to describe a candidate. Title/abstract-included record mappings
remain required by the unchanged report model.

## Fictional workflow

The starting example contains five descriptions of four candidate report-study
pairs, including one stale description. The new fixture adds one explicitly
supplied description of `candidate-new` on the retrieved, still-pending
`report-three`. No actual publication, scientific fact or experimental procedure
is included. Use new paths in an existing directory outside this public repository.

```sh
python inventory_intake.py template examples/report-study-inventory.json --report-id=report-three --study-id=candidate-new --candidate-output /outside/new-inventory-draft.json --text
python inventory_intake.py target examples/report-study-inventory.json examples/manual-inventory-candidates.json --output /outside/new-inventory-target.json --text
```

The first command saves an **unfinished candidate document**, not a protocol.
Only the caller's exact report/study IDs and current source-context hash are filled.
The assertion ID, recorder, date, description, locator and selected source IDs are
null. There is no inferred source selection, empty-source assertion or invented
person. This blank draft is deliberately rejected by `target`.

For real use, complete that draft after actual source inspection and pass your
completed file to `target`. The second example command instead uses a separately
authored, completed fictional fixture. Neither command performs a human review.
Save the target output's `review_document` as a separate review file and fill its
null human fields honestly: `receipt_id`, `reviewer`, `reviewed_at`, `rationale`,
and `decision: "import_descriptive_inventory"`. Retain the exact target reviewed.
Do not change a source basis or review hash merely to clear a stale-context error.

```sh
python inventory_intake.py assemble examples/report-study-inventory.json examples/manual-inventory-candidates.json /outside/completed-inventory-review.json --output /outside/new-inventory-application.json --text
python inventory_intake.py verify examples/report-study-inventory.json /outside/new-inventory-application.json --protocol-output /outside/new-inventory-protocol.json --text
python report_study_inventory.py /outside/new-inventory-protocol.json --report-id=report-three --study-id=candidate-new --text
python prisma_audit.py /outside/new-inventory-protocol.json --text
python compare_runs.py examples/report-study-inventory.json /outside/new-inventory-protocol.json --text
python research_bundle.py create /outside/new-inventory-protocol.json /outside/new-inventory-research.zip
python research_bundle.py verify /outside/new-inventory-research.zip
```

Replace `/outside` with your directory and quote paths containing spaces.
`assemble` saves the detached application. Only `verify --protocol-output` exports
its candidate after replay against the actual original input. Each inventory-intake
command creates at most one new file; its saved outputs remain JSON even with
`--text`. The separate research-bundle commands create and verify a ZIP.

The fixture moves inventory assertions from five to six and described pairs from
four to five. The original stale description stays stale. Five report rows, three
included study labels, two result rows and all search/record/report counts remain
unchanged. The new label is **not** included membership, a newly counted independent
study, an eligibility position, an extraction result or completed source coverage.

## Explicit completed candidates

The candidate document has exactly integer `schema_version: 1` and `candidates`,
a nonempty ordered list of at most 100 new assertion rows using the existing
inventory schema. Each row has exactly:

- `inventory_id`: a new explicit assertion ID.
- `report_id`, `study_id`: the selected report and a human-supplied candidate label.
- `recorded_by`, `recorded_at`: supplied recorder text and real `YYYY-MM-DD` date.
- `description`, `source_locator`: supplied descriptive text and scope/location.
- `source_ids`: a nonempty list of unique exact same-report descriptor IDs.
- `source_basis_sha256`: the exact current inventory source-context hash.

All scalar text is nonblank and preserved literally. Hashes are 64 lowercase
hexadecimal characters. No identity normalization, trimming, date winner or preferred
wording is applied. The existing inventory validator rejects duplicate assertion
IDs or exact `(report_id, study_id, recorded_by)` tuples across both old and new
rows. Different recorders may describe the same pair, and all descriptions remain.
This command does not update, replace or renew an old recorder's assertion.

Every new row must refer to a retrieved report and existing same-report sources,
even though the underlying inventory model can retain stale historical rows with
unresolved sources. New stale hashes are rejected, never refreshed. The target
calculation includes validated mapped CSV provenance when present. Source hashes
bind supplied criteria, report/record/search context and document declarations,
not actual source bytes, reading or correct descriptions. Null document digests
remain unbound; nonnull digests remain unverified assertions.

The template, candidate descriptions and import review do not select report-study
membership. Inclusion still needs a separate [full-text decision](REPORT_DECISIONS.md),
with explicit study declarations and its own review. Candidate eligibility positions
remain a separate [inventory review scope](INVENTORY_CANDIDATE_REVIEWS.md).
Result extraction remains a separate [manual intake](MANUAL_RESULT_INTAKE.md).

## Exact review, append and replay

`target` validates the entire original protocol, all completed candidate rows and
the full hypothetical append. Its target binds the canonical whole-input hash,
ordered candidates, current candidate/report/record source targets, explicitly
selected document descriptors, and implementation fingerprints. Only schema and
target hash are prefilled in the blank review document. The decision is only
permission to append supplied descriptions, not scientific acceptance.

Changes anywhere in the original protocol, including unrelated version or work
metadata, invalidate the old import-review target. Candidate content, order, source
selection and implementation changes also require a fresh explicit review. Canonical
JSON ignores object-key order and formatting, not values, number types or list order.
There is no automatic rebase or reuse of an earlier assertion as approval.

Assembly appends the exact completed rows in order to `report_study_inventory`.
Absent inventory becomes a supplied ledger; an existing empty ledger stays explicitly
supplied. All old rows and all other raw protocol fields are preserved exactly,
including opaque metadata, version, search/CSV provenance, eligibility, report-study
memberships, evidence, sources, contexts and work. Whole-input and candidate
validation also checks unchanged record/report accounting. Mock `adapter_receipts`
inputs are unsupported and must not be stripped to bypass their immutable contract.

The application has exactly `schema_version: 1`, `kind: "detached_inventory_intake"`,
`receipt`, and `protocol_candidate`. The receipt retains the candidates, review,
source snapshots, before/after inventory and research counts, input/candidate
hashes and implementation map. Verification reconstructs and compares the entire
record; changing a field and resealing its checksum is insufficient. A consistently
reauthored set of inputs may replay, however: this is not signed history, reviewer
identity verification, a global receipt registry or authenticated chronology.

## Earlier assertions and retention limits

Existing raw inventory and eligibility-review assertions remain unchanged. Adding
another description of the **same** pair changes its inventory-review basis and
can make prior candidate eligibility positions stale. No consensus, review winner,
new eligibility choice or automatic renewal is generated. Report inclusion and
result counts do not change. Other downstream assertions are neither rewritten nor
universally reassessed; not all have source bindings.

Inventory rows and their source hashes persist in the candidate protocol. The
import-review assertion and selected-source snapshots remain in this **detached**
application. Ordinary research bundles preserve the candidate, not its original
input/application, and do not independently replay this import. Existing report-
transition archives do not accept inventory intake applications. Keep the original,
application and matching repository revision separately; no receipt migration or
full-history archive is added here.

Python callers use `template(protocol, report_id, study_id)`, `prepare(protocol,
candidate_document)`, `assemble(protocol, candidate_document, review_document)`
and `verify(original_protocol, application_record)`. Caller objects are not changed.
The existing inventory inspection/template command remains available and unchanged.

Candidates/reviews are bounded by 10 MB; original/candidate protocols, application
records and encoded outputs by 50 MB. Strict JSON and UTF-8 are required. These
are size bounds, not guaranteed memory/CPU ceilings. Validation and output encoding
precede exclusive file creation. Existing final entries, including observed
dangling symlinks, are refused; path inspection failures are not bypassed. Concurrent
ancestor/path replacement is outside this guard. A write failure may leave a partial
new file. Shell redirection has its own overwrite risks.

No locator is opened, downloaded or executed. Supplied source/private text remains
unredacted. No biological experiment, scientific inference, source authentication,
verified identity, PRISMA compliance or complete census is established. Inventory
and extraction completeness remain `NOT_ESTABLISHED`; conclusions remain `NOT_READY`.
