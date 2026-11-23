"""Published physiology Step P1: validator and decision rules for the literature review.

Preregistered in docs/evidence/physiology-review-v1/protocol.json. The review's extraction table
(evidence.json) is checked against the declared schema and against the R1 front-left network's cell
table, and the decision rules D1-D5 and the P1 label are computed from it mechanically. No simulation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'docs/evidence/physiology-review-v1/protocol.json'
PROTOCOL_SHA256 = 'c28c524a0ad466c92b763239c00ef7f109aa04a81ffb57923d8ca00662f0334c'
TABLE = 'docs/evidence/physiology-review-v1/network_table.json'
SCHEMA = 'physiology-review-result-v1'
SPECIES = 'Drosophila melanogaster'
CORE_TYPES = ('IN17A001', 'INXXX466', 'IN16B036')                 # E1, E2, I1
QUESTIONS = ('Q1', 'Q2', 'Q3', 'Q4', 'Q5')
MEASURES = {'Q1': ('spiking', 'graded'),
            'Q2': ('resting_potential', 'input_resistance', 'membrane_time_constant', 'threshold', 'rheobase',
                   'firing_rate_range', 'recruitment_order'),
            'Q3': ('synaptic_sign', 'synaptic_kinetics', 'graded_release', 'gap_junction'),
            'Q4': ('target_candidate',),
            'Q5': ('model',)}
PARAMETERS = MEASURES['Q2']
SYNAPTIC = ('synaptic_sign', 'synaptic_kinetics', 'graded_release')
REQUIRED = ('id', 'question', 'citation', 'doi_or_url', 'preprint', 'primary', 'species', 'stage', 'preparation',
            'method', 'published_identity', 'mapping', 'grade', 'measure', 'value', 'units', 'n', 'summary',
            'read_level', 'check')
HEMILINEAGE = re.compile(r'^(?:IN|AN|SN)(\d{2}[AB])\d{3}')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


# ---- the network's cell table (structure only) ----------------------------------------------------

def network_table(data, net):
    """Types, hemilineages (from MANC-style type names) and superclasses present in R1's network."""
    types, hl, classes = {}, {}, {}
    for i in net:
        t = str(data.types[i])
        types[t] = types.get(t, 0) + 1
        m = HEMILINEAGE.match(t)
        if m:
            hl[m.group(1)] = hl.get(m.group(1), 0) + 1
        c = data.superclasses[int(data.superclass_ids[i])]
        classes[c] = classes.get(c, 0) + 1
    return dict(rule='hemilineage = the two digits and letter after IN/AN/SN in a MANC-style type name',
                neurons=len(net), types=dict(sorted(types.items())), hemilineages=dict(sorted(hl.items())),
                classes=dict(sorted(classes.items())))


# ---- validation -------------------------------------------------------------------------------------

def mapped(entry, table):
    m = entry['mapping']
    kind, value = m.get('kind'), m.get('value')
    return {'type': table['types'], 'hemilineage': table['hemilineages'], 'class': table['classes']}.get(kind, {}).get(value)


def validate(entry, table):
    """Errors for one extraction entry ([] if valid)."""
    errors = [f'missing {k}' for k in REQUIRED if k not in entry]
    if errors:
        return errors
    q, g = entry['question'], entry['grade']
    if q not in QUESTIONS:
        errors.append('bad question')
    elif entry['measure'] not in MEASURES[q]:
        errors.append('measure not declared for question')
    if g not in ('A', 'B', 'C'):
        errors.append('bad grade')
    kind = entry['mapping'].get('kind')
    if g == 'A' and not (kind == 'type' and mapped(entry, table)):
        errors.append('grade A needs a type in the network')
    if g == 'B' and not (kind in ('hemilineage', 'class') and mapped(entry, table)):
        errors.append('grade B needs a hemilineage or class in the network')
    if g in ('A', 'B') and entry['species'] != SPECIES:
        errors.append('grade A/B needs Drosophila melanogaster')
    if entry['read_level'] not in ('full', 'abstract'):
        errors.append('bad read_level')
    c = entry['check']
    if not isinstance(c, dict) or 'second_read' not in c or 'agrees' not in c:
        errors.append('check needs second_read and agrees')
    if entry['measure'] == 'target_candidate':
        for k in ('stimulus_reproducible', 'readout_quantitative'):
            if not isinstance(entry.get(k), bool):
                errors.append(f'target needs {k}')
    if entry['measure'] == 'gap_junction' and not isinstance(entry.get('connectivity_source'), bool):
        errors.append('gap_junction needs connectivity_source')
    return errors


def counts(entry):
    """An entry counts toward a decision only if it is primary Drosophila evidence at grade A or B, checked."""
    c = entry['check']
    return (entry['primary'] and entry['species'] == SPECIES and entry['grade'] in ('A', 'B')
            and c['second_read'] and c['agrees'])


def group_key(entry):
    return f"{entry['mapping']['kind']}:{entry['mapping']['value']}"


# ---- decision rules ---------------------------------------------------------------------------------

def d1(entries):
    """Graded-unit candidates: a group with graded evidence and no spiking evidence."""
    seen = {}
    for e in entries:
        if e['question'] == 'Q1' and counts(e):
            seen.setdefault(group_key(e), set()).add(e['measure'])
    out = {}
    for k, ms in sorted(seen.items()):
        out[k] = 'CONFLICTING' if ms == {'graded', 'spiking'} else ('CANDIDATE' if ms == {'graded'} else 'SPIKING')
    return out


def d2(entries):
    """Parameter replacements: measured Drosophila values at grade A/B with n reported."""
    out = {}
    for e in entries:
        if e['question'] == 'Q2' and counts(e) and isinstance(e['n'], int) and e['n'] >= 1:
            out.setdefault(f"{group_key(e)}|{e['measure']}", []).append(e['id'])
    return out


def d3(entries):
    out = {}
    for e in entries:
        if e['question'] == 'Q3' and e['measure'] in SYNAPTIC and counts(e):
            out.setdefault(f"{group_key(e)}|{e['measure']}", []).append(e['id'])
    return out


def d4(entries):
    rows = [e for e in entries if e['measure'] == 'gap_junction']
    return dict(recorded=[e['id'] for e in rows],
                usable=[e['id'] for e in rows if counts(e) and e['connectivity_source']])


def d5(entries):
    return [e['id'] for e in entries if e['measure'] == 'target_candidate' and counts(e)
            and e['stimulus_reproducible'] and e['readout_quantitative']]


def label(entries):
    change = any(v == 'CANDIDATE' for v in d1(entries).values()) or bool(d2(entries)) or bool(d3(entries))
    targets = len(d5(entries))
    if change and targets >= 2:
        return 'EVIDENCE_SUFFICIENT_FOR_VARIANT'
    if change or targets:
        return 'EVIDENCE_PARTIAL'
    return 'EVIDENCE_INSUFFICIENT'


def expectations(entries, lab):
    core_a = [e for e in entries if e['grade'] == 'A' and e['mapping'].get('value') in CORE_TYPES and counts(e)]
    graded_b = [e for e in entries if e['question'] == 'Q1' and e['measure'] == 'graded' and counts(e)]
    mn = [e for e in entries if e['question'] == 'Q2' and counts(e)]
    return dict(X1=not core_a, X2=bool(graded_b), X3=bool(mn), X4=lab == 'EVIDENCE_PARTIAL')


def evaluate(evidence, log, table):
    entries = evidence['entries']
    invalid = {e.get('id', f'#{i}'): validate(e, table) for i, e in enumerate(entries)}
    invalid = {k: v for k, v in invalid.items() if v}
    ids = [e.get('id') for e in entries]
    log_ok = all(k in log for k in ('queries', 'screened')) and all('decision' in s for s in log['screened'])
    integrity = dict(valid_entries=not invalid, invalid=invalid, unique_ids=len(ids) == len(set(ids)),
                     every_entry_checked=all(e.get('check', {}).get('second_read') for e in entries),
                     search_log_complete=log_ok)
    ok = all(v for k, v in integrity.items() if k != 'invalid')
    if not ok:
        return dict(schema=SCHEMA, label='INCONCLUSIVE', integrity=integrity)
    lab = label(entries)
    return dict(schema=SCHEMA, label=lab, D1=d1(entries), D2=d2(entries), D3=d3(entries), D4=d4(entries),
                D5=d5(entries), expectations=expectations(entries, lab), integrity=integrity,
                counts=dict(entries=len(entries), counted=sum(counts(e) for e in entries),
                            by_question={q: sum(e['question'] == q for e in entries) for q in QUESTIONS},
                            disagreements=[e['id'] for e in entries if not e['check']['agrees']]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = protocol()
    if sha(ROOT/TABLE) != spec['network_table_sha256']:
        raise ValueError('network table changed')
    table = json.loads((ROOT/TABLE).read_text())
    result = evaluate(json.loads(args.evidence.read_text(encoding='utf-8')),
                      json.loads(args.log.read_text(encoding='utf-8')), table)
    result.update(protocol_sha256=PROTOCOL_SHA256, evidence_sha256=sha(args.evidence), log_sha256=sha(args.log))
    with args.output.open('x', encoding='utf-8') as f:                 # exclusive: evaluated once
        f.write(json.dumps(result, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('label', 'expectations') if k in result}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
