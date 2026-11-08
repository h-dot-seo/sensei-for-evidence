"""Validate supplied nonclinical comparison conditions, never prescribe experiments."""
import copy
from context_links import id_list, nonempty_text

BOUNDARY = ('Each record describes one supplied treatment/comparator condition pair, not an '
            'independent statistical unit or replicate count. Values/units are preserved text; '
            'no conversion, dosing advice, procedure, effect calculation or causal assessment '
            'is performed. Source conditions and causal claims are unverified supplied assertions.')
STATES = {'reported', 'not_reported', 'not_applicable', 'unknown'}


def fields(row, required, optional, label):
    if not isinstance(row, dict) or set(row) - set(required) - set(optional):
        raise ValueError(label + ' has invalid shape or unknown fields')
    if any(key not in row for key in required):
        raise ValueError(label + ' missing required fields')


def text(row, keys, label):
    if any(not nonempty_text(row.get(key)) for key in keys):
        raise ValueError(label + ' requires nonempty text fields')


def measurement(row, label, with_unit=True):
    if not isinstance(row, dict) or not isinstance(row.get('status'), str) or row['status'] not in STATES:
        raise ValueError(label + ' requires explicit reporting status')
    required = (('status', 'source_locator', 'value') + (('unit',) if with_unit else ())) if row['status'] == 'reported' else ('status', 'source_locator', 'reason')
    fields(row, required, (), label)
    text(row, required, label)
    return row['status'] in ('not_reported', 'unknown')


def condition(row, label):
    fields(row, ('label', 'source_locator', 'concentration', 'exposure_time'), (), label)
    text(row, ('label', 'source_locator'), label)
    return [label + '.' + key for key in ('concentration', 'exposure_time') if measurement(row[key], label + '.' + key)]



def sampling(rows, refs):
    """Preserve outcome/arm-specific n semantics without computing or assessing n."""
    if not isinstance(rows, list):
        raise ValueError('outcome_sampling must be a list')
    seen, gaps = set(), []
    for row in rows:
        fields(row, ('evidence_id', 'treatment', 'comparator', 'analysis_unit',
                     'independence_basis', 'limitations', 'source_locator'), (), 'outcome sampling')
        text(row, ('evidence_id', 'limitations', 'source_locator'), 'outcome sampling')
        eid = row['evidence_id']
        if eid not in refs or eid in seen:
            raise ValueError('outcome_sampling requires each linked evidence ID exactly once')
        seen.add(eid)
        for key in ('analysis_unit', 'independence_basis'):
            if measurement(row[key], 'sampling ' + key, with_unit=False):
                gaps.append('outcome_sampling.' + eid + '.' + key)
        for arm in ('treatment', 'comparator'):
            counts = row[arm]
            fields(counts, ('animal_n', 'biological_n', 'technical_n', 'analyzed_n'), (), 'sampling arm')
            for key in ('animal_n', 'biological_n', 'technical_n', 'analyzed_n'):
                if measurement(counts[key], 'sampling ' + arm + '.' + key):
                    gaps.append('outcome_sampling.' + eid + '.' + arm + '.' + key)
    if seen != set(refs):
        raise ValueError('outcome_sampling requires each linked evidence ID exactly once')
    return sorted(gaps)


def statistics(rows, refs):
    """Check reporting shape and literal labels, never infer effects or significance."""
    if not isinstance(rows, list):
        raise ValueError('outcome_statistics must be a list')
    seen, gaps, differences = set(), [], []
    for row in rows:
        fields(row, ('evidence_id', 'treatment', 'comparator', 'contrast',
                     'limitations', 'source_locator'), (), 'outcome statistics')
        text(row, ('evidence_id', 'limitations', 'source_locator'), 'outcome statistics')
        eid = row['evidence_id']
        if eid not in refs or eid in seen:
            raise ValueError('outcome_statistics requires each linked evidence ID exactly once')
        seen.add(eid)
        prefix = 'outcome_statistics.' + eid + '.'
        for arm in ('treatment', 'comparator'):
            fields(row[arm], ('value', 'summary_statistic', 'dispersion', 'dispersion_type'), (), 'statistics arm')
            for key in ('value', 'summary_statistic', 'dispersion', 'dispersion_type'):
                if measurement(row[arm][key], 'statistics ' + arm + '.' + key,
                               with_unit=key in ('value', 'dispersion')):
                    gaps.append(prefix + arm + '.' + key)
        contrast = row['contrast']
        keys = ('measure', 'estimate', 'uncertainty', 'uncertainty_type', 'uncertainty_level',
                'statistical_test', 'p_value', 'multiplicity_adjustment', 'direction')
        fields(contrast, keys, (), 'statistics contrast')
        for key in keys[:-1]:
            if measurement(contrast[key], 'contrast ' + key, with_unit=key in ('estimate', 'uncertainty')):
                gaps.append(prefix + 'contrast.' + key)
        direction = contrast['direction']
        if isinstance(direction, dict) and direction.get('status') == 'reported':
            fields(direction, ('status', 'value', 'source_text', 'source_locator', 'orientation'), (), 'effect direction')
            text(direction, ('value', 'source_text', 'source_locator', 'orientation'), 'effect direction')
            if direction['value'] not in ('higher', 'lower', 'no_difference_reported', 'mixed', 'unclear'):
                raise ValueError('invalid supplied effect direction')
            if direction['orientation'] != 'treatment_relative_to_comparator':
                raise ValueError('effect direction requires treatment_relative_to_comparator orientation; do not auto-invert')
        elif measurement(direction, 'effect direction', with_unit=False):
            gaps.append(prefix + 'contrast.direction')
        # Exact supplied-label differences only. Different labels need not be incompatible.
        for key, label in (('value', 'unit'), ('summary_statistic', 'value'), ('dispersion', 'unit'), ('dispersion_type', 'value')):
            left, right = row['treatment'][key], row['comparator'][key]
            if left['status'] == right['status'] == 'reported' and left[label] != right[label]:
                differences.append(dict(evidence_id=eid, field=key + '.' + label,
                                        treatment=left[label], comparator=right[label]))
    if seen != set(refs):
        raise ValueError('outcome_statistics requires each linked evidence ID exactly once')
    return dict(stage='SUPPLIED', missing_fields=sorted(gaps), literal_label_differences=differences,
                numeric_consistency='NOT_ASSESSED', effect_assessment='NOT_PERFORMED',
                boundary='Values and directions are supplied unverified text. Label differences are review cues, not incompatibility findings. No arithmetic, significance, equivalence, direction inversion, effect or causal inference is performed.')

def link_experiments(protocol, evidence):
    supplied = protocol.get('experimental_units', [])
    if not isinstance(supplied, list):
        raise ValueError('experimental_units must be a list')
    known = {row['evidence_id']: row for row in evidence}
    ledger, assigned = {}, {}
    for row in supplied:
        required = ('experiment_id', 'evidence_ids', 'source_locator', 'model', 'treatment', 'comparator',
                    'observation_times', 'causal_basis', 'causal_statement', 'causal_limitations', 'causal_source_locator', 'limitations')
        fields(row, required, ('outcome_sampling', 'outcome_statistics'), 'experimental unit')
        text(row, ('experiment_id', 'source_locator', 'causal_statement', 'causal_limitations', 'causal_source_locator', 'limitations'), 'experimental unit')
        xid = row['experiment_id']
        if xid in ledger:
            raise ValueError('duplicate experiment ID')
        refs = id_list(row['evidence_ids'], 'experimental unit evidence_ids')
        if not refs or any(eid not in known for eid in refs):
            raise ValueError('experimental unit must link to known extracted evidence')
        if any(eid in assigned for eid in refs):
            raise ValueError('evidence cannot be assigned to multiple condition pairs; leave aggregate results unlinked')
        records = {known[eid]['record_id'] for eid in refs}
        studies = {known[eid]['study_id'] for eid in refs}
        if len(records) != 1 or len(studies) != 1:
            raise ValueError('one experimental condition must stay within one supplied record and study')
        model = row['model']
        fields(model, ('kind', 'label', 'source_locator', 'limitations'), (), 'model')
        text(model, ('kind', 'label', 'source_locator', 'limitations'), 'model')
        if model['kind'] not in ('in_vitro', 'in_vivo', 'ex_vivo', 'in_silico', 'other', 'unknown'):
            raise ValueError('invalid supplied model kind')
        unresolved = ['model.kind'] if model['kind'] == 'unknown' else []
        unresolved.extend(condition(row['treatment'], 'treatment'))
        comparator = row['comparator']
        if not isinstance(comparator, dict) or not isinstance(comparator.get('status'), str) or comparator['status'] not in STATES:
            raise ValueError('comparator requires explicit reporting status')
        if comparator['status'] == 'reported':
            fields(comparator, ('status', 'label', 'source_locator', 'concentration', 'exposure_time'), (), 'comparator')
            unresolved.extend(condition({k:v for k,v in comparator.items() if k != 'status'}, 'comparator'))
        else:
            fields(comparator, ('status', 'reason', 'source_locator'), (), 'comparator')
            text(comparator, ('status', 'reason', 'source_locator'), 'comparator')
            if comparator['status'] in ('unknown', 'not_reported'): unresolved.append('comparator')
        observations = row['observation_times']
        if not isinstance(observations, list):
            raise ValueError('observation_times must be a list')
        observed = set()
        for observation in observations:
            fields(observation, ('evidence_id', 'time', 'reference_event'), (), 'observation time')
            eid = observation['evidence_id']
            if not nonempty_text(eid) or eid not in refs or eid in observed:
                raise ValueError('observation times require each linked evidence ID exactly once')
            observed.add(eid)
            if measurement(observation['time'], 'observation time'):
                unresolved.append('observation_times.' + eid + '.time')
            if measurement(observation['reference_event'], 'observation reference event', with_unit=False):
                unresolved.append('observation_times.' + eid + '.reference_event')
        if observed != set(refs):
            raise ValueError('observation times require each linked evidence ID exactly once')
        if row['causal_basis'] not in ('association', 'intervention', 'unknown') or any(known[eid]['mechanism_basis'] != row['causal_basis'] for eid in refs):
            raise ValueError('supplied causal basis must match all linked extraction basis labels')
        ledger[xid] = dict(copy.deepcopy(row), record_id=next(iter(records)), study_id=next(iter(studies)),
                            unresolved_fields=sorted(unresolved), condition_review_status='NOT_ASSESSED',
                            causal_assessment='NOT_PERFORMED',
                            scope='one_supplied_comparison_condition_not_independent_statistical_unit')
        if 'outcome_sampling' in row:
            ledger[xid]['sampling_review'] = dict(stage='SUPPLIED',
                unresolved_fields=sampling(row['outcome_sampling'], refs),
                independence_assessment='NOT_PERFORMED', numeric_consistency='NOT_ASSESSED',
                boundary='Counts are supplied text by outcome and arm, not totals or independent sample sizes. No arithmetic, unit equivalence, pooling, statistical adequacy or independence is inferred.')
        if 'outcome_statistics' in row:
            ledger[xid]['statistics_review'] = statistics(row['outcome_statistics'], refs)
        for eid in refs: assigned[eid] = xid
    return dict(stage='SUPPLIED' if 'experimental_units' in protocol else 'NOT_SUPPLIED',
                experimental_unit_ledger=[ledger[xid] for xid in sorted(ledger)],
                evidence_links=[dict(evidence_id=eid, experiment_id=assigned.get(eid)) for eid in sorted(known)],
                evidence_without_experimental_unit=sorted(set(known)-set(assigned)) if 'experimental_units' in protocol else None,
                units_with_unresolved_conditions=sorted(xid for xid,row in ledger.items() if row['unresolved_fields']) if 'experimental_units' in protocol else None,
                units_without_outcome_sampling=sorted(xid for xid,row in ledger.items() if 'outcome_sampling' not in row) if 'experimental_units' in protocol else None,
                units_with_unresolved_sampling=sorted(xid for xid,row in ledger.items() if row.get('sampling_review', {}).get('unresolved_fields')) if 'experimental_units' in protocol else None,
                units_without_outcome_statistics=sorted(xid for xid,row in ledger.items() if 'outcome_statistics' not in row) if 'experimental_units' in protocol else None,
                units_with_statistics_review_cues=sorted(xid for xid,row in ledger.items() if row.get('statistics_review', {}).get('missing_fields') or row.get('statistics_review', {}).get('literal_label_differences')) if 'experimental_units' in protocol else None,
                boundary=BOUNDARY)
