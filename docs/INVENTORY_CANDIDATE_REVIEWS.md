# Human positions on described study candidates

A mixed-study paper may need study-level review before its report is included.
`report_study_inventory_reviews` records separate human eligibility positions on
explicitly described candidates without changing report decisions or declaring
included memberships. It is a separate scope from `report_study_reviews`, which
continues to concern included memberships. Never interchange the two hashes.

Only fictional inputs are shipped. No article is opened, scientific fact checked,
clinical applicability established or biological experiment designed or executed.
Keep real protocols, source descriptions and generated outputs outside this public
repository. Outputs retain supplied information without redaction.

## Fictional review journey

```sh
python report_study_inventory_review.py examples/report-study-inventory-reviews.json --text
python report_study_inventory_review.py examples/report-study-inventory-reviews.json --report-id=report-three --study-id=candidate-X --template --output /outside/new-candidate-review.json
python research_status.py examples/report-study-inventory-reviews.json --text
python review_handoff.py examples/report-study-inventory-reviews.json --text
python prisma_audit.py examples/report-study-inventory-reviews.json --text
python research_bundle.py create examples/report-study-inventory-reviews.json /outside/new-candidate-review.zip
python research_bundle.py verify /outside/new-candidate-review.zip
```

Choose new paths in an existing directory. `--output` exclusively creates a JSON
view or scaffold, not a modified protocol. `--text` affects stdout only. Full-input
validation and UTF-8 encoding precede output creation; a later disk/write failure
can still leave a partial new file. Shell redirection has its own overwrite rules.

The example retains five candidate-review assertions: two differing positions on
candidate X in a pending report, an unclear position on candidate Y in an excluded
report, one position on study A with a separate included membership, and one stale
retrospective position whose candidate description is no longer supplied.
Four review assertions match their current supplied context. The removed pair is
not a new task. All five original descriptions and two result rows remain intact.
Three described candidates have review cues; an empty cue list would not establish
correct eligibility, complete reading or exhaustive inventory.

## Explicit human assertion

Each row has exactly these fields:

```json
{
  "review_id": "a-human-supplied-review-label",
  "report_id": "an-exact-report-id",
  "study_id": "an-explicitly-described-candidate-label",
  "reviewer": "a-supplied-human-label",
  "reviewed_at": "2026-11-04",
  "decision": "unclear",
  "rationale": "The person's reason for this position.",
  "reviewed_locator": "The supplied page, section and scope reference.",
  "reviewed_inventory_ids": ["a-description-assertion-id"],
  "reviewed_source_ids": ["a-source-descriptor-id"],
  "source_basis_sha256": "the-exact-candidate-review-target-actually-used"
}
```

The hash placeholder is invalid by design. Scalars must be nonblank literal
strings, the date a real `YYYY-MM-DD` date and the hash 64 lowercase hexadecimal
characters. Decisions are `include`, `exclude` or `unclear`, all human positions,
not a canonical decision. Both selection lists must be nonempty unique literal
IDs. The selected inventory IDs must belong to the exact report/study pair;
selected document IDs must belong to that report. Neither subset is inferred.
They need not equal one another's source selections, and neither establishes
actual reading, equal coverage or an authenticated source.

Review IDs are unique within this ledger. The exact `(report_id, study_id,
reviewer)` tuple must also be unique. Different people retain separate positions;
no latest date, majority, preferred description or reviewer is selected. IDs are
not normalized or matched by similarity. Identical study labels across reports
remain separate pairs and do not establish identity or independence.

1. Describe the candidate with the [inventory workflow](REPORT_STUDY_INVENTORY.md).
2. Generate a review template for that already described pair. Only report ID,
   study ID and current target hash are filled. All human fields, including both
   selection lists, are null. No earlier assertion is renewed or copied.
3. After actual human inspection, complete the fields honestly, then use the separate
   [reviewed append/replay intake](REPORT_STUDY_INVENTORY_REVIEW_INTAKE.md) instead of
   manually copying assertions into a working protocol.
4. Keep report inclusion and membership declarations explicit and separate.

Templates require a currently described pair, a retrieved report and at least one
source descriptor. Pending or excluded **eligibility** permits a scaffold when
retrieval is supplied as retrieved. Pending/unavailable **retrieval** does not;
the output gives retrieval guidance. Missing descriptors give source-first guidance.
Null document digests are allowed but remain unbound. Nonnull digests are unverified.
A new arbitrary study label is not a candidate merely because it is passed on the
command line. `--study-id` requires `--report-id`; exact selection happens only
after the entire protocol is validated.

## Source binding and changed descriptions

The version-1 scope `report_study_inventory_supplied_eligibility_context` binds:

- The exact report and study labels and whether a description is currently supplied.
- The existing report-source basis hash, including criteria, mapped search/CSV
  provenance, retrieval, report locator and the entire ordered source catalog.
- **Every full raw inventory assertion for this pair in supplied order**, including
  unselected descriptions, their source selections and recorded source hashes.

Changing any same-pair description or its metadata, adding/removing/reordering
same-pair descriptions, or changing report source context can stale the review.
Changing an unselected source descriptor in the same report can also stale it.
Other-pair description changes do not. Relocating report, inventory or source
rows without changing bound description/source order does not change this hash.
Changing search ordering can change inherited record-source hashes and therefore
stale candidate reviews; not every input-pointer relocation is independent.
Canonical report decision/reason, included membership declarations, result rows,
other review assertions and protocol version are not part of this basis. Those
changes alone do not renew or stale candidate reviews. Whole-protocol validity
rules still apply. Object-key order is ignored; literal values and relevant list
order are retained.

A current review may explicitly refer to a stale description. Its current context
includes that stale supplied assertion; it does **not** make the description current
or correct. The inventory ledger and selected-description source-match labels stay
visible, with a stale-inventory cue. Likewise, a current hash on a supplied position
never proves that a person read the source or had access at the recorded date.

Removing any same-pair description stales a retained review. It has unresolved
inventory IDs if the removed description was selected. Removing every description
for that pair makes it retrospective orphan
context, without a fresh scaffold or candidate-review queue entry. A matching
current hash cannot refer to a missing selected description/source or undescribed
pair. A known inventory ID belonging to another exact pair or source ID belonging
to another report is always rejected, even on stale assertions. Missing IDs may
survive only in stale context; that is not evidence the deleted item ever existed.
The supplied report itself must still exist. Retain original versions separately
if historical descriptions are needed; hashes do not reconstruct missing content.

## Integration and compatibility

Core/report/audit/synthesis views retain the optional complete projection. Status
and handoff expose candidate review cues and a detailed-view link; only currently
described pairs enter that cue queue. Inventory descriptions alone still do not
create tasks. Candidate positions never become membership-review agreement,
canonical report decisions, extraction authorizations or result filters.

Comparison retains exact before/after assertions, pair context and source labels.
Detached [full-text decisions](REPORT_DECISIONS.md) include same-report candidate
review snapshots when this ledger is supplied, but still require an explicit human
decision and study declaration. No position is selected automatically. Candidate
review assertions remain unchanged during an otherwise valid report transition.

Omitting the key preserves prior projection shapes and semantic source hashes.
`[]` opts in, including without reports; null is invalid. Nonempty reviews require
known reports. Existing PRISMA units/counts, membership hashes, result rows,
planning/completion semantics and CSV bytes remain unchanged by these positions.
The key is allowed enrichment in retained CSV-import histories. Seven-file bundles
retain supplied rows and the new helper fingerprint, not article bytes. Verify
older engine-bound artifacts using their recorded implementation.

Reviewer identity, authentication, independence, study identity and completeness
remain unestablished. No consensus, adjudication, canonical study selection,
source authentication or scientific/clinical validity is inferred from successful
validation, a current hash, a completed work package or a verified bundle.
