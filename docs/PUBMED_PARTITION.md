# Offline PubMed date-window reconciliation

`pubmed_partition.py` reviews explicitly supplied calendar windows and retained
[discovery records](PUBMED_DISCOVERY.md). It does not generate queries, split
windows automatically, fetch, authorize fetch, merge intake, or remove duplicates.
This closes a manual reconciliation gap: detect omitted dates, overlapping dates,
wrong-spec responses and repeated identifiers across separately supplied records.
It does not establish that a literature search was exhaustive or appropriate.

## Supplied plan and limits

A schema-1 plan has exactly `schema_version`, `query`, `date_filter`, and `specs`.
`date_filter` has exactly the existing discovery `datetype`, `mindate`, `maxdate`
fields: `pdat`, `edat` or `mdat`, real inclusive `YYYY/MM/DD` dates. `specs` contains
1 through 100 complete existing discovery specs. Request IDs must be unique; each
spec has the identical verbatim query and date type, with its own explicit dates.
No query normalization, date rewriting or inferred approval is performed.

Each spec still allows at most 100 IDs per page, 1,000 occurrences and 10 requests.
Those are this repository's local discovery caps, **not a universal PubMed limit**.
The upstream ESearch retrieval window and PubMed export actions have distinct
limits. This command does not enlarge any cap or work around a preview digest.
A single-day window with too many observed hits remains visibly capped; no hidden
subdivision, automatic retry or additional request occurs.

The API checks canonical JSON sizes; plan plus supplied artifacts are bounded to
20,000,000 bytes, as is the report. CLI reads the plan plus artifacts under a shared
20,000,000-byte raw input budget, and a verify report under a separate equally sized
budget. Each read requests only the remaining budget plus one byte before parsing.
The CLI also bounds its rendered UTF-8 JSON output to 20,000,000 bytes before
writing. Input and output bounds are inclusive; they are not total memory, CPU,
file-type, directory-containment or hard process resource guarantees. Inputs are not
restricted to regular files; a FIFO or other special stream may block. JSON parsing
retains the existing strict depth and number rules. At most 100 artifact arguments
are accepted before opening inputs. The original discovery verifier remains final
for each supplied artifact, including its own response and occurrence bounds.

## Reading the result

Calendar gaps are clipped to the supplied outer interval; every pairwise overlap
and every out-of-outer-range request ID is reported. `covers_outer_calendar` means
only no missing calendar dates. `exact_nonoverlapping_partition` additionally
requires no overlaps and no outside windows. Neither field establishes disjoint or
complete PMID sets: print/electronic dates and publication date ranges can overlap,
and the index may change between requests.

Missing observations stay `MISSING`, rather than zero hits. A supplied zero-hit
observation can account for its reported count but is still not proof of a census.
Each supplied record must replay under the current discovery implementation and
match its complete planned spec, including request ID and all caps. Duplicate,
unknown, wrong-spec, changed or old-implementation artifacts are refused. Retain
the original implementation for old records; this command never reseals them.
Input artifact order does not matter; output windows follow supplied plan order.

All occurrence rows remain, in each original order, with their window ID. Repeated
PMIDs are indexed with all occurrence positions, both within and across windows.
The unique-PMID count is only a diagnostic; no deduplicated record set is produced.
Initial counts, page-level count/translation observations, recorded timestamps,
stop reasons and capped states remain visible. Different translations are observed,
not declared incorrect. Count sums across windows must not be interpreted as a
global total. `all_supplied_counts_accounted_for` excludes missing windows by name;
read `all_windows_supplied` separately. Even both true plus exact calendar coverage
leaves `census` and `search_completeness` at `NOT_ESTABLISHED` and conclusion
`NOT_READY`. No protocol, ENGINE, research gate or human review changes.

## Local commands

Supply your own explicit plan and retained records; the following syntax is not a
permission to execute live discovery. No real queries or records are shipped here.
The commands below are illustrative placeholders, not an automatically executed
shell block. The synthetic CLI tests exercise review, separate-input replay,
exclusive output, missing observations, changed targets and safe diagnostics.

```text
python pubmed_partition.py review PLAN.json --discovery A.json --discovery B.json --output REPORT.json
python pubmed_partition.py verify PLAN.json REPORT.json --discovery A.json --discovery B.json
```

Omit `--discovery` to inspect only the calendar plan; repeat it for observations.
Review without `--output` prints JSON only. With output it exclusively creates a
new file and also prints the same JSON. Existing files and dangling symlinks are
refused before inputs are read; exclusive creation is still used at write time.
Writes are not atomic: an OS failure may leave a partial file. Retain it for
inspection and choose a new output path, rather than overwriting it. A later stdout
failure can occur after a complete output file was created; failure is not rollback. Successful
review/replay exits 0. Calendar gaps and partial observations are ordinary report
content, not an exit-code claim of completeness. Invalid input/output or replay
mismatch exits 1 with empty stdout and a fixed diagnostic; argparse usage exits 2.
Usage diagnostics can include supplied arguments and are not a privacy guarantee.

Replay requires the original plan and separately retained discovery artifacts.
Reports are unsigned; self-consistent fabricated or reauthored observations can
replay. Verification is not proof requests happened, source authentication,
publication identity, query adequacy or independent scientific review. Queries,
identifiers, timestamps and retained bodies can be sensitive and are not redacted.
Keep real inputs and outputs private and outside public repositories. No network
calls are made by either command. Nothing in a report authorizes external use.
