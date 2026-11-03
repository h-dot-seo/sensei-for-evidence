# Synthetic manual search-receipt intake

This CLI closes the gap between a declared query plan and a manually entered
**synthetic mock fixture** for the existing adapter. It provides a deliberately
unfinished template and a diagnostic check, not another search/import engine.
No actual database, paper, private data, model, paid API or credential is accessed.
Real retrieval and scientific validity are not established by this rehearsal.

## Reproduce the entry → review → audit journey

Run from the repository root. Use a separate base with a declared search plan,
empty searches and evidence, and no adapter_receipts. Do not erase completed work
to make a protocol fit. The fixture below is entirely fictional:

```sh
python receipt_intake.py template examples/adapter-protocol.json
python receipt_intake.py check examples/adapter-protocol.json examples/manual-receipt-fixture.json --text
python receipt_intake.py check examples/adapter-protocol.json examples/manual-receipt-fixture.json --protocol-output ../unreviewed-search-candidate.json
python search_manifest.py ../unreviewed-search-candidate.json --text
python prisma_audit.py ../unreviewed-search-candidate.json --text
python review_handoff.py ../unreviewed-search-candidate.json --text
```

The candidate output path must not already exist; choose a new path outside the
public repository. Input files are never changed. `--protocol-output` is optional
and exclusive: an existing file is rejected rather than overwritten. Validation
failure creates no candidate. An I/O failure is reported as an error, not success.
The check normally prints its full JSON result; `--text` gives a concise summary.
Saved protocols are **unreviewed candidates**, never approved search receipts.

Template output goes only to stdout. Save it to a new scratch file if editing;
ordinary shell redirection can overwrite an existing file. Do not paste this
fixture into a real service or treat the placeholder request as an API request.

## Fill source facts, not favorable defaults

The template copies declared search_id/source/query/window exactly. It leaves
provider_id, adapter_version, request IDs, dates, page facts and records null. It
creates no source observations, timestamps, zero-result searches or accept flags.
All modes remain mock; provider labels/version are supplied synthetic metadata.

1. Supply a unique request_id and searched_at for each supplied request. Every
   page's request_id must match that request. Provide unique response_id values
   across all pages and a supplied retrieved_at string. These are assertions,
   not authenticated service receipts or date checks.
2. Supply each actual page number and its ordered record list. Each record needs
   record_id and source_locator; optional title/other metadata can remain supplied
   text. IDs and locators must be internally consistent across the exchange.
   Do not infer identity or merge records from similar titles.
3. For a deliberately empty supplied result page, explicitly use records: [],
   total_count: 0 and has_more: false only if those facts are supplied. Template
   records: null is missing entry, not an empty result. The check rejects it.
4. Preserve actual unknown totals, continuation, truncation, pagination limits
   and error signals. Unknown total_count may stay null; do not invent it. Page
   totals are optional and must agree with exchange totals if asserted; null or
   inconsistent page totals stay visible as unresolved issues. An unknown
   has_more remains unresolved, not false. No cursor or restart point is inferred.
5. Keep repeated IDs on different supplied pages visible: the existing adapter
   preserves page overlap warnings while normalizing its record list. Duplicate
   IDs inside a single page, conflicting locators or invalid structural links
   are rejected. Do not remove overlaps merely to obtain a clean check.
6. For a planned search never supplied, omit its entire response entry from the
   filled fixture while retaining the plan entry. It becomes MISSING. Do not
   manufacture an empty page, clear the plan entry or leave an unfilled template
   exchange and call it a completed search.

The core template does not translate or implement extra plan filters. The original
base retains them; the check's search_manifest lists original_plan_entry and
unsupported_plan_fields. Inspect these and the [search manifest limits](SEARCH_MANIFEST.md)
before any future provider work. Runtime metadata is not a provider-readiness
checklist. The base may contain supplied screening/report assertions, as the
example does; intake preserves and validates these, but makes no new eligibility
decision. Base extraction or existing adapter receipts are never overwritten.

## What checking means

`check` calls the existing `offline_adapter.assemble` with **no reviews**. It requires
extraction_candidates: [] and rejects top-level reviews/review_decisions payloads,
so they cannot be mistaken for approvals. Other opaque nested metadata, even a
field named review_status, does not become an approval. All normalized search
complete flags remain false, the receipt review list stays empty and no evidence
row is promoted. Extraction review remains a separate existing adapter workflow.

- INVALID_INPUT / valid_input false: no candidate is returned or saved. The check
  lists JSON-pointer hints for unfilled required fields and the canonical adapter
  validation error. Hints are entry aids, not a replacement schema validator or
  exhaustive error list; malformed nonblank values may appear only in the error.
- UNREVIEWED_SUPPLIED_CANDIDATES / valid_input true: structural assembly succeeded,
  **not** receipt acceptance or complete research. review_pending gives existing
  receipt review targets. Do not copy their hashes as approval without reviewing.
  Completion-not-asserted, missing searches, page overlap, unknown totals and
  interruption signals remain visible in search_manifest. Full record/report
  accounting is exposed through prisma_audit.

The fictional filled example deliberately contains page overlap, an interrupted
last page and a missing secondary search. It passes structural entry checking but
stays unreviewed/incomplete. This distinction is intentional. Receipt normalization,
count/page rules, source hashing and PRISMA bookkeeping use the existing engines;
intake never loosens those rules or accepts an operator decision.

Invalid-input diagnostic reports exit 1, even though they produce JSON/text on
stdout. Invalid JSON/unreadable files and output I/O failures use a nonzero exit
with stderr instead. Valid candidate checks exit 0 despite unresolved review
queues; callers must not interpret exit 0 as source completeness. No candidate is
printed as approved and no live-mode call is supported.

## Audit and reproducibility boundaries

Check JSON includes base/fixture hashes, implementation hashes, the unreviewed
candidate, source manifest and PRISMA-oriented audit. Original protocol/fixture
bytes stay unchanged. A saved candidate can be fed to existing status/handoff/audit
and bundle commands, but a verified bundle still establishes only internal hashes
and deterministic derivation. Supplied record/report/study IDs, source locators,
provider labels and eligibility assertions remain unverified.

The [operator handoff](OPERATOR_HANDOFF.md) links this workflow separately with a
BASE_PROTOCOL.json placeholder, never as an instruction to erase the current
research protocol. Actual source retrieval, permissions, human source reading,
eligibility/extraction, receipt review, appraisal and scientific interpretation
remain manual or unimplemented. External calls stay 0, census stays
NOT_ESTABLISHED, and conclusion readiness stays NOT_READY.

A candidate with evidence=[] can now have [source-review work packages](SOURCE_REVIEW_WORK.md)
for declared searches or enumerated records. Add them explicitly under gaps after
entry; no fake extraction IDs or automatic scientific work plans are needed.
Receipt checking does not generate or complete those work packages.
