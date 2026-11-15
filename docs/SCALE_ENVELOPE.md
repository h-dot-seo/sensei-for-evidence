# Opt-in local synthetic scale observations

Roadmap #52 adjustments (4), (5), (9): an explicit local measurement, not a performance guarantee or an additional CI job. Existing eight CI jobs and all product sources, ENGINE, schemas and examples are unchanged.

## Run deliberately

From the checkout root, choose a fixed bounded profile. Neither importing the module nor omitting `--run` starts a measurement. Outputs are small receipts, not the generated protocol or computed payloads. An existing output path is never overwritten.

```sh
python -m tests.scale_probe --run --profile smoke --output smoke-observation.json
```

For an explicitly selected larger local run, replace `smoke` with `moderate` or `large`. Large runs are not part of automatic test discovery. No remote services, external data or new workflow are used. Do not infer a safe machine-memory requirement from these input bounds.

| Profile | Records | Results | Work packages | Searches | Maximum statement width |
| --- | ---: | ---: | ---: | ---: | ---: |
| smoke | 200 | 50 | 20 | 2 | 4 |
| moderate | 4000 | 1000 | 300 | 4 | 4 |
| large | 40000 | 10000 | 3000 | 4 | 4 |

Each included record has one result, each work package one evidence link, and statement groups are disjoint. Contexts, experimental units, appraisals and reports are absent. Wider cross-links can grow quadratically; this narrow shape does not characterize them.

## What is measured

Eight real product calls execute: engine, status, synthesis, work review, handoff, self-comparison, research ZIP creation, then verification of those exact created bytes. Imports precede timing. Generation, canonical input serialization, product computation and output serialization have separate durations. These are warm-process wall-clock observations, not CPU measurements. Peak memory and CPU are explicitly NOT_MEASURED.

The receipt records UTC observation time, Python/OS/architecture (not hostname or local paths), probe and fictional seed hashes, all root Python source hashes, canonical compact UTF-8 input bytes/hash, complete output bytes/hash and source-input preservation. The root inventory is not dependency tracing or identity authentication. JSON output hashes cover indented UTF-8 plus LF, not native platform newline translation; ZIP hashes cover exact bytes.

Input is capped at 50,000,000 UTF-8 bytes, each serialized output at 50,000,000 bytes, receipt at 1,000,000 bytes. Output accounting occurs AFTER the product computes/allocates its result. It cannot bound product CPU, peak memory or allocation. Over-budget output has no full size/hash claim: bytes/sha256 are null and observed_at_least_bytes is only a lower bound. PRODUCT_REFUSED and SERIALIZATION_REFUSED remain distinct; verification without successful bundle creation is NOT_RUN_PREREQUISITE_FAILED. Any incomplete operation or changed input yields INCOMPLETE_OBSERVATION and CLI exit 1. Usage errors remain exit 2. Fixed diagnostics do not print exception messages or payloads. An interrupted process may produce no receipt; an interrupted exclusive output write may leave a partial file. No timeout, process isolation, atomic publication or total privacy guarantee is claimed.

## Dated observations, not a baseline SLA

The following were explicitly run locally on 2026-11-15, CPython 3.12.14, Linux 6.18.57, x86_64. Both profiles completed all eight operations. Times vary by machine/load; no speedup or general linear bound follows. Product code and fictional seed hashes are retained in the local receipts. This table is an observation summary, not an authenticated benchmark.

### moderate

Observed 2026-11-15T05:24:14.670521+00:00. Input 828,191 bytes; SHA-256 `36e00ec3645857cec6fa7c13d4d28d0205d1956200f8cf6c765de62760c8582a`. Generation 0.010638s; input serialization 0.006885s.

| Operation | Output bytes | Compute seconds | Output serialization seconds |
| --- | ---: | ---: | ---: |
| engine | 3,790,772 | 0.054000 | 0.101093 |
| status | 70,745 | 0.049406 | 0.000720 |
| synthesis | 4,866,039 | 0.123503 | 0.131083 |
| work | 2,167,265 | 0.067696 | 0.054260 |
| handoff | 1,168,192 | 0.169868 | 0.023954 |
| self_comparison | 1,222,072 | 0.185144 | 0.036046 |
| bundle_create | 4,766,900 | 0.245622 | 0.002671 |
| bundle_verify | 205 | 0.219742 | 0.000039 |

### large

Observed 2026-11-15T05:24:16.420035+00:00. Input 8,401,795 bytes; SHA-256 `34dbf551ab163f4d8a760f42e7113dae19a8c78632442607d7c0a71277b1be86`. Generation 0.121305s; input serialization 0.097893s.

| Operation | Output bytes | Compute seconds | Output serialization seconds |
| --- | ---: | ---: | ---: |
| engine | 38,101,549 | 1.752968 | 1.044881 |
| status | 652,101 | 1.731896 | 0.006189 |
| synthesis | 48,809,916 | 2.588315 | 1.365006 |
| work | 21,709,173 | 2.044856 | 0.568761 |
| handoff | 11,151,906 | 3.667780 | 0.238229 |
| self_comparison | 12,168,392 | 4.623769 | 0.358965 |
| bundle_create | 47,917,494 | 5.736112 | 0.026952 |
| bundle_verify | 205 | 5.749681 | 0.000062 |

The large synthesis output (48,809,916 bytes) and ZIP (47,917,494 bytes) approach the existing 50 MB limit. Wider or different inputs may exceed it or be refused earlier by existing product validators. No limit was raised. A receipt COMPLETE means these calls and output accounting completed, not READY, scientific validity, authentic review or external interoperability.
