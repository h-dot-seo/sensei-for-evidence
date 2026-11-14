# One-file dispatcher selection

Unlike the preceding test-harness changes, this increment changes a real user path:
`python sensei.py run SCRIPT ...`. It avoids reading and parsing every root Python
file before selecting one script. Script arguments, actual execution, stdout/stderr,
exit propagation and the existing command list are unchanged on a healthy checkout.
ENGINE_FILES and the scientific workflows are unchanged.

## Selection versus discovery

The selector first validates the existing literal basename grammar, then rejects
the dispatcher itself, missing files, directories and non-exact directory-entry
spellings. Exact case still matters on Windows: an existing `Chosen.py` does not
authorize `chosen.py`. It enumerates directory names for this check, but does not
open or parse unrelated files. The selected file is read once and parsed once,
then the existing structural main/`__main__` check decides eligibility. Helpers,
paths, traversal, glob characters and hidden leading-dot names remain rejected.
The original error strings and exit behavior remain for these cases.

There is no cached eligibility. Changing a selected source into a helper or deleting
it affects the very next call. A selected source read error or syntax error still
propagates; malformed source is not silently executed. An unrelated syntax error
no longer prevents selecting a valid script. This difference is intentional:
`list` still performs full root discovery and reports that error, and `check` keeps
its whole-checkout inventory/syntax smoke behavior. Fast selection does not certify
checkout health or bypass a selected script's own validation.

This is a trusted-checkout convenience dispatcher, not a filesystem security sandbox.
The existing symlink behavior is preserved: root aliases to files can appear in
listing and selection; broken aliases are not files. There is no new guarantee
against symlink targets, file replacement between selection/execution or ancestor
races. Do not use untrusted checkout contents as code merely because a filename
passes this selector. No import or execution occurs during selection itself.

## Verification and measurement

Existing dispatcher subprocess tests remain unchanged: direct invocation versus
wrapper output/status, arbitrary working directories, argument forwarding, rejected
names, help and no eager catalog imports. New tests compare every root file's
eligibility against full discovery and cover exact-case spelling, directories,
helpers, stale eligibility, selected read/syntax errors and unrelated syntax failure.
They pin zero source reads/AST parses for invalid names and one for valid selection.
The root directory is still enumerated; these counts are not OS metadata syscall counts.

Run `python -m tests.benchmark_dispatcher_selection --repeats 3` from the repository
root. The test-only reference retains the exact previous selection algorithm and
compares selected paths or exact ValueError strings on a healthy checkout. It uses
one valid script, one helper, one missing basename and one traversal string, in
alternating old/new order, counting source reads and AST parses. No script is run,
no timing assertion exists and no runtime cache is introduced.

Local Python 3.12.14/Linux, four selections per sample:

| Repeat | Previous reads / AST parses | Selected reads / AST parses | Previous seconds | Selected seconds |
|---|---:|---:|---:|---:|
| 1 | 388 / 388 | 2 / 2 | 0.660 | 0.00237 |
| 2 | 388 / 388 | 2 / 2 | 0.674 | 0.00230 |
| 3 | 388 / 388 | 2 / 2 | 0.678 | 0.00237 |

All paths and exact errors matched. The two reads are the actual script and helper;
the missing/traversal cases do not read sources. This measures selection overhead,
not the selected script's workload, whole-suite time or a promise about CI runners.

The unchanged real-process rejected-name regression was also measured directly
against consecutive checkouts: 4.880s before and 0.466s after (one local run each).
This supports the narrower selection-overhead result; runner variation and the
script workload still determine end-to-end runtime.
