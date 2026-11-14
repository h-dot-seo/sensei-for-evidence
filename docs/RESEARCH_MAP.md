# Standalone supplied research-map records

This is the first standalone part of the research-map roadmap, not a completed
engine-integrated research-map ledger. It lets an operator retain an authored plan,
separate supplied recording statements and supplied stopping statements beside an
unchanged protocol. No plan, recorder, date, approval or stop rule is generated.

## Rehearse with fictional inputs

Keep real/private documents outside the public checkout. These commands use only
fictional supplied inputs and exclusively create new files:

```sh
python research_map.py template examples/bibliographic-base.json --output /outside/map-template.json
python research_map.py review examples/bibliographic-base.json examples/research-map-sidecar.json --output /outside/map-review.json
python research_map.py verify examples/bibliographic-base.json examples/research-map-sidecar.json /outside/map-review.json
```

The template wrapper contains `draft`, a separate `record_template` and an
`event_template`. All map fields and record/event fields are null; empty `records`
and `stop_events` lists mean no supplied statements. The wrapper itself is not a
completed authored document. Its source_context copies question, criteria and search
plan only for inspection; it does not choose any plan values.

Author the draft's research_map fields explicitly. Use empty lists only as an explicit
statement that no entries were supplied, not as proof the plan needs none. A document
with a completed map and empty records/events can be reviewed to inspect its current
basis. A recording statement must then be supplied separately with its recorder,
calendar date, statement and that exact basis. This tool never appends a record or
renews its hash for you. Later editing a map/core can leave old records stale; retain
the original documents rather than overwriting history or clearing stale cues.

## What is checked and what is merely supplied

The document has exactly schema_version1, research_map, records and stop_events.
The map contains decision_scope, boundaries, evidence_classes, planned_sources,
extraction_dimensions, appraisal_plan, challenge_plan, expected_outputs and stop_rules.
Evidence classes contain label/description; appraisal rows contain evidence_class,
method/method_locator, referencing an explicitly declared class. Methods and source
locators are inert text. This does not test method suitability or whether actual
appraisals conform to the plan.

A stop rule contains stop_rule_id, applies_to (an exact planned search_id or ALL) and
rule. Records contain record_id, recorder, recorded_at, statement and basis_sha256.
Events contain event_id, record_id, search_id, stop_rule_id, recorded_by, recorded_at
and note. Their record_id must select a supplied map record, their search/rule IDs
must exist, and the rule must cover that search. Events inherit the referenced
record's basis status; a changed rule or changed core cannot silently renew an event.
Current-document references are checked, not historical event execution. If a revised
map deletes a referenced rule, preserve the old sidecar with its original protocol
rather than treating a formerly recorded event as applicable to the new plan.

Each record's basis is the canonical digest of exactly:
`{protocol_core: {question, inclusion_criteria, exclusion_criteria, search_plan}, research_map}`.
Version, actual search/evidence rows, record/event lists and engine hashes are excluded.
Changing them does not imply the declared scope changed. The review separately records
full current protocol/document hashes and current implementation hashes, so exact report
replay still detects those changes. Different records are all retained; no latest
record, accepted record or consensus is selected. CURRENT_SOURCE is equality only,
STALE_SOURCE is inequality only, and an empty record list is NOT_SUPPLIED.

Input_observation counts are from the currently supplied protocol, not a historical
recording-time snapshot. Dates and labels are unverified declarations; this cannot
establish that the plan preceded research, preregistration, consent or approval.
The gaps in planned stop-rule coverage are an inventory, not a recommendation. A stop
event never changes incomplete search accounting, gates, sufficiency or readiness.

## Deliberate separation

The original protocol is read, validated by existing run() rules and never modified.
This standalone input additionally requires a nonempty search_plan with unique
nonblank search IDs to resolve supplied rule references. Core fields preserve their
existing values and are not rewritten into a stronger protocol schema.

Existing run(), adapter receipts, research bundles, status, handoff and comparison
views do not consume or validate this sidecar. A passing research bundle therefore
says nothing about the map. Retain the sidecar and its report separately with their
original inputs. The standalone choice follows the roadmap's ENGINE-external option;
full integration, protocol-resident records, automatic navigation, method comparison
and any new gate are outside this increment. Do not insert these fields into an old
adapter protocol: its immutable base-context check can reject such changes.

Review reports may be stored. Verify compares the complete deterministic review with
a newly computed review using the current implementation and supplied inputs. It
never executes stored code and does not establish authenticity, historical existence
or scientific acceptance. Verification is not supported as a historical-code migration.
A mismatch returns JSON stdout with valid:false and exit1; a match returns exit0.
Other caught input/output errors use fixed stderr, empty stdout and exit1. Usage is
exit2. Template/review optionally write a new JSON file and also print JSON. They
never overwrite; partial files on OS write failures remain possible, not transactional.

Strict JSON/UTF-8, duplicate-key/nonfinite rejection and depth128 checks apply.
Bounds are50MB protocol/report,10MB sidecar,1000 rows per authored list. These are
processing limits, not limits on scientific studies. Inputs/outputs include supplied
text, labels and hashes and are not anonymized. No external calls or document reads.

[Starting protocol](PROTOCOL_SCAFFOLD.md) · [Existing comparison notes](AMENDMENT_NOTES.md)
