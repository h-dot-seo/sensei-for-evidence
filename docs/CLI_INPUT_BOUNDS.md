# Bounded CLI inputs

Roadmap #54, reader adjustment 7: the fifteen remaining non-intake entrypoints now
read each supplied JSON input with an inclusive **50,000,000-byte** limit before
JSON parsing. This is a raw UTF-8 byte limit, not a character count or a combined
multi-input budget. An extra byte is rejected even if it is only whitespace.

| CLI | Bounded supplied arguments |
| --- | --- |
| evidence_workflow | protocol |
| prisma_reports | protocol |
| prisma_audit | protocol |
| search_manifest | protocol |
| readiness_review | protocol |
| receipt_intake | protocol, fixture |
| report_decision | protocol, decision_document, application_record |
| report_review | protocol |
| report_study_inventory | protocol |
| report_study_inventory_review | protocol |
| report_study_review | protocol |
| screening_decision | protocol, decision_document |
| screening_review | protocol |
| synthesis_review | protocol |
| work_review | protocol |

There are nineteen distinct input-read sites. Each script declares
`MAX_CLI_INPUT_BYTES`. The existing `archive_safety.read_bounded` implementation is
reused without any changes: binary chunked reads, inclusive size, partial-stream
support, and caller stream ownership/position remain as before. Internal module
source reads for implementation fingerprints are not supplied JSON inputs.

The four formerly text-mode readers (evidence_workflow, prisma_reports,
prisma_audit, search_manifest) decode UTF-8 and explicitly preserve the old
universal-newline conversion: CRLF to LF, then remaining CR to LF. This is product
input compatibility, not output-test normalization. Thus malformed JSON error
positions retain their old meaning. All other readers still parse exact bytes.
Existing strict JSON parsing, error prefixes, ordinary and negative report exit
codes, native stdout/stderr newlines, exclusive writing and scientific decisions
are unchanged. An over-limit input now exits 1 with empty stdout and the existing
command error wrapper around `input exceeds size limit`; no new output is opened.
Previously accepted inputs over this limit are intentionally no longer accepted.
Existing malformed-input diagnostics are not newly sanitized by this change.

This is not a total memory, CPU, nesting, path-security or symlink guarantee and
not a claim to fix a known vulnerability. Limits apply only to these CLI readers,
not direct Python calls. The existing bounded status/compare/handoff/legacy-state/
research-bundle paths, offline_adapter, and seven other ZIP implementations are
not modified. The shared ZIP helper and research-bundle implementation are byte
unchanged; their tests still exercise preflight, exact canonical replay, CRC,
size/metadata rejection, bounded streams and create/verify symmetry.

## Reproducibility and verification

ENGINE source changes are exactly evidence_workflow.py, prisma_reports.py and
screening_decision.py. Their functions outside CLI main are unchanged. Recorded
implementation hashes still matter: older bundles/reviews require their recorded
implementation, and this release does not silently replay or reseal them. Only the
fixed fifteen fictional walkthrough target hashes are maintained. No real review,
reviewer, date, decision or research data is rewritten.

Historical baseline files remain intact. `cli_input_source_changes.json` records
exact old/new fragments; the compatibility helper reverses only those fragments
and tests their full previous-source SHA-256. New actual previous-release CLI
baselines cover all fifteen entrypoints. Only explicitly listed own implementation
hash strings, with exact occurrence counts, are substituted; every other stdout/
stderr byte and exit code is checked. Text error baselines include CRLF, bare CR,
embedded control characters, duplicate keys and invalid UTF-8. Size tests cover all
nineteen input sites, real subprocess/harness parity and inclusive multibyte input.
Existing documentation walkthroughs retain the accepted assembly/review/replay and
negative-report cases. This work does not expand the partially reviewed agent
command contract or confer execution permission.

Run from the repository root:

```sh
python -m unittest tests.test_cli_input_bounds tests.test_research_zip_safety -v
python -m unittest discover -v
python audit_publication.py
python verify_manifest.py
```
