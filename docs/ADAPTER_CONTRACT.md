# Offline provider adapter contract (schema 1)

This is a provider-neutral **data exchange contract and mock runner**, not an API
client. It makes no literature-service or model calls, handles no credentials,
and does not implement live provider execution. The examples are entirely
synthetic. A `mode: "mock"` label is an execution boundary, not proof that arbitrary
user-supplied text is synthetic or safe to publish.

## Run the synthetic example

From the repository root, with Python 3.10+:

```sh
python offline_adapter.py examples/adapter-protocol.json examples/adapter-fixture.json
python offline_adapter.py examples/adapter-protocol.json examples/adapter-fixture.json --reviews examples/adapter-reviews.json --protocol-output ../reviewed-mock-protocol.json
python research_status.py ../reviewed-mock-protocol.json --text
python research_bundle.py create ../reviewed-mock-protocol.json ../reviewed-mock-bundle.zip
python research_bundle.py verify ../reviewed-mock-bundle.zip
```

Both output paths must not already exist. Keep supplied inputs and generated
artifacts outside the public repository. The exported protocol and bundle retain
source text, proposals, provider metadata and reviewer labels without redaction.
No file is uploaded by these commands.

The preview has three pending review targets and **zero accepted result rows**.
The reviewed fixture has two result rows from one supplied study/report, while a
second planned search remains missing. It deliberately still has no scientific
appraisals, no verified source identities and no established census or conclusion.
The example review file is a test assertion, not evidence of an actual review.

## Input protocol

Use the existing protocol structure with a nonempty `search_plan`, empty
`searches` and empty `evidence`. Existing work is never silently replaced.
Screening and optional report retrieval/full-text decisions remain independently
supplied protocol data. This adapter does not create those decisions or appraisals.
It rejects an existing `adapter_receipts` ledger rather than overwriting it.

Without reports, accepted candidates receive only the existing record-screening
checks. With reports, they must also map to a supplied retrieved/included report
and matching study ID. Neither case independently establishes full-text access or
scientific validity. Work packages/context/appraisals can be added to the exported
protocol using the ordinary validated evidence IDs; the adapter does not invent
these links. Version the protocol when adding or changing work. Downstream validation allows
changes only to version, work packages (`gaps`), contexts and appraisals beyond the
derived searches/evidence. Changing question, criteria, plan, screening or reports
requires a new assembly and new hash-bound reviews. The original base protocol
and its review version remain in the receipt ledger.

## Fixture envelope

Required top-level fields:

- `schema_version`: integer `1`.
- `mode`: exactly `"mock"`; other modes are rejected.
- `provider_id`, `adapter_version`: nonempty asserted labels.
- `search_responses`, `extraction_candidates`: arrays, possibly empty.

Each search response contains:

- `request`: nonempty `request_id`, `search_id`, `source`, exact `query`, `window`
  and `searched_at`. Source/query/window must match its declared plan item.
- `pages`: a nonempty array, including one empty terminal page for zero results.
- `total_count`: supplied total; an accepted search needs a nonnegative integer
  matching its distinct returned IDs.
- Optional `error`, `truncated`, `pagination_limited`, `field_pages_pending` flags.

Each page contains nonempty `response_id`, matching `request_id`, `retrieved_at`,
a positive integer `page_number`, `has_more`, and `records`. Every record has a
nonempty `record_id` and `source_locator`; optional metadata such as title is
retained in its receipt. Optional page `total_count` must match the exchange total
when supplied. Existing page accounting checks sequence, overlap, pagination,
errors and truncation. Response IDs, search IDs and request IDs are unique across
the fixture. Pagination cursors or provider-specific metadata can be retained as
inert extra data; the runner never follows a cursor or executes instructions.

IDs are globally exact within a fixture. Conflicting source locators for one
record ID, even across requests, are rejected. Normalize to a consistent canonical
locator or use separate IDs upstream; the runner cannot determine whether two
publications are the same. Distinct IDs are never bibliographically merged.

## Extraction candidates

Each candidate requires:

- Unique `candidate_id`; the related search `request_id`, returned `record_id`,
  and its exact `source_locator`.
- Nonempty `extraction_request_id`, `extractor_id`, `extractor_version` and
  `instruction` describing the supplied extraction request. These are metadata,
  not executable instructions or an assertion that a model actually ran.
- `source_text` and `supporting_quote`. The quote must occur literally in the
  supplied text. This tests string consistency only, not source authenticity,
  quote adequacy, factual support or scientific interpretation.
- `proposal`: explicit unique `evidence_id`, `study_id`, `locator`, `model`,
  `intervention`, `comparator`, `endpoint`, `result`, `limitations` and
  `mechanism_basis` (`association`, `intervention` or `unknown`). If supplied,
  proposal `record_id` must match the candidate's record ID.

Multiple candidate results may come from one source. They remain in the receipt
ledger and outside evidence unless explicitly accepted. Provider-supplied
instructions and proposed conclusions are data, never authority to act.

## Reviews and hashes

The preview exposes `review_pending` targets. Every review contains exactly:
`target_type` (`search` or `extraction`), `target_id`, `target_sha256`, `decision`
(`accept` or `reject`), `reviewer`, ISO-date `reviewed_at` and nonempty `rationale`.
Unknown targets, duplicate decisions, extra mutation fields and stale hashes fail.

A search acceptance is an operator assertion of reconciled receipt accounting.
It succeeds only if all existing count/page checks pass. Extraction acceptance
requires an accepted review for its search and passes existing evidence/report
validation. A rejection records the decision but never promotes that extraction.
There is no authenticated reviewer identity or automatic scientific appraisal.

Hashes cover sorted compact UTF-8 JSON, preserving list order but ignoring object
key order. They are **not exact-byte response receipts or digital signatures**:

- Search receipt: schema, base-protocol hash, provider labels, and the full request
  and ordered response exchange.
- Extraction receipt: schema, base-protocol hash, provider labels, search-receipt
  hash and the full candidate, including source text and proposed extraction.

Changing the base protocol input, provider metadata, source pages or extraction
proposals invalidates the associated review binding. Later version/work-package/
context/appraisal enrichment is the explicit downstream exception described above. The exported protocol stores the original base-protocol snapshot, receipts,
reviews and the adapter source-file hash. Promoted searches/evidence retain mock
provenance and `UNVERIFIED_PROVIDER_RESPONSE` even after review acceptance.

## Integration and limits

`assemble(protocol, fixture, reviews=None)` returns the assembled protocol,
ordinary research/report outputs, pending/rejected review targets and fixed
`NOT_ESTABLISHED`/`NOT_READY` bounds. The CLI also supports exclusive protocol
export. Existing bundle generation preserves the receipt ledger in `protocol.json`
and extraction provenance in derived outputs. Every downstream research/report/status/bundle run validates attached receipt
hashes, review bindings, preserved review context and normalized promoted rows.
The same fixture/candidate schema checks run during assembly and downstream
receipt reconstruction. Canonical comparisons distinguish integers, floats and
booleans even where Python equality would treat them as equal. Editing accepted
extraction content while retaining its old review, or dropping
the ledger while retaining adapter provenance, is rejected. Bundle verification
checks this internal consistency and derived outputs; it does **not** repeat an
external search/model call or authenticate the provider, reviewer or factual claims.
Someone who fabricates a wholly consistent new ledger/review can still fabricate
assertions; hashes are not signatures. Keep the recorded implementation to verify
its engine hashes and reproduce the normalization.

A production transport, credentials, retries/rate limits, actual raw HTTP receipts,
provider terms, model usage/costs and privacy controls are deliberately unimplemented.
Adding one requires separate authorization and review. This mock workflow does not
establish actual literature retrieval, full-corpus enumeration, guideline currency,
mechanistic validity, clinical suitability or PRISMA compliance.
