# Source-bound command effects (partial coverage)

`python sensei.py contract` emits deterministic JSON; `--text` emits escaped text.
This is a declaration to inspect, not an action plan, permission, or scientific
judgment. No listed script is executed and no request is sent. The dispatcher
suppresses bytecode writes while loading the contract. Other commands may create
interpreter caches; effect profiles describe logical outputs, not a sandbox.

```sh
python sensei.py contract
python sensei.py contract --text
```

The inventory includes every command row in [COMMANDS.md](COMMANDS.md), including
parent parsers. `has_parser=false` and `usage=null` identify the two scripts for
which `--help` actually runs checks: audit_publication and verify_manifest. Do not
probe those as help. Route IDs join the existing operator catalog; `routes` carries
its unchanged required human inputs and boundaries. A command with no route is
not necessarily free of human-input requirements.

## Reviewed effects, not inferred effects

There are26 reviewed subcommands: the local NBIB intake, bibliographic identity
review, screening decision, status/PRISMA views, research bundle, base scaffold,
PubMed discovery/metadata and collection native export. Every other entry is
explicitly `NOT_REVIEWED` with `effects=null`. Null means unknown, not read-only,
safe to run, or permission granted. This is partial #57 coverage, not a complete
machine contract for all repository operations. Read the guide and implementation
before using commands without an effects profile.

Each reviewed profile names actual input arguments, conditional exclusive output
arguments, network effect, success channel, handled-error channel and any explicit
negative report. `inputs` lists file arguments, not every scalar CLI parameter.
Repeated wrapper inputs contain INDEX=PATH. Success applies after accepted inputs;
profiles do not prove that any particular input will be accepted.

Important distinctions:

- NBIB `verify` can create a file via `--intake-output` or `--csv-output`.
- Collection export `verify --output` **reads** an existing native file. `create`
  with no selected bytes reports NO_OUTPUT and creates nothing.
- Scaffold `check` on an invalid draft emits JSON and exits2, not a usage error.
- Only the two declared PubMed `fetch` commands transmit queries/identifiers to
  NCBI. Matching a preview digest is not permission. A later failure may occur
  after transmission, so do not blindly retry. Contract tests use fake transports,
  never live NCBI requests.
- `sensei run`, `build_manifest --check`, and all other unreviewed commands must
  not inherit a guessed read-only classification from their names. In particular,
  a check may use temporary staging files and a dispatcher may call a fetch.
- Error quoting is not redaction. Diagnostics can include supplied paths or data.
  Handled errors are described, not every unexpected exception, failed stdout
  write, resource exhaustion, or partial output file after an OS write failure.

Do not invent exact-target receipt_id, reviewer, reviewed_at, rationale or decision
fields for a person, or copy a stale target hash merely to clear a queue. This
contract does not enforce authorship or review. It does not prohibit separately
requested agent-authored challenges/readiness assertions under existing skills.
NOT_ESTABLISHED and NOT_READY remain unchanged.

## Source drift and maintenance

The registry is [command_contract.json](command_contract.json). It pins exact bytes
of every root Python module, including dispatcher, declaration reader and engine.
A changed, missing or extra root module causes contract inspection to refuse with
stderr and exit1, without a partial stdout contract. This is not authentication:
anyone who changes the checkout can also change declarations and their hashes.
The registry's own SHA256 is included in the output. Documentation/test changes
alone do not change the root implementation binding.

For a release that changes root Python code, review affected effects and tests,
update the registry's implementation SHA256 map and command metadata, then run
contract tests and the complete suite. Regenerating hashes without reviewing
semantics does not validate declarations. COMMANDS usage is compared with actual
parser help by the existing test; no second full help subprocess loop is added.
No N-1 reader, MCP server, permission evaluator or automatic executor is provided.
