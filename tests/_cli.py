"""Serial, trusted-test CLI harness; not process isolation or a general subprocess replacement."""
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]


def run_cli(script, *args, cwd=None, stdin=b'', encoding='utf-8'):
    """Run a reviewed CLI in-process, capturing bytes and restoring interpreter surfaces.

    Imported-module caches remain shared. No timeout, signal, startup/environment
    semantics or child-process isolation is simulated. Use subprocess for those,
    documented command walkthroughs and real entrypoint smoke tests. Call serially.
    Integer SystemExit values are returned directly, not platform wait-status encoded.
    """
    path = (ROOT / script).resolve()
    argv = [str(path), *map(str, args)]
    old_argv, old_path = sys.argv, sys.path
    argv_values, path_values = list(old_argv), list(old_path)
    old_streams = sys.stdin, sys.stdout, sys.stderr
    old_cwd, old_environ = os.getcwd(), dict(os.environ)
    streams = [io.TextIOWrapper(io.BytesIO(stdin), encoding=encoding),
               io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors='strict'),
               io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors='backslashreplace')]
    code = 0
    try:
        sys.argv = argv
        sys.path = [str(path.parent), *path_values]
        sys.stdin, sys.stdout, sys.stderr = streams
        if cwd is not None:
            os.chdir(cwd)
        try:
            runpy.run_path(str(path), run_name='__main__')
        except SystemExit as error:
            if error.code is None:
                code = 0
            elif isinstance(error.code, int):
                code = error.code
            else:
                print(error.code, file=sys.stderr)
                code = 1
        except Exception:
            traceback.print_exc()
            code = 1
        streams[1].flush()
        streams[2].flush()
        return subprocess.CompletedProcess(argv, code, streams[1].buffer.getvalue(), streams[2].buffer.getvalue())
    finally:
        sys.stdin, sys.stdout, sys.stderr = old_streams
        old_argv[:] = argv_values
        old_path[:] = path_values
        sys.argv, sys.path = old_argv, old_path
        os.environ.clear()
        os.environ.update(old_environ)
        os.chdir(old_cwd)
        for stream in streams:
            stream.close()
