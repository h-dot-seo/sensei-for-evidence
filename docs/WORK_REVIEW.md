# Guideline/development work review packets

`work_review.py` joins supplied evidence, source/report lineage, clinical-guideline
context, drug-development context and appraisal records around a work package.
This removes a manual cross-ledger lookup; it does **not** automate scientific,
clinical, regulatory or project go/no-go decisions.

## Synthetic workflow

```sh
python work_review.py examples/translation-review.json --work-package WP-TRANSLATION --text
python work_review.py examples/translation-review.json --work-package WP-TRANSLATION
python research_status.py examples/translation-review.json --text
```

The entirely synthetic example deliberately contains unresolved work:

- Two result rows (`e1`, `e2`), one source record, one report and one supplied study ID.
- Guideline context applies to the listed `e1` link only. It preserves the supplied
  population/model limitation, unknown strength/certainty and pending review.
- Development context applies to `e2` only. A recorded review does not change its
  unknown regulatory status or establish a development-stage transition.
- The recorded appraisal covers `e1`; `e2` has no recorded appraisal. This is not
  a judgement that `e2` or its study is poor quality.
- `WP-TRANSLATION` depends on unfinished `WP-MECHANISM`.
- A second planned search is missing at **protocol scope**. It is not automatically
  turned into a work-specific dependency or scientific blocker.

The packet places those statements beside the supplied question, deliverable and
acceptance criterion. It does not infer that a cellular result supports a clinical
recommendation or that a development stage is achieved.

## Packet contract, schema 1

`review_packets(protocol, work_package_id=None)` validates the **whole** protocol
before selecting work. An unknown selector fails. JSON contains canonical input
and implementation hashes, protocol-wide search-plan accounting, fixed readiness
bounds and deterministically ordered packets. No work packages yields an empty
packet list, not generated work or a completion assertion.

Each packet includes:

- Full supplied work-package fields and direct dependency assertions. `blocked_by`
  means unfinished recorded dependencies, not scientific or clinical approval.
- Full linked extraction rows, screening decisions, report mapping and search
  occurrences. Searches join by zero-based `search_index`, not optional search ID.
- Separate result-row, source-record, supplied-study-ID and report counts. They
  count IDs in the input, not independently resolved real-world entities.
- Only contexts explicitly named by that work package. Each context and appraisal
  shows its intersection with the WP evidence IDs and its other linked IDs.
- Full supplied guideline strength/certainty, applicability, limitations, source,
  version and access/review provenance; full supplied development-stage and
  regulatory-status labels. Free-text values are preserved, not interpreted.
- Every intersecting appraisal record, including its method, reviewer, domain
  judgements, source locators and limitations. Different judgements remain separate.
- Work-scoped pending context IDs, missing recorded appraisals and source searches
  with unresolved accounting. These overlap and are not summed into a score.

If reports were not supplied, report fields/counts remain null and the stage is
`NOT_SUPPLIED`. If a plan was not supplied, text says “not supplied,” not zero
missing searches. `NO_CONTEXT_LINKS_SUPPLIED` means only that no contexts were
linked to this WP; it does not diagnose missing clinical or regulatory requirements.

Text output exposes the same core provenance and uncertainty in labelled lines.
Supplied values are JSON-quoted and Unicode control/format/line-separator characters
are escaped, so input text cannot create a fake packet status line. Normal Unicode
text remains readable. `COMPLETE`, reviewed labels and artifact assertions stay
explicitly supplied assertions. Every packet ends with `NO_AUTOMATED_DECISION`. Extraction completeness and
record identity remain `NOT_ESTABLISHED`, even when recorded review gaps are empty.

## Adapter-to-management path

A reviewed mock adapter protocol can be enriched with `gaps`, `contexts`,
`appraisals` and a revised version, as documented in the
[adapter contract](ADAPTER_CONTRACT.md). The work-review command uses the same
validation pipeline, including downstream adapter receipt checks. Relevant mock
candidate source locators, supporting quotes and extractor labels are retained in
the packet, explicitly unverified. Full source text stays in the original protocol
receipt ledger rather than being copied into each packet.

The end-to-end synthetic test exercises mock receipt review → accepted result rows
→ guideline/development context → WP packet. Editing accepted evidence while
retaining stale adapter reviews fails before a packet is produced.

## Reproducibility and boundaries

The input hash covers sorted compact UTF-8 JSON, ignoring object-key order and
retaining list order. Save the original protocol and recorded implementation to
recompute a packet. This is not a signature, reviewer authentication or a new
standalone archive-verification format. The existing research bundle format is
unchanged.

Outputs contain supplied research data and reviewer/source metadata without
redaction. Keep real inputs and generated packets outside this public repository.
The command performs no external retrieval, model call, credential use or upload.
It does not verify guideline currency, source authenticity, study identity,
clinical applicability, scientific adequacy or regulatory compliance. Census stays
`NOT_ESTABLISHED`; conclusion readiness stays `NOT_READY`.

Packets also include [supplied planning assertions](PLANNING_ASSERTIONS.md), their
source-match status and a current basis/hash review target. Stale ranks are retained
as historical assertions but excluded from current-rank groups. No rank is inferred.

[Supplied comparison conditions](EXPERIMENT_CONDITIONS.md) add exact result-linked
model/treatment/comparator and timing metadata. Full intersecting condition rows
participate in review/planning source binding when the ledger is supplied, with
explicit scope for sibling outcomes. No causal validity is inferred.

Source-review packets can precede extraction. They show planned-search/record
inputs and counts separately from results, preserving missing receipts and pending
screening/report states. See [source-review work](SOURCE_REVIEW_WORK.md).

For a revised guideline/development context, [context amendment comparison](CONTEXT_AMENDMENTS.md)
uses the existing compare_runs CLI to connect exact context/result changes to old
and new explicit WP links, without determining clinical or regulatory impact.

Use [prerequisite review](PREREQUISITE_REVIEW.md) with `--work-package ID
--include-prerequisites` to open the selected work plus all explicit transitive
prerequisite packets in dependency-first order. Defaults remain selected-only or
lexical all-work order. This order is not priority or scientific readiness.
