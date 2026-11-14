"""Explain or check documented JSON shapes with a bounded offline subset, never approve inputs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from json_io import configure_utf8_stdio, parse_json

MAX_SCHEMA_BYTES=10_000_000
MAX_DOCUMENT_BYTES=50_000_000
MAX_DEPTH=64
MAX_NODES=100_000
MAX_ERRORS=100
MAX_COMPARE_CHARS=5_000_000
KEYWORDS={'$schema','title','description','type','properties','required','additionalProperties',
          'items','minItems','maxItems','minLength','enum','const','pattern','oneOf','uniqueItems'}
TYPES={'object','array','string','integer','number','boolean','null'}
PATTERNS={'^[0-9a-f]{64}$','^[0-9]{4}-[0-9]{2}-[0-9]{2}$'}
BOUNDARY=('Descriptive shape subset only, not the authoritative Python validator, exact-target review, '
          'input acceptance, compatibility, permission or scientific approval. No source/context/ID '
          'cross-reference, source-hash binding, real calendar date, nonblank text or research adequacy '
          'is established. JSON numeric integer1.0 may pass where Python requires integer1. '
          'No network, external schema reference, model call, data mutation or output-file creation. '
          'Use the recorded implementation and the workflow target/assemble/verify checks. '
          'Schema metadata and diagnostic property names may be private; this is not anonymization.')


def _json_tree(value,depth,budget):
    budget[0]+=1
    if depth>MAX_DEPTH or budget[0]>MAX_NODES:raise ValueError('JSON tree complexity limit')
    if type(value) is dict:
        if any(type(key) is not str for key in value):raise ValueError('non-JSON key')
        for child in value.values():_json_tree(child,depth+1,budget)
    elif type(value) is list:
        for child in value:_json_tree(child,depth+1,budget)
    elif type(value) not in (str,int,float,bool,type(None)):
        raise ValueError('non-JSON value')
    elif type(value) is float and not math.isfinite(value):raise ValueError('nonfinite number')


def _schema(schema,depth=0,budget=None):
    budget=[0] if budget is None else budget;budget[0]+=1
    if depth>MAX_DEPTH or budget[0]>MAX_NODES:raise ValueError('schema complexity limit')
    if type(schema) is not dict or set(schema)-KEYWORDS:raise ValueError('unsupported schema keyword or shape')
    if '$schema' in schema and schema['$schema']!='https://json-schema.org/draft/2020-12/schema':
        raise ValueError('unsupported schema dialect declaration')
    for key in ('title','description'):
        if key in schema and type(schema[key]) is not str:raise ValueError('invalid annotation')
    if 'type' in schema:
        kinds=schema['type'] if type(schema['type']) is list else [schema['type']]
        if not kinds or any(type(k) is not str or k not in TYPES for k in kinds) or len(kinds)!=len(set(kinds)):
            raise ValueError('invalid schema type')
    for key in ('minItems','maxItems','minLength'):
        if key in schema and (type(schema[key]) is not int or schema[key]<0):raise ValueError('invalid schema bound')
    for key in ('additionalProperties','uniqueItems'):
        if key in schema and type(schema[key]) is not bool:raise ValueError('only boolean '+key+' supported')
    if 'pattern' in schema and schema['pattern'] not in PATTERNS:raise ValueError('pattern outside audited ASCII subset')
    if 'required' in schema:
        value=schema['required']
        if type(value) is not list or any(type(k) is not str for k in value) or len(value)!=len(set(value)):
            raise ValueError('invalid required list')
    if 'enum' in schema:
        value=schema['enum']
        if type(value) is not list or not value:raise ValueError('invalid enum')
    if 'properties' in schema:
        if type(schema['properties']) is not dict:raise ValueError('invalid properties')
        for child in schema['properties'].values():_schema(child,depth+1,budget)
    if 'items' in schema:_schema(schema['items'],depth+1,budget)
    if 'oneOf' in schema:
        if type(schema['oneOf']) is not list or not schema['oneOf']:raise ValueError('invalid oneOf')
        for child in schema['oneOf']:_schema(child,depth+1,budget)


def _equal(a,b,depth=0,budget=None):
    budget=[0] if budget is None else budget;budget[0]+=1
    if depth>MAX_DEPTH or budget[0]>MAX_NODES:raise ValueError('equality complexity limit')
    if len(budget)<2:budget.append(0)
    if type(a) is str and type(b) is str:
        budget[1]+=len(a)+len(b)
        if budget[1]>MAX_COMPARE_CHARS:raise ValueError('string comparison budget')
    if type(a) in (int,float) and type(b) in (int,float):return a==b
    if type(a) is not type(b):return False
    if type(a) is dict:return set(a)==set(b) and all(_equal(a[k],b[k],depth+1,budget) for k in a)
    if type(a) is list:return len(a)==len(b) and all(_equal(x,y,depth+1,budget) for x,y in zip(a,b))
    return a==b


def _type(value,name):
    if name=='integer':return type(value) is int or type(value) is float and math.isfinite(value) and value.is_integer()
    if name=='number':return type(value) in (int,float)
    return type(value) is {'object':dict,'array':list,'string':str,'boolean':bool,'null':type(None)}[name]


def _pointer(path,key):return path+'/'+str(key).replace('~','~0').replace('/','~1')


def _check(schema,value,path,depth,budget):
    budget[0]+=1
    if depth>MAX_DEPTH or budget[0]>MAX_NODES:raise ValueError('document/check complexity limit')
    errors=[]
    def error(rule,pointer=path):errors.append(dict(input_pointer=pointer,rule=rule))
    if 'type' in schema:
        kinds=schema['type'] if type(schema['type']) is list else [schema['type']]
        if not any(_type(value,k) for k in kinds):error('type');return errors
    if 'const' in schema and not _equal(value,schema['const'],depth+1,budget):error('const')
    if 'enum' in schema and not any(_equal(value,item,depth+1,budget) for item in schema['enum']):error('enum')
    if type(value) is dict:
        props=schema.get('properties',{})
        for name in schema.get('required',[]):
            if name not in value:error('required',_pointer(path,name))
        for name,item in value.items():
            if name in props:errors.extend(_check(props[name],item,_pointer(path,name),depth+1,budget))
            elif schema.get('additionalProperties') is False:error('additionalProperties',_pointer(path,name))
            if len(errors)>MAX_ERRORS:raise ValueError('diagnostic count limit')
    if type(value) is list:
        if len(value)<schema.get('minItems',0):error('minItems')
        if 'maxItems' in schema and len(value)>schema['maxItems']:error('maxItems')
        if schema.get('uniqueItems'):
            if len(value)>1000:raise ValueError('uniqueItems comparison limit')
            if any(_equal(value[i],value[j],depth+1,budget) for i in range(len(value)) for j in range(i)):error('uniqueItems')
        if 'items' in schema:
            for i,item in enumerate(value):
                errors.extend(_check(schema['items'],item,_pointer(path,i),depth+1,budget))
                if len(errors)>MAX_ERRORS:raise ValueError('diagnostic count limit')
    if type(value) is str:
        if len(value)<schema.get('minLength',0):error('minLength')
        if 'pattern' in schema and re.search(schema['pattern'],value) is None:error('pattern')
    if 'oneOf' in schema:
        if sum(not _check(branch,value,path,depth+1,budget) for branch in schema['oneOf'])!=1:error('oneOf')
    if len(errors)>MAX_ERRORS:raise ValueError('diagnostic count limit')
    return errors


def check(schema,document):
    budget=[0,0]
    _json_tree(schema,0,budget);_schema(schema,budget=budget)
    _json_tree(document,0,budget)
    return _check(schema,document,'',0,budget)


def _read(path,limit):
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('input byte limit')
    return raw


def main():
    configure_utf8_stdio()
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('check','explain'):
        sub=commands.add_parser(name);sub.add_argument('schema',type=Path)
        if name=='check':sub.add_argument('document',type=Path)
    args=parser.parse_args()
    try:
        raw=_read(args.schema,MAX_SCHEMA_BYTES);schema=parse_json(raw);_json_tree(schema,0,[0]);_schema(schema)
        result=dict(schema_version=1,boundary=BOUNDARY,external_calls=0,
            engine_validation='NOT_PERFORMED',cross_reference_check='NOT_PERFORMED',
            scientific_assessment='NOT_PERFORMED',census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',
            schema_sha256=hashlib.sha256(raw).hexdigest(),checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        if args.command=='explain':result.update(status='DESCRIPTIVE_SCHEMA_ONLY',schema=schema,supported_keywords=sorted(KEYWORDS))
        else:
            raw=_read(args.document,MAX_DOCUMENT_BYTES);errors=check(schema,parse_json(raw))
            result.update(status='SHAPE_MATCH_ONLY' if not errors else 'SHAPE_MISMATCH',valid=not errors,errors=errors,
                          document_sha256=hashlib.sha256(raw).hexdigest())
        encoded=json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)+'\n'
        if len(encoded.encode())>MAX_DOCUMENT_BYTES:raise ValueError('output byte limit')
    except (ValueError,OSError,TypeError,RecursionError):
        parser.exit(2,'schema check: unsupported schema, malformed input or bounded processing limit\n')
    print(encoded,end='')
    if args.command=='check' and not result['valid']:raise SystemExit(1)


if __name__=='__main__':main()
