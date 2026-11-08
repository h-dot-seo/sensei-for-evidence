# Continue with a separate planned search after extraction

This synthetic continuation adds the already declared `local-secondary` search to
an existing protocol that has screening decisions, reports, result rows and
explicit unknown nonclinical conditions. It exercises the existing import rules;
there is no new intake engine, plan amendment or automatic reconciliation.

First execute all commands in the [NBIB-to-evidence rehearsal](BATCH_TO_EVIDENCE.md).
Use that same outside-repository output directory as `OUTPUT` below. All new paths
must be unused. Keep every original, wrapper and detached application from the
first rehearsal. The tests execute both guides in order, with paths containing
spaces. Commands below run from the repository root and use fictional inputs only.

The three files in `examples/second-search/` are prewritten software-test data,
not actual publications, acquisition evidence or human review. The timestamp,
separate-query association, record identity choices and review are supplied
assertions. Do not copy this review or refresh its hash for actual research.

## 1. Use the original common base, then review against current research

The native wrapper must still use `examples/bibliographic-base.json`, the exact
ledger-free common base retained by the first import. Do not use `OUTPUT/final.json`
as a new base, erase its ledger or reconstruct a new empty protocol. Current
research is used later for collision checks and the exact export-review target.
The two inputs serve different purposes.

```sh
python nbib_batch_intake.py preview examples/bibliographic-base.json --export secondary=examples/second-search/export.nbib --search-id local-secondary --searched-at 2026-11-04T01:00:00Z --output OUTPUT/secondary-batch.json
python nbib_batch_intake.py verify OUTPUT/secondary-batch.json --intake-output OUTPUT/secondary-intake.json
python bibliographic_review.py template OUTPUT/secondary-intake.json --review-output OUTPUT/secondary-blank-choices.json
python bibliographic_review.py target OUTPUT/final.json OUTPUT/secondary-intake.json examples/second-search/choices.json --review-output OUTPUT/secondary-target.json
python bibliographic_review.py assemble OUTPUT/final.json OUTPUT/secondary-intake.json examples/second-search/review.json --protocol-output OUTPUT/continued.json
```

The supplied choices explicitly link the first row to existing record A and create
record D for the second row. The identifier string does not make that decision.
The new record has no screening decision, report, study or result. Existing
screening, report/source, result and nonclinical rows remain literally unchanged,
as does the first import. Only the second incomplete search and its import receipt
are appended. The version label is not changed automatically.

This is an **unused entry in the original plan**, not another execution of
`local-primary`. Reusing an executed search ID, editing the immutable plan, changing
the common base or supplying a review prepared for another current protocol is
rejected. A late file for an already imported search is not handled by this recipe.
Keep distinct runs and seek an explicitly designed migration rather than clearing
history to bypass these restrictions.

## 2. Inspect counts in their own units

```sh
python research_status.py OUTPUT/continued.json
python search_manifest.py OUTPUT/continued.json
python prisma_audit.py OUTPUT/continued.json
python compare_runs.py OUTPUT/final.json OUTPUT/continued.json
```

Both planned searches now have supplied imports, but both remain incomplete with
unknown totals and pagination. Zero missing planned searches is not a complete
search, complete source coverage or a census.

- Seven raw native/CSV row occurrences: five from the first search and two new.
- Six promoted raw occurrences and one withheld raw occurrence.
- Five search-record memberships: A/B/C in the first search, A/D in the second.
- Four distinct exact record IDs; one repeated exact-ID membership across searches.
- Three supplied screening decisions and one pending record, D.
- Two retrieved reports, one included report, one still awaiting assessment,
  one declared included study and the same two result rows.

The search ledger's legacy `duplicates` count of one describes repeated exact
record IDs only. It is not a verified publication duplicate or an automatic PRISMA
removal decision. The earlier within-export row reconciliation remains a different
unit. All raw rows, including the withheld one, remain inspectable. No new sample
size, study independence, effect or result is inferred from the new occurrence.

## 3. Compare prior result-source context without renewing it

```sh
python result_source_review.py OUTPUT/included.json OUTPUT/result-application.json OUTPUT/continued.json --output OUTPUT/continued-result-source.json
python screening_decision.py inspect OUTPUT/continued.json --record-id record-A
```

The comparison first replays the retained result intake against its actual
`included.json` original. Both result rows, both current result links, their
original report/study mappings, the recorded report and the selected document
descriptors remain unchanged. One shared report-source context changes because
record A now has another supplied search occurrence. Both result rows refer to
that same changed context; they are not two changed documents or two new results.

The earlier screening receipt remains retained and the canonical include decision
remains unchanged. Inspection labels its source comparison `STALE_SOURCE` while
`matches_current_screening` remains true; it does not choose a new decision. Neither command authenticates the history, verifies document bytes,
reads sources, renews reviews or decides whether any scientific assertion must be
corrected. In particular, changed context does not justify re-importing unchanged
result rows or silently updating a review hash.

## 4. Package both explicit native import bindings

```sh
python batch_collection_bundle.py create OUTPUT/continued.json OUTPUT/continued-native.zip --batch 0=OUTPUT/batch.json --batch 1=OUTPUT/secondary-batch.json
python batch_collection_bundle.py verify OUTPUT/continued-native.zip
```

This archive contains two native wrappers and three exact native source files.
Import 0 still binds its two original files to the historical common base; import
1 binds its one separate source to that same base and its reviewed current-input
snapshot. No files are concatenated or deduplicated. Verification can succeed after
copying only this ZIP to another directory with the recorded implementation
available; the historical inputs retained within its import ledger are used.

The archive does not preserve all detached result, condition or report-transition
applications, intermediate protocol files or their complete history. Keep the
whole output directory and recorded code separately. The earlier native archive
continues to represent the earlier snapshot; it is not overwritten or made current
by this continuation. Archive success does not establish source authenticity,
reviewer identity, reading, search completeness, PRISMA compliance or scientific
validity. Census remains `NOT_ESTABLISHED` and conclusion readiness `NOT_READY`.

For real inputs, use fresh supplied choices and actual exact-target review under
[the bibliographic reconciliation rules](BIBLIOGRAPHIC_REVIEW.md), preserve
[batch-native bindings](BATCH_COLLECTION_BUNDLES.md), and inspect
[result-source comparison](RESULT_SOURCE_REVIEW.md) separately. This guide does
not authorize external retrieval, sharing or scientific decisions. Real/private
inputs and outputs remain outside the public repository, without automatic
redaction.
