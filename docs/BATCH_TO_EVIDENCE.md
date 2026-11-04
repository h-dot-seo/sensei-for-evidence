# Rehearse a supplied NBIB-to-evidence workflow

This walkthrough connects two local NBIB exports to explicit collection choices,
screening, report registration, a later retrieval assertion, full-text assessment,
result rows, missing nonclinical metadata and a native-source bundle. It uses only
bundled fictional inputs. It never searches, downloads or reads actual literature,
calls a provider, performs review, or generates scientific/experimental decisions.

Create a new empty output directory outside this repository. Replace `OUTPUT` in
the commands with its path and quote paths containing spaces. Run from the
repository root. The test suite executes these exact command blocks in order.
All output files must be new. Keep the whole output directory, including the
intermediate original protocols and detached receipts.

Every file in `examples/batch-to-evidence/` is a **prewritten synthetic assertion**,
not a real human review. Read it before applying it. Targets and templates remain
blank until those separate explicit fixture assertions are supplied. Fixture
reviews are bound to this exact example, including its recorded implementation;
never reuse them for real research or edit a target hash to bypass a mismatch.
The directory contains inputs, not a script that automatically decides real data.

## 1. Preserve two originals and inspect five raw occurrences

```sh
python nbib_batch_intake.py preview examples/bibliographic-base.json --export first=examples/pubmed-export.nbib --export second=examples/pubmed-export-additional.nbib --search-id local-primary --searched-at 2026-11-04T00:00:00Z --output OUTPUT/batch.json
python nbib_batch_intake.py verify OUTPUT/batch.json --intake-output OUTPUT/intake.json
python bibliographic_review.py template OUTPUT/intake.json --review-output OUTPUT/blank-choices.json
```

Five native occurrences remain five CSV candidate rows, including repeated
identifier strings and similar titles. No row is merged, withheld or screened by
these commands. Both original files, native spans, source labels and their order
remain available. The selected query/grouping/time are supplied assertions, not
verified pagination or acquisition chronology.

## 2. Apply explicit collection reconciliation

Read `collection-choices.json`: row 1 creates record A; row 2 explicitly maps to A;
row 3 creates B despite similar text; row 4 is deliberately not promoted; row 5
creates C. The repeated identifier does not make those choices automatically.
Row 4's collection triage is neither screening exclusion nor a duplicate verdict.

```sh
python bibliographic_review.py target examples/bibliographic-base.json OUTPUT/intake.json examples/batch-to-evidence/collection-choices.json --review-output OUTPUT/collection-target.json
python bibliographic_review.py assemble examples/bibliographic-base.json OUTPUT/intake.json examples/batch-to-evidence/collection-review.json --protocol-output OUTPUT/collected.json
```

The supplied review produces one incomplete search with three declared record
memberships. Its total is unknown; the second planned search is missing. Four raw
occurrences were promoted into those three memberships and one was withheld, with
all five original rows preserved in the collection ledger. The search ledger's
identified-occurrence count is **three**, not the raw-export count of five.
Its repeated-exact-ID count is zero because its membership list is unique. Do not
present either scope as a verified count of unique publications or as automatic
PRISMA duplicate-removal accounting. Inspect raw reconciliation separately.

## 3. Supply title/abstract choices in order

The three separate fixture documents explicitly include A, B and C. Each target
binds its current complete input, so the sequence matters. No source is read and
no title/abstract choice is inferred from the collection disposition.

```sh
python screening_decision.py target OUTPUT/collected.json --record-id record-A --output OUTPUT/screen-A-target.json
python screening_decision.py assemble OUTPUT/collected.json examples/batch-to-evidence/screen-record-A.json --protocol-output OUTPUT/screened-A.json
python screening_decision.py target OUTPUT/screened-A.json --record-id record-B --output OUTPUT/screen-B-target.json
python screening_decision.py assemble OUTPUT/screened-A.json examples/batch-to-evidence/screen-record-B.json --protocol-output OUTPUT/screened-B.json
python screening_decision.py target OUTPUT/screened-B.json --record-id record-C --output OUTPUT/screen-C-target.json
python screening_decision.py assemble OUTPUT/screened-B.json examples/batch-to-evidence/screen-record-C.json --protocol-output OUTPUT/screened.json
```

All three records are now included at screening, with explicit supplied decision
history. There are still no registered reports, studies or extracted results.

## 4. Register reports without deciding full-text eligibility

`reports.json` explicitly groups records A and B into report A, declared retrieved
with source A. Record C maps to report B, whose retrieval is pending. Grouping
and document declarations are supplied, not inferred from matching titles/IDs.

```sh
python report_intake.py target OUTPUT/screened.json examples/batch-to-evidence/reports.json --output OUTPUT/report-target.json
python report_intake.py assemble OUTPUT/screened.json examples/batch-to-evidence/reports.json examples/batch-to-evidence/reports-review.json --output OUTPUT/report-application.json
python report_intake.py verify OUTPUT/screened.json OUTPUT/report-application.json --protocol-output OUTPUT/registered.json
```

Three included records become two sought reports; they are not three studies.
Both full-text choices remain pending. Source A's document hash is null, and no
file bytes have been compared. Registration review is not scientific review.

## 5. Record a supplied later retrieval outcome

`retrieval.json` explicitly asserts that report B is now retrieved and adds source
B. The tool does not obtain it. Report identity, record mappings, source A and
screening history remain unchanged. The prior retrieval value remains in the
original protocol and detached application, not a new protocol event ledger.

```sh
python report_retrieval.py target OUTPUT/registered.json examples/batch-to-evidence/retrieval.json --output OUTPUT/retrieval-target.json
python report_retrieval.py assemble OUTPUT/registered.json examples/batch-to-evidence/retrieval.json examples/batch-to-evidence/retrieval-review.json --output OUTPUT/retrieval-application.json
python report_retrieval.py verify OUTPUT/registered.json OUTPUT/retrieval-application.json --protocol-output OUTPUT/retrieved.json
```

There are now two retrieved reports, both awaiting assessment. Retrieval is not
inclusion, reading or a verified complete search. No review is renewed.

## 6. Apply one separate full-text choice and supplied results

`full-text.json` explicitly includes report A and declares study A. Report B stays
unassessed. These are fictional supplied decisions, not a review performed by the
software. `results.json` then supplies two fictional result rows for study A,
including an explicit null finding and a direction-only observation. Neither a
new study nor an effect size is inferred from having two rows.

```sh
python report_decision.py target OUTPUT/retrieved.json --report-id report-A --output OUTPUT/full-text-target.json
python report_decision.py assemble OUTPUT/retrieved.json examples/batch-to-evidence/full-text.json --output OUTPUT/full-text-application.json
python report_decision.py verify OUTPUT/retrieved.json OUTPUT/full-text-application.json --protocol-output OUTPUT/included.json
python result_intake.py target OUTPUT/included.json examples/batch-to-evidence/results.json --output OUTPUT/result-target.json
python result_intake.py assemble OUTPUT/included.json examples/batch-to-evidence/results.json examples/batch-to-evidence/results-review.json --output OUTPUT/result-application.json
python result_intake.py verify OUTPUT/included.json OUTPUT/result-application.json --protocol-output OUTPUT/results.json
```

Only record A is the explicit anchor for these result rows. Record B shares its
report, so no second result is fabricated merely to cover that record. Report A
has supplied extraction presence; that does not establish extraction completeness.

## 7. Retain explicit missing nonclinical metadata

`conditions.json` attaches descriptive context to both result IDs. Concentration,
exposure time, comparator, observation time and reference event are explicitly
unknown. Causal basis stays unknown. There are no numerical experimental values,
procedural instructions, independent-unit claims or replicate counts.

```sh
python condition_intake.py target OUTPUT/results.json examples/batch-to-evidence/conditions.json --output OUTPUT/condition-target.json
python condition_intake.py assemble OUTPUT/results.json examples/batch-to-evidence/conditions.json examples/batch-to-evidence/conditions-review.json --output OUTPUT/condition-application.json
python condition_intake.py verify OUTPUT/results.json OUTPUT/condition-application.json --protocol-output OUTPUT/final.json
python prisma_audit.py OUTPUT/final.json
python research_status.py OUTPUT/final.json
```

Final supplied accounting: three records, two retrieved reports, one assessed and
included report, one unassessed report, one declared study and two result rows.
One record anchors extraction; two included records have no direct result row.
Those record-level absences are not two unextracted included reports. Both
results have the supplied missing-condition context, not completed scientific
characterization. Unknown totals, the missing secondary search and source/review
limits remain visible. Census and conclusion readiness remain `NOT_ESTABLISHED`
and `NOT_READY`.

## 8. Preserve native originals and their historical import binding

```sh
python batch_collection_bundle.py create OUTPUT/final.json OUTPUT/batch-to-evidence.zip --batch 0=OUTPUT/batch.json
python batch_collection_bundle.py verify OUTPUT/batch-to-evidence.zip
```

The archive includes the unchanged ordinary research bundle, the native wrapper,
both exact original NBIB members and an explicit binding to historical import 0.
It verifies after later screening, report and evidence additions because those
changes do not replace the original collection association. It does not certify
source identity, actual review, complete searching, extraction or scientific truth.

The archive does **not** embed the detached report-registration, retrieval,
full-text, result or condition applications or all intermediate originals. Retain
the entire `OUTPUT` directory and recorded code revision to replay those steps.
Do not call the ZIP alone a complete review-history archive. Data is not redacted;
real inputs and outputs belong outside the public repository and should only be
shared with authorized recipients.

For real supplied inputs, create fresh blank choices and targets, inspect sources,
and supply actual decisions through the individual guides: [NBIB batch](PUBMED_NBIB_BATCH.md),
[collection review](BIBLIOGRAPHIC_REVIEW.md), [screening](SCREENING_DECISIONS.md),
[report registration](MANUAL_REPORT_INTAKE.md), [retrieval](REPORT_RETRIEVAL_UPDATES.md),
[full-text decision](REPORT_DECISIONS.md), [result intake](MANUAL_RESULT_INTAKE.md)
and [condition intake](MANUAL_CONDITION_INTAKE.md). Actual retrieval, reading,
appraisal and research judgments remain separate authorized human work.
