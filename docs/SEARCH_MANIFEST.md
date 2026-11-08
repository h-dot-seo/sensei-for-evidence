# Supplied query and receipt manifest

`search_manifest.py` packages **exact supplied query text and receipt accounting**
for inspection before connecting any real search provider. It reuses the existing
search, page, plan, adapter-integrity and downstream-link validators. It is not a
second search engine and does not issue requests, translate queries, validate
provider syntax, calculate a restart cursor or overwrite prior work.

```sh
python search_manifest.py examples/search-manifest.json
python search_manifest.py examples/search-manifest.json --text
python review_handoff.py examples/search-manifest.json --work-package WP-TRANSLATION --text
python prisma_audit.py examples/search-manifest.json --text
```

Output is JSON by default or escaped text with `--text`. Commands only read input
and print stdout. Use new paths outside the public repository if saving outputs;
shell redirection can overwrite an existing file. This manifest is separate from
the existing seven-file research bundle and is not authenticated by bundle
verification. Original protocol inputs remain necessary to reproduce the output.

## The fictional example

The fixture has four planned requests on three exact source labels:

- The primary source has one interrupted supplied receipt and a second missing
  request with identical core source/query/window but different extra filters.
- The secondary source has an internally reconciled, supplied complete assertion.
- A planned citation-followup source has no supplied receipt at all.

The primary receipt records an announced total different from the ten enumerated
IDs, continuation and error signals, and two pages with one repeated exact ID.
Two IDs overlap between the primary and secondary searches. Page overlap and
cross-search overlap are different ledgers; the former does not inflate normalized
search-record counts. All signals, queries, numbers and cursors are fictional.
No stop cause, provider failure, identity equivalence or next-page instruction is
inferred. Even the internally reconciled secondary receipt does not establish
source completeness or a census.

## Request specifications

`planned_requests` retains every original plan entry, its `/search_plan/N` pointer,
and a canonical SHA-256 of the **whole** entry. `request_fields` exposes the
existing provider-neutral core: search_id, source, query, window. Source strings,
Unicode, whitespace and query syntax are unchanged. The original entry retains
all extra values, while `unsupported_plan_fields` explicitly lists fields the
current core does not interpret. An extra filter is not silently accepted as an
implemented search restriction.

Each specification includes its existing MISSING/INCOMPLETE/ASSERTED_COMPLETE
receipt status and observed search index when available. It lists request_id and
searched_at as required new runtime inputs; they are not fabricated or recycled
from a prior execution. These fields are only the existing mock contract's minimum
runtime requirements, **not an exhaustive provider-readiness checklist**. Provider
credentials, endpoints, pagination settings, syntax, filters, index versions and
other requirements are not implemented or validated here.

Full request hashes bind all supplied plan fields. `core_query_sha256` and
`same_core_request_groups` compare only literal source/query/window. They do not
compare extra filters, normalize synonyms or establish scientific/semantic
equivalence. Identical core requests may be intentional. No request is removed,
merged, prioritized or automatically re-executed based on this grouping.

With an absent/null plan, planned_requests is null: observed receipt queries are
not promoted into a new plan or executable requests. Existing validator rules
remain in force: supplied plans are nonempty, executed IDs must belong to the plan,
and duplicate attempts under the same declared search ID must be reconciled in an
explicitly revised plan/version rather than appended or silently overwritten.

## Receipt and source accounting

`observed_receipts` uses original search indices and input pointers as stable
within-input references. Optional missing or duplicate search IDs in a protocol
without a plan cannot collapse receipts. Each row preserves exact core query,
supplied searched_at, enumerated record IDs, full receipt hash, recorded completion/
count/continuation/error/truncation signals and existing page/accounting issues.
Missing signals stay absent rather than becoming false assertions.

Pages have input pointers, supplied page numbers and record IDs, recorded signals
and full-page hashes. `page_overlap` identifies exact repeated IDs and page
pointers. Other receipt/page fields, including opaque provider cursors or metadata,
are preserved under `uninterpreted_fields` without claiming support or executing
them. `continuation=NOT_COMPUTED` remains fixed, even if has_more or an opaque cursor
is present. Full hashes bind omitted-under-summary and uninterpreted input fields;
the original input, not reconstructed normalized text, is the replay source.

`source_coverage` groups by exact source label, not independently verified database
identity. It distinguishes planned/missing search IDs, observed indices, internally
reconciled supplied completion assertions and unresolved receipts. Source-level
ASSERTED_ACCOUNTED means only the declared source's supplied accounting reconciles;
source_completeness remains NOT_ESTABLISHED. A missing source receipt has
receipt_stage NOT_SUPPLIED and null enumeration/overlap counts. A supplied empty
receipt has stage SUPPLIED and zero counts. Neither means the database contains
no relevant literature. Sources with no plan keep declared_plan_status NOT_SUPPLIED.

Cross-search overlap uses normalized search record_ids and exact supplied identity
only. Within-source repeated occurrences and cross-source overlap IDs are separate.
Page duplicates or page/search set mismatches remain visible in receipt audits,
not silently merged into a more favorable completeness label. No fuzzy publication
or study identity matching, independent study count or deduplication decision is
made. Record occurrences still feed the existing PRISMA-oriented accounting view.

## Manual replay and scientific limits

To prepare another run, a human must inspect the exact query and unsupported
parameters, choose an authorized provider, validate syntax and scope, provide new
runtime metadata and retain prior inputs. The current mock adapter still needs
explicit fabricated response pages and operator reviews for synthetic testing;
this manifest is not directly executable input to that adapter. There is no live
adapter or new API key/cost workflow here. Changed datasets or provider versions
mean repeating the same query cannot guarantee identical results.

The manifest records protocol and implementation hashes for reproducibility of
**this supplied-data transformation**, not externally reproducible literature
results. Source authenticity, query adequacy, current guideline coverage, citation
followup completion and census remain unestablished. No review decision, clinical
judgment, causal inference or automatic retry is performed. External calls stay 0
and conclusion readiness stays NOT_READY.

For a guided synthetic input workflow, see [receipt intake](RECEIPT_INTAKE.md).
Use a separate empty-search/evidence base; the manifest itself is not executable
input, and existing receipts must not be erased to satisfy intake requirements.
