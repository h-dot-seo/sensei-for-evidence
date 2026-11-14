# Explicit standalone map context in existing views

A supplied research-map sidecar can now be inspected beside status, handoff and
before/after comparison. This completes the explicit optional-view route of the
standalone increment, **not** engine/protocol/bundle integration or the full roadmap.
No map is auto-discovered from a filename or from protocol fields. No record, map,
stop event, review, gate, queue or canonical decision is modified or inferred.

```sh
python research_status.py examples/bibliographic-base.json --research-map examples/research-map-sidecar.json --text
python review_handoff.py examples/bibliographic-base.json --research-map examples/research-map-sidecar.json --text
python compare_runs.py examples/bibliographic-base.json examples/bibliographic-base.json --before-map examples/research-map-sidecar.json --after-map examples/research-map-sidecar.json --text
```

The same explicit files work with JSON stdout (omit --text). Status/handoff add a
separate research_map_context section: protocol/document/current-basis hashes,
all current/stale record IDs, source statuses, explicit stop-event links and uncovered
planned search IDs. The summary does not copy all supplied free-text assertions;
[research_map.py review](RESEARCH_MAP.md) remains the full authored-map inspection.
Labels, IDs and hashes can still be sensitive. Text quotes supplied identifiers so
control characters cannot become additional display lines.

Map context is protocol-wide even with handoff --work-package. It is not a selected
work-package applicability claim. Existing manual_review_steps, work selection,
queues, counts and readiness remain untouched. No new task or blocking gate is derived
from stale map records, missing stop rules or events. All records remain visible,
not a selected latest statement or consensus.

Comparison requires both --before-map and --after-map, each explicitly paired to its
own protocol. One alone is usage error exit2. It adds two map contexts and separate
map_document_changed/basis_changed/supplied_changes fields. Added/removed IDs, changed
supplied fields and list order are shown separately for records and events. Changing
only a recorder/date/statement/event note can change the document without changing the
basis. Changing only protocol version can change the full protocol digest without
changing the map basis. A changed basis can stale records even if the sidecar itself
is identical. No copying of a current hash renews any record automatically.

The existing top-level has_changes/unversioned_change and amendment check still refer
only to protocols and their supplied amendment, not the map. Map-only differences do
not change command exit decisions. Existing amendment MISMATCH remains JSON/text
stdout plus exit1. Valid map differences are not errors. Invalid or unreadable supplied
map/protocol inputs produce fixed stderr with empty stdout/exit1, without path or
parser exception contents; usage remains argparse exit2. Normal reports are not an
anonymizer.

## Default and implementation boundaries

Without map options, no extra section is emitted. Regression baselines cover12 default
views over four existing protocol fixtures, preserving complete JSON serialization
and text apart from the source digests named below. Only these exact top-level implementation digest entries are exempt from
the old JSON baseline and checked against current source bytes instead:

- status: engine_sha256/research_status.py
- handoff: engine_sha256/research_status.py and engine_sha256/review_handoff.py
- compare: engine_sha256/compare_runs.py

Compare text prints engine_sha256, so its same named compare_runs.py digest is also
substituted with the recorded baseline value solely for text comparison. No line is
removed and no other text is normalized. Status/handoff text does not print those hashes.
No other field, nested hash, count, queue or claim is excluded. Optional context carries
its own research_map.py/engine/research_map_views.py implementation bindings. The
standalone map module itself is unchanged, so its earlier exact replay is not altered
by this display integration. Existing research bundles still neither retain nor
validate sidecars, and run()/adapter validation is unchanged.

Explicit map reads are bounded to10MB/depth128; optional joined JSON/text views are
bounded to50MB. Input/JSON/processing failures fail closed rather than silently dropping
a supplied map. Existing default-view limits and semantics remain as before. The
optional context runs the existing standalone validator as well as normal views;
there is no claim of constant-time processing or performance improvement. No external
calls, source-file reading, automatic plan generation or scientific assessment occurs.
