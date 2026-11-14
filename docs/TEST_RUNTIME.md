# Synthetic-test runtime budget

The initial two increments documented here (0.104.0 and 0.105.0) are test-only,
not a faster or more permissive research engine. Those increments leave production
Python and ENGINE_FILES byte-identical. The later, separately scoped production
dispatcher change is linked at the end of this guide. The first
converted loop was `test_catalog_schema_files_and_parser_help_entrypoints_are_real`:
it still runs every one of the 129 actual CLI help parsers from an empty working
directory and asserts success, usage output and no output files.

## Trusted serial harness

`tests/_cli.py` runs an explicitly selected reviewed script with `runpy.run_path`
as `__main__`, a script-root import path and fresh byte-backed text streams.
It captures stdout/stderr as bytes. SystemExit None means 0, integers are returned
directly and other values are printed to stderr with code 1. Ordinary exceptions
produce a traceback and code 1; KeyboardInterrupt propagates after restoration.
The helper restores argv/path objects and contents, stdin/stdout/stderr, cwd and
environment in a finally block, including setup and exceptional paths.

This is **not process isolation**. Imported module caches remain shared. No startup,
signal, timeout, `os._exit`, environment-at-interpreter-start or process-level effects
are simulated. Integer exit values are not encoded as platform wait statuses.
Traceback frames differ from a fresh interpreter. Do not use this helper for unknown
scripts, threaded tests, side-effectful imported modules, startup behavior or tests
that specifically require a subprocess. Closing/replacing harness streams inside a
script is not part of this narrow contract. Only reviewed help and clean JSON-rejection paths are converted.
`encoding='ascii'` tests stream reconfiguration, not locale or PYTHONUTF8 startup.

## Preserved process coverage

Apart from the explicitly described JSON rejection loop below, existing process
tests remain unchanged, including:

- Every guide `sh` walkthrough and journey, including setup-class work.
- Actual CLI roundtrips, per-CLI real JSON-rejection smoke, and explicit
  environment/PYTHONIOENCODING tests.
- Dispatcher subprocess behavior and `-c` checks requiring fresh interpreters.
- Existing real-process smoke/roundtrip tests for every script in the help catalog.

The new contract tests compare real subprocess stdout/stderr bytes and exit status
for representative root/subcommand help, parser error, normal/noninteger/integer
exits, raw stdin/output and UTF-8 reconfiguration from ASCII streams. They exercise
restoration on success, SystemExit, ordinary exceptions, KeyboardInterrupt and
setup failure, and verify sequential invocations do not reuse captured output.

## Reproduce the measurement

From the repository root, run `python -m tests.benchmark_cli_help --repeats 3`.
This opt-in benchmark executes the same complete help catalog through both paths,
compares every returncode/stdout/stderr tuple exactly, asserts no output files, and
prints JSON timings and platform metadata. COLUMNS=80 makes argparse wrapping
comparable. Repeat order alternates; there is no timing assertion. It is not run in
full during ordinary discovery, because that would reintroduce all removed processes.

Local Python 3.12.14/Linux measurements for 129 entrypoints:

| Repeat | Subprocess seconds | In-process seconds |
|---|---:|---:|
| 1 | 5.945 | 0.465 |
| 2 | 5.183 | 0.444 |
| 3 | 5.167 | 0.426 |

All three full-catalog comparisons matched exactly. This saves roughly five seconds
in this local loop, **not** a claim that the whole suite or Windows CI shrinks by the
same ratio. Local full-suite and remote job numbers are affected by load and runner
variation. Prior PR21 Windows 3.10 job was 452 seconds (test step 385), Windows 3.12
368 seconds (test step 354); these are baseline observations, not regression limits.

CI's existing ten-minute timeout is unchanged. Python 3.12 jobs now use unittest
`--durations 25`; Python 3.10 keeps the supported original invocation. When Windows
jobs exceed six minutes, inspect the slowest tests before expanding conversion.
Duration output omits class fixture costs such as setUpClass, so also measure total
module/job time. Do not remove checks, inflate timeouts or convert document/process
semantics merely to make numbers smaller. Larger bundle computation may dominate
runtime and needs a separate measured proposal, not this harness.

## Follow-up: bounded JSON rejection loop

The second increment converts only the six-input/four-command loop in
`test_all_clis_reject_ambiguous_or_nonobject_input`. These are pure parsing/rejection
paths, not interpreter startup, signal or environment tests. All 24 assertions still
run through their real main functions. Input bytes are now also checked unchanged.
A new real-subprocess rejection smoke covers each of evidence_workflow, prisma_reports,
validate_run and research_bundle create, comparing exact bytes/exit with the harness.
The existing ASCII-environment Unicode roundtrip and bundle fingerprint tests are
untouched. Every bundle invalid-input test also stays subprocess-based in this slice.

The original loop took 0.840s locally, compared with 0.493s for the measured batch
bundle invalid-input loop. Neither dominates the full suite; screening batch lifetime
checks and dispatcher work are larger, separately scoped bottlenecks. This increment
claims a modest local saving, not a major full-suite speedup.

Run `python -m tests.benchmark_cli_json_rejections --repeats 3` to reproduce the exact
24-case comparison. The shared synthetic matrix retains duplicate keys, NaN, null,
array and malformed-surrogate cases verbatim. Every case checks exact bytes/exit,
no output creation, unchanged source bytes and restoration of interpreter surfaces.
Alternate order and full platform metadata are recorded; no timing assertion exists.
The ordinary suite keeps four actual-process error checks rather than rerunning the
entire opt-in benchmark. All previous harness limitations still apply.

| Repeat | Subprocess seconds | In-process seconds |
|---|---:|---:|
| 1 | 0.762 | 0.063 |
| 2 | 0.734 | 0.056 |
| 3 | 0.741 | 0.056 |

All 24 cases matched in all three runs. The four retained subprocess smoke calls cost
about 0.176s locally, so the net saving is smaller than the raw table difference.
Measurements use Python 3.12.14/Linux and are not a prediction for other runners.
In that JSON-test increment, production code, shared harness, workflow matrix,
timeouts and supported semantics are unchanged.

## Separate user-path optimization

[Dispatcher selection](DISPATCHER_SELECTION.md) is a separate production-code
increment, not another test conversion. It removes full AST discovery from explicit
script selection while retaining full list/check behavior and actual subprocess tests.
