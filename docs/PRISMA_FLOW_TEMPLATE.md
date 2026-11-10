# Native PRISMA-oriented count crosswalk

`prisma_flow_template.py` writes a new, local **sensei-native crosswalk CSV** and
prints its mapping receipt. Despite the command name, this is **not an official
PRISMA 2020 template or an import-compatible file for any external diagram tool**.
No third-party template, box wording, tooltip or source asset is included. Mapping
into a separately selected tool remains a manual task, with its own format and
rights checks. No external tool is installed, contacted or executed.

The existing [PRISMA audit](PRISMA_AUDIT.md) is unchanged. The new command calls
`export_audit` and derives a view without changing searches, screening, reports,
study IDs, reviews, readiness or the protocol. No model, source retrieval,
authentication, scientific judgement or deduplication is performed. Census stays
`NOT_ESTABLISHED`; conclusion readiness stays `NOT_READY`.

## Entirely fictional rehearsal

Replace `OUTPUT` with an existing directory outside this public repository. Each
CSV destination must be new. These commands are replayed by the synthetic tests:

```sh
python prisma_flow_template.py examples/prisma-audit.json --search-arm 0=databases --search-arm 1=databases --output OUTPUT/flow-conservative.csv
python prisma_flow_template.py examples/prisma-audit.json --search-arm 0=databases --search-arm 1=databases --include-exact-id-accounting --output OUTPUT/flow-opt-in.csv --text
```

The default keeps `duplicates` and `records_screened` blank. The explicit opt-in
fills **exact supplied record-ID repeats**, not deduplicated publications, and
**supplied screening decisions**, not a completed post-deduplication screening
stage. Never paste these values into differently worded diagram boxes without
preserving their unit and scope. The native CSV is an accounting worksheet, not
a diagram or a claim of PRISMA compliance.

## Native schema and mappings

The fixed header is `schema,template_key,search_index,label,count,unit,mapped_node,
scope,boundary,census_claim,conclusion_readiness` (one CSV header row). Schema is
`sensei.prisma-flow-crosswalk.v1`. Symbolic `template_key` values are native mapping
hints, not a pinned external template contract. There is no `--template` import in
this version. Every row carries the boundary and negative claims so the CSV can be
read on its own. Retain the stdout receipt too for pending states and count gaps.

- `--search-arm INDEX=databases|registers` is an explicit supplied classification,
  keyed by zero-based input index, never inferred from a source label or search ID.
  Repeat the option for different indices. Duplicate, out-of-range and malformed
  indices are rejected. Missing or repeated optional search IDs remain distinct.
- `database_results` and `register_results` contain enumerated occurrences only,
  one row per assigned search. Identical source labels are not aggregated. Missing
  assignments produce blank `unassigned_search` rows and receipt entries. An arm
  without an assigned search has a blank placeholder, not zero.
- Downstream values cover **all supplied searches**, including unassigned ones.
  They are not partitioned by method. The `dbr_*` hints do not establish that all
  reports originated from database/register searches.
- In the example, database rows are 10 and 3. With opt-in, `duplicates` is 2 and
  `records_screened` is 9. `records_excluded` is 1; `dbr_sought_reports` is 6;
  `dbr_notretrieved_reports` is 1; `dbr_assessed` is 3; `dbr_excluded` is 1;
  `new_studies` is 1 supplied study ID; `new_reports` is 2.
- `dbr_excluded_reason` has one row per supplied reason group. The example has
  `Fictional exclusion reason`, count 1. These rows subdivide `dbr_excluded`; they
  are not additional reports to add to that total. No label/reason delimiter is
  introduced, and standard CSV quoting retains commas and embedded line breaks.
- Absent report data makes report/study cells blank. Explicit `reports: []` makes
  the corresponding supplied report/study totals zero. These states are different.
- Website, organisation, citation-search, automation-removal, previous-study and
  method-specific `other_*` hints have no matching accounting and stay blank.

Spreadsheet-facing values use `csv_safety.safe_csv_cell`. A leading apostrophe is
added before formula-like or whitespace-leading cells; this may be visible if
copied into another tool. The JSON receipt preserves the original labels/reasons.
CSV escaping is not a guarantee for every spreadsheet viewer, and source text is
not redacted or cleared for sharing.

## Receipt and unfinished work

Default stdout is JSON. `--text` quotes supplied values to prevent control or
directional characters from forging summary lines. Both forms include the full
mapping ledger, each search's supplied total/completion/has-more assertions and
page audit, plan audit, four outside-flow nodes and mechanical transition gaps.
For the example:

- Screening pending: 2; unmapped included records: 1.
- Retrieval pending: 1; assessment pending: 1.
- One planned search is missing: `search-citation-followup`.
- Identified occurrences minus exact-ID repeats minus screened records leaves 2.
- Included records minus mapped included records leaves 1.
- Reports sought minus not-retrieved minus assessed reports leaves 2, the sum of
  retrieval-pending and assessment-pending reports.

These are recorded count differences and existing member partitions, not scientific
checks or validated PRISMA transitions. Unknown stages remain null/NOT_SUPPLIED.
The receipt binds the canonical supplied protocol, current engine plus audit and
crosswalk implementation bytes, and exact CSV bytes by SHA-256. Hashes do not
authenticate inputs or establish completeness. Existing bundles do not include or
verify a separately saved crosswalk.

## File and size boundary

Only the requested CSV is written, using exclusive creation after both CSV and
stdout are serialized and checked. Existing files and dangling links are refused.
Protocol input, encoded CSV and encoded stdout each have a 16 MiB limit. If a
derived output exceeds the cap, narrow the supplied protocol; nothing is truncated.
All data is read before output creation, so the input cannot be overwritten.
CSV uses UTF-8 without BOM and LF record endings. Embedded source line breaks are
preserved. The receipt does not add filesystem paths or a clock-derived timestamp.

**PRIVATE FILE:** source labels and reasons can contain private research information.
Keep real inputs, CSVs and receipts outside this repository and do not transmit
them without separate authorization. The command itself makes no external call.
