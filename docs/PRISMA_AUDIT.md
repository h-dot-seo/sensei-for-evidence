# PRISMA-oriented accounting export

`prisma_audit.py` emits an application-specific, machine-readable accounting JSON
for the **supplied** corpus. This is not an official PRISMA interchange schema,
certified PRISMA diagram, completed review or literature-completeness assessment.
No source retrieval, full-text reading, study identity verification, scientific
appraisal or medical decision occurs.

```sh
python prisma_audit.py examples/prisma-audit.json
python prisma_audit.py examples/prisma-audit.json --text
python review_handoff.py examples/prisma-audit.json --work-package WP-TRANSLATION --text
```

JSON is the full audit artifact; text is a count/reason/check summary, not the full
member ledger. Commands write only stdout and never modify the input. If saving
output, choose a new path outside the public repository and protect against shell
redirection overwriting a file. The handoff points to this audit view alongside
existing work and synthesis views. Existing research bundles do not include or
verify separately saved audit output; they retain their existing seven-file format.

## Fictional journey and expected accounting

The fixture extends the nonclinical claim/guideline/WP workflow with two supplied
searches, repeated exact record IDs and a still-missing planned citation-followup
source. It contains no real articles or scientific observations:

- 13 search occurrences → 11 exact record IDs; two repeated exact-ID occurrences.
- Nine screened records → eight title/abstract-included and one excluded;
  two records remain unscreened.
- Seven included records map to six reports; one included record is unmapped.
- Four reports are marked retrieved, one unavailable and one retrieval-pending.
- Three reports are assessed: two included, one excluded; another retrieved report
  still has a pending full-text decision.
- The two included reports share one supplied study ID. Only one has extracted
  results. Three result rows are from one record/report/study ID.

The title/abstract and full-text exclusions deliberately share the same wording.
They remain separate reason groups because their stages and counted units differ.
A second record for an already-extracted report has no individual result row:
record-level extraction absence must not be confused with an unextracted report.
Work-package statuses, prerequisites, acceptance assertions and stale reviews are
not changed by exporting this accounting.

## Schema version 1

Top-level question, protocol version, canonical protocol SHA-256 and implementation
hashes identify the supplied data and code. Canonical hashes ignore object-key
order but preserve list order; they do not authenticate a source or reviewer.

`nodes` contains fixed node IDs, explicit unit, stage, count, member_ids and scope.
Units are record_occurrence, record, report, supplied_study_id or result. Member
IDs make every count inspectable. Occurrence IDs are JSON pointers into the raw
search arrays, such as `/searches/1/record_ids/0`; other member IDs are the supplied
record/report/study IDs or effective result IDs.

- Identified occurrences count enumerated IDs, not claimed search totals or
  records from missing sources.
- Retention takes the first occurrence in supplied search order per exact record
  ID. Repeated occurrence links preserve both pointers. It does not select a
  more authoritative source or perform fuzzy publication/study deduplication.
- Included records mean title/abstract inclusion. Included reports mean supplied
  retrieved/full-text inclusion. Study IDs may be shared by multiple reports;
  result rows are not independent studies, replicates or sample sizes.
- records_with_extraction and included_records_without_extraction describe at
  least one result per record, not exhaustive extraction or required full-text
  tasks. included_reports_without_extraction is a distinct report-level queue.

`partition_checks` verifies disjoint member-ID partitions within the same unit:
occurrence retention/removal, record screening and mapping, report retrieval,
report assessment, report eligibility and included-report extraction. A successful
check says RECORDED_MEMBERS_PARTITION, not COMPLETE or READY. It checks membership
as well as counts; it does not equate record, report, study and result counts.
The input validators reject inconsistent report/extraction links before output.

`occurrence_ledger`, `repeated_occurrence_links` and `record_ledger` preserve search
occurrences, supplied screening decisions/reasons, report links and extracted
result IDs. `report_ledger` preserves original report rows with input pointers.
`evidence_links` gives effective result ID, source record, supplied study ID,
locator and original input pointer. `study_links` lists included reports and
result IDs by supplied study ID; it is not a claim of independent study identity.

`reasons` keeps exact supplied wording and member IDs for record exclusions,
full-text report exclusions and reports_not_retrieved separately. No semantic
reason classification, merging or quality judgment is performed. Unavailable full
text is not counted as an assessed exclusion.

`searches` includes input indices, raw supplied search/page receipts and existing
accounting issues; optional absent or duplicate search IDs cannot replace source
indices. `search_plan_audit` shows missing/incomplete declared searches and whether a plan
was supplied. Searches outside a supplied plan are rejected by validation.
Membership partitions can match even while search coverage is incomplete. This
is expected and never promotes census or extraction completeness.

## Missing stages and limitations

When reports are absent, report nodes, report reasons and report links that require
that stage remain null/NOT_SUPPLIED. Extracted result/study information can still
be shown without pretending full-text eligibility is known. An explicitly supplied
empty report ledger has zero report counts and unmapped included records; it is
not equivalent to a missing stage. No reports are invented to fill a diagram.

The modeled workflow still permits at most one report per supplied record and one
study ID per report/record. Results from reports that cannot be represented under
those constraints need explicit human reconciliation, not fabricated mappings.
Citation searching, registry coverage, full-text access, risk of bias, certainty,
scientific validity and omitted literature remain outside this export's claims.
Census, identity and extraction completeness stay NOT_ESTABLISHED, and conclusion
readiness stays NOT_READY even when all partitions match and all queues are empty.
