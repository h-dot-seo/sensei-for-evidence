"""Opt-in old/new selection equality, source-read/AST counts and observational timing."""
import argparse
import ast
import json
from pathlib import Path
import platform
import re
import time
from unittest.mock import patch

import sensei

NAMES = ('research_status.py','json_io.py','missing.py','../research_status.py')


def legacy_resolve(name):
    """Exact round18 selection algorithm, retained only as a measurement reference."""
    listed = {script for script, _ in sensei.entry_point_scripts()}
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.py', name):
        raise ValueError('not a root script file name: ' + sensei.plain(ascii(name)))
    if name not in listed:
        raise ValueError('not a listed root script: ' + sensei.plain(name) + ' (see `python sensei.py list`)')
    return sensei.ROOT / name


def trace(resolver, names):
    reads=[];parses=[];results=[]
    original_read,original_parse=Path.read_bytes,ast.parse
    def read(path):reads.append(str(path));return original_read(path)
    def parse(*args,**kwargs):parses.append(kwargs.get('filename'));return original_parse(*args,**kwargs)
    started=time.perf_counter()
    with patch.object(Path,'read_bytes',read),patch.object(ast,'parse',parse):
        for name in names:
            try:results.append(dict(name=name,path=str(resolver(name))))
            except ValueError as error:results.append(dict(name=name,error=str(error)))
    return dict(results=results,source_reads=len(reads),ast_parses=len(parses),seconds=time.perf_counter()-started)


def measure(repeats=3):
    if type(repeats) is not int or not 1 <= repeats <= 10:raise ValueError('repeats must be 1 to 10')
    samples=[]
    for index in range(repeats):
        records={}
        for name in (('legacy','selected') if index%2==0 else ('selected','legacy')):
            records[name]=trace(legacy_resolve if name=='legacy' else sensei.resolve_script,NAMES)
        if records['legacy']['results']!=records['selected']['results']:
            raise ValueError('selected path or exact error changed on clean checkout')
        samples.append(dict(repeat=index+1,**records))
    return dict(python=platform.python_version(),platform=platform.platform(),equivalent=True,
        names=NAMES,samples=samples,boundary='Clean-checkout selection only, not full discovery or execution. Source reads/AST parses counted, not directory metadata system calls. No timing assertion or cache.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args();print(json.dumps(measure(args.repeats),indent=2))


if __name__=='__main__':main()
