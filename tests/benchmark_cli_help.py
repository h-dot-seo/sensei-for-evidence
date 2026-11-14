"""Opt-in catalog help equivalence and timing; not a wall-clock acceptance test."""
import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import json

from review_handoff import SUPPLIED_INPUT_WORKFLOWS
from tests._cli import ROOT, run_cli


def measure(entries, repeats=3):
    if type(repeats) is not int or not 1 <= repeats <= 10:
        raise ValueError('repeats must be 1 to 10')
    samples=[]
    with tempfile.TemporaryDirectory(prefix='sensei help benchmark ') as cwd, patch.dict(os.environ, {'COLUMNS':'80'}):
        for index in range(repeats):
            outputs={};elapsed={}
            # Alternate the order to avoid always giving the second path warmed imports.
            for method in (('subprocess','in_process') if index%2==0 else ('in_process','subprocess')):
                results=[];started=time.perf_counter()
                for entry in entries:
                    args=entry['arguments'];script=entry['script']
                    if method=='subprocess':
                        result=subprocess.run([sys.executable,str(ROOT/script),*args],cwd=cwd,
                            capture_output=True,timeout=30,env=dict(os.environ,PYTHONIOENCODING='utf-8'))
                    else:result=run_cli(script,*args,cwd=cwd)
                    results.append((result.returncode,result.stdout,result.stderr))
                elapsed[method]=time.perf_counter()-started;outputs[method]=results
            if outputs['subprocess']!=outputs['in_process']:
                mismatches=[entries[i] for i,(a,b) in enumerate(zip(outputs['subprocess'],outputs['in_process'])) if a!=b]
                raise ValueError('help byte/exit mismatch: '+repr(mismatches))
            if any(code!=0 or b'usage:' not in out for code,out,err in outputs['in_process']):
                raise ValueError('catalog help did not succeed')
            if list(Path(cwd).iterdir()):raise ValueError('help wrote to empty working directory')
            samples.append(dict(repeat=index+1,**elapsed))
    return dict(python=platform.python_version(),platform=platform.platform(),entries=len(entries),
                equivalent=True,columns=80,samples_seconds=samples,
                boundary='Local serial warm-cache measurements, not CI prediction; imported modules remain shared.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args()
    entries=[entry for item in SUPPLIED_INPUT_WORKFLOWS for entry in item['entrypoints']]
    print(json.dumps(measure(entries,args.repeats),indent=2))


if __name__=='__main__':main()
