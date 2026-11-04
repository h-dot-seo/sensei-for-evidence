# Descriptive study inventory before full-text inclusion

A retrieved report can describe several candidate studies before a person decides
whether to include that report. `report_study_inventory` records explicit human
labels, descriptions and source references without requiring a full-text inclusion
label. It does not create included memberships, eligibility decisions or results.

This is **pre-full-text-inclusion**, not pre-screening discovery. Existing report
validation still requires links to title/abstract-included records. Do not alter
screening or full-text eligibility merely to obtain an inventory template.

Only generic code and fictional examples are included. Actual/private sources and
generated artifacts belong outside this public repository. No source is retrieved,
opened or authenticated, no scientific fact is checked, and no biological experiment
is designed or executed by this workflow.

## Reproduce the fictional inventory

```sh
python report_study_inventory.py examples/report-study-inventory.json --text
python report_study_inventory.py examples/report-study-inventory.json --report-id=report-three --study-id=candidate-X --text
python report_study_inventory.py examples/report-study-inventory.json --report-id=report-three --study-id=candidate-new --template --output /outside/new-candidate-description.json
python prisma_audit.py examples/report-study-inventory.json --text
python review_handoff.py examples/report-study-inventory.json --text
python research_bundle.py create examples/report-study-inventory.json /outside/new-inventory-bundle.zip
python research_bundle.py verify /outside/new-inventory-bundle.zip
```

Choose a new output path in an existing directory. `--output` exclusively creates
a separate JSON view/scaffold and refuses overwrite, including the input file.
`--text` affects stdout only. The entire protocol is validated before selection.
`--study-id` requires `--report-id`; ordinary inspection requires a described pair.

A new template requires explicit report and study IDs supplied by the operator.
It can accept a **new** candidate label without claiming that candidate is already
stored. `proposed_target` is separate from `candidate_targets` and stored inventory
counts. For `candidate-new`, those stored assertion/pair counts remain zero.
A blank scaffold is not a completed assertion or a modified protocol.

The example preserves five human assertions for four exact report-study labels:

- Two people separately describe candidate X in a retrieved, decision-pending report.
- Candidate Y remains described on a full-text-excluded report.
- Study A has a description and a separately declared included membership.
- Candidate Z has a stale earlier assertion after its source became unavailable.

Four assertions match current supplied context and one is stale. Five report rows,
three current included report-study memberships and two result rows remain separate
from those inventory counts. The older calendar date of one description does not
select or discard it. No candidate is promoted into inclusion or an extraction task.

## Explicit schema and human input

Each `report_study_inventory` row has exactly these fields:

```json
{
  "inventory_id": "a-stable-supplied-assertion-id",
  "report_id": "an-exact-report-id",
  "study_id": "a-human-supplied-candidate-label",
  "recorded_by": "a-supplied-recorder-label",
  "recorded_at": "2026-11-04",
  "description": "A human description distinguishing this reported candidate.",
  "source_locator": "The supplied page, section and scope reference.",
  "source_ids": ["a-source-id-declared-for-this-report"],
  "source_basis_sha256": "the-exact-inventory-target-actually-used"
}
```

The placeholder hash is deliberately invalid. Actual hashes require 64 lowercase
hexadecimal characters. Scalar fields are nonblank literal strings; the date must
be a real `YYYY-MM-DD` date. `source_ids` is a nonempty list of unique literal IDs,
explicitly selected by a person. No eligibility `decision` field is accepted.

Inventory IDs are globally unique. Duplicate exact `(report_id, study_id,
recorded_by)` tuples are rejected, but different people may describe the same
pair. All descriptions remain visible. No recorder, description or latest date is
selected as authoritative. IDs are not trimmed, case-folded, matched by similarity
or concatenated for identity. Equal study IDs across reports do not prove one study;
different labels do not prove independent studies. A description and locator do not
prove that the source actually contains that candidate.

1. Inspect the report and its supplied document-version/source declarations.
2. Supply an explicit candidate label and generate a separate template. The tool
   fills report ID, study ID and current source hash only. Inventory ID, recorder,
   date, description, locator and source selection remain null.
3. After actual human inspection, fill the missing fields honestly and copy only
   completed assertion rows into a separate working protocol. Never copy a new
   hash just to clear a stale-context label.
4. Keep inclusion, study review and extraction decisions separate. The inventory
   command never makes them or supplies supporting scientific evidence.

A fresh descriptive scaffold requires a retrieved report and at least one supplied
source descriptor, regardless of whether the full-text decision is pending,
included or excluded. Missing descriptors yield `source_first_candidates` guidance;
pending/unavailable retrieval yields `retrieval_required_candidates`. Neither
case fabricates a description or silently marks a report retrieved/included.
Null document digests remain unbound; nonnull digests remain unverified assertions.
Use the [report source workflow](REPORT_REVIEWS.md) for source-first declarations.

## Source binding is independent of inclusion

The versioned inventory basis contains exact report/study IDs and the existing
report-source basis hash. It intentionally contains **no membership-presence
Boolean**. The report hash binds criteria, mapped record/search/CSV provenance,
retrieval state, report locator and the complete ordered source-descriptor catalog.
Shared catalogs are retained once, not copied into each candidate target.

Canonical report decision/reason and study membership changes do not stale the
inventory. Thus honest pending → included → excluded transitions can retain the
same inventory source hash. Report ordering changes pointers, not the hash.
Descriptions, recorders, dates, selected source IDs, assertion positions, sibling
candidates, results, work and protocol version remain assertion/output context,
not the source basis. Changing a description or selected subset is a changed
supplied assertion, not proof of a new source reading or true scientific revision.

Source metadata/digest/version, criteria, mapped provenance, retrieval or catalog
changes can stale the context, even when the changed descriptor was not selected.
Object-key order is ignored by canonical JSON hashes; literal values, types and
relevant list order remain significant. Hashes do not authenticate authors,
verify source bytes, prove reading or judge description correctness.

Existing report-review and report-study-review semantic source hashes are unchanged
by adding this inventory. The older study-review basis still includes current
membership presence, so it can become stale when a membership disappears even
while the inventory basis remains stable. Do not interchange these scopes or
copy an inventory hash into a study-review assertion.

## Keep stale source claims explicit

Unknown report IDs are rejected. Preserve prior protocol/bundle snapshots when
removing an entire report rather than inventing a replacement report identity.
For source selections:

- A currently known source assigned to a different report is always invalid,
  including for stale assertions.
- A deleted/unknown source can remain only under stale context and is listed in
  `unresolved_source_ids`; no historical validity is established.
- A matching context hash requires all selected source IDs to exist for that report.
  Replacing an old hash with the current one cannot legitimize a missing reference.

Retrieval can later become unavailable while a description remains. A current
hash merely matches supplied context; it never proves current access or reading.
Dates and different descriptions/source-ID sets are not votes, contradictions or
quality scores. Constant verification limits remain explicit regardless of cues.

## Integration and limits

Core/report/audit/synthesis views retain the optional inventory projection. Status
and handoff add a descriptive summary and detailed view, **not a new pending queue**.
Comparison preserves before/after assertions and source-match labels; changes are
not automatically justified amendments or verified scientific reassessment.

Counts are `inventory_assertions`, `described_report_study_pairs`,
`current_source_assertions` and `stale_source_assertions`, never eligible or
independent studies. Existing report/record/study counts, CSV bytes, extracted
results and review/extraction queues remain unchanged by inventory descriptions.
`inventory_completeness`, study identity and independence remain `NOT_ESTABLISHED`;
`eligibility_assessment` and document-byte verification remain `NOT_PERFORMED`.

This increment does not expand existing report-study review templates to candidates
outside included memberships, and it does not add canonical per-study selection.
An explicit future versioned migration would be needed to use candidate inventory
as an eligibility-review target. Do not mark a report included to bypass that limit.

Omitting the key preserves legacy projection shapes. `[]` opts in; null is invalid.
Empty inventory without reports is allowed, while nonempty assertions require
known reports. The key is reserved enrichment in CSV import histories. Existing
seven-file bundles retain raw assertions and the new helper fingerprint, not
full-text bytes. Verify older engine-bound artifacts with their recorded code;
semantic source-hash compatibility does not mean identical implementation hashes.
