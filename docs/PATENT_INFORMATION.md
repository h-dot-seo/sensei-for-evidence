# Supplied patent-information ledger, outside the engine

This is **not legal advice, an FTO opinion, a legal-rights determination, a patent
search backend, or verification of legal-status currency**. The only product is a
supplied information ledger. SEARCH_INVENTORY, LANDSCAPE and PRIOR_ART_SCREEN are
operator labels, not findings that those deliverables are complete. FTO_OPINION is
not accepted. No locator is opened, model called or external request sent.

## Scope and original design choice

Roadmap #45, reader adjustment path B, explicitly permits an ENGINE-external first
release. This implementation completes that path's four-entity intake/replay/view
flow, rather than changing the research engine. It does not implement priority
claims, claim-feature mapping, claim interpretation, infringement, validity or FTO
analysis. It does not normalize identifiers or kind codes, infer family membership,
interpret status text, or verify identities, jurisdictions, dates or sources.

The ordinary supplied protocol gains exactly five fields together:
`patent_question`, `patent_publications`, `patent_applications`, `patent_families`,
`patent_legal_status_observations`. Existing fields and rows are preserved. Existing
`run()` ignores these patent fields: a successful run is **not** patent validation.
Only the new commands validate them. ENGINE_FILES, canonical decisions, allowlists,
run(), adapter code, bundle summary and readiness gates are unchanged. The 12
literature gates can remain open and do not measure patent readiness. Bundles may
preserve raw fields but do not regenerate or semantically verify the patent ledger;
keep the original protocol and detached application for the dedicated replay.
The status/handoff/compare map context introduced earlier is not patent integration.

Protocols containing `adapter_receipts` or `bibliographic_imports` are rejected,
including null/empty values. Adapter provenance without a receipt is also rejected.
Do not strip an import history to evade this limitation. Use an ordinary independently
supplied protocol, not a relabeled imported ledger. Integration is a separate future
scope. The three new modules are discoverable through `sensei.py` and COMMANDS;
the existing operator handoff catalog is intentionally unchanged.

## Authoring and exact references

`patent_question` has exactly `jurisdictions` (nonempty unique supplied labels),
`as_of_date` (calendar YYYY-MM-DD), `intended_output`, `technical_question`, and
`claim_feature_scope`. The last is supplied scope text, not a claim mapping. A
jurisdiction label is not validated against an authority and the question does not
establish that every row falls within that jurisdiction or technical scope.

Every row has `basis_sha256` and its exact listed fields:

- Publications: `publication_id`, `jurisdiction`, `kind_code`, `publication_date`,
  `locator`. Exact publication IDs join supplied search record IDs. No case folding,
  prefix stripping, identifier resolution or kind-code parsing occurs.
- Applications: `application_id`, `jurisdiction`, `filing_date`, `publication_ids`.
  All publication references must already exist or be in the same candidate batch.
  An explicit empty publication list is allowed; no relation is invented.
- Families: `family_id`, `family_definition_label`, nonempty unique `member_ids`,
  `grouping_basis`, `asserted_by`, `asserted_at`. Grouping is either
  SUPPLIED_FAMILY_IDENTIFIER (assertion fields explicitly null) or MANUAL_ASSERTION
  (nonblank supplier and calendar date required). Definitions are not merged.
  Outside members are retained and queued. Multiple families with the same definition
  containing the same member are exposed, not rejected or reconciled.
- Legal-status observations: `observation_id`, `application_id`, `jurisdiction`,
  `observed_at`, `source`, `status_text`. The application reference must exist. Text
  is reproduced as supplied, never translated into active/expired/enforceable labels.
  An absent observation is not a legal-status finding. Row and question jurisdiction
  strings are not compared as a legal consistency or territorial-rights test.

IDs are unique within each entity list, not across unrelated namespaces. Extra or
missing fields, duplicate IDs/list references, blank required text, invalid calendar
dates and unsupported labels are rejected. No priorities or publication/application
date order is assessed. Chronology and reviewer identity are not authenticated.

## Basis, review and append semantics

The row basis is canonical SHA-256 of the supplied `patent_question`, entire
`search_plan`, and entire `searches` value, including all receipt fields. It is not
an inferred search window or immutable historical observation. Exact equality is
CURRENT_SOURCE; otherwise the row remains visible as STALE_SOURCE. Version labels,
screening, evidence and ledger rows are outside this particular basis. The full
protocol and candidate bytes (canonical JSON), candidate protocol and exact engine/
new-module/search-manifest implementation hashes are separately bound by the intake
target. A version-only change therefore invalidates an import review even though it
does not stale row search basis. No claim of semantic equivalence is made.

Template returns null authoring fields, empty row lists and null review values.
Optionally supply `--question question.json` to obtain the current basis for your
explicit question before filling row templates. It never fills reviewer, acceptance,
legal text or scientific judgments. Copy the explicit current basis into new rows.
Target requires 1–100 new rows in total across the four lists, all on the current
basis. This is a **batch limit**, not a 100-row whole-ledger limit. Existing stale
rows are preserved; importing new rows does not renew them. Append cannot change
an existing patent question, replace IDs, amend rows, or delete history.

A separate supplied review with exact schema_version=1, target_sha256, decision,
reviewer, reviewed_at and rationale is required for assemble. Only `accept` permits
recording; `reject`, missing/incomplete review and a changed target do not produce a
candidate. Acceptance means permission to record these exact supplied rows, not
endorsement of legal conclusions. Review identity and historical timing remain
unverified. Assembly returns a detached application containing target, candidate
rows, supplied review and complete candidate protocol. Original inputs are unchanged.

Verify replays assembly from the **original protocol** and compares the entire
application using the current trusted implementation. A structurally replayable
mismatch returns valid=false JSON and exit 1. Missing/malformed review or changed
implementation/target instead uses the fixed error channel. Consistently reauthored
inputs and assertions can replay: this is not signature authentication or a tamper-
proof archive. Preserve the matching implementation for old records.

## Read view and queues

`patent_review.py` emits rows with basis status, question, the existing exact-ID
search accounting, supplied family co-occurrence and these fact-only queues:
publications missing from searches; search IDs without publication rows; publications
not listed in supplied families; family members absent from this ledger; applications
without supplied observations; observation dates after the supplied as-of date.
The last is only a calendar-date comparison, not a currency or admissibility verdict.
Family occurrences count zero-based supplied search rows, not independent sources.
All queues and co-occurrences describe current supplied inputs, not a historical
snapshot of what existed when a stale row was recorded.
The existing search manifest's cross_search_overlap and source_coverage are reused;
equal query/window groups are not mislabeled independent cross-validation.

## Fictional end-to-end rehearsal

All ZZ-SYN labels below are software fixtures, not real applications, applicants,
authorities, legal event codes or rights. Work in a fresh private output directory
(or ensure every named output below is absent). Commands below assume the repository
working directory. The test executes all commands and supplies the explicitly fictional
review between target and assemble; the software does not generate that acceptance.

```sh
python patent_intake.py template examples/patent-protocol.json --output patent-draft.json
python patent_intake.py target examples/patent-protocol.json examples/patent-candidates.json --output patent-target.json
```

Create `patent-review.json` separately: copy the target's review_template and supply
`decision: "accept"`, `reviewer: "Fictional reviewer"`, `reviewed_at: "2026-01-03"`,
`rationale: "Synthetic recording rehearsal only"`. These are example supplied choices,
not recommended decisions for real data. Do not change the target digest.

```sh
python patent_intake.py assemble examples/patent-protocol.json examples/patent-candidates.json patent-review.json --output patent-application.json
python patent_intake.py verify examples/patent-protocol.json patent-application.json
python -c "import json; a=json.load(open('patent-application.json',encoding='utf-8')); f=open('patent-candidate.json','x',encoding='utf-8'); json.dump(a['protocol_candidate'],f,ensure_ascii=False); f.close()"
python patent_review.py patent-candidate.json --output patent-observations.json
python patent_review.py patent-candidate.json --text
```

The final view intentionally shows missing ledger/search/family/observation links,
a supplied observation after the as-of date, and unchanged literature readiness.
Those are unresolved supplied-data facts, not failure to manufacture a legal answer.
This tested flow does not establish live-provider compatibility or real legal utility.

## Resource, output and privacy boundaries

Strict UTF-8 JSON rejects duplicate keys, nonfinite numbers and unpaired surrogates.
Protocol/application/report limits are 50,000,000 bytes; candidate/question/review
inputs are 10,000,000 bytes; nesting is limited to 128. The input byte count and
serialized output budget are separate. API values must be JSON-shaped. Whole-ledger
size is bounded by bytes, not a row ceiling. No linear-time or performance guarantee
is made. No locator, source root, external file or URL inside a document is opened.

Successful commands emit JSON stdout, except review --text. Review --output always
writes JSON even with text stdout. Requested outputs are exclusive new files;
existing entries and dangling links are refused. Output creation is not a multi-file
transaction or secure-root API; ancestor aliases and concurrent path changes are
not defended. OS failures can leave a partial new file. Size/encoding is checked
before write. Printed text quotes control characters; JSON retains supplied values.
Both text and JSON expose supplied IDs, statuses, locators, reviewer labels and
hashes and are not anonymized. Do not publish real inputs or output by default.

Caught input/access/output failures emit fixed, non-echoing stderr, empty stdout,
and exit 1. CLI usage errors are argparse exit 2. Valid view queues/stale rows do
not change exit 0 to a legal or scientific verdict. Replay mismatch is the distinct
normal JSON-negative exit 1 described above. Unexpected interpreter/OS resource
failures remain outside the normalized error contract. New commands retain unknown
NOT_REVIEWED effects in the agent contract; discovery is not execution permission.
