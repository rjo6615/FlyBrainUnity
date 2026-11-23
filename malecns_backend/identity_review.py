"""Published physiology Step P2: identity-mapping review — validator, mapping rules and restatements.

Preregistered in docs/evidence/identity-mapping-v1/protocol.json. Published cells that P1's evidence rests
on are mapped to connectome types usable in our male CNS v1.0 data (R1-R5); P1's D1, D2 and D5 are
restated from the mappings as a new versioned result (P1's own evidence and result are unchanged). No
simulation.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'docs/evidence/identity-mapping-v1/protocol.json'
PROTOCOL_SHA256 = '9c7919bc6fffd968a13447d39214f336928ca69370d134733503ae239e03a0f3'
TYPE_TABLE = 'docs/evidence/identity-mapping-v1/type_table.json'
SCHEMA = 'identity-mapping-result-v1'
OUR = 'maleCNS'
DATASETS = ('maleCNS', 'MANC', 'FANC', 'BANC')
TARGETS = ('T1:13Ba', 'T2:10Ba', 'T3:9Aa', 'T3:9Aa2',
           'T4:club', 'T4:claw-flexion', 'T4:claw-extension', 'T4:hook-flexion', 'T4:hook-extension',
           'T5:8Aa', 'T5:9Ba', 'T5:9Bb', 'T5:10Ba', 'T5:13Ba', 'T5:13Bb', 'T5:19Aa', 'T5:19Ab', 'T5:20/22Ab',
           'T6:fast', 'T6:intermediate', 'T6:slow')
GRADED = ('T1:13Ba', 'T2:10Ba')                 # P1's D1 candidates
MNS = ('T6:fast', 'T6:intermediate', 'T6:slow')  # P1's D2 class
KINDS = {'Q1': ('crosswalk',), 'Q2': ('identity',), 'Q3': ('identity',), 'Q4': ('identity',),
         'Q5': ('functional_connectivity',)}
LEVELS = ('M-A', 'M-B', 'M-C')
READOUTS = ('presence', 'sign', 'relative_size', 'latency_rank')
COMMON = ('id', 'question', 'kind', 'citation', 'doi_or_url', 'preprint', 'primary', 'read_level', 'summary', 'check')
REQUIRED = {'crosswalk': COMMON + ('datasets', 'crosswalk_level', 'method'),
            'identity': COMMON + ('target', 'published_identity', 'source_dataset', 'level', 'types', 'method'),
            'functional_connectivity': COMMON + ('stimulated', 'recorded', 'neural_readout', 'readout', 'pairs', 'method')}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


# ---- the whole-dataset type table (structure only) -------------------------------------------------

def type_table(data, net):
    inside = set(int(i) for i in net)
    out = {}
    for i in range(data.neuron_count):
        t = str(data.types[i])
        if not t:
            continue
        row = out.setdefault(t, dict(count=0, in_network=0, superclasses=set()))
        row['count'] += 1
        row['in_network'] += i in inside
        row['superclasses'].add(data.superclasses[int(data.superclass_ids[i])])
    return {t: dict(count=r['count'], in_network=r['in_network'], superclasses=sorted(r['superclasses']))
            for t, r in sorted(out.items())}


# ---- validation -------------------------------------------------------------------------------------

def validate(e):
    kind = e.get('kind')
    if kind not in REQUIRED:
        return ['bad kind']
    errors = [f'missing {k}' for k in REQUIRED[kind] if k not in e]
    if errors:
        return errors
    if e['question'] not in KINDS or kind not in KINDS[e['question']]:
        errors.append('kind not declared for question')
    if e['read_level'] not in ('full', 'abstract'):
        errors.append('bad read_level')
    c = e['check']
    if not isinstance(c, dict) or 'second_read' not in c or 'agrees' not in c:
        errors.append('check needs second_read and agrees')
    if kind == 'crosswalk':
        if not (isinstance(e['datasets'], list) and len(e['datasets']) == 2 and all(d in DATASETS for d in e['datasets'])):
            errors.append('crosswalk needs two known datasets')
        if e['crosswalk_level'] not in ('type', 'neuron', 'partial'):
            errors.append('bad crosswalk_level')
    if kind == 'identity':
        if e['target'] not in TARGETS:
            errors.append('unknown target')
        if e['level'] not in LEVELS:
            errors.append('bad level')
        if e['source_dataset'] not in DATASETS + ('none',):
            errors.append('bad source_dataset')
        if not isinstance(e['types'], list):
            errors.append('types must be a list')
    if kind == 'functional_connectivity':
        if not isinstance(e['neural_readout'], bool):
            errors.append('neural_readout must be bool')
        if e['readout'] not in READOUTS + ('none',):
            errors.append('bad readout')
        for p in e['pairs']:
            if not (isinstance(p, dict) and p.get('stim') in TARGETS and p.get('rec') in TARGETS and 'response' in p):
                errors.append('pair needs stim and rec targets and a response')
                break
    return errors


def counts(e):
    c = e['check']
    return bool(e['primary'] and c['second_read'] and c['agrees'])


# ---- mapping rules ----------------------------------------------------------------------------------

def crosswalks(entries):
    """Datasets with a checked type-level crosswalk to our data."""
    out = {OUR}
    for e in entries:
        if e['kind'] == 'crosswalk' and counts(e) and e['crosswalk_level'] == 'type' and OUR in e['datasets']:
            out.update(e['datasets'])
    return out


def in_our_data(e, table, walks):
    """The entry's types as our-data type names, or None if they do not carry over."""
    if e['source_dataset'] not in walks or not e['types']:
        return None
    if not all(t in table for t in e['types']):
        return None
    return frozenset(e['types'])


def mapping(target, entries, table, walks):
    rows = [e for e in entries if e['kind'] == 'identity' and e['target'] == target and counts(e)
            and e['level'] in ('M-A', 'M-B')]
    a = [e for e in rows if e['level'] == 'M-A']
    b = [e for e in rows if e['level'] == 'M-B']
    a_sets = [in_our_data(e, table, walks) for e in a]
    if a:
        here = [s for s in a_sets if s is not None]
        if len(set(here)) > 1:
            return 'CONFLICTING', sorted(set().union(*here))
        if here and len(here) == len(a_sets):
            return 'MAPPED', sorted(here[0])
        if here:                                      # some M-A carry over, some only in their source dataset
            return 'MAPPED', sorted(here[0])
    b_sets = [in_our_data(e, table, walks) for e in b]
    if b and all(s is not None for s in b_sets):
        return 'CANDIDATE_SET', sorted(set().union(*b_sets))
    if a or b:
        return 'SOURCE_ONLY', sorted({t for e in rows for t in e['types']})
    return 'UNMAPPED', []


def mappings(entries, table):
    walks = crosswalks(entries)
    return {t: dict(zip(('status', 'types'), mapping(t, entries, table, walks))) for t in TARGETS}, sorted(walks)


# ---- restatements of P1 ------------------------------------------------------------------------------

def restate_d1(maps, table):
    out = {}
    for t in GRADED:
        m = maps[t]
        if m['status'] in ('MAPPED', 'CANDIDATE_SET'):
            out[t] = dict(level='type', status=m['status'], types=m['types'],
                          in_network=sum(table[x]['in_network'] for x in m['types']))
        else:
            out[t] = dict(level='hemilineage', status=m['status'])
    return out


def restate_d2(maps):
    return {t: maps[t] for t in MNS if maps[t]['status'] == 'MAPPED'}


def d5(entries, maps):
    out = []
    for e in entries:
        if e['kind'] != 'functional_connectivity' or not counts(e) or not e['neural_readout'] or e['readout'] == 'none':
            continue
        for p in e['pairs']:
            if maps[p['stim']]['status'] == 'MAPPED' and maps[p['rec']]['status'] == 'MAPPED':
                out.append(dict(entry=e['id'], stim=p['stim'], rec=p['rec'], response=p['response'], readout=e['readout']))
    return out


def label(targets, d1):
    if len(targets) >= 2:
        return 'TARGETS_AVAILABLE'
    if any(v['level'] == 'type' for v in d1.values()):
        return 'MAPPING_ONLY'
    return 'INSUFFICIENT'


def expectations(walks, maps, lab):
    t4 = [t for t in TARGETS if t.startswith('T4:')]
    return dict(X1=any(d in walks for d in ('MANC', 'FANC', 'BANC')),
                X2=all(maps[t]['status'] != 'MAPPED' or len(maps[t]['types']) > 1 for t in GRADED),
                X3=any(maps[t]['status'] in ('MAPPED', 'CANDIDATE_SET', 'SOURCE_ONLY', 'CONFLICTING') for t in t4),
                X4=lab == 'MAPPING_ONLY')


def evaluate(evidence, log, table):
    entries = evidence['entries']
    invalid = {e.get('id', f'#{i}'): validate(e) for i, e in enumerate(entries)}
    invalid = {k: v for k, v in invalid.items() if v}
    ids = [e.get('id') for e in entries]
    integrity = dict(valid_entries=not invalid, invalid=invalid, unique_ids=len(ids) == len(set(ids)),
                     every_entry_checked=all(e.get('check', {}).get('second_read') for e in entries),
                     search_log_complete=all(k in log for k in ('queries', 'screened'))
                     and all('decision' in s for s in log['screened']))
    if not all(v for k, v in integrity.items() if k != 'invalid'):
        return dict(schema=SCHEMA, label='INCONCLUSIVE', integrity=integrity)
    maps, walks = mappings(entries, table)
    d1 = restate_d1(maps, table)
    targets = d5(entries, maps)
    lab = label(targets, d1)
    return dict(schema=SCHEMA, label=lab, crosswalks=walks, mappings=maps, D1_restated=d1, D2_restated=restate_d2(maps),
                D5_targets=targets, expectations=expectations(walks, maps, lab), integrity=integrity,
                counts=dict(entries=len(entries), counted=sum(counts(e) for e in entries),
                            disagreements=[e['id'] for e in entries if not e['check']['agrees']]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = protocol()
    if sha(ROOT/TYPE_TABLE) != spec['type_table_sha256']:
        raise ValueError('type table changed')
    table = json.loads((ROOT/TYPE_TABLE).read_text(encoding='utf-8'))
    result = evaluate(json.loads(args.evidence.read_text(encoding='utf-8')),
                      json.loads(args.log.read_text(encoding='utf-8')), table)
    result.update(protocol_sha256=PROTOCOL_SHA256, evidence_sha256=sha(args.evidence), log_sha256=sha(args.log))
    with args.output.open('x', encoding='utf-8') as f:                 # exclusive: evaluated once
        f.write(json.dumps(result, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('label', 'expectations') if k in result}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
