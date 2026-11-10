# Command reference

Every script and subcommand in this repository, with the exact usage line its parser
prints for `--help`, a one-line purpose and the guide that documents it. Run commands
from the repository root with Python 3.10+ and the standard library only. The
narratives grouped by workflow stage are in [WORKFLOWS.md](WORKFLOWS.md); field
requirements, strict JSON rules, ID migration, stage definitions and compatibility are
in [detailed usage](USAGE.md); the [operator handoff](OPERATOR_HANDOFF.md) shows the
same supplied-input routes as parser-help entry points without executing them.

Layout: the command-line scripts and the engine modules they import are flat modules at
the repository root, so every command below runs as `python <script>.py ...` from there;
the synthetic test suite is the `tests/` package. `python sensei.py list` prints the same
scripts and the operator-handoff routes, and `python sensei.py run <script> ...` runs one
of them without changing its arguments, output or exit status.

Shared conventions:

- Inputs are supplied JSON protocols, candidate documents or explicitly authorized local
  export files. Outputs are bookkeeping over supplied data, never a scientific judgement,
  an authentication of a source or reviewer, or a generated conclusion.
- Output options create a new file and refuse an existing path. Stdout is a report, not
  a saved protocol, unless `--output` or `--protocol-output` is given. Keep real research
  inputs and generated outputs, including bundles, outside this public repository.
- `--text` prints a quoted, read-only summary; JSON is the default output.
- No tool calls a model. Only the explicitly invoked `pubmed_discovery.py fetch` and
  `pubmed_metadata.py fetch` subcommands make a network request, and only after an exact
  preview-hash check.
- Census stays `NOT_ESTABLISHED` and the mechanical conclusion readiness stays
  `NOT_READY` in every output.
- Existing bundles require their recorded implementation bytes for verification.
  Comparison hashes ignore object key order but retain list order; exact-input bundle
  hashes preserve original bytes. Neither kind of hash is a signature.

Intake tools share four steps. `template` drafts a blank candidate document bound to the
current protocol context and leaves every human field null; `target` binds the completed
candidates to the exact current protocol and writes the review target; `assemble`
applies the separately supplied review to that target and writes a detached application
record; `verify` replays the application against the original protocol and, with
`--protocol-output`, exports the resulting protocol. No blank is interpreted as agreement,
and no step fills a decision, judgement or label on your behalf.

## Dispatcher

| Usage | Purpose | Guide |
|---|---|---|
| `python sensei.py [-h] {list,run,check} ...` | Discover and run the root scripts from one entry point; the documented `python <script>` form stays the primary one | [Commands at a glance](../README.md#commands-at-a-glance) |
| `python sensei.py check [-h]` | Read-only listed-byte inventory, in-memory syntax compilation and one synthetic status; no bytecode writes, not full tests, CI or research validation | [Checkout check](CHECKOUT_CHECK.md) |
| `python sensei.py list [-h]` | Print every root script that has a main entry point with the first sentence of its docstring, then the supplied-input routes of the operator handoff catalog with their scripts and guides; nothing is executed and only this repository's own files are read | [Operator handoff](OPERATOR_HANDOFF.md) |
| `python sensei.py run [-h] script ...` | Execute one listed root script with the remaining arguments exactly as `python <script> ...` would, without a shell; any other name is rejected before anything runs, and the script keeps its own output, exit status and boundaries | this reference |

## Start, status and navigation

| Usage | Purpose | Guide |
|---|---|---|
| `python review_handoff.py [-h] [--work-package WORK_PACKAGE] [--text] protocol` | Read-only operator sheet: manual queues, input locations, work deliverables, detailed-view navigation and the static supplied-input workflow catalog | [Operator handoff](OPERATOR_HANDOFF.md) |
| `python research_status.py [-h] [--text] protocol` | View mechanical review queues and unknown stages | [Concise research status](USAGE.md#concise-research-status) |
| `python views_export.py [-h] {status,flow,records} ...` | Discover detached status Markdown, supplied-accounting Mermaid text and records CSV; no renderer or scientific judgement | [Shareable status](SHAREABLE_VIEWS.md) |
| `python views_export.py records [-h] --output NEW_CSV [--text] protocol` | Save existing record joins as detached CSV with a separate receipt | [Records CSV](RECORDS_CSV.md) |
| `python views_export.py status [-h] --output NEW_MD [--text] protocol` | Write a new read-only status Markdown file preserving every status field/queue; stdout is only a JSON or quoted receipt | [Shareable status](SHAREABLE_VIEWS.md) |
| `python views_export.py flow [-h] [--format {mermaid}] --output NEW_MMD [--text] protocol` | Write a new supplied-accounting flow text file from existing audit partitions; no official diagram or renderer | [Accounting flow](ACCOUNTING_FLOW.md) |
| `python evidence_workflow.py [-h] protocol` | Reconcile search, screening, results, context, appraisal and work | [Search-to-work-package workflow](USAGE.md#search-to-work-package-workflow) |
| `python prisma_reports.py [-h] protocol` | Add report/full-text/study and extraction-queue accounting | [Report retrieval and full-text screening](USAGE.md#report-retrieval-and-full-text-screening) |
| `python validate_run.py [-h] state` | Validate selected state/release consistency rules | [Quick start](USAGE.md#quick-start), [validator boundary](ARCHITECTURE.md#validator-boundary) |
| `python search_manifest.py [-h] [--text] protocol` | Freeze exact query specs and source-wise receipt, interruption and overlap accounting without executing searches | [Search manifest](SEARCH_MANIFEST.md) |
| `python prisma_audit.py [-h] [--text] protocol` | Export unit-specific members, exclusion reasons, identity links and supplied-count partitions | [PRISMA audit](PRISMA_AUDIT.md) |
| `python prisma_flow_template.py [-h] [--search-arm INDEX=ARM] [--include-exact-id-accounting] --output OUTPUT [--text] protocol` | Write a new native count-crosswalk CSV with explicit search-arm assignments and a full mapping/pending-state receipt; not an external diagram template | [Native count crosswalk](PRISMA_FLOW_TEMPLATE.md) |
| `python synthesis_review.py [-h] [--text] protocol` | Review stage counts, supplied statement citations and unresolved limits | [Synthesis review](SYNTHESIS_REVIEW.md) |
| `python work_review.py [-h] [--work-package WORK_PACKAGE] [--include-prerequisites] [--text \| --brief] protocol` | Join evidence/context/uncertainty around a work deliverable; `--include-prerequisites` opens the transitive prerequisites, `--brief` compacts the packet view | [Work review](WORK_REVIEW.md), [prerequisite review](PREREQUISITE_REVIEW.md), [work navigation](WORK_NAVIGATION.md) |
| `python compare_runs.py [-h] [--amendment AMENDMENT] [--text] before after` | Show mechanical input/ledger changes, explicit report-study migrations, completion-source differences and version warnings; `--amendment` binds a supplied amendment note | [Run-to-run comparison](USAGE.md#offline-run-to-run-comparison), [amendment notes](AMENDMENT_NOTES.md), [context amendments](CONTEXT_AMENDMENTS.md), [completion comparison](COMPLETION_COMPARISON.md) |

## Search receipts and the mock adapter

| Usage | Purpose | Guide |
|---|---|---|
| `python receipt_intake.py template [-h] protocol` | Guide synthetic manual receipt entry with deliberately unfilled request/page fields | [Receipt intake](RECEIPT_INTAKE.md) |
| `python receipt_intake.py check [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol fixture` | Inspect a filled mock receipt fixture as unreviewed candidates through the existing adapter, without accepting reviews | [Receipt intake](RECEIPT_INTAKE.md) |
| `python offline_adapter.py [-h] [--reviews REVIEWS] [--protocol-output PROTOCOL_OUTPUT] protocol fixture` | Run the synthetic adapter contract and hash-bound review gates offline | [Adapter contract](ADAPTER_CONTRACT.md) |

## Supplied citation files and collection review

| Usage | Purpose | Guide |
|---|---|---|
| `python bibliographic_intake.py preview [-h] --search-id SEARCH_ID --searched-at SEARCHED_AT [--id-column ID_COLUMN] [--locator-column LOCATOR_COLUMN] [--output OUTPUT] [--text] protocol export` | Retain exact local CSV bytes with an explicit search-plan association as a detached, unreviewed artifact | [Bibliographic intake](BIBLIOGRAPHIC_INTAKE.md) |
| `python bibliographic_intake.py verify [-h] [--text] artifact` | Re-check the artifact's byte consistency and inspect its detached unreviewed candidates | [Bibliographic intake](BIBLIOGRAPHIC_INTAKE.md) |
| `python nbib_intake.py preview [-h] --search-id SEARCH_ID --searched-at SEARCHED_AT [--output OUTPUT] [--text] protocol export` | Preserve native PubMed-format field occurrences and exact bytes in a strict-subset NBIB wrapper | [PubMed NBIB intake](PUBMED_NBIB_INTAKE.md) |
| `python nbib_intake.py verify [-h] [--intake-output INTAKE_OUTPUT \| --csv-output CSV_OUTPUT] [--text] artifact` | Verify the wrapper and write either the CSV derivative or the unreviewed intake artifact for explicit reconciliation | [PubMed NBIB intake](PUBMED_NBIB_INTAKE.md) |
| `python nbib_batch_intake.py preview [-h] --export EXPORT --search-id SEARCH_ID --searched-at SEARCHED_AT [--output OUTPUT] [--text] protocol` | Preserve each explicitly grouped native file (`--export ID=PATH`, repeatable) for one incomplete search | [PubMed NBIB batch](PUBMED_NBIB_BATCH.md) |
| `python nbib_batch_intake.py verify [-h] [--intake-output INTAKE_OUTPUT \| --csv-output CSV_OUTPUT] [--text] artifact` | Verify the batch wrapper and prepare one unreviewed CSV intake for the grouped files | [PubMed NBIB batch](PUBMED_NBIB_BATCH.md) |
| `python ris_intake.py preview [-h] --search-id SEARCH_ID --searched-at SEARCHED_AT [--output OUTPUT] [--text] protocol export` | Preserve strict-subset native RIS bytes and field occurrences without DOI/ID resolution | [RIS intake](RIS_INTAKE.md) |
| `python ris_intake.py verify [-h] [--intake-output INTAKE_OUTPUT \| --csv-output CSV_OUTPUT] [--text] artifact` | Verify the RIS wrapper and prepare CSV candidates for the same human reconciliation path | [RIS intake](RIS_INTAKE.md) |
| `python bibliographic_review.py template [-h] [--review-output REVIEW_OUTPUT] [--text] artifact` | Draft blank per-row identity/withholding choices for a prepared intake artifact | [Bibliographic review](BIBLIOGRAPHIC_REVIEW.md) |
| `python bibliographic_review.py target [-h] [--text] [--review-output REVIEW_OUTPUT] protocol artifact review_document` | Bind the completed row choices to the exact protocol and artifact and write the review target | [Bibliographic review](BIBLIOGRAPHIC_REVIEW.md) |
| `python bibliographic_review.py assemble [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol artifact review_document` | Apply the supplied review to the append-only incomplete search and export the resulting protocol; no eligibility decision is made | [Bibliographic review](BIBLIOGRAPHIC_REVIEW.md) |

## Optional live PubMed clients

| Usage | Purpose | Guide |
|---|---|---|
| `python pubmed_discovery.py preview [-h] [--output OUTPUT] input` | Freeze the exact ESearch request offline and compute the preview hash | [PubMed discovery](PUBMED_DISCOVERY.md) |
| `python pubmed_discovery.py fetch [-h] --preview-sha256 PREVIEW_SHA256 --output OUTPUT input` | Transmit the previewed query to NCBI ESearch (the only networked discovery step) and retain native observations with caps and failures | [PubMed discovery](PUBMED_DISCOVERY.md) |
| `python pubmed_discovery.py from-responses [-h] --output OUTPUT input execution` | Replay retained response bodies offline into the same discovery record shape | [PubMed discovery](PUBMED_DISCOVERY.md) |
| `python pubmed_discovery.py verify [-h] input` | Re-check a discovery record's internal consistency | [PubMed discovery](PUBMED_DISCOVERY.md) |
| `python pubmed_discovery.py to-intake [-h] --search-id SEARCH_ID --output OUTPUT input protocol` | Convert discovered identifiers into an unreviewed CSV intake for a declared search | [PubMed discovery](PUBMED_DISCOVERY.md) |
| `python pubmed_metadata.py preview [-h] [--output OUTPUT] input selection` | Freeze an explicit PMID selection from a verified discovery and compute the preview hash | [PubMed metadata](PUBMED_METADATA.md) |
| `python pubmed_metadata.py fetch [-h] --preview-sha256 PREVIEW_SHA256 --output OUTPUT input selection` | Send the previewed PMID batches to NCBI EFetch (the only networked metadata step) and retain MEDLINE text | [PubMed metadata](PUBMED_METADATA.md) |
| `python pubmed_metadata.py from-responses [-h] --output OUTPUT input selection execution` | Replay retained EFetch responses offline into the same metadata record shape | [PubMed metadata](PUBMED_METADATA.md) |
| `python pubmed_metadata.py verify [-h] input` | Re-check a metadata record's internal consistency and literal PMID reconciliation | [PubMed metadata](PUBMED_METADATA.md) |
| `python pubmed_metadata.py to-intake [-h] --search-id SEARCH_ID --output OUTPUT input protocol` | Convert title/abstract candidates into an unreviewed CSV intake for a declared search | [PubMed metadata](PUBMED_METADATA.md) |

## Screening

| Usage | Purpose | Guide |
|---|---|---|
| `python screening_review.py [-h] [--record-id RECORD_ID] [--template] [--text] [--output OUTPUT] protocol` | Inspect source-bound supplied reviewer positions or prepare blank assertions without deciding eligibility | [Screening reviews](SCREENING_REVIEWS.md) |
| `python screening_decision.py target [-h] [--text] --record-id RECORD_ID [--output OUTPUT] protocol` | Prepare the exact-context target for one explicit record's supplied screening choice | [Screening decisions](SCREENING_DECISIONS.md) |
| `python screening_decision.py assemble [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol decision_document` | Apply only the explicit supplied choice to a new protocol candidate, retaining source/reviewer receipts | [Screening decisions](SCREENING_DECISIONS.md) |
| `python screening_decision.py inspect [-h] [--text] [--record-id RECORD_ID] protocol` | Inspect retained decision receipts without selecting an authoritative one | [Screening decisions](SCREENING_DECISIONS.md) |

## Reports, retrieval and full text

| Usage | Purpose | Guide |
|---|---|---|
| `python report_intake.py template [-h] [--text] [--output OUTPUT] protocol reference_document` | Draft blank report rows for explicitly selected included, unmapped records | [Manual report intake](MANUAL_REPORT_INTAKE.md) |
| `python report_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind completed report registrations to the current protocol for separate review | [Manual report intake](MANUAL_REPORT_INTAKE.md) |
| `python report_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied registration review as a detached application | [Manual report intake](MANUAL_REPORT_INTAKE.md) |
| `python report_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the registration; new reports keep pending full-text decisions | [Manual report intake](MANUAL_REPORT_INTAKE.md) |
| `python report_retrieval.py template [-h] [--text] [--output OUTPUT] protocol reference_document` | Draft a retrieval-state transition for explicitly selected unassessed reports | [Report retrieval updates](REPORT_RETRIEVAL_UPDATES.md) |
| `python report_retrieval.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the supplied transitions to the current protocol for exact-target review | [Report retrieval updates](REPORT_RETRIEVAL_UPDATES.md) |
| `python report_retrieval.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied retrieval review as a detached application | [Report retrieval updates](REPORT_RETRIEVAL_UPDATES.md) |
| `python report_retrieval.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the retrieval update without remapping records, replacing sources or renewing reviews | [Report retrieval updates](REPORT_RETRIEVAL_UPDATES.md) |
| `python report_source_intake.py template [-h] [--text] --report-id REPORT_ID --candidate-output CANDIDATE_OUTPUT protocol` | Draft a blank source declaration for one retrieved report | [Manual source declarations](MANUAL_SOURCE_DECLARATIONS.md) |
| `python report_source_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the new declarations to the current protocol for exact-input review | [Manual source declarations](MANUAL_SOURCE_DECLARATIONS.md) |
| `python report_source_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied import review as a detached application | [Manual source declarations](MANUAL_SOURCE_DECLARATIONS.md) |
| `python report_source_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the declaration append, preserving prior catalogs and exposing stale reviews without byte verification | [Manual source declarations](MANUAL_SOURCE_DECLARATIONS.md) |
| `python report_source_check.py template [-h] [--source-id SOURCE_ID] [--output OUTPUT] [--text] protocol` | Draft the explicit source-to-local-file manifest for a supplied digest | [Report source check](REPORT_SOURCE_CHECK.md) |
| `python report_source_check.py check [-h] --root ROOT [--output OUTPUT] [--text] protocol manifest` | Compare an explicitly mapped local document with its supplied digest through a bounded no-follow checker; native Windows fails closed | [Report source check](REPORT_SOURCE_CHECK.md) |
| `python report_review.py [-h] [--report-id REPORT_ID] [--template] [--text] [--output OUTPUT] protocol` | Inspect supplied full-text versions and reviewer positions without verifying documents or changing decisions | [Report reviews](REPORT_REVIEWS.md) |
| `python report_decision.py target [-h] [--text] --report-id REPORT_ID [--output OUTPUT] protocol` | Prepare the exact-context target for one retrieved report's supplied full-text choice | [Report decisions](REPORT_DECISIONS.md) |
| `python report_decision.py assemble [-h] [--text] [--output OUTPUT] protocol decision_document` | Apply the supplied include/exclude choice and study declaration to a detached candidate | [Report decisions](REPORT_DECISIONS.md) |
| `python report_decision.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the decision against the original input before exporting the protocol; conflicting result links are rejected, not deleted | [Report decisions](REPORT_DECISIONS.md) |
| `python report_study_review.py [-h] [--report-id REPORT_ID] [--study-id STUDY_ID] [--template] [--text] [--output OUTPUT] protocol` | Keep exact report-study human positions and explicit reviewed-source selections separate from report eligibility | [Report-study reviews](REPORT_STUDY_REVIEWS.md) |
| `python report_study_inventory.py [-h] [--report-id REPORT_ID] [--study-id STUDY_ID] [--template] [--text] [--output OUTPUT] protocol` | Describe explicit candidate studies before full-text inclusion without creating memberships or eligibility | [Report-study inventory](REPORT_STUDY_INVENTORY.md) |
| `python inventory_intake.py template [-h] [--text] --report-id REPORT_ID --study-id STUDY_ID --candidate-output CANDIDATE_OUTPUT protocol` | Draft a blank descriptive candidate for one explicit report and human study label | [Manual inventory intake](MANUAL_INVENTORY_INTAKE.md) |
| `python inventory_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the completed description to the current inventory source basis for exact-input review | [Manual inventory intake](MANUAL_INVENTORY_INTAKE.md) |
| `python inventory_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied import review as a detached application | [Manual inventory intake](MANUAL_INVENTORY_INTAKE.md) |
| `python inventory_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the description append, preserving eligibility and result counts | [Manual inventory intake](MANUAL_INVENTORY_INTAKE.md) |
| `python report_study_inventory_review.py [-h] [--report-id REPORT_ID] [--study-id STUDY_ID] [--template] [--text] [--output OUTPUT] protocol` | Record separate human positions on described candidates before report inclusion, without declaring memberships | [Inventory candidate reviews](INVENTORY_CANDIDATE_REVIEWS.md) |

## Results, source passages and conditions

| Usage | Purpose | Guide |
|---|---|---|
| `python result_extraction.py [-h] --report-id REPORT_ID --study-id STUDY_ID --record-id RECORD_ID [--text] [--output OUTPUT \| --candidate-output CANDIDATE_OUTPUT] protocol` | Join exact report-study context and existing results with a deliberately blank manual intake candidate | [Extraction worksheets](EXTRACTION_WORKSHEETS.md) |
| `python result_passage_check.py template [-h] [--output OUTPUT] [--text] protocol candidates` | Draft the explicit source-file mapping manifest for completed result candidates | [Result passage check](RESULT_PASSAGE_CHECK.md) |
| `python result_passage_check.py catalog [-h] --root ROOT [--output OUTPUT] [--text] protocol candidates manifest` | List the lines of explicitly mapped local UTF-8 sources for human selection of byte ranges | [Result passage check](RESULT_PASSAGE_CHECK.md) |
| `python result_passage_check.py check [-h] --root ROOT [--output OUTPUT] [--text] protocol candidates manifest` | Compare declared hashes and exact UTF-8 quotes beside unchanged manual fields; matching text is not scientific acceptance | [Result passage check](RESULT_PASSAGE_CHECK.md) |
| `python result_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind supplied manual result rows and detached document associations to the current protocol for review | [Manual result intake](MANUAL_RESULT_INTAKE.md) |
| `python result_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied import review as a detached application | [Manual result intake](MANUAL_RESULT_INTAKE.md) |
| `python result_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the exact-input import and append the result rows without changing prior evidence | [Manual result intake](MANUAL_RESULT_INTAKE.md) |
| `python result_source_review.py [-h] [--output OUTPUT] [--text] original_protocol application_record current_protocol` | Replay a manual intake record, then separately compare current result rows, report links and supplied document context | [Result source review](RESULT_SOURCE_REVIEW.md) |
| `python result_correction.py target [-h] [--text] --output OUTPUT protocol correction_document` | Bind supplied result/limitations text corrections to existing result IDs for exact-target review | [Result corrections](RESULT_CORRECTIONS.md) |
| `python result_correction.py assemble [-h] [--text] --output OUTPUT protocol correction_document review_document` | Record the supplied correction review as a detached application | [Result corrections](RESULT_CORRECTIONS.md) |
| `python result_correction.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the wording change without changing extraction IDs, row order or counts | [Result corrections](RESULT_CORRECTIONS.md) |
| `python condition_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind completed nonclinical condition descriptions to existing result rows and chosen document declarations | [Manual condition intake](MANUAL_CONDITION_INTAKE.md), [experiment conditions](EXPERIMENT_CONDITIONS.md) |
| `python condition_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied condition review as a detached application | [Manual condition intake](MANUAL_CONDITION_INTAKE.md) |
| `python condition_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the condition append, preserving all existing results | [Manual condition intake](MANUAL_CONDITION_INTAKE.md) |

## Context and appraisal

| Usage | Purpose | Guide |
|---|---|---|
| `python context_intake.py template [-h] [--text] [--candidate-output CANDIDATE_OUTPUT] protocol reference_document` | Draft blank guideline/development contexts for explicit source or result references | [Manual context intake](MANUAL_CONTEXT_INTAKE.md), [source contexts](SOURCE_CONTEXTS.md) |
| `python context_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the completed contexts to the current protocol for exact-input review | [Manual context intake](MANUAL_CONTEXT_INTAKE.md) |
| `python context_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied import review as a detached application | [Manual context intake](MANUAL_CONTEXT_INTAKE.md) |
| `python context_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the append; new contexts stay unassigned and existing links, bases and review states are unchanged | [Manual context intake](MANUAL_CONTEXT_INTAKE.md) |
| `python work_context_intake.py template [-h] [--text] [--candidate-output CANDIDATE_OUTPUT] protocol reference_document` | Draft explicit context-to-work assignments for named existing work | [Work context intake](WORK_CONTEXT_INTAKE.md) |
| `python work_context_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the selected assignments to the current protocol, exposing selected and direct-dependent source bases | [Work context intake](WORK_CONTEXT_INTAKE.md) |
| `python work_context_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied assignment review as a detached application | [Work context intake](WORK_CONTEXT_INTAKE.md) |
| `python work_context_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the assignment; only selected context-ID lists change, ranks, completion assertions and hashes do not | [Work context intake](WORK_CONTEXT_INTAKE.md) |
| `python appraisal_intake.py template [-h] [--text] [--candidate-output CANDIDATE_OUTPUT] protocol reference_document` | Draft blank method/domain appraisals for exact existing result IDs | [Manual appraisal intake](MANUAL_APPRAISAL_INTAKE.md) |
| `python appraisal_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the authored appraisals to the current protocol for exact-target review | [Manual appraisal intake](MANUAL_APPRAISAL_INTAKE.md) |
| `python appraisal_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied import review as a detached application | [Manual appraisal intake](MANUAL_APPRAISAL_INTAKE.md) |
| `python appraisal_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the append; disagreement is preserved and no score, consensus or review renewal is produced | [Manual appraisal intake](MANUAL_APPRAISAL_INTAKE.md) |
| `python appraisal_source_review.py [-h] [--output OUTPUT] [--text] original_protocol application_record current_protocol` | Replay imported appraisals, then compare their original result/source snapshots with later literal context | [Appraisal source review](APPRAISAL_SOURCE_REVIEW.md) |

## Independent challenge and conclusion readiness

| Usage | Purpose | Guide |
|---|---|---|
| `python challenge_intake.py template [-h] [--text] [--candidate-output CANDIDATE_OUTPUT] protocol reference_document` | Draft a blank challenge for explicit statement IDs, listing the recorded reviewer/appraiser labels and the current statement bases | [Independent challenge](INDEPENDENT_CHALLENGE.md) |
| `python challenge_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the supplied challenges to the current statement bases; a stale basis or a colliding challenger label is rejected | [Independent challenge](INDEPENDENT_CHALLENGE.md) |
| `python challenge_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied import review as a detached application | [Independent challenge](INDEPENDENT_CHALLENGE.md) |
| `python challenge_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the append and expose open material gaps without upholding or refuting any statement | [Independent challenge](INDEPENDENT_CHALLENGE.md) |
| `python readiness_review.py [-h] [--text] protocol` | Show the mechanical conclusion-readiness gate ledger, its open items and hash, and supplied readiness assertions bound to it; closed gates are bookkeeping, not sufficiency | [Conclusion readiness](CONCLUSION_READINESS.md) |
| `python readiness_intake.py template [-h] [--text] [--candidate-output CANDIDATE_OUTPUT] protocol` | Draft a blank protocol-wide readiness assertion bound to the current `gates_sha256` with the full gate ledger | [Conclusion readiness](CONCLUSION_READINESS.md) |
| `python readiness_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the supplied sufficiency/readiness assertions to the current gate ledger; a stale gate hash is rejected | [Conclusion readiness](CONCLUSION_READINESS.md) |
| `python readiness_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied import review as a detached application | [Conclusion readiness](CONCLUSION_READINESS.md) |
| `python readiness_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the append; a READY assertion while gates are open stays visible with those gates, and nothing is promoted | [Conclusion readiness](CONCLUSION_READINESS.md) |

## Work packages and completion

| Usage | Purpose | Guide |
|---|---|---|
| `python source_work_intake.py template [-h] [--text] [--candidate-output CANDIDATE_OUTPUT] protocol reference_document` | Draft blank source-review work for explicit typed planned-search or record references | [Source work intake](SOURCE_WORK_INTAKE.md), [source-review work](SOURCE_REVIEW_WORK.md) |
| `python source_work_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the human-authored tasks to the current protocol for proposal review | [Source work intake](SOURCE_WORK_INTAKE.md) |
| `python source_work_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied proposal review as a detached application | [Source work intake](SOURCE_WORK_INTAKE.md) |
| `python source_work_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the append of PLANNED source-review work without changing existing research decisions | [Source work intake](SOURCE_WORK_INTAKE.md) |
| `python evidence_work_intake.py template [-h] [--text] [--candidate-output CANDIDATE_OUTPUT] protocol reference_document` | Draft blank result-linked review work for exact existing result IDs | [Evidence work intake](EVIDENCE_WORK_INTAKE.md) |
| `python evidence_work_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the human deliverables and prerequisites to the current protocol for exact-input review | [Evidence work intake](EVIDENCE_WORK_INTAKE.md) |
| `python evidence_work_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied proposal review as a detached application | [Evidence work intake](EVIDENCE_WORK_INTAKE.md) |
| `python evidence_work_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the append of PLANNED evidence-review work; no scientific task is generated | [Evidence work intake](EVIDENCE_WORK_INTAKE.md) |
| `python work_completion_intake.py template [-h] [--text] --work-package WORK_PACKAGE [--candidate-output CANDIDATE_OUTPUT] protocol` | Draft a blank completion assertion for one explicit unfinished work package | [Work completion intake](WORK_COMPLETION_INTAKE.md) |
| `python work_completion_intake.py target [-h] [--text] --output OUTPUT protocol candidate_document` | Bind the supplied artifact/acceptance assertion to the reviewed work/source basis for exact-target review | [Work completion intake](WORK_COMPLETION_INTAKE.md) |
| `python work_completion_intake.py assemble [-h] [--text] --output OUTPUT protocol candidate_document review_document` | Record the supplied completion review as a detached application | [Work completion intake](WORK_COMPLETION_INTAKE.md) |
| `python work_completion_intake.py verify [-h] [--text] [--protocol-output PROTOCOL_OUTPUT] protocol application_record` | Replay the single completion with source binding and dependency-change cues, without artifact checks or acceptance assessment | [Work completion intake](WORK_COMPLETION_INTAKE.md) |
| `python artifact_review.py [-h] --root ROOT protocol manifest` | Check explicitly listed local files against supplied size/SHA-256 expectations under a dedicated root; matching bytes are never acceptance | [Local artifact review](LOCAL_ARTIFACT_REVIEW.md) |

## Portable archives

| Usage | Purpose | Guide |
|---|---|---|
| `python research_bundle.py create [-h] protocol output` | Create a new portable supplied-data bundle (protocol, validated JSON, CSV, bounded summary, SHA-256 manifest) | [Portable offline research bundle](USAGE.md#portable-offline-research-bundle) |
| `python research_bundle.py verify [-h] bundle` | Check hashes, implementation bytes and regenerated outputs without extracting paths | [Portable offline research bundle](USAGE.md#portable-offline-research-bundle) |
| `python collection_bundle.py create [-h] --nbib INDEX=PATH [--text] protocol output` | Carry selected single-file native NBIB wrappers with the research bundle, bound to their exact import associations | [Collection bundles](COLLECTION_BUNDLES.md) |
| `python collection_bundle.py verify [-h] [--text] bundle` | Replay the wrapper bindings and compare the entire canonical ZIP | [Collection bundles](COLLECTION_BUNDLES.md) |
| `python batch_collection_bundle.py create [-h] --batch INDEX=PATH [--text] protocol output` | Package selected batch wrappers and every exact native source file with historical import bindings | [Batch collection bundles](BATCH_COLLECTION_BUNDLES.md) |
| `python batch_collection_bundle.py verify [-h] [--text] bundle` | Replay the batch bindings and compare the entire canonical ZIP | [Batch collection bundles](BATCH_COLLECTION_BUNDLES.md) |
| `python native_collection_bundle.py create [-h] [--ris INDEX=PATH] [--nbib INDEX=PATH] [--nbib-batch INDEX=PATH] [--text] protocol output` | Bind explicitly typed RIS and NBIB wrappers plus exact originals to historical imports in one portable snapshot; at least one selection required | [Native collection bundles](NATIVE_COLLECTION_BUNDLES.md) |
| `python native_collection_bundle.py verify [-h] [--text] bundle` | Replay the typed bindings and compare the entire canonical ZIP | [Native collection bundles](NATIVE_COLLECTION_BUNDLES.md) |
| `python report_transition_bundle.py create [-h] --application APPLICATION.json [--text] initial endpoint output` | Retain an explicitly selected contiguous registration/retrieval/full-text segment with exact original bytes | [Report transition bundles](REPORT_TRANSITION_BUNDLES.md) |
| `python report_transition_bundle.py verify [-h] [--text] bundle` | Replay the retained report segment; earlier and later history stay unassessed | [Report transition bundles](REPORT_TRANSITION_BUNDLES.md) |
| `python extraction_transition_bundle.py create [-h] --application APPLICATION.json [--text] initial endpoint output` | Retain a contiguous reviewed result/correction/condition segment with its historical source context | [Extraction transition bundles](EXTRACTION_TRANSITION_BUNDLES.md) |
| `python extraction_transition_bundle.py verify [-h] [--text] bundle` | Replay the retained extraction segment without renewing any review | [Extraction transition bundles](EXTRACTION_TRANSITION_BUNDLES.md) |
| `python work_transition_bundle.py create [-h] --application APPLICATION.json [--text] initial endpoint output` | Retain an explicit contiguous source-work/evidence-work/completion segment with exact original bytes | [Work transition bundles](WORK_TRANSITION_BUNDLES.md) |
| `python work_transition_bundle.py verify [-h] [--text] bundle` | Replay the retained work segment without renewing completion or assessing artifacts | [Work transition bundles](WORK_TRANSITION_BUNDLES.md) |
| `python appraisal_transition_bundle.py create [-h] --application APPLICATION.json [--text] initial endpoint output` | Retain exact original/import/endpoint bytes for an explicitly selected contiguous appraisal segment | [Appraisal transition bundles](APPRAISAL_TRANSITION_BUNDLES.md) |
| `python appraisal_transition_bundle.py verify [-h] [--text] bundle` | Replay the retained appraisal segment without renewing reviews or assessing validity | [Appraisal transition bundles](APPRAISAL_TRANSITION_BUNDLES.md) |

## Implementation revision diagnostics

| Usage | Purpose | Guide |
|---|---|---|
| `python implementation_check.py inspect [-h] [--engine-root ENGINE_ROOT] [--manifest MANIFEST] [--text] artifact` | Compare recorded hashes without executing artifact code; manifest is repeatable | [Implementation revisions](IMPLEMENTATION_REVISIONS.md) |

## Tests and publication checks

| Usage | Purpose | Guide |
|---|---|---|
| `python -m unittest discover -v` | Run the synthetic test suite, the `tests/` package, including the tests that execute the documented walkthrough command blocks | [End-to-end and CI verification](USAGE.md#end-to-end-and-ci-verification), [validation record](../VALIDATION.md) |
| `python -m unittest tests.test_<module> -v` | Run one module of the `tests/` package, for example `tests.test_dispatcher` or `tests.test_cli_e2e` | [End-to-end and CI verification](USAGE.md#end-to-end-and-ci-verification) |
| `python audit_publication.py` | Limited public-file/type/secret-pattern scan of the checkout; a pass is not proof of anonymity or clearance | [Publication inventory checks](USAGE.md#publication-inventory-checks), [security](../SECURITY.md) |
| `python verify_manifest.py` | Verify the complete published inventory against exact checkout bytes; unlisted files and link-like paths fail | [Publication inventory checks](USAGE.md#publication-inventory-checks), [publication boundary](../PUBLICATION.md) |

## Engine modules without a command line

These modules are imported by the commands above and have no entry point of their own.
The ones named in `ENGINE_FILES` of `research_bundle.py` have their exact bytes recorded
in every bundle, so verification fails closed on implementation drift.

| Module | Purpose |
|---|---|
| `adapter_integrity.py` | Check internal mock receipt/review consistency; never authenticate external sources |
| `appraisal_links.py` | Preserve supplied appraisal methods and domain judgements without scoring evidence |
| `bibliographic_integrity.py` | Validate flat, supplied-review bibliographic import history without trusting identity |
| `challenge_links.py` | Record supplied independent challenges to synthesis statements without adjudicating them ([guide](INDEPENDENT_CHALLENGE.md)) |
| `context_links.py` | Validate supplied guideline/development context links without judging their validity |
| `csv_export_parser.py` | Parse local bibliographic CSV bytes without resolving or merging records |
| `records_csv.py` | Detached CSV serializer of existing audit joins, outside ENGINE_FILES |
| `csv_safety.py` | Conservative text escaping for spreadsheet-facing CSV cells |
| `experiment_links.py` | Validate supplied nonclinical comparison conditions, never prescribe experiments |
| `json_io.py` | Strict shared JSON decoding, UTF-8 stdio and the shared quoting helper for `--text` renderings |
| `nbib_export_parser.py` | Lossless local NBIB intake for an explicit fixed-column PubMed-format subset |
| `planning_links.py` | Track supplied planning ranks and source staleness without generating priorities |
| `readiness_links.py` | Derive the twelve mechanical conclusion-readiness gates and record supplied readiness assertions without judging sufficiency ([guide](CONCLUSION_READINESS.md)) |
| `report_links.py` | Validate supplied report-study memberships without inferring source identity |
| `report_review_links.py` | Pure supplied full-text source/review links; never retrieve or adjudicate |
| `report_study_inventory_links.py` | Pure, descriptive supplied study inventory; no membership or eligibility decisions |
| `report_study_inventory_review_links.py` | Supplied eligibility positions on described candidate studies, never selection |
| `report_study_review_links.py` | Read-only supplied human eligibility positions for exact report-study pairs |
| `ris_export_parser.py` | Preserve an explicit fixed-column UTF-8 RIS subset without identity inference |
| `screening_decision_links.py` | Pure integrity checks for explicit supplied screening decisions, not adjudication |
| `screening_links.py` | Link supplied screening assertions without adjudicating canonical decisions |
| `search_audit.py` | Compare supplied searches with a declared search plan, without running searches |
| `synthesis_links.py` | Trace supplied synthesis statements without judging entailment or writing conclusions |
| `work_document_links.py` | Bind explicitly selected supplied document descriptors to source-review work |
