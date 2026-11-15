# Shared metadata preflight for seven existing ZIP workflows

Roadmap #54's remaining duplication is consolidated in the existing
`archive_safety.py` leaf. This is a maintenance change, **not** a newly discovered
vulnerability, a stronger archive guarantee, a new format or a new acceptance rule.
The seven verifiers already had metadata preflight, bounded inputs, semantic checks,
attack regressions and final whole-canonical-byte comparison before this change.

## Exact scope

The affected modules are collection_bundle, batch_collection_bundle,
native_collection_bundle, report_transition_bundle, extraction_transition_bundle,
appraisal_transition_bundle and work_transition_bundle. Each retains its existing
`_check_entries` entry point. The three collection wrappers delegate the existing
name predicate, entry limit and `_size` function. The four transition wrappers keep
their fixed/application-name predicate and their exact fixed-member-missing errors.
Missing required collection members remain checked by the existing verifier body.

`check_dynamic_stored_entries(archive, allowed, max_entries, size_check)` uses trusted
implementation callbacks, never code loaded from a supplied artifact. It preserves:

1. One metadata inventory in its original order.
2. Entry-count and duplicate-name rejection before size or name callbacks.
3. The caller's existing declared-total-size check and its own error message.
4. Per-entry name predicate first, then directory/encryption/STORED/size-equality/
   creator/regular-file metadata checks, with the existing short-circuit order.
5. The original ordered list of member names for the caller's remaining checks.

It never opens or reads a payload. Required member sets, ZIP reading/CRC failures,
exact schema and receipt binding, implementation fingerprints, semantic replay and
full canonical-byte comparison stay in their original callers. No additional magic,
offset, timestamp, EOCD or overlap rule is inferred or introduced by this helper.
The size callback retains each archive's existing size meaning and thresholds.

The seven previous wrapper bodies totalled102 source lines. Their new wrapper
bodies total34, plus19 lines for the common function:53 body lines rather than102,
plus seven new import statements. These counts include function docstrings and use
AST start/end locations. The value is one shared place to maintain these mechanics,
not a demonstrated CPU/memory or CI-time improvement. Some local wrappers remain
intentionally: their required-member rules and diagnostics are not interchangeable.

## Boundaries and compatibility

Exactly eight root files change: the existing ENGINE leaf archive_safety plus the
seven wrappers. Existing `read_bounded`, `_read_stream`, and research ZIP
`check_stored_entries` are unchanged. All seven build/verify function bodies and
recorded ENGINE filename sets are unchanged. The shared leaf was already present
in their transitive research implementation maps; no unrecorded helper is introduced.
All scientific decisions, gate rules, review requirements and original inputs retain
their existing authority. No source is fetched, extracted or executed.

Actual implementation **bytes** change, so old receipts/archives still require the
matching recorded implementation. The controlled old/new ZIP experiment below does
not mean that a newly released archive has identical fingerprints to a previous
release. No old archive or real review is rewritten. Only the fixed15 fictional
walkthrough target fields are refreshed against their actual regenerated targets;
reviewer, date, decision and every other example byte remain unchanged. There is no
public automatic refresh tool or license/tag-policy change.

## Checks performed

`tests/test_archive_preflight_shared.py` compiles the exact previous seven local
module sources reconstructed from named fragment reversals, rather than copying
an assumed older algorithm into a new expected-value function. It compares15 metadata
variants under both successful and failing size callbacks for all seven callers:
210 old/new pairs. Outcomes include ordered names or exact exception class/message;
event traces compare inventory, size, name-regex/predicate and directory checks.
Fake archives refuse any payload read/open. Existing real-ZIP mutation matrices
continue to cover CRC, malformed headers, compression, encryption, declared sizes,
extra/missing entries, path/type metadata, trailing bytes and semantic tampering.

A second test constructs real archives in all seven workflows under an explicitly
controlled prior-implementation read map for exactly the eight changed source files.
It compares old/current archive bytes and replays them through both verifiers.
Only those implementation-byte reads are controlled; inputs, payloads, results and
output bytes are not normalized. This separates algorithm equivalence from the
intentional release fingerprint change. The old function source, new source,
unchanged build/verify bodies and existing research checks are also compared.

Historical baseline JSON files are retained. Compatibility layers reverse exact
new source fragments and the fixed fictional target substitutions before older
revisions' existing proofs. Output comparisons allow only explicitly named
implementation hash fields, not arbitrary text changes or semantic differences.
Passing these synthetic tests is not proof of complete archive safety, provenance,
real reviewer independence, scientific adequacy or overall resource confinement.
