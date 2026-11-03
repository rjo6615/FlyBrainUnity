"""Synthetic checks for the RF hair-plate BANC cross-check; no real connectome or BANC table."""
from types import SimpleNamespace

import pandas as pd
import pytest

from malecns_backend.embodiment import rf_hair_plate_banc as b

NERVE = {'T1': 'ventral_prothoracic_nerve', 'T2': 'mesothoracic_leg_nerve', 'T3': 'metathoracic_leg_nerve'}


def table(per_leg, extra=()):
    """per_leg: {leg: [cable,...]}; extra: (nerve, side, cable) rows."""
    rows = []
    for leg, cables in per_leg.items():
        seg, side = leg.split()
        rows += [dict(root_id=len(rows), cell_type='SNpp45', nerve=f'{side}_{NERVE[seg]}', side=side,
                      proofread='TRUE', status='x', l2_cable_length_um=c, volume_nm3=10.) for c in cables]
    rows += [dict(root_id=len(rows) + i, cell_type='SNpp45', nerve=n, side=s, proofread='FALSE', status='x',
                  l2_cable_length_um=c, volume_nm3=float('nan')) for i, (n, s, c) in enumerate(extra)]
    rows.append(dict(root_id=-1, cell_type='SNpp52', nerve='left_ventral_prothoracic_nerve', side='left',
                     proofread='TRUE', status='x', l2_cable_length_um=1., volume_nm3=1.))
    return pd.DataFrame(rows)


SYM = {leg: [100.]*4 for leg in b.LEGS}


def test_banc_leg_rule_exclusions_and_sensitivity():
    t = table(SYM, extra=[('left_prothoracic_leg_nerve', 'left', 50.),
                          ('left_mesothoracic_leg_nerve, right_mesothoracic_leg_nerve', 'left', 50.),
                          (None, None, 50.), ('right_ventral_prothoracic_nerve', 'left', 70.)])
    legs, excluded, disagree, sens, total = b.banc_legs(t)
    assert total == 28 and len(excluded) == 3
    assert len(legs['T1 right']) == 5 and len(disagree) == 1
    assert sens == {'T1 left': 5, 'T1 right': 5}  # ventral + leg nerve on the left; ventral only on the right


def test_label_boundaries():
    assert b.q_count(-2) == 'COUNT_DEFICIT_REPLICATED' and b.q_count(-1) == 'COUNT_SYMMETRIC'
    assert b.q_count(1) == 'COUNT_SYMMETRIC' and b.q_count(2) == 'COUNT_REVERSED'
    assert b.q_size(0.67) == 'SIZE_DEFICIT_REPLICATED' and b.q_size(0.70) == 'SIZE_INDETERMINATE'
    assert b.q_size(0.85) == 'SIZE_SYMMETRIC' and b.q_size(1/0.85) == 'SIZE_SYMMETRIC'
    assert b.q_size(1.3) == 'SIZE_INDETERMINATE' and b.q_size(1.5) == 'SIZE_REVERSED'
    assert b.q_rf('COUNT_DEFICIT_REPLICATED', 'SIZE_DEFICIT_REPLICATED') == 'RF_DEFICIT_REPLICATED'
    assert b.q_rf('COUNT_REVERSED', 'SIZE_SYMMETRIC') == 'RF_DEFICIT_NOT_REPLICATED'
    assert b.q_rf('COUNT_SYMMETRIC', 'SIZE_INDETERMINATE') == 'RF_PARTIAL'
    assert b.q_rf('COUNT_DEFICIT_REPLICATED', 'SIZE_SYMMETRIC') == 'RF_PARTIAL'


def mal_sizes():
    return {leg: [500.]*n for leg, n in b.EXPECTED_MALECNS.items()}


def run_eval(per_leg, extra=(), source_ok=True, sizes=None, step_a=None):
    legs, excluded, disagree, sens, total = b.banc_legs(table(per_leg, extra))
    return b.evaluate(legs, excluded, disagree, sens, total, sizes or mal_sizes(), source_ok,
                      step_a or dict(b.EXPECTED_MALECNS))


def test_replicated_and_not_replicated_worlds():
    rep = dict(SYM, **{'T1 left': [300.]*7, 'T1 right': [100.]*5})
    e = run_eval(rep)
    assert e['status'] == 'INTEGRITY_ACCEPTED'
    assert e['labels']['Q_RF']['label'] == 'RF_DEFICIT_REPLICATED' and e['labels']['Q_COUNT']['d'] == -2
    e = run_eval(SYM)
    assert e['labels']['Q_RF']['label'] == 'RF_DEFICIT_NOT_REPLICATED'
    assert e['labels']['Q_SIZE']['r'] == pytest.approx(1.0)
    assert e['malecns']['segments']['T1']['count_diff'] == -2


def test_malecns_sizes_sum_csr_rows():
    data = SimpleNamespace(row_ptr=[0, 2, 3, 5], synapse_counts=[4, 6, 7, 1, 2])
    assert b.malecns_sizes(data, {('T1', 'left'): {0, 2}, ('T1', 'right'): {1}}) == \
        {'T1 left': [10., 3.], 'T1 right': [7.]}


@pytest.mark.parametrize('fault', ['source', 'typing', 'exclusions', 'reproduction', 'step_a', 'size'])
def test_integrity_faults(fault):
    per_leg, extra, kw = dict(SYM), [], {}
    if fault == 'source': kw['source_ok'] = False
    if fault == 'typing': per_leg['T3 right'] = []
    if fault == 'exclusions': extra = [(None, None, 1.)]*7
    if fault == 'reproduction': kw['sizes'] = dict(mal_sizes(), **{'T1 right': [500.]*6})
    if fault == 'step_a': kw['step_a'] = dict(b.EXPECTED_MALECNS, **{'T1 right': 6})
    if fault == 'size': per_leg['T1 right'] = [100., float('nan')]
    e = run_eval(per_leg, extra, **kw)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'labels' not in e


def test_protocol_lock():
    spec = b.protocol()
    assert spec['labels']['Q_SIZE']['SIZE_DEFICIT_REPLICATED'] == 'r <= 0.67'
    assert spec['sources']['banc_meta']['sha256'].startswith('86ccf5df')
