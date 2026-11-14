# Synthetic-test runtime budget

This is a test-only performance increment, not a faster or more permissive research
engine. Production Python files and ENGINE_FILES remain byte-identical. The single
converted loop is `test_catalog_schema_files_and_parser_help_entrypoints_are_real`:
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
script is not part of this narrow contract. Only reviewed help paths are converted.
`encoding='ascii'` tests stream reconfiguration, not locale or PYTHONUTF8 startup.

## Preserved process coverage

All other pre-existing tests remain unchanged, including:

- Every guide `sh` walkthrough and journey, including setup-class work.
- Actual CLI roundtrips, every json_io ambiguous/non-object rejection, and explicit
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
