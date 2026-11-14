# Find the shape and verification path for a retained record

This is a navigation index, not a JSON Schema, file detector or verifier. Start with
the recorded `kind`, `target_type` or `mode` below. A matching string does not prove
the rest of the document is valid. The linked guide supplies the actual command,
required original inputs and human-review fields. Never invoke `verify` on a target
just because its producer also has a verify subcommand: application verification
usually requires the original protocol and the complete application, not its nested target.

1. Preserve the original bytes and original protocol, wrappers and supplied reviews.
2. Find the exact marker and its guide below; `target_type` may be nested, not top-level.
3. Check the recorded implementation using [implementation inspection](IMPLEMENTATION_REVISIONS.md).
   Matching names, versions or hashes alone do not verify derivation or authenticate data.
4. Use the matching trusted implementation and the guide's verifier with all required
   inputs. No command is selected or run by this index. Old hashes must not be edited
   to make a newer implementation accept them.

## Compatibility boundaries

`schema_version` is scoped to its own object, not a global protocol version. The
protocol's free-text `version` is a supplied label, not a schema selector. Some nested
review targets have no schema version of their own; the table explicitly says so.
Targets, blank worksheets, previews and mock receipts do not constitute approval.

Current readers enforce their actual Python contracts, often exact fields and versions,
and replay against recorded implementation bytes. Same-version records are not promised
to work after those bytes change. Adding a field may break an exact-field reader;
there is no generic optional-field guarantee, N-1 reader, automatic migration or
`schema_migration` marker. Do not rewrite retained records. Rebuild from preserved
inputs with newly supplied reviews where the actual workflow requires them. The
research bundle schema-1 prototype must be rebuilt; current research bundles use 2.
Document a shape/version change explicitly in VALIDATION.md and its chronological
history; this index describes current shapes, not a new compatibility guarantee.

The [three authored-document schemas](SCHEMAS.md) help before collection review.
They do not cover a whole protocol or these 76 tagged constructors. Python validation,
exact target binding and explicit human decisions remain authoritative. Names-only
[protocol inspection](PROTOCOL_KEYS.md) is separate and neither rejects nor corrects keys.

## Untagged research archive

The ordinary research ZIP's `manifest.json` has no kind/mode/target_type marker.
`research_bundle.py:build_bundle` produces schema_version 2 with `engine_sha256` and
`input_sha256`; see [research bundle create/verify](USAGE.md#portable-offline-research-bundle).
Do not infer this type from version 2 alone. Collection and transition ZIPs below have
their own manifests; segment entries are not independent archives.

## Tagged stored shapes

| Discriminator value | Object version | Role | Producer function | Shape and command guide |
|---|---|---|---|---|
| `target_type=search` | 1 | review_target | `adapter_integrity.py:prepare_exchange` | [Guide](ADAPTER_CONTRACT.md) |
| `target_type=extraction` | 1 | review_target | `adapter_integrity.py:prepare_exchange` | [Guide](ADAPTER_CONTRACT.md) |
| `target_type=manual_appraisal_intake` | 1 | review_target | `appraisal_intake.py:_prepare` | [Guide](MANUAL_APPRAISAL_INTAKE.md) |
| `kind=detached_appraisal_intake` | 1 | detached_application | `appraisal_intake.py:assemble` | [Guide](MANUAL_APPRAISAL_INTAKE.md) |
| `kind=detached_appraisal_source_review` | 1 | detached_application | `appraisal_source_review.py:review` | [Guide](APPRAISAL_SOURCE_REVIEW.md) |
| `mode=explicit_appraisal_transition_segment` | 1 | bundle_segment | `appraisal_transition_bundle.py:build_bundle` | [Guide](APPRAISAL_TRANSITION_BUNDLES.md) |
| `mode=explicit_appraisal_transition_bundle` | 1 | bundle_manifest | `appraisal_transition_bundle.py:build_bundle` | [Guide](APPRAISAL_TRANSITION_BUNDLES.md) |
| `mode=explicit_nbib_batch_collection_bundle` | 1 | bundle_manifest | `batch_collection_bundle.py:build_bundle` | [Guide](BATCH_COLLECTION_BUNDLES.md) |
| `mode=local_export` | 1 | prepared_or_retained_record | `bibliographic_intake.py:prepare` | [Guide](BIBLIOGRAPHIC_INTAKE.md) |
| `target_type=bibliographic_export` | none on this object | review_target | `bibliographic_intake.py:prepare` | [Guide](BIBLIOGRAPHIC_INTAKE.md) |
| `target_type=bibliographic_reconciliation` | 1 | review_target | `bibliographic_integrity.py:reconciliation_target` | [Guide](BIBLIOGRAPHIC_REVIEW.md) |
| `target_type=manual_challenge_intake` | 1 | review_target | `challenge_intake.py:_prepare` | [Guide](INDEPENDENT_CHALLENGE.md) |
| `kind=detached_challenge_intake` | 1 | detached_application | `challenge_intake.py:assemble` | [Guide](INDEPENDENT_CHALLENGE.md) |
| `mode=explicit_native_collection_bundle` | 1 | bundle_manifest | `collection_bundle.py:build_bundle` | [Guide](COLLECTION_BUNDLES.md) |
| `target_type=manual_condition_intake` | 1 | review_target | `condition_intake.py:_prepare` | [Guide](MANUAL_CONDITION_INTAKE.md) |
| `kind=detached_condition_intake` | 1 | detached_application | `condition_intake.py:assemble` | [Guide](MANUAL_CONDITION_INTAKE.md) |
| `target_type=manual_context_intake` | 1 | review_target | `context_intake.py:_prepare` | [Guide](MANUAL_CONTEXT_INTAKE.md) |
| `kind=detached_context_intake` | 1 | detached_application | `context_intake.py:assemble` | [Guide](MANUAL_CONTEXT_INTAKE.md) |
| `target_type=manual_evidence_work_intake` | 1 | review_target | `evidence_work_intake.py:_prepare` | [Guide](EVIDENCE_WORK_INTAKE.md) |
| `kind=detached_evidence_work_intake` | 1 | detached_application | `evidence_work_intake.py:assemble` | [Guide](EVIDENCE_WORK_INTAKE.md) |
| `mode=explicit_extraction_transition_segment` | 1 | bundle_segment | `extraction_transition_bundle.py:build_bundle` | [Guide](EXTRACTION_TRANSITION_BUNDLES.md) |
| `mode=explicit_extraction_transition_bundle` | 1 | bundle_manifest | `extraction_transition_bundle.py:build_bundle` | [Guide](EXTRACTION_TRANSITION_BUNDLES.md) |
| `target_type=descriptive_inventory_intake` | 1 | review_target | `inventory_intake.py:_prepare` | [Guide](MANUAL_INVENTORY_INTAKE.md) |
| `kind=detached_inventory_intake` | 1 | detached_application | `inventory_intake.py:assemble` | [Guide](MANUAL_INVENTORY_INTAKE.md) |
| `mode=explicit_typed_native_collection_bundle` | 1 | bundle_manifest | `native_collection_bundle.py:build_bundle` | [Guide](NATIVE_COLLECTION_BUNDLES.md) |
| `mode=local_nbib_batch_preparation` | 1 | prepared_or_retained_record | `nbib_batch_intake.py:prepare` | [Guide](PUBMED_NBIB_BATCH.md) |
| `target_type=nbib_batch_preparation` | none on this object | review_target | `nbib_batch_intake.py:prepare` | [Guide](PUBMED_NBIB_BATCH.md) |
| `mode=local_nbib_preparation` | 1 | prepared_or_retained_record | `nbib_intake.py:prepare` | [Guide](PUBMED_NBIB_INTAKE.md) |
| `target_type=nbib_preparation` | none on this object | review_target | `nbib_intake.py:prepare` | [Guide](PUBMED_NBIB_INTAKE.md) |
| `mode=pubmed_discovery_preview` | 1 | prepared_or_retained_record | `pubmed_discovery.py:preview` | [Guide](PUBMED_DISCOVERY.md) |
| `mode=pubmed_discovery` | 1 | prepared_or_retained_record | `pubmed_discovery.py:from_responses` | [Guide](PUBMED_DISCOVERY.md) |
| `mode=pubmed_metadata_preview` | 1 | prepared_or_retained_record | `pubmed_metadata.py:preview` | [Guide](PUBMED_METADATA.md) |
| `mode=pubmed_metadata` | 1 | prepared_or_retained_record | `pubmed_metadata.py:from_responses` | [Guide](PUBMED_METADATA.md) |
| `target_type=manual_readiness_intake` | 1 | review_target | `readiness_intake.py:_prepare` | [Guide](CONCLUSION_READINESS.md) |
| `kind=detached_readiness_intake` | 1 | detached_application | `readiness_intake.py:assemble` | [Guide](CONCLUSION_READINESS.md) |
| `mode=mock` | 1 | prepared_or_retained_record | `receipt_intake.py:template` | [Guide](RECEIPT_INTAKE.md) |
| `target_type=report_decision` | 1 | review_target | `report_decision.py:_target` | [Guide](REPORT_DECISIONS.md) |
| `kind=detached_report_decision` | 1 | detached_application | `report_decision.py:assemble` | [Guide](REPORT_DECISIONS.md) |
| `target_type=manual_report_intake` | 1 | review_target | `report_intake.py:_prepare` | [Guide](MANUAL_REPORT_INTAKE.md) |
| `kind=detached_report_intake` | 1 | detached_application | `report_intake.py:assemble` | [Guide](MANUAL_REPORT_INTAKE.md) |
| `target_type=manual_report_retrieval_update` | 1 | review_target | `report_retrieval.py:_prepare` | [Guide](REPORT_RETRIEVAL_UPDATES.md) |
| `kind=detached_report_retrieval_update` | 1 | detached_application | `report_retrieval.py:assemble` | [Guide](REPORT_RETRIEVAL_UPDATES.md) |
| `target_type=report_review_positions_intake` | 1 | review_target | `report_review_intake.py:_prepare` | [Guide](REPORT_REVIEW_INTAKE.md) |
| `kind=detached_report_review_positions_intake` | 1 | detached_application | `report_review_intake.py:assemble` | [Guide](REPORT_REVIEW_INTAKE.md) |
| `target_type=report_source_declaration_intake` | 1 | review_target | `report_source_intake.py:_prepare` | [Guide](MANUAL_SOURCE_DECLARATIONS.md) |
| `kind=detached_report_source_intake` | 1 | detached_application | `report_source_intake.py:assemble` | [Guide](MANUAL_SOURCE_DECLARATIONS.md) |
| `target_type=report_study_inventory_review_positions_intake` | 1 | review_target | `report_study_inventory_review_intake.py:_prepare` | [Guide](REPORT_STUDY_INVENTORY_REVIEW_INTAKE.md) |
| `kind=detached_report_study_inventory_review_positions_intake` | 1 | detached_application | `report_study_inventory_review_intake.py:assemble` | [Guide](REPORT_STUDY_INVENTORY_REVIEW_INTAKE.md) |
| `target_type=report_study_review_positions_intake` | 1 | review_target | `report_study_review_intake.py:_prepare` | [Guide](REPORT_STUDY_REVIEW_INTAKE.md) |
| `kind=detached_report_study_review_positions_intake` | 1 | detached_application | `report_study_review_intake.py:assemble` | [Guide](REPORT_STUDY_REVIEW_INTAKE.md) |
| `mode=explicit_report_transition_segment` | 1 | bundle_segment | `report_transition_bundle.py:build_bundle` | [Guide](REPORT_TRANSITION_BUNDLES.md) |
| `mode=explicit_report_transition_bundle` | 1 | bundle_manifest | `report_transition_bundle.py:build_bundle` | [Guide](REPORT_TRANSITION_BUNDLES.md) |
| `target_type=manual_result_correction` | 1 | review_target | `result_correction.py:_prepare` | [Guide](RESULT_CORRECTIONS.md) |
| `kind=detached_result_correction` | 1 | detached_application | `result_correction.py:assemble` | [Guide](RESULT_CORRECTIONS.md) |
| `kind=manual_result_extraction_worksheet` | 1 | worksheet | `result_extraction.py:worksheet` | [Guide](EXTRACTION_WORKSHEETS.md) |
| `target_type=manual_result_intake` | 1 | review_target | `result_intake.py:_prepare` | [Guide](MANUAL_RESULT_INTAKE.md) |
| `kind=detached_result_intake` | 1 | detached_application | `result_intake.py:assemble` | [Guide](MANUAL_RESULT_INTAKE.md) |
| `kind=detached_result_source_review` | 1 | detached_application | `result_source_review.py:review` | [Guide](RESULT_SOURCE_REVIEW.md) |
| `target_type=ris_continuation_preparation` | none on this object | review_target | `ris_continuation_intake.py:prepare` | [Guide](RIS_CONTINUATION_INTAKE.md) |
| `mode=local_ris_preparation` | 1 | prepared_or_retained_record | `ris_intake.py:prepare` | [Guide](RIS_INTAKE.md) |
| `target_type=ris_preparation` | none on this object | review_target | `ris_intake.py:prepare` | [Guide](RIS_INTAKE.md) |
| `target_type=screening_decision_batch_preview` | 1 | review_target | `screening_decision_batch.py:_simulate` | [Guide](SCREENING_DECISION_BATCH_PREVIEW.md) |
| `kind=detached_reviewed_screening_decision_batch` | 1 | detached_application | `screening_decision_batch_apply.py:assemble` | [Guide](SCREENING_DECISION_BATCH_APPLICATION.md) |
| `target_type=screening_decision` | 1 | review_target | `screening_decision_links.py:prepare_target` | [Guide](SCREENING_DECISIONS.md) |
| `target_type=screening_position_csv_intake` | 1 | review_target | `screening_position_intake.py:_prepare` | [Guide](SCREENING_POSITION_INTAKE.md) |
| `kind=detached_screening_position_csv` | 1 | detached_application | `screening_position_intake.py:assemble` | [Guide](SCREENING_POSITION_INTAKE.md) |
| `target_type=screening_sheet_positions_intake` | 1 | review_target | `screening_sheet_intake.py:_prepare` | [Guide](SCREENING_SHEET_INTAKE.md) |
| `kind=detached_screening_sheet_positions` | 1 | detached_application | `screening_sheet_intake.py:assemble` | [Guide](SCREENING_SHEET_INTAKE.md) |
| `target_type=manual_source_work_intake` | 1 | review_target | `source_work_intake.py:_prepare` | [Guide](SOURCE_WORK_INTAKE.md) |
| `kind=detached_source_work_intake` | 1 | detached_application | `source_work_intake.py:assemble` | [Guide](SOURCE_WORK_INTAKE.md) |
| `target_type=manual_work_completion_intake` | 1 | review_target | `work_completion_intake.py:_prepare` | [Guide](WORK_COMPLETION_INTAKE.md) |
| `kind=detached_work_completion_intake` | 1 | detached_application | `work_completion_intake.py:assemble` | [Guide](WORK_COMPLETION_INTAKE.md) |
| `target_type=manual_work_context_assignment` | 1 | review_target | `work_context_intake.py:_prepare` | [Guide](WORK_CONTEXT_INTAKE.md) |
| `kind=detached_work_context_intake` | 1 | detached_application | `work_context_intake.py:assemble` | [Guide](WORK_CONTEXT_INTAKE.md) |
| `mode=explicit_work_transition_segment` | 1 | bundle_segment | `work_transition_bundle.py:build_bundle` | [Guide](WORK_TRANSITION_BUNDLES.md) |
| `mode=explicit_work_transition_bundle` | 1 | bundle_manifest | `work_transition_bundle.py:build_bundle` | [Guide](WORK_TRANSITION_BUNDLES.md) |

## Machine-readable index and coverage

[record_registry.json](record_registry.json) is the explicit companion registry.
Each row names a source module/function, literal discriminator, the version on that
same constructor, its role and guide. `constructor_bindings` lists only direct
constructor keys ending in `_sha256` plus `review_target`; it is not a complete
recursive list of binding requirements. Read the linked guide and validator.

The drift test compares every root-module literal `dict(...)` or dictionary-literal
kind/target_type/mode constructor in both directions, with explicit exclusions.
It also checks the untagged research manifest and guide/CLI navigation. Existing ** expansion expressions are explicitly inventoried as `constructor_expansions`;
new or changed expressions require registry review. Their returned fields are not
inferred or included in the direct binding list. It parses
source only and never imports or executes the research engines. Variables, mutated
objects and dynamically composed tags are not inferred; this is not proof of all
possible runtime shapes. It indexes these constructor identities, not every way an
artifact can reach one of them. Plain candidate/reference/review forms without a
marker, other untagged documents and one-off status/output schemas are not enumerated.
The authored-schema guide and individual intake guides cover some, not all, of them.

Excluded literal markers are explicitly recorded: the three receipt authoring hints,
the implementation diagnostic, and the two blank-screening-sheet export receipts.
The CSVs those receipts describe still require their separate supplied-review flows.
This does not say excluded outputs can never be saved; they are not indexed as
replayable research inputs here. New kinds and moved constructors require explicit
registry review rather than silent automatic catalogue expansion.

No network access, cross-repository compatibility, scientific assessment or automatic
acceptance is established. Canonical decisions and census/readiness claims are unchanged.
