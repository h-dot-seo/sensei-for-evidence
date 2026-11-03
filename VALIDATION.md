# Validation record

Release preparation date: 2026-11-02 (Asia/Seoul).

- Python standard-library unittest: 4 synthetic tests passed.
- Limited public-file/type/secret-pattern scan: passed.
- Manual selected-content review: no actual conversation, researcher corpus, private
  configuration, credential, real experiment or article/book/figure asset selected.
- Examples: synthetic; no scientific or persona-predictive validation claimed.
- Private history import: none; new public repository with a separate initial history.

The scanner is not a complete secret detector, anonymizer or legal clearance tool.
Framework-level code/tests and general methods were selected; private source DBs
and third-party source materials were excluded rather than redacted and republished.
Remote publication is verified separately after committing; this file does not
claim an upload has succeeded merely because local tests passed.

## 2026-11-03 increment

Run `python -m unittest discover -v` and `python audit_publication.py`.
New tests exercise the documented synthetic workflow and rejection boundaries.
On restricted Windows hosts, set TEMP and TMP to an authorized writable directory.
No real corpus, account data, or scientific fidelity evaluation was used.

Second increment: 10 tests passed; failure boundaries and deterministic repeated results covered.

Third increment: 13 tests passed, including supplied-evidence rejection and deterministic output. No external model/search integration tested.

Fourth increment: CLI end-to-end scenarios and failure recovery added. Local tests: 15 passed. Remote CI status is recorded separately in the private development log.

Fifth increment: 18 local tests passed. New CLI paths, source boundaries, deterministic output and tamper/no-overwrite checks are covered. See private development log for remote matrix CI.

Cloud reconciliation (2026-11-03): hdbio's fifth-increment ZIP/CSV/summary exporter
was consolidated with implementation fingerprinting, strict JSON parsing and
record-only support. All 26 tests passed, including the original 18 and eight
integration cases. The duplicate JSON-envelope prototype is not published.
Schema 2 intentionally rejects prototype schema 1 and changed implementation
bytes. No literature retrieval or scientific completeness validation was performed.

Supplied-context increment (2026-11-03): 35 tests passed. Nine new tests cover
provenance requirements, typed context domains, evidence/work-package joins,
review assertions, dates, dangling/duplicate references, record-only compatibility
and context preservation in portable bundles. Synthetic data only; no real
guideline currency, applicability or scientific adequacy evaluation was performed.

Search-plan accounting increment (2026-11-03): 44 tests passed. Nine additional
tests cover missing planned searches, asserted-only completion, count/paging/error
reasons, strict integer totals, source/query/window mismatch, duplicate/unplanned
search IDs, invalid shapes, legacy no-plan input and bundle/report propagation.
No source authentication, live retrieval or completeness assessment was performed.

Contradictory-completion correction (2026-11-03): 49 tests passed. Five regression
tests cover each truncation/pagination-limit flag, malformed values, legacy absent
flags, no-plan coverage and combined report/bundle propagation. This aligns the
workflow with the state validator's pre-existing truncation boundary.

Validator parity correction (2026-11-03): 52 tests passed. The standalone state
validator now reuses the workflow's completion checks, rejects Boolean/float totals
and Boolean screening counts, records malformed search shapes as validation errors
and refuses unresolved paging/error flags in completed search assertions. Three
regression tests cover these previously inconsistent input paths.

Report/work-package provenance correction (2026-11-03): 59 tests passed. Seven
new tests reject blank/nontext report provenance, malformed report containers,
empty/duplicate/malformed work evidence links, unsupported completed work after
full-text exclusion and blank completion artifacts. Pending reports remain valid.

CSV export consistency correction (2026-11-03): 63 tests passed. Four additional
tests cover formula/whitespace prefixes, plain Unicode text, multiline report CSV
round trips and work-package CSV inside verified bundles. Both exporters use one
escaping function, whose bytes are bound in bundle implementation fingerprints.
Original protocol JSON remains unchanged; no spreadsheet application was invoked.

Multi-result extraction increment (2026-11-03): 73 tests passed. Nine new extraction tests
cover multiple endpoint rows from one record, distinct record/study counts, legacy
ID defaults without mutation, duplicate/malformed IDs, extraction-level context
and work links, remaining unextracted records, full-text reconciliation of every
result and preservation of null findings in verified bundles. Extraction
completeness and scientific independence are not established.

The same increment includes one ZIP portability regression: a simulated Windows
creator previously changed archive bytes despite identical input/code. Fixed
creator metadata now makes those byte streams identical. Actual multi-platform
CI verifies runtime behavior separately.

Report extraction accounting increment (2026-11-03): 78 tests passed. Five new
tests distinguish report-level extraction from title/abstract record queues,
exclude unretrieved/excluded reports, prevent alias/result-row count inflation,
and run a combined plan + context + multi-result + full-text + bundle scenario
through CLI subprocesses while preserving pending reviews and readiness bounds.

Supplied appraisal provenance increment (2026-11-03): 87 tests passed. Nine new
tests cover provenance/domain requirements, missing appraisal coverage, duplicate
and dangling links, same-study scope, preservation of differing reviewer judgements,
legacy inputs, dates/shapes and report/bundle propagation. No appraisal method,
domain rubric, source authenticity or scientific adequacy was evaluated.

JSON entrypoint consistency increment (2026-11-03): 93 tests passed. Six new
tests cover duplicate/nested keys, nonfinite/overflow numbers, all four CLIs on
ambiguous/nonobject inputs, UTF-8 output under a forced ASCII stream environment,
unpaired-surrogate-safe diagnostics, and malformed bundle manifests without tracebacks. The shared parser is included
in implementation fingerprints; no external services were invoked.

Offline comparison increment (2026-11-03): 102 tests passed. Nine new tests cover
unchanged/key-reordered inputs, unversioned result changes, version-label bounds,
additional result rows without study inflation, reconciled full-text exclusions,
new source records, context/appraisal/plan changes, no-report input and strict
repeatable CLI output. Positional work-package IDs are explicitly warned about.

Comparator review also closed a shared workflow error path: malformed screening,
evidence and gap containers/rows now return validation errors instead of
AttributeError tracebacks. Regression cases run through the comparison CLI.
