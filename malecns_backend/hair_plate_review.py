"""Published physiology Step P3: hair plates — identities and validation targets.

Preregistered in docs/evidence/hair-plate-review-v1/protocol.json (design docs/HAIR_PLATE_REVIEW_V1.md).
Reuses P2's identity levels, crosswalk and mapping rules R1-R5 (malecns_backend.identity_review, unchanged),
P2's male CNS type table and P2's checked male CNS <-> MANC crosswalk entry. Adds a declared, read-only
annotation query over the BANC v888 and male CNS v1.0 annotation tables already in the repository, the
SNpp45 verdict, encoder-validation targets (E), CNS-validation targets (C) and the P3 label. No simulation;
the engine and the hair-plate encoder are not touched.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from . import identity_review as p2
from .embodiment.rf_hair_plate_banc_v2 import id_list

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'docs/evidence/hair-plate-review-v1/protocol.json'
PROTOCOL_SHA256 = 'd240f6268f281e6b047d7bdd61ee415c2fe46692a01a25873277974041a5a4e3'
SCHEMA = 'hair-plate-review-result-v1'
SOURCES = {'banc': 'docs/evidence/distal-tarsus-reference-v1/banc_888_meta.feather',
           'malecns': 'docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather'}
P2_EVIDENCE = 'docs/evidence/identity-mapping-v1/evidence.json'
OUR = p2.OUR
DMEL = 'Drosophila melanogaster'

AFFERENTS = ('H1:CxHP8', 'H2:CxHP3', 'H2:CxHP4', 'H3:TrHP5', 'H3:TrHP6', 'H3:TrHP7')
H1 = AFFERENTS[0]
SNPP45 = 'H4:SNpp45'
TARGETS = AFFERENTS + (SNPP45,)
DOWNSTREAM = re.compile(r'^D:\S')            # downstream cells named by Q4 sources (mapped by the same rules)
SNPP45_IS = tuple(t.split(':')[1] for t in AFFERENTS) + ('other_hair_plate', 'not_hair_plate', 'hair_plate_unspecified')
KINDS = {'Q1': ('identity',), 'Q2': ('crosswalk', 'annotation'), 'Q3': ('afferent_tuning',),
         'Q4': ('identity', 'functional_connectivity'), 'Q5': ('behaviour',)}
JOINTS = ('coxa', 'trochanter', 'femur', 'tibia', 'other')
REPRODUCIBLE = ('coxa', 'trochanter')
QUANT = ('tuning_curve', 'threshold_angle', 'rate_vs_angle')
TUNING_READOUTS = QUANT + ('qualitative', 'none')
GRADES = ('A', 'B', 'C')
MANIPULATIONS = ('activation', 'silencing', 'ablation', 'other')
COMMON = p2.COMMON
REQUIRED = dict(p2.REQUIRED,
                annotation=COMMON + ('datasets', 'output_sha256', 'link_summary'),
                afferent_tuning=COMMON + ('target', 'species', 'grade', 'preparation', 'joint', 'stimulus', 'readout',
                                          'values', 'n', 'method'),
                behaviour=COMMON + ('target', 'species', 'manipulation', 'effect', 'method'))

# ---- the declared annotation query --------------------------------------------------------------------
PATTERNS = {'hair plate': re.compile(r'hair[ _-]?plate', re.I),
            'HP token': re.compile(r'(?<![A-Za-z])HP(?![A-Za-z])'),
            'CxHP': re.compile(r'CxHP', re.I),
            'TrHP': re.compile(r'TrHP', re.I)}
TYPE_COLUMN = {'banc': 'cell_type', 'malecns': 'type'}
TYPED = 'SNpp45'
REPORT = {'banc': ('root_id', 'cell_type', 'side', 'nerve', 'region', 'hemilineage', 'super_class', 'cell_class',
                   'cell_sub_class', 'body_part_sensory', 'peripheral_target_type', 'cell_function',
                   'cell_function_detailed', 'malecns_cell_type', 'manc_cell_type', 'fanc_cell_type',
                   'malecns_match', 'manc_match', 'fanc_match', 'malecns_nblast_match'),
          'malecns': ('bodyId', 'type', 'instance', 'somaSide', 'rootSide', 'entryNerve', 'exitNerve', 'superclass',
                      'class', 'subclass', 'somaNeuromere', 'mancType', 'mancBodyid', 'synonyms', 'matchingNotes',
                      'receptorType')}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def text_columns(df):
    return [c for c in df.columns if str(df[c].dtype) in ('object', 'string', 'category')]


def cell(v):
    if v is None:
        return None
    try:
        if v != v:                                                      # NaN
            return None
    except TypeError:                                                   # pandas NA
        return None
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def hits(df, name):
    """{row index: dict(reasons, matched, fields)} for the declared patterns and the SNpp45 type rows."""
    out = {}
    for c in text_columns(df):
        s = df[c].astype('string')
        for label, rx in PATTERNS.items():
            for i in s.index[s.str.contains(rx, na=False)]:
                row = out.setdefault(int(i), dict(reasons=set(), matched=[]))
                row['reasons'].add(label)
                row['matched'].append(dict(column=c, pattern=label, value=str(s[i])))
    typed = df.index[df[TYPE_COLUMN[name]].astype('string') == TYPED]
    for i in typed:
        out.setdefault(int(i), dict(reasons=set(), matched=[]))['reasons'].add(f'typed {TYPED}')
    cols = [c for c in REPORT[name] if c in df.columns]
    for i, row in out.items():
        row['reasons'] = sorted(row['reasons'])
        row['matched'] = sorted(row['matched'], key=lambda m: (m['column'], m['pattern']))
        row['fields'] = {c: cell(df.at[i, c]) for c in cols}
    return out


def banc_link(banc_hits, mcns):
    """Per BANC cell type among the hit rows: male CNS types reached through malecns_match, and the link level."""
    types = {int(b): cell(t) for b, t in zip(mcns['bodyId'], mcns['type'])}
    groups = {}
    for i, r in banc_hits.items():
        g = groups.setdefault(r['fields'].get('cell_type') or '', dict(rows=0, matched_rows=0, ids={}, reached=set(),
                                                                          unresolved=0, banc_malecns_cell_type=set()))
        g['rows'] += 1
        if r['fields'].get('malecns_cell_type'):
            g['banc_malecns_cell_type'].add(r['fields']['malecns_cell_type'])
        ids = id_list(r['fields'].get('malecns_match'))
        if ids:
            g['matched_rows'] += 1
        for b in ids:
            g['ids'][b] = g['ids'].get(b, 0) + 1
            if b in types and types[b]:
                g['reached'].add(types[b])
            else:
                g['unresolved'] += 1
    out = {}
    for t, g in sorted(groups.items()):
        if not g['matched_rows']:
            level = 'none'
        elif any(n > 1 for n in g['ids'].values()):
            level = 'group'
        else:
            level = 'neuron'
        out[t] = dict(rows=g['rows'], matched_rows=g['matched_rows'], distinct_ids=len(g['ids']),
                      max_rows_per_id=max(g['ids'].values(), default=0), unresolved_ids=g['unresolved'],
                      level=level, malecns_types=sorted(g['reached']),
                      carries_over=bool(t) and len(g['reached']) == 1 and not g['unresolved'],
                      banc_malecns_cell_type=sorted(g['banc_malecns_cell_type']))
    return out


def annotation_query(banc, mcns, source_sha=None):
    b, m = hits(banc, 'banc'), hits(mcns, 'malecns')
    link = banc_link(b, mcns)

    def tally(h, name):
        by_reason, by_type = {}, {}
        for r in h.values():
            for x in r['reasons']:
                by_reason[x] = by_reason.get(x, 0) + 1
            t = r['fields'].get(TYPE_COLUMN[name]) or ''
            by_type[t] = by_type.get(t, 0) + 1
        return dict(rows=len(h), by_reason=dict(sorted(by_reason.items())), by_type=dict(sorted(by_type.items())))
    return dict(schema='hair-plate-annotation-query-v1', sources=source_sha or {},
                patterns={k: v.pattern + (' (case-insensitive)' if v.flags & re.I else '') for k, v in PATTERNS.items()},
                typed=TYPED, banc=dict(summary=tally(b, 'banc'), rows=[b[i] for i in sorted(b)]),
                malecns=dict(summary=tally(m, 'malecns'), rows=[m[i] for i in sorted(m)]),
                banc_to_malecns=link)


def carry_map(link):
    return {t: g['malecns_types'][0] for t, g in link.items() if g['carries_over']}


# ---- validation -----------------------------------------------------------------------------------------

def target_ok(e):
    t = e.get('target')
    if e['question'] == 'Q1':
        return t in TARGETS
    if e['question'] == 'Q4':
        return isinstance(t, str) and bool(DOWNSTREAM.match(t))
    return t in AFFERENTS


def validate(e):
    kind = e.get('kind')
    if kind not in REQUIRED:
        return ['bad kind']
    errors = [f'missing {k}' for k in REQUIRED[kind] if k not in e]
    if errors:
        return errors
    if e['question'] not in KINDS or kind not in KINDS[e['question']]:
        return ['kind not declared for question']
    if e['read_level'] not in ('full', 'abstract', 'dataset'):
        errors.append('bad read_level')
    c = e['check']
    if not isinstance(c, dict) or 'second_read' not in c or 'agrees' not in c:
        errors.append('check needs second_read and agrees')
    if kind == 'crosswalk':
        if not (isinstance(e['datasets'], list) and len(e['datasets']) == 2 and all(d in p2.DATASETS for d in e['datasets'])):
            errors.append('crosswalk needs two known datasets')
        if e['crosswalk_level'] not in ('type', 'neuron', 'partial'):
            errors.append('bad crosswalk_level')
    if kind == 'annotation' and sorted(e['datasets']) != ['BANC', OUR]:
        errors.append('annotation entry covers BANC and maleCNS')
    if kind in ('identity', 'afferent_tuning', 'behaviour') and not target_ok(e):
        errors.append('unknown target')
    if kind == 'identity':
        if e['level'] not in p2.LEVELS:
            errors.append('bad level')
        if e['source_dataset'] not in p2.DATASETS + ('none',):
            errors.append('bad source_dataset')
        if not isinstance(e['types'], list):
            errors.append('types must be a list')
        if e['target'] == SNPP45 and (e.get('snpp45_is') not in SNPP45_IS or TYPED not in e['types']):
            errors.append('H4 entry needs snpp45_is and SNpp45 in types')
    if kind == 'afferent_tuning':
        if e['joint'] not in JOINTS:
            errors.append('bad joint')
        if e['readout'] not in TUNING_READOUTS:
            errors.append('bad readout')
        if e['grade'] not in GRADES or (e['species'] != DMEL) != (e['grade'] == 'C'):
            errors.append('grade C if and only if not Drosophila melanogaster')
    if kind == 'behaviour' and e['manipulation'] not in MANIPULATIONS:
        errors.append('bad manipulation')
    if kind == 'functional_connectivity':
        if not isinstance(e['neural_readout'], bool):
            errors.append('neural_readout must be bool')
        if e['readout'] not in p2.READOUTS + ('none',):
            errors.append('bad readout')
        for p in e['pairs']:
            if not (isinstance(p, dict) and p.get('stim') in AFFERENTS and isinstance(p.get('rec'), str)
                    and DOWNSTREAM.match(p['rec']) and 'response' in p):
                errors.append('pair needs a hair-plate stim, a D: recorded cell and a response')
                break
    return errors


counts = p2.counts


# ---- crosswalks, mappings, verdict, targets ----------------------------------------------------------

def crosswalks(entries, p2_entries, link):
    """P2's checked crosswalks, this review's crosswalk entries, and BANC if the annotation entry counts and
    at least one hit BANC type carries over to exactly one male CNS type."""
    walks = p2.crosswalks([e for e in p2_entries if e['kind'] == 'crosswalk'] +
                          [e for e in entries if e['kind'] == 'crosswalk'])
    banc = any(e['kind'] == 'annotation' and counts(e) for e in entries) and bool(carry_map(link))
    if banc:
        walks.add('BANC')
    return walks


def translated(entries, link):
    """BANC-sourced identity entries with their BANC types replaced by the male CNS types they carry over to
    (all or nothing; a type that does not carry over keeps a BANC: prefix and so never matches by name)."""
    cm = carry_map(link)
    out = []
    for e in entries:
        if e['kind'] == 'identity' and e['source_dataset'] == 'BANC':
            ts = e['types']
            e = dict(e, types=sorted({cm[t] for t in ts}) if ts and all(t in cm for t in ts) else [f'BANC:{t}' for t in ts])
        out.append(e)
    return out


def mappings(entries, table, walks):
    names = list(TARGETS) + sorted({e['target'] for e in entries if e['kind'] == 'identity' and DOWNSTREAM.match(e['target'])}
                                   | {p['rec'] for e in entries if e['kind'] == 'functional_connectivity' for p in e['pairs']})
    return {t: dict(zip(('status', 'types'), p2.mapping(t, entries, table, walks))) for t in names}


def verdict(maps, entries, table, walks):
    h1 = maps[H1]
    against = [e['id'] for e in entries if e['kind'] == 'identity' and e['target'] == SNPP45 and counts(e)
               and e['level'] in ('M-A', 'M-B') and p2.in_our_data(e, table, walks) is not None
               and e['snpp45_is'] not in ('CxHP8', 'hair_plate_unspecified')]
    if against or (h1['status'] == 'MAPPED' and TYPED not in h1['types']):
        return 'CONTRADICTED', against
    if h1['status'] == 'MAPPED' and h1['types'] == [TYPED]:
        return 'SUPPORTED', []
    return 'UNRESOLVED', []


def e_targets(entries, maps):
    return [dict(entry=e['id'], target=e['target'], joint=e['joint'], readout=e['readout'])
            for e in entries if e['kind'] == 'afferent_tuning' and counts(e) and e['species'] == DMEL
            and maps[e['target']]['status'] == 'MAPPED' and e['joint'] in REPRODUCIBLE and e['readout'] in QUANT]


def c_targets(entries, maps):
    out = []
    for e in entries:
        if e['kind'] != 'functional_connectivity' or not counts(e) or not e['neural_readout'] or e['readout'] == 'none':
            continue
        for p in e['pairs']:
            if maps[p['stim']]['status'] == 'MAPPED' and maps[p['rec']]['status'] == 'MAPPED':
                out.append(dict(entry=e['id'], stim=p['stim'], rec=p['rec'], response=p['response'], readout=e['readout']))
    return out


def label(c, e, maps):
    if len(c) >= 2:
        return 'TARGETS_AVAILABLE'
    if e:
        return 'ENCODER_VALIDATION_AVAILABLE'
    if any(maps[t]['status'] == 'MAPPED' for t in AFFERENTS):
        return 'MAPPING_ONLY'
    return 'INSUFFICIENT'


def expectations(entries, maps, link, verd, e, c, lab):
    h1_sources = {x['source_dataset'] for x in entries if x['kind'] == 'identity' and x['target'] == H1 and counts(x)
                  and x['level'] in ('M-A', 'M-B')}
    matched = [g for g in link.values() if g['level'] != 'none']
    quant = [x for x in entries if x['kind'] == 'afferent_tuning' and counts(x) and x['species'] == DMEL and x['readout'] in QUANT]
    return dict(X1=maps[H1]['status'] == 'SOURCE_ONLY' and h1_sources == {'FANC'} and verd == 'UNRESOLVED',
                X2=bool(carry_map(link)) and bool(matched) and all(g['level'] == 'group' for g in matched),
                X3=bool(quant) and not e, X4=not c, X5=lab == 'INSUFFICIENT')


def evaluate(evidence, log, table, annotation, p2_entries, annotation_sha=None):
    entries = evidence['entries']
    invalid = {x.get('id', f'#{i}'): validate(x) for i, x in enumerate(entries)}
    invalid = {k: v for k, v in invalid.items() if v}
    ids = [x.get('id') for x in entries]
    notes = [x for x in entries if x.get('kind') == 'annotation']
    integrity = dict(valid_entries=not invalid, invalid=invalid, unique_ids=len(ids) == len(set(ids)),
                     every_entry_checked=all(x.get('check', {}).get('second_read') for x in entries),
                     search_log_complete=all(k in log for k in ('queries', 'screened'))
                     and all('decision' in s for s in log['screened']),
                     one_annotation_entry=len(notes) == 1,
                     annotation_entry_matches_output=len(notes) == 1 and annotation_sha is not None
                     and notes[0].get('output_sha256') == annotation_sha)
    if not all(v for k, v in integrity.items() if k != 'invalid'):
        return dict(schema=SCHEMA, label='INCONCLUSIVE', integrity=integrity)
    link = annotation['banc_to_malecns']
    walks = crosswalks(entries, p2_entries, link)
    work = translated(entries, link)
    maps = mappings(work, table, walks)
    verd, against = verdict(maps, work, table, walks)
    e, c = e_targets(work, maps), c_targets(work, maps)
    lab = label(c, e, maps)
    graded_c = [x['id'] for x in entries if x['kind'] == 'afferent_tuning' and x['grade'] == 'C']
    return dict(schema=SCHEMA, label=lab, snpp45_verdict=verd, snpp45_against=against, crosswalks=sorted(walks),
                banc_carry_over=carry_map(link), mappings=maps, E_targets=e, C_targets=c,
                expectations=expectations(work, maps, link, verd, e, c, lab), integrity=integrity,
                reported=dict(behaviour=[x['id'] for x in entries if x['kind'] == 'behaviour'], grade_c_tuning=graded_c,
                              m_c_identities=[x['id'] for x in entries if x['kind'] == 'identity' and x['level'] == 'M-C']),
                counts=dict(entries=len(entries), counted=sum(counts(x) for x in entries),
                            disagreements=[x['id'] for x in entries if not x['check']['agrees']]))


# ---- command line --------------------------------------------------------------------------------------

def load_sources(spec):
    import pandas as pd
    got = {k: sha(ROOT/p) for k, p in SOURCES.items()}
    if got != spec['annotation_sources_sha256']:
        raise ValueError('annotation source changed')
    return pd.read_feather(ROOT/SOURCES['banc']), pd.read_feather(ROOT/SOURCES['malecns']), got


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('annotate')
    a.add_argument('--output', type=Path, required=True)
    v = sub.add_parser('evaluate')
    for k in ('evidence', 'log', 'annotation', 'output'):
        v.add_argument(f'--{k}', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = protocol()
    banc, mcns, got = load_sources(spec)
    query = annotation_query(banc, mcns, got)
    raw = (json.dumps(query, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
    if args.cmd == 'annotate':
        with args.output.open('xb') as f:                              # exclusive: run once
            f.write(raw)
        print(json.dumps(dict(banc=query['banc']['summary'], malecns=query['malecns']['summary']), indent=1))
        return 0
    if args.annotation.read_bytes() != raw:
        raise ValueError('annotation output does not reproduce')
    p2_raw = (ROOT/P2_EVIDENCE).read_bytes()
    if hashlib.sha256(p2_raw).hexdigest() != spec['p2']['evidence_sha256']:
        raise ValueError('P2 evidence changed')
    if sha(ROOT/p2.TYPE_TABLE) != spec['p2']['type_table_sha256']:
        raise ValueError('P2 type table changed')
    table = json.loads((ROOT/p2.TYPE_TABLE).read_text(encoding='utf-8'))
    result = evaluate(json.loads(args.evidence.read_text(encoding='utf-8')), json.loads(args.log.read_text(encoding='utf-8')),
                      table, query, json.loads(p2_raw)['entries'], annotation_sha=hashlib.sha256(raw).hexdigest())
    result.update(protocol_sha256=PROTOCOL_SHA256, evidence_sha256=sha(args.evidence), log_sha256=sha(args.log),
                  annotation_sha256=hashlib.sha256(raw).hexdigest())
    with args.output.open('x', encoding='utf-8') as f:                 # exclusive: evaluated once
        f.write(json.dumps(result, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('label', 'snpp45_verdict', 'expectations') if k in result}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
