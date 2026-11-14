"""Inspect supplied research-output disclosures; no actual publication or release assessment."""
import argparse
import copy
import json
from pathlib import Path
from evidence_workflow import run
from synthesis_review import snapshot
from output_disclosure_links import link_disclosures, NEGATIVE_CLAIMS, BOUNDARY
from output_disclosure_intake import _write, MAX_PROTOCOL_BYTES
from json_io import configure_utf8_stdio, parse_json, quoted_display
from archive_safety import read_bounded


def review(protocol):
    research=run(protocol);existing=snapshot(protocol)
    context=research.get('output_disclosures')
    if context is None:context=link_disclosures(protocol,research['readiness'],research['work_packages'])
    citations=[]
    for statement in existing['statements']:
        linked=[]
        for citation in statement['citations']:
            report=citation['report'];report_id=report.get('report_id') if report else None
            linked.append(dict(citation=copy.deepcopy(citation), supplied_report_sources=[copy.deepcopy(s) for s in protocol.get('report_sources',[]) if report_id is not None and s['report_id']==report_id]))
        citations.append(dict(statement_id=statement['statement']['statement_id'],citations=linked))
    return dict(schema_version=1,question=research['question'],output_disclosures=copy.deepcopy(context),
        current_gate_ledger=copy.deepcopy(research['readiness']['gate_ledger']),
        gates_sha256=research['readiness']['gates_sha256'],citation_linkage=citations,
        citation_scope='EXISTING_SYNTHESIS_REVIEW_LINKS_PLUS_SUPPLIED_REPORT_DESCRIPTORS_NOT_SUPPORT_OR_AUTHENTICITY',
        protocol_changed=False,**NEGATIVE_CLAIMS,boundary=BOUNDARY)


def context_lines(context):
    return ['Supplied research-output disclosure records: '+str(len(context['disclosure_ledger']))+'; stale gate bindings: '+str(len(context['stale_disclosure_ids'])),
        'Declared RELEASED with NOT_READY/INSUFFICIENT context: '+str(len(context['released_with_not_ready_assertion'])),
        'Supplied labels are not actual publication or scientific closure. Mechanical release readiness: NOT_RELEASED.']


def render_text(result):
    context=result['output_disclosures'];lines=['Research-output disclosure review']+context_lines(context)
    lines.extend(quoted_display(row) for row in context['disclosure_ledger'])
    lines.append('Current citation linkage (not source authentication): '+quoted_display(result['citation_linkage']))
    return '\n'.join(lines+[BOUNDARY])+'\n'


def main():
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol',type=Path);parser.add_argument('--text',action='store_true');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        result=review(parse_json(read_bounded(args.protocol,MAX_PROTOCOL_BYTES)))
        if args.output:_write(args.output,result)
        print(render_text(result) if args.text else json.dumps(result,ensure_ascii=False,indent=2),end='' if args.text else '\n')
    except (OSError,ValueError,TypeError,KeyError,OverflowError,RecursionError,AttributeError):
        parser.exit(1,'output_disclosure_review: invalid input or unavailable output\n')


if __name__=='__main__':main()
