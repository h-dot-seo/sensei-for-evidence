# Recheck detached result-source context

`result_source_review.py` compares a retained manual-result application record with
a later supplied protocol. It first replays that record against its original
input, then validates the entire current protocol and reports literal differences.
It does not renew the original review, repair a source association or establish
that the current result actually descended from the earlier intake.

The tool is standalone. Existing canonical engine and `result_intake.py` bytes
are unchanged, so receipts produced by that exact implementation still replay.
Keep the original input, detached application record and recorded code. This does
not migrate older receipts across implementation changes.

## Reproduce the fictional change

First create the application record using the [manual result intake journey](MANUAL_RESULT_INTAKE.md).
The original is `examples/report-study-inventory-reviews.json`, and the explicit
batch is `examples/manual-result-candidates.json`. Fill its human review honestly;
the examples are software-test assertions, not real reading or scientific findings.

```sh
python result_source_review.py examples/report-study-inventory-reviews.json /outside/new-result-application.json examples/result-source-current.json --output /outside/new-source-comparison.json --text
```

Use the actual saved application path and a new output path. To compare the exact
newly imported state, use that intake's exported candidate protocol as the third
input instead. `--output` is optional and exclusively creates one JSON report.
`--text` changes stdout only. Inputs are never edited, no source locator is opened
and nothing is uploaded. Real/private protocols and outputs belong outside this
public repository; supplied information is retained without redaction.

The fictional current fixture changes study C's supplied result text and the
supplement's supplied version label. The second imported result remains exactly
the same. Output therefore shows:

- One changed result row and one unchanged result row.
- Both current result links and both original record/report/study links unchanged.
- One unchanged report assertion, but one changed shared report-source context.
- Two changed selected-source references and one unchanged reference. The same
  supplement is selected for both result rows, so it is counted twice here.

These are different units. A changed version label does not prove a file changed,
and unchanged text does not prove correct extraction or scientific validity.
The previously supplied null-finding description is not automatically discarded,
re-extracted or approved by this comparison.

## Replay first, validate all current data

`result_intake.verify(original_protocol, application_record)` must succeed before
comparison. Edited inputs, tampered receipt fields or mismatched implementation
bytes fail rather than becoming a partial successful report. The nested
`original_replay_result.valid` concerns only exact replay of that historical
supplied operation. There is no overall approval or current-validity flag.

The entire current protocol then undergoes ordinary core validation and full
report/evidence reconciliation when reports are supplied. Invalid unrelated rows
are not ignored merely because they were outside the imported batch. Current CSV
provenance is validated and retained through its existing source bindings.
Mock `adapter_receipts` inputs are unsupported here and must not be stripped to
bypass their provenance contract.

An absent report ledger remains `NOT_SUPPLIED`; a supplied ledger missing the
original report is `MISSING`. Likewise, an absent `report_sources` field differs
from a supplied empty/source-missing ledger. Unknown current values stay null
rather than becoming zero or an invented decision.

## Separate comparison dimensions

Only the originally imported candidates are compared, in their original order.
Unrelated current result rows are validated but are outside the comparison scope.
No similar text, locator or label is used to identify another result.

**Raw result row.** Match only a currently explicit `evidence_id` exactly equal
to the imported ID. A legacy row whose implicit record-based ID happens to match
is not a match. Status is `UNCHANGED`, `CHANGED` or `MISSING`. The entire raw row is
compared, including added opaque metadata, absent versus null fields and literal
JSON types. Before/after rows and changed field names remain visible.

**Original record/report/study mapping.** Check whether the original report still
exists, where the original record now maps, whether the original study is still
a declared included membership, and the report's current retrieval and decision.
This dimension can remain unchanged even if the current result row moved to a
different record or study.

**Current matched-row linkage.** Separately compare the current explicit result's
record, mapped report and study to its imported link. The
`current_matched_row_link_status` and separate count prevent a moved current result
from being mistaken for an unchanged original mapping. This still compares labels,
not verified study identity or historical continuity.

**Recorded report assertion.** Compare the complete report object independently.
For example, reordering study declarations or switching an equivalent scalar
membership to a singleton plural form can change this assertion while keeping the
original study membership present. Report ordering alone changes navigation, not
the report object's content.

**Shared report-source context.** Compare the existing source basis and its hash.
It binds question/criteria, mapped record/search/CSV context, retrieval, report
locator and the complete ordered source catalog. It excludes canonical report
eligibility and study declarations, which is why those require separate checks.
Changing an unselected descriptor in the same report can change context while
selected descriptor content remains unchanged. Reordering bound search/catalog
inputs can also change hashes. Unrelated protocol version or review metadata alone
does not change this source basis. There is one shared report comparison per
original report ID, not one report count per result.

**Each selected source.** Compare the historical descriptor by its exact source ID
with the current descriptor. `MOVED` means that same ID now declares another
report, not that its list position changed. Other statuses are `UNCHANGED`,
`CHANGED`, `MISSING` and `NOT_SUPPLIED`. Full descriptors and changed fields remain
visible. Original page/section `extraction_locator` text is historical supplied
context only; it is not currently verified, automatically rebound or refreshed.

Source descriptors count once per candidate selection. The same descriptor can
therefore appear several times, whereas report source contexts count unique
original report IDs. There is deliberately no combined “current”, “approved” or
“ready” result that hides these separate dimensions.

## Pointers, hashes and interpretation limits

The result's recorded pointer is into the application record's candidate document,
not the original protocol, which did not yet contain that imported result. Source
and report historical pointers refer to the original protocol. Current pointers
refer to the current protocol. Result and historical-comparison pointer objects
carry explicit scope fields; nested `current_*` mapping pointers refer to the
current protocol. These are navigation within that input, not stable identities
across versions.

Canonical comparisons ignore object-key ordering and JSON formatting, while
retaining literal values, JSON number types and relevant list order. Pure pointer
relocation does not mean descriptor reassignment. Existing inherited source-basis
rules can still bind search ordering, so not all input reorderings are irrelevant.

Hashes and exact matches do not establish authenticity, reading, document bytes,
lineage, authorship, clinical correctness, study independence, result correctness
or complete extraction. The tool adds no human opinion, scientific appraisal,
new extraction, canonical decision or protocol-level provenance ledger. Source
associations remain `DETACHED_RECORD_ONLY`; this output is itself an editable
mechanical comparison, not durable proof or automatic monitoring.

Original, application and current input files are each limited to 50 MB. The
comparison has a 50 MB output bound, including encoded CLI output. Strict JSON
and UTF-8 validation occur before exclusive output creation; a later disk/write
failure can still leave a partial new file. Source content is never fetched or
inspected. A byte check, when separately requested, remains a different operation.
