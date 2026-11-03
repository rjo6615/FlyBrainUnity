"""Synthetic checks for the RF hair-plate V2 neuron-match cross-check; no real BANC or MaleCNS table."""
import pandas as pd
import pytest

from malecns_backend.embodiment import rf_hair_plate_banc as v1
from malecns_backend.embodiment import rf_hair_plate_banc_v2 as b

NERVE = {'T1': 'VProN', 'T2': 'MesoLN', 'T3': 'MetaLN'}


def annotations(extra_known=()):
    """Anchors: body = 1000*seg + 100*(side R) + i; mancBodyid = body + 50000 for even i."""
    rows = []
    for leg, n in v1.EXPECTED_MALECNS.items():
        seg, side = leg.split()
        for i in range(n):
            body = 1000*int(seg[1]) + (100 if side == 'right' else 0) + i
            rows.append(dict(bodyId=body, type='SNpp45', entryNerve=NERVE[seg], rootSide=side[0].upper(),
                             somaSide=None, mancBodyid=float(body + 50000) if i % 2 == 0 else None))
    rows.append(dict(bodyId=b.EXCLUDED_ANCHOR, type='SNpp45', entryNerve='ProLN', rootSide='L', somaSide=None,
                     mancBodyid=None))
    rows += [dict(bodyId=k, type='X', entryNerve=None, rootSide=None, somaSide=None, mancBodyid=None)
             for k in extra_known]
    return pd.DataFrame(rows)


def banc_for(ann, cable=lambda side: 100., skip=(), flip=(), via_manc=True):
    """One BANC counterpart per anchor; even anchors also matched via MANC (same root)."""
    rows = []
    for r in ann[ann['type'] == 'SNpp45'].to_dict('records'):
        body = r['bodyId']
        if body in skip:
            continue
        side = 'left' if r['rootSide'] == 'L' else 'right'
        if body in flip:
            side = 'left' if side == 'right' else 'right'
        manc = r['mancBodyid']
        rows.append(dict(root_id=f'r{body}', cell_type='SNxx', nerve=f'{side}_x_nerve', side=side, proofread='TRUE',
                         malecns_match=str(body),
                         manc_match=f'7, {int(manc)}' if via_manc and manc == manc and manc else None,
                         l2_cable_length_um=cable(side)))
    return pd.DataFrame(rows)


def ev(ann=None, banc=None, source_ok=True, step_a=None):
    ann = annotations() if ann is None else ann
    banc = banc_for(ann) if banc is None else banc
    return b.evaluate(banc, ann, source_ok, step_a or dict(v1.EXPECTED_MALECNS))


def test_ids_and_side_helpers():
    assert b.id_list('7, 52000') == [7, 52000] and b.id_list(None) == [] and b.id_list('12.0') == [12]
    assert b.side_of(dict(side=None, nerve='right_prothoracic_leg_nerve')) == 'right'
    assert b.side_of(dict(side=None, nerve=None)) is None


def test_both_bridges_and_shared_counterpart_counted_once():
    e = ev()
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    t1 = e['segments']['T1']
    assert t1['n'] == {'left': 7, 'right': 5} and t1['count_diff'] == -2
    rec = e['per_anchor']['1000']['counterparts']
    assert len(rec) == 1 and sorted(rec[0]['bridges']) == ['B1', 'B2']
    assert e['per_anchor']['1001']['counterparts'][0]['bridges'] == ['B1']
    # two anchors on one side sharing a counterpart count once
    ann = annotations()
    banc = banc_for(ann)
    banc.loc[banc['root_id'] == 'r1101', 'root_id'] = 'r1100'
    assert ev(ann, banc)['segments']['T1']['n']['right'] == 4


def test_labels_replicated_and_not():
    ann = annotations()
    e = ev(ann, banc_for(ann, cable=lambda s: 40. if s == 'right' else 100.))
    assert e['labels']['Q_COUNT']['label'] == 'COUNT_DEFICIT_REPLICATED'
    assert e['labels']['Q_SIZE']['label'] == 'SIZE_DEFICIT_REPLICATED' and e['labels']['Q_RF']['label'] == 'RF_DEFICIT_REPLICATED'
    banc = banc_for(ann)
    extra = banc[banc['root_id'].isin(['r1100', 'r1101'])].assign(root_id=lambda d: d['root_id'] + 'b')
    e = ev(ann, pd.concat([banc, extra]))
    assert e['segments']['T1']['n']['right'] == 7 and e['labels']['Q_RF']['label'] == 'RF_DEFICIT_NOT_REPLICATED'


@pytest.mark.parametrize('fault', ['source', 'anchors', 'version', 'coverage', 'side', 'size'])
def test_integrity_faults(fault):
    ann, kw = annotations(), {}
    banc = banc_for(ann)
    if fault == 'source': kw['source_ok'] = False
    if fault == 'anchors': kw['step_a'] = dict(v1.EXPECTED_MALECNS, **{'T1 right': 4})
    if fault == 'version':
        junk = banc.iloc[:1].assign(root_id='junk')
        banc = pd.concat([banc] + [junk.assign(malecns_match=str(900000 + i), root_id=f'j{i}') for i in range(10)])
    if fault == 'coverage': banc = banc_for(ann, skip={1100, 1101})
    if fault == 'side': banc = banc_for(ann, flip={1000, 1001, 1002, 1100})
    if fault == 'size': banc.loc[banc['root_id'] == 'r1100', 'l2_cable_length_um'] = float('nan')
    e = ev(ann, banc, **kw)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'labels' not in e


def test_protocol_lock():
    spec = b.protocol()
    assert spec['labels']['Q_SIZE']['SIZE_DEFICIT_REPLICATED'] == v1.protocol()['labels']['Q_SIZE']['SIZE_DEFICIT_REPLICATED']
    assert spec['integrity']['I3_coverage'].startswith('>= 0.75')
