"""Opt-in exact-byte JSON rejection matrix comparison; timing is observational only."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

from tests._cli import ROOT, run_cli
from tests._json_cli_cases import COMMANDS, REJECTIONS, arguments


def measure(repeats=3):
    if type(repeats) is not int or not 1 <= repeats <= 10:
        raise ValueError('repeats must be 1 to 10')
    samples=[]
    with tempfile.TemporaryDirectory(prefix='sensei JSON rejection ') as folder, patch.dict(os.environ,{'COLUMNS':'80'}):
        root=Path(folder);source=root/'input.json';target=root/'bundle.zip'
        for repeat in range(repeats):
            outputs={};elapsed={}
            for method in (('subprocess','in_process') if repeat%2==0 else ('in_process','subprocess')):
                results=[];started=time.perf_counter()
                for raw in REJECTIONS:
                    original=raw.encode('utf-8');source.write_bytes(original)
                    for command in COMMANDS:
                        args=arguments(command,source,target)
                        argv,path=sys.argv,sys.path;argv_values=list(argv);path_values=list(path)
                        streams=(sys.stdin,sys.stdout,sys.stderr);cwd=os.getcwd();env=dict(os.environ)
                        if method=='subprocess':
                            result=subprocess.run([sys.executable,str(ROOT/command[0]),*args],capture_output=True,timeout=20,
                                env=dict(os.environ,PYTHONIOENCODING='utf-8'))
                        else:result=run_cli(command[0],*args)
                        if (sys.argv is not argv or sys.path is not path or sys.argv!=argv_values or sys.path!=path_values
                                or (sys.stdin,sys.stdout,sys.stderr)!=streams or os.getcwd()!=cwd or dict(os.environ)!=env):
                            raise ValueError('interpreter surface changed')
                        if result.returncode==0 or b'Traceback' in result.stdout+result.stderr:
                            raise ValueError('expected clean rejection')
                        if source.read_bytes()!=original or sorted(p.name for p in root.iterdir())!=['input.json']:
                            raise ValueError('rejection changed input or produced output')
                        results.append((result.returncode,result.stdout,result.stderr))
                elapsed[method]=time.perf_counter()-started;outputs[method]=results
            if outputs['subprocess']!=outputs['in_process']:
                raise ValueError('JSON rejection byte/exit mismatch')
            samples.append(dict(repeat=repeat+1,**elapsed))
    return dict(python=platform.python_version(),platform=platform.platform(),cases=len(COMMANDS)*len(REJECTIONS),
        equivalent=True,input_and_output_preserved=True,interpreter_surfaces_restored=True,samples_seconds=samples,
        boundary='Local serial warm-cache observation, not total-suite/CI prediction; imported modules remain shared.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args();print(json.dumps(measure(args.repeats),indent=2))


if __name__=='__main__':main()
