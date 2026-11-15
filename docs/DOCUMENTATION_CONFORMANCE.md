# Local documentation conformance and explicit coverage

Roadmap common #102, Sensei-only implementation. This is not a common library deployed to the other repositories and not proof that every guide executes. The existing command-reference/help contract already has its own test and is not replaced.

## Links and Markdown scope

The discovery test scans root Markdown and all Markdown under docs. Local file links must resolve within the checkout; decoded fragments must match the target's heading slug. External schemes and network locations are skipped, never fetched. Percent-encoded paths are decoded strictly. Escaping the checkout, malformed encoding, missing local files and missing headings fail.

The helper implements this repository's inline-link and ATX-heading dialect, not a full Markdown/CommonMark or GitHub renderer. It ignores fenced blocks, indented code and inline code; headings use lowercase, Unicode word characters/hyphen/space, spaces become hyphens, with globally unique duplicate suffixes. The tests include Hangul, duplicate/colliding headings, percent encoding, malformed paths and code fences. Reference-style definitions/links, setext headings outside initial YAML front matter, HTML links/images/comments and nested-parenthesis link destinations are not fully parsed; their appearance now fails an explicit unsupported-dialect check instead of silently claiming coverage. A later change using another dialect needs an explicit helper extension, not a silent claim of coverage. No network or visual browser verification follows from link success.

## Every existing shell block is registered, not necessarily executed

`tests/doc_block_registry.json` pins all 197 existing sh-block contents and assigns an explicit class. `tests/doc_conformance_prior_bytes.json` proves their exact preservation against the previous release and pins existing product, example, schema and workflow bytes.

- **run:** 16 explicitly reviewed blocks, 77 commands, with shipped fictional examples and exact argv allowlists. Each block gets a fresh temporary output directory; only named scratch paths are remapped. Python is invoked directly, never a shell. Script names are separately allowlisted. Each invocation has a 30-second timeout, stdin disabled, bounded captured-output inspection and exact expected exit/stderr checks. The output-size check happens after execution, so it is not a disk/CPU/memory resource sandbox. Templates remain incomplete templates; no human choice is fabricated.
- **parse-only:** one two-command research-bundle block. The explicitly reviewed parser runs, then a sentinel stops before product reads or writes. Tests prove create/verify are never invoked. Passing means argument syntax only, not that the inputs exist or an archive works.
- **covered-by:** 19 blocks in ten guides point to exact existing bespoke test methods and source hashes. Those tests model their own fictional human steps and execute during ordinary discovery; this checker does not run them a second time. Changing their source requires renewed review of this declared link. A filename mention alone is not proof of execution.
- **exempt:** 161 blocks do not receive execution/parse coverage from this generic runner. Reasons include supplied inputs, prior human steps, cross-block prerequisites, recursive test invocation, explicit opt-in scale measurements and commands not reviewed for generic execution. Some already have other bespoke tests; this class is not a claim that they are untested. It is an explicit limit of this registry.

A changed or newly added sh block must be deliberately reviewed and registered. Editing the hash is not a substitute for reviewing its behavior. Unknown/unapproved commands never become runnable merely because they appear in documentation. External operations, real-data paths, human review choices, policy decisions, whole-suite recursion and scale probes are not generic-run candidates.

## Cost and historical correction

The initial local new test run passed seven tests in 5.533 seconds, including 77 actual fixture commands. A corrected compact historical-proof representation passed the same seven in 5.376 seconds. This is a local observation, not a CI budget guarantee; the unchanged eight-job matrix remains the final check.

The first exploratory argv run expected the amendment comparison's exit to be 1. Its supplied note is accepted and the existing command correctly returns 0; only the new test expectation was corrected. No product behavior changed.

Five pre-existing links in VALIDATION_HISTORY pointed through an erroneous extra docs directory after the historical text moved. Only their link targets were corrected: TEST_RUNTIME twice, DISPATCHER_SELECTION, CLI_ERROR_CONTRACT and SHARED_VIEW_ANALYSIS once each. All historical prose/results and all other prefix bytes are preserved. The test pins the exact five offsets and validates both corrected-prefix and reconstructed-original hashes. No broken-link exemption hides these corrections.

No engine, gate, scientific judgment, supplied review, existing fixture, public command or workflow changes in this revision. Conformance tests do not establish source authenticity, human independence, license permission, external interoperability or complete guide execution.

A separate read-only scan of the current Markdown found no unsupported reference definitions/links, HTML links/images/comments or nested-parenthesis destinations. The only setext-like delimiters were the initial SKILL.md YAML front matter. The initial 1112 count is supported-syntax link observations, including skipped external URLs, not a universal Markdown link census.
