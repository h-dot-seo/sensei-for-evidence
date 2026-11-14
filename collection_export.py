"""Export all supplied decision-matching native occurrences, never deduplicated bibliography."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import bibliographic_intake
import nbib_intake
import nbib_batch_intake
import ris_intake
import nbib_export_parser
import ris_export_parser
from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display

MAX_BYTES=50_000_000
MAX_BINDINGS=100
FORMATS={'ris':ris_intake,'nbib':nbib_intake,'nbib_batch':nbib_batch_intake}
BOUNDARY=('Supplied title/abstract screening decision per record only, not full-text eligibility or study inclusion. '
          'Pending means no screening row; withheld means do_not_promote collection triage, not exclusion. '
          'All selected occurrences are retained, not deduplicated; repeated identifiers are not verified duplicates. '
          'Each record body equals its retained source span except a recorded leading BOM omission and synthesized '
          'terminator; separators are generated. No field normalization or decision injection. '
          'No source authenticity, exhaustive search or scientific validity established. Abstracts may be copyrighted; '
          'keep real files outside the public repository and public trackers, and check rights and authorization before sharing.')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def bounded(raw):
    if len(raw)>MAX_BYTES:raise ValueError('combined content exceeds 50 MB limit')
    return raw

def implementation_hashes():
    names={'collection_export.py'}
    for module in FORMATS.values():names.update(module.implementation_hashes())
    return {name:sha(Path(__file__).with_name(name).read_bytes()) for name in sorted(names)}

def build(protocol,bindings,decision):
    if decision not in ('include','exclude','pending','withheld'):raise ValueError('unknown decision')
    protocol=parse_json(bounded(canonical_json_bytes(protocol)))
    if type(bindings) is not list or not 1<=len(bindings)<=MAX_BINDINGS:raise ValueError('supply 1..100 typed wrappers')
    selected={};retained=0
    for b in bindings:
        if type(b) is not dict or set(b)!={'import_index','format','artifact'}:raise ValueError('invalid binding fields')
        index,kind=b['import_index'],b['format']
        if type(index) is not int or index<0 or index in selected:raise ValueError('unique nonnegative import_index required')
        if type(kind) is not str or kind not in FORMATS:raise ValueError('unknown typed format')
        raw=canonical_json_bytes(b['artifact']);retained+=len(raw)
        if retained>MAX_BYTES:raise ValueError('combined wrappers exceed 50 MB limit')
        selected[index]=(kind,parse_json(raw))
    families={'ris' if k=='ris' else 'nbib' for k,a in selected.values()}
    if len(families)!=1:raise ValueError('RIS and NBIB cannot be mixed')
    family=next(iter(families));research=run(protocol)
    ledger=protocol.get('bibliographic_imports')
    if not ledger:raise ValueError('bibliographic_imports ledger required')
    entries=ledger['imports']
    if any(i>=len(entries) for i in selected):raise ValueError('unknown import_index')
    bound=[];native={}
    for index,(kind,artifact) in sorted(selected.items()):
        FORMATS[kind].verify(artifact)
        expected=dict(entries[index]['intake'],protocol_snapshot=ledger['base_protocol'])
        if canonical_json_bytes(artifact['csv_intake'])!=canonical_json_bytes(expected):raise ValueError('wrapper differs from selected historical import')
        sources=artifact['source_exports'] if kind=='nbib_batch' else [dict(source_index=0,source_export=artifact['source_export'],parsed_export=artifact['parsed_export'])]
        for source in sources:
            for record in source['parsed_export']['records']:
                key=(index,source['source_index'],record['candidate_id'])
                if key in native:raise ValueError('duplicate native occurrence binding')
                native[key]=(source,record)
        bound.append(dict(import_index=index,format=kind,wrapper_sha256=sha(canonical_json_bytes(artifact)),receipt_sha256=entries[index]['sha256']))
    screening={r['record_id']:r for r in research['screening_ledger']}
    output=bytearray();rows=[];missing=[];expected_bodies=[];seen_records=set()
    for row in research['bibliographic_collection']['row_ledger']:
        resolution=row['resolution'];withheld=resolution['disposition']=='do_not_promote'
        rid=None if withheld else resolution['record_id']
        if rid is not None:seen_records.add(rid)
        screen=screening.get(rid)
        actual='withheld' if withheld else ('pending' if screen is None else screen['decision'])
        if actual!=decision:continue
        reason=resolution['rationale'] if withheld else (screen['reason'] if screen else None)
        common=dict(record_id=rid,candidate_id=row['candidate_id'],source_pointer=row['source_pointer'],decision=actual,reason=reason,import_index=row['import_index'])
        if row['import_index'] not in selected:
            missing.append(dict(common,status='NOT_EXPORTED',cause='NO_TYPED_WRAPPER'));continue
        kind,_=selected[row['import_index']];values=row['original_values'];prefix='ris' if kind=='ris' else 'nbib'
        source_index=int(values['nbib_source_index']) if kind=='nbib_batch' else 0
        key=(row['import_index'],source_index,values[prefix+'_occurrence_id'])
        if key not in native:raise ValueError('explicit native occurrence not found')
        source,record=native[key];text=record['raw_text'];bom=text.startswith('\ufeff')
        if bom:text=text[1:]
        endings=re.findall(r'\r\n|\r|\n',text);ending=endings[-1] if endings else '\n'
        added=not text.endswith(('\r','\n'))
        if added:text+=ending
        raw=text.encode('utf-8');start=len(output);output.extend(raw)
        if family=='nbib':output.extend(ending.encode('ascii'))
        if len(output)>MAX_BYTES:raise ValueError('output exceeds 50 MB limit')
        expected_bodies.append(text)
        rows.append(dict(common,status='EXPORTED',format=kind,source_index=source_index,source_id=source.get('source_id'),native_candidate_id=record['candidate_id'],original_export_sha256=source['source_export']['sha256'],source_span=record['source_span'],output_span=dict(byte_start=start,byte_end=start+len(raw),sha256=sha(raw)),bom_omitted=bom,terminator_added=ending if added else None))
    # Canonical records not represented by any bibliographic occurrence are not inferred as native.
    for provenance in research['record_provenance']:
        rid=provenance['record_id'];screen=screening.get(rid);actual='pending' if screen is None else screen['decision']
        non_native=[o for o in provenance['occurrences'] if 'bibliographic_provenance' not in protocol['searches'][o['search_index']]]
        if actual==decision and (non_native or rid not in seen_records):
            missing.append(dict(record_id=rid,status='NOT_EXPORTED',cause='NON_BIBLIOGRAPHIC_SEARCH' if non_native else 'NO_BIBLIOGRAPHIC_OCCURRENCE',decision=actual,search_occurrences=non_native))
    raw=bytes(output)
    if raw:
        # The existing parser has a stricter 10 MB cap: retain it, do not relax engine constants.
        parser=ris_export_parser if family=='ris' else nbib_export_parser
        parsed=parser.parse_export(raw)
        if [r['raw_text'] for r in parsed['records']]!=expected_bodies:raise ValueError('generated output record bodies differ')
    receipt=dict(schema_version=1,status='EXPORTED' if raw else 'NO_OUTPUT',format=family,decision=decision,protocol_sha256=sha(canonical_json_bytes(protocol)),engine_sha256=implementation_hashes(),wrappers=bound,bytes=len(raw),sha256=sha(raw),occurrences=rows,not_exported=missing,exported_occurrences=len(rows),not_exported_count=len(missing),census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',external_calls=0,boundary=BOUNDARY)
    bounded(canonical_json_bytes(receipt))
    return raw,receipt

def verify(protocol,bindings,decision,output):
    expected,receipt=build(protocol,bindings,decision)
    if not expected:raise ValueError('no selected native occurrences; no output to verify')
    if type(output) is not bytes or output!=expected:raise ValueError('native output differs from exact replay')
    return dict(receipt,valid=True)

def main():
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for verb in ('create','verify'):
        cmd=commands.add_parser(verb);cmd.add_argument('protocol',type=Path);cmd.add_argument('--output',type=Path,required=True)
        cmd.add_argument('--decision',choices=('include','exclude','pending','withheld'),required=True)
        for kind in FORMATS:cmd.add_argument('--'+kind.replace('_','-'),action='append',default=[],metavar='INDEX=PATH')
        cmd.add_argument('--text',action='store_true')
    args=parser.parse_args()
    try:
        protocol=parse_json(bibliographic_intake.read_bounded(args.protocol,MAX_BYTES));bindings=[];total=0
        for kind in FORMATS:
            for spec in getattr(args,kind):
                index,sep,path=spec.partition('=')
                if not sep or not path or re.fullmatch('[0-9]+',index) is None:raise ValueError('wrapper requires ASCII INDEX=PATH')
                raw=bibliographic_intake.read_bounded(Path(path),MAX_BYTES-total);total+=len(raw)
                bindings.append(dict(import_index=int(index),format=kind,artifact=parse_json(raw)))
        raw,result=build(protocol,bindings,args.decision)
        if args.output.suffix.lower()!='.'+result['format']:raise ValueError('output extension differs from declared native family')
        if args.command=='verify':result=verify(protocol,bindings,args.decision,bibliographic_intake.read_bounded(args.output,MAX_BYTES))
        stdout=(quoted_display(result)+'\n') if args.text else json.dumps(result,ensure_ascii=False,allow_nan=False)+'\n'
        bounded(stdout.encode('utf-8'))
        if args.command=='create' and raw:ris_intake._write_new(args.output,raw)
    except (ValueError,OSError,KeyError,TypeError,UnicodeError,RecursionError) as error:
        parser.exit(1,'collection export: '+quoted_display(str(error))+'\n')
    print(stdout,end='')

if __name__=='__main__':main()
