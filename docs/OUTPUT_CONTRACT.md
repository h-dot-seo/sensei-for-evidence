# Exclusive output: scoped shared writer

Fifteen existing non-engine consumers now use `output_io.write_new` at sixteen
output sites. This closes their missing explicit existing-directory-entry guard;
it is not a complete migration of every writer in this repository or other tools.

| Consumers | Sites |
| --- | --- |
| condition_intake, nbib_intake, receipt_intake | one each |
| collection_bundle | create and verified protocol output |
| report_decision, report_review, report_source_check | one each |
| report_study_inventory, report_study_inventory_review, report_study_review | one each |
| result_correction, result_extraction, result_intake, result_source_review | one each |
| screening_review | one |

## Exact tier and limits

The helper accepts already-encoded bytes, checks the destination with `lstat`,
refuses **any existing entry**, and then uses exclusive `xb` creation. Existing
files, directories, symlinks and dangling symlinks are refused without opening
those entries. Parent directories must exist. Existing valid UTF-8/LF and binary
output bytes are preserved. The existing caller still pre-serializes, computes its
own result/receipt, selects outputs and determines ordinary/negative exit status.
The helper generates no receipt and changes no scientific decision or review.
A negative check may still save its requested negative report and exit 1.

This is **exclusive create**, not staged hard-link publication. Write or close
failure can leave a partial newly created file; it is not automatically removed.
The guard and open are separate operations. Exclusive create still refuses a
competing existing entry, but this is not complete TOCTOU protection, parent-path
alias rejection, no-follow source reading, transactional multi-output rollback,
atomic publication or fsync durability. It does not prevent same-user concurrent
path replacement. No permissions or system security settings are changed.

An existing entry now receives an explicit EEXIST error in the command's existing
error wrapper. Some platform-specific directory/link error classes or messages
can therefore change; failure remains failure with empty stdout and no overwrite.
No general privacy cleanup of older error messages is claimed. Native Windows
symlink tests run when creation is supported; unavailable link privileges are
reported as skips, not proof of native coverage. Windows junction entry checks
are separately conditional. No claim is made that every old runtime followed
links or that this fixes a confirmed vulnerability on every platform.

## Deliberately unchanged

- Existing guarded writers, including PubMed's exists/is_symlink preflight and
  result_passage_check's lexists preflight, are not migrated.
- The five engine/adapter-bound writers (bibliographic_intake,
  bibliographic_review, offline_adapter, research_bundle, screening_decision)
  are excluded. `research_bundle.ENGINE_FILES` and all those files are unchanged.
- Source readers, strict JSON validators, date checks, byte limits, gates,
  scientific decisions, approvals and real records are unchanged.
- This does not complete the original proposal's broader writer/strict-JSON/date
  deduplication. No checkout-location restriction or new external permission is added.

Consumers include the helper in their existing implementation fingerprints.
Collection/wrapper fingerprint unions can include it transitively; the ordinary
research ENGINE set does not. Successful records/views consequently have new
implementation hashes and affected detached targets change. Older artifacts need
their original recorded implementation. No automatic refresh tool is added.
Only the fixed fifteen fictional targets were recreated: nine required one hash
replacement and six were already correct. All other example bytes, reviewer/date/
decision fields, real data and actual reviews are untouched.

## Rehearse without overwriting

At the repository root, replace OUTPUT with an existing empty temporary folder.
These commands use only fictional examples. The views and unfinished worksheet
are not approvals. Repeating a command with its existing output path must fail;
choose a different new destination instead of deleting or overwriting work.

```sh
python nbib_intake.py preview examples/bibliographic-base.json examples/pubmed-export.nbib --search-id local-primary --searched-at 2026-11-04T00:00:00Z --output OUTPUT/native.json --text
python nbib_intake.py verify OUTPUT/native.json --intake-output OUTPUT/csv-intake.json --text
python nbib_intake.py verify OUTPUT/native.json --csv-output OUTPUT/native.csv --text
python report_review.py examples/bibliographic-base.json --output OUTPUT/report-review.json
python report_study_inventory.py examples/bibliographic-base.json --output OUTPUT/study-inventory.json
python screening_review.py examples/bibliographic-base.json --output OUTPUT/screening-review.json
python result_extraction.py examples/extraction-worksheet-protocol.json --report-id report-one --study-id study-C --record-id record-one --candidate-output OUTPUT/unfinished-candidates.json
```

The conformance test executes these seven commands, repeats each against its saved
output to check refusal and byte preservation, and attempts a dangling output link
when the host supports it. Existing intake/review/replay journeys and the fixed
seven-guide/61-command fictional maintenance flow remain separate validation.
