# Explicit full-text decisions with detached replay records

Human reviewer positions and candidate descriptions do not choose a canonical
full-text outcome. `report_decision.py` applies an explicitly supplied human
include/exclude choice to a separate protocol candidate and records the exact
inputs. A second command replays the operation before exporting that candidate.

This is structural research bookkeeping. It does not read a paper, authenticate a
person, vote among reviewers, assess scientific or clinical validity, verify
source bytes, or create biological experiment instructions. All examples are
fictional; keep real/private inputs and generated records outside this repository.

## Fictional end-to-end application

```sh
python report_decision.py target examples/report-study-inventory.json --report-id=report-three --output /outside/new-report-target.json --text
python report_decision.py assemble examples/report-study-inventory.json examples/report-decision-document.json --output /outside/new-report-application.json --text
python report_decision.py verify examples/report-study-inventory.json /outside/new-report-application.json --protocol-output /outside/new-decided-protocol.json --text
python compare_runs.py examples/report-study-inventory.json /outside/new-decided-protocol.json --text
python prisma_audit.py /outside/new-decided-protocol.json --text
python research_bundle.py create /outside/new-decided-protocol.json /outside/new-decided-bundle.zip
python research_bundle.py verify /outside/new-decided-bundle.zip
```

Use new output paths in an existing directory. The first command saves a target
and blank `decision_document`. The second uses a separately authored, completed
fictional document, not the unfilled template. `assemble --output` saves an
**application record**, not a protocol. Only `verify --protocol-output` exports
the candidate after exact replay succeeds. Keep the original input protocol.

The fictional choice includes report three and explicitly declares candidate X
as its report membership. It changes the included-report count from one to two
and distinct supplied included-study labels from three to four. Five inventory
assertions, their original source bindings, and the two existing result rows stay
unchanged. Candidate X is not selected because a description exists or reviewers
agree: the completed human document expressly names it. This operation does not
establish candidate X's independent identity, per-study eligibility or extraction
completeness.

`--text` affects stdout only; saved output remains JSON. Each command writes at
most one new file and refuses overwrite, including its input. Encoding and
structural checks occur before opening an output. A disk-full/write failure can
still leave a newly created partial file; this is not an atomic filesystem commit.
Invalid replay never creates a protocol output. Original objects/files are not
edited by these commands.

## Human decision document

The exact document fields are:

```json
{
  "schema_version": 1,
  "receipt_id": "a-human-supplied-application-label",
  "report_id": "an-existing-retrieved-report-id",
  "target_sha256": "the-exact-current-target-fingerprint",
  "decision": "include",
  "reason": "The exact supplied reason to store on the report.",
  "adjudicator": "A supplied human identity label, not authenticated.",
  "decided_at": "2026-11-04",
  "rationale": "The person's explanation of this choice.",
  "source_locator": "An inert supplied reference to the decision basis.",
  "study_declaration": {"study_ids": ["an-explicit-study-label"]}
}
```

The displayed hash placeholder is deliberately invalid. Actual hashes are 64
lowercase hexadecimal characters. The schema version is integer 1; all text
fields must be nonblank literal strings and the date a real `YYYY-MM-DD` date.
No trimming, case folding, similarity matching or calendar-based winner selection
occurs. `receipt_id` is only a supplied label within this detached record; there
is no global uniqueness registry, chronology or receipt chain.

Only schema version, exact report ID and target hash are filled in the template.
Every human field, including `study_declaration`, remains null. Save just the
completed `decision_document` object separately after an actual human choice.
No current membership, candidate label, reviewer identity, decision or date is
copied into it.

- Include requires exactly `{"study_id": "a-label"}` or
  `{"study_ids": ["label-A", "label-B"]}`. The plural form must be nonempty and
  contain unique nonblank literal IDs. Shape and list order remain explicit.
- Exclude requires `study_declaration: null`. This explicitly removes both
  controlled membership fields, including an otherwise permitted legacy scalar
  `study_id`. Its previous value remains in the recorded prior report.
- Pending/retrieval decisions are outside this command. The selected report must
  already be retrieved and have a valid locator. The command never marks it
  retrieved, changes record mappings or fabricates source declarations.

Absent, unclear, opposing or stale reviewer positions do not prevent an explicit
human choice solely because they disagree. Missing document digests and source
descriptors do not become verified evidence. Their existing supplied states stay
visible in the target. No quorum, correct adjudication or complete reading is
claimed by successful structural assembly.

## Exact input and narrow mutation

The target binds the canonical hash of the **entire original protocol**, the
complete prior report row, its existing report-source target and exact same-report
review, study-review and inventory snapshots with their presence stages. When
`report_study_inventory_reviews` is supplied, same-report candidate-review
snapshots and their supplied stage are also retained, without choosing a winner.
Mapped search/CSV context is retained in the report source hash. The original protocol
remains required because these selected snapshots do not reproduce every source
body or arbitrary input field.

Those snapshots are available context, not proof the person read or relied on
every listed assertion or source. Source hashes bind supplied data, not document
bytes or source authenticity. Canonical JSON ignores object-key order and file
whitespace; literal values, JSON number types and list order remain significant.

Any intervening protocol change, including unrelated metadata, work or version
edits, invalidates the earlier target. There is no automatic rebase, refresh or
silent reuse. Generate a fresh target and supply the human document honestly.

Assembly validates the complete input and candidate with both the main workflow
and full report/evidence reconciliation. It changes only the selected report's
`decision`, `reason` and controlled scalar/plural membership declaration. It
preserves report position, ID, record mappings, retrieval, locator and all other
metadata. All other report rows, source declarations, screening/history, reviews,
inventory descriptions, results, contexts and work remain unchanged. The protocol
version is not automatically advanced.

Excluding a report with retained result rows fails. Dropping an evidenced study
membership also fails, including scalar-only protocols without optional review
ledgers. Dropping an unevidenced membership can succeed if the resulting whole
protocol is valid. The tool does not delete, relabel or filter evidence to make a
choice pass. Existing study-review assertions may become stale orphan context
under their existing rules; those assertions are retained, not renewed or turned
into a new task. Inventory source hashes remain independent of report inclusion.

## Detached record and replay limits

The application record has exactly `schema_version`,
`kind: "detached_report_decision"`, `receipt` and `protocol_candidate`. The receipt
retains target, supplied document, resulting report, whole input/candidate hashes,
before/after accounting, implementation hashes and explicit nonverification
boundaries. Its own hash covers every receipt field except that self-hash.

`verify` rebuilds the candidate and receipt from the retained original protocol
and recorded human document, then compares the entire application record. Editing
the target, report, candidate, counts, assertion, hashes, implementation map or
extra fields fails that comparison unless a new internally consistent record is
actually constructed. A passed replay establishes reproducibility of the supplied
operation, **not authorship, authority, execution, scientific truth or an honest
historical account**. Anyone able to replace supplied inputs can construct another
internally consistent record.

Use the exact recorded implementation to replay older records. Changing a bound
engine file intentionally makes them fail comparison under the new code. This is
not evidence that a prior human decision was wrong. Preserve code versions along
with original protocols and application records; no automatic migration is made.

No new history key is written into the protocol. Ordinary audit/status/handoff
views therefore do not claim to retain or validate these separate receipts.
Seven-file bundles preserve the exported candidate but do not include its original
protocol or detached application record. Keep those files separately when needed.
Repeated decisions require another explicit operation using the last exported
candidate as the new original input; no append-only or cross-record history is
inferred.
