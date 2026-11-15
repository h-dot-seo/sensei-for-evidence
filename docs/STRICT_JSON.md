# Shared JSON input and explicit container depth

Roadmap #95 closes the remaining shared decoder-depth boundary. `json_io.parse_json`
rejects duplicate object keys, non-finite numbers (`NaN`, either infinity, and float
overflow), and unpaired surrogate code points in keys or strings. Those prior
rules and their diagnostics are unchanged. Input bytes/bytearrays are decoded as
strict UTF-8; the loader does not auto-detect UTF-16/32 and does not accept a leading
BOM. Existing source-format parsers have their own documented framing; this page
does not redefine NBIB/RIS/CSV grammar or every direct Python API.

## Count containers, not brackets or scalar leaves

The shared loader now permits at most **128 nested containers** on any path. A root
object or array has container depth **0**. Containers at depths 0 through 127 are
allowed; a container at depth 128 is the 129th and is rejected. Empty arrays and
objects still count. Object keys and scalar leaves do not add a container. Strings
containing bracket characters are just strings, not additional nesting.

| Input shape | Count | Shared loader |
|---|---:|---|
| A top-level number, Boolean, null or string | 0 | permitted; consumer shape validation remains separate |
| A root empty object or array | 1 | permitted |
| 128 nested arrays with a scalar leaf | 128 | permitted; deepest container depth127, leaf depth128 |
| 127 nested arrays enclosing an empty object | 128 | permitted |
| 128 nested arrays enclosing an empty object | 129 | rejected |
| Any mixed object/array path of 129 containers | 129 | rejected |
| Root protocol object plus 127 nested arrays in one value | 128 | permitted by loader; normal protocol validators still apply |
| A string containing thousands of `[` or `{` characters | 0 extra | treated as string data |

Noncharacters, finite values and integers above 2^53 remain accepted at the loader
layer. The interpreter's configured integer-digit limits still apply. This is an
explicit application contract influenced by I-JSON constraints, **not** a claim of
complete RFC conformance. Object/type/domain requirements belong to each consumer.
The canonical JSON encoder is unchanged; this decoder limit is not a universal
limit for arbitrary in-memory values passed directly to another API.

## Distinguish a decoder limit from the explicit count

After decoding, the existing iterative surrogate walk also counts containers.
Exceeding the explicit count raises `JsonNestingError`, a `ValueError` subclass,
with fixed reason `container_limit`. A `RecursionError` raised by the interpreter
JSON decoder is converted, without the supplied exception text, to the same class
with fixed reason `decoder_capacity`. The latter can happen before the iterative
walk; an extremely deep input can therefore reach different rejection reasons on
different Python versions. It is still rejected without requiring callers to catch
an interpreter-specific recursion exception. This is not pre-decoder allocation
control or a guarantee about total CPU, memory, interpreter crashes or every error.
Per-file byte bounds remain the responsibility of the existing callers.

The four already bounded CLI readers in research_status, compare_runs,
review_handoff and validate_run catch **this specific class** as their existing
`input-too-complex` category. Decoder-capacity and explicit-128 diagnostics stay
distinct. Other ValueError/Unicode/shape errors keep their existing classifications;
source paths and content are not inserted into these four fixed messages. Their
existing local shape/depth checks remain as additional consumer checks. Other
consumers that already catch ValueError handle the new rejection through their
existing error channel. This does not normalize every arbitrary Python exception
or imply all commands have the same exit or output semantics.

## Intentional compatibility cost

Previously, the shared loader could accept inputs deeper than 128 containers if
that interpreter could decode them. **Those inputs are now rejected**, including
opaque metadata and deeply nested empty containers. Four bounded CLIs already had
local checks, but their local depth convention was not a universal container cap;
this common limit is an explicit tightening, not a claim of fully unchanged input
acceptance. In-range values, successful scientific decisions and existing error
messages unrelated to depth are preserved by targeted regression tests.

`json_io.py` is in the existing research ENGINE and many artifact implementation
maps. The exact root changes are that file plus the four CLI readers named above.
Its new bytes intentionally make old recorded implementation fingerprints stale.
Keep the matching old repository revision to replay old intake artifacts/bundles;
this release does not authenticate, rewrite or automatically reseal them. Only the
fixed 15 fictional example target fields are maintained against their actually
regenerated targets. No real review, reviewer identity, date, decision or other
example byte changes. No license, gate, closure rule or research claim is added.

The new tests use exact source-fragment reversals to retain historical baseline
files instead of replacing them. Historical views substitute only declared named
implementation-hash fields, not findings, queue contents, data or arbitrary text.
The primary previous/current process comparison preserves all stdout/stderr/exit
bytes except the named `json_io.py` digest field in the two outputs that expose it.
Later shared-preflight maintenance additionally names `archive_safety.py` in those
same outputs; no other bytes or scientific results are normalized.

## Validation scope

`tests/test_json_depth.py` checks scalar/empty-container/mixed/string cases and the
128/129 boundary, UTF-8 bytes and bytearray inputs, fixed decoder-capacity errors,
unchanged duplicate/numeric/surrogate/BOM diagnostics and canonical encoder bytes.
It executes nine actual CLI entry points with 129 and 100,000 nested containers,
compares subprocess and harness bytes, and checks that no output archive is created.
It also compares four accepted previous/current CLI outputs and all 44 retained
protocol/run baselines. Existing malformed-input, byte-bound, source-private-error,
ZIP and guide tests continue to apply.

This is the **Sensei-only** implementation of the roadmap item. No assertion is made
that another repository currently has identical framing, limits, diagnostics or a
byte-identical case table. There is no cross-repository loader replacement or live
source transfer in this change.
