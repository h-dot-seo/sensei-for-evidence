# Supplied screening selection back to native occurrences

Run the existing BATCH_TO_EVIDENCE and SECOND_SEARCH_CONTINUATION guides first.
These commands consume their unchanged synthetic outputs, not real citations.

```sh
python collection_export.py create OUTPUT/continued.json --nbib-batch 0=OUTPUT/batch.json --nbib-batch 1=OUTPUT/secondary-batch.json --decision include --output OUTPUT/included.nbib
python collection_export.py verify OUTPUT/continued.json --nbib-batch 0=OUTPUT/batch.json --nbib-batch 1=OUTPUT/secondary-batch.json --decision include --output OUTPUT/included.nbib
python collection_export.py create OUTPUT/continued.json --nbib-batch 0=OUTPUT/batch.json --nbib-batch 1=OUTPUT/secondary-batch.json --decision pending --output OUTPUT/pending.nbib
python collection_export.py create OUTPUT/continued.json --nbib-batch 0=OUTPUT/batch.json --nbib-batch 1=OUTPUT/secondary-batch.json --decision withheld --output OUTPUT/withheld.nbib
```

`--ris`, `--nbib`, `--nbib-batch INDEX=PATH` select the existing verifier,
never an inferred format. Each wrapper must match the exact historical import
including the common base. RIS and NBIB cannot be mixed; single/batch NBIB can.
The extension must match `.ris` or `.nbib`. Strict wrappers only: a separate
RIS continuation-dialect wrapper is not silently treated as the strict RIS format.

The JSON receipt is stdout (optional `--text` quoted display). It binds protocol,
wrappers, import receipts, implementation, output bytes/hash, each source and
output span, original native export hash, CSV/native candidate IDs and resolution.
All matching occurrences remain in ledger order. No representative is selected,
no record is merged and no screening tag is injected. `include`/`exclude` are
supplied title/abstract screening decisions, not full-text eligibility or study
inclusion. `pending` means no screening row. `withheld` is do_not_promote collection
triage, not exclusion. Selection never constitutes review or approval.

Each record body equals its retained span except a leading BOM is removed and
recorded; a missing final terminator is synthesized using that record's last
terminator or LF. NBIB gets exactly one additional blank separator line. Output
is re-parsed before writing and every body must match. The source's field values,
order and other bytes are not normalized. Repeated PMIDs remain occurrences.

Uncovered imports and non-bibliographic records selected by decision are listed
as NOT_EXPORTED, not silently treated as complete. With no native occurrence,
create prints NO_OUTPUT and writes nothing; verify refuses because no native
file exists. It may report uncovered matches even when nothing was exported.

Wrapper aggregate, protocol, output and receipt caps are50 MB. The existing
self-check parsers impose a stricter10 MB native file cap and line/record caps;
these are retained, so output may fail earlier. No engine limits are raised.
Output creation is exclusive. OS write errors may leave a partial new file;
check the success receipt and use verify before relying on a file. Hostile path
races are not sandboxed. Verify compares actual bytes with complete regeneration,
not merely an editable checksum. The protocol and wrappers are never changed.

No network, source authentication, scholarly validity, census or final conclusion
is established. Abstracts may be copyrighted. Real source files, receipts and
outputs belong outside this public repository and public trackers; check rights
and sharing authorization. Reference-manager acceptance/deduplication is not
verified here. BibTeX, sidecar CSV, native tag edits and representative selection
are deliberately absent.
