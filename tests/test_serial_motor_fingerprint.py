"""Synthetic checks for the serial fingerprint test; no real connectome, physics or CNS."""
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import serial_motor_fingerprint as s


def graph(edges, types):
    """edges: (pre, post, count); CSR rows are presynaptic."""
    n = len(types)
    edges = sorted(edges)
    row_ptr = [0]*(n + 1)
    for pre, _, _ in edges:
        row_ptr[pre + 1] += 1
    row_ptr = list(np.cumsum(row_ptr))
    return SimpleNamespace(row_ptr=row_ptr, target_indices=[e[1] for e in edges],
                           synapse_counts=[e[2] for e in edges], types=types)


def bodymap(entries):
    return dict(muscles=[dict(name=n, actuator=a, dir=1, idx=i) for n, a, i in entries])


def test_labels_union_joint_classes_and_exclude_ambiguous():
    neurons, ambiguous = s.labels(bodymap([
        ('Pleural remotor/abductor MN T1 left', 'coxa_T1_left', [1, 2]),
        ('Pleural remotor/abductor MN T1 left', 'coxa_abduct_T1_left', [1, 2]),
        ('Ti flexor MN T1 left', 'tibia_T1_left', [3, 2]),
        ('GNG133 antenna', 'antenna_left', [9])]))
    assert ambiguous == [2] and set(neurons) == {1, 3}
    assert neurons[1]['joints'] == {'coxa', 'coxa_abduct'} and neurons[1]['leg'] == (1, 'left')


def test_labels_reject_actuator_leg_disagreement():
    with pytest.raises(ValueError, match='disagreement'):
        s.labels(bodymap([('Ti flexor MN T1 left', 'tibia_T2_left', [1])]))


def test_fingerprints_use_incoming_typed_input_only():
    # 0,1 premotor typed A/B; 2 untyped; 3 and 4 are motor targets; 3 -> 0 is outgoing from 3
    data = graph([(0, 3, 3), (1, 3, 1), (2, 3, 50), (3, 0, 7), (2, 4, 5)], ['A', 'B', '', 'MN', 'MN'])
    prints, vocabulary, zero = s.fingerprints(data, [3, 4])
    assert vocabulary == ['A', 'B'] and zero == [4]
    assert np.allclose(prints[3], [.75, .25])


def serial_world(swap=False):
    """Two populations in every leg; population X gets type A input, Y gets type B input."""
    types, edges, entries = ['A', 'B'], [], []
    for segment, side in s.LEGS:
        for pop, partner in (('X', 0), ('Y', 1)):
            ids = []
            for _ in range(2):
                ids.append(len(types)); types.append('MN')
                edges.append((partner if not (swap and segment == 2) else 1 - partner, ids[-1], 10))
                edges.append((1 - partner, ids[-1], 1))
            entries.append((f'{pop} MN T{segment} {side}', f'{"tibia" if pop == "X" else "femur"}_T{segment}_{side}', ids))
    return graph(edges, types), bodymap(entries)


def test_serial_pairs_and_contralateral_pairs_are_the_declared_sets():
    assert len(s.pairs('serial')) == 12 and all(a[1] == b[1] and a[0] != b[0] for a, b in s.pairs('serial'))
    assert len(s.pairs('contralateral')) == 6 and all(a[0] == b[0] and a[1] != b[1] for a, b in s.pairs('contralateral'))


def spec(permutations=19):
    return dict(null=dict(seed=1, permutations=permutations), acceptance=dict(PASS_requires_all=dict(
        a_pooled_serial_type_accuracy_min=.7, b_permutation_p_max=.1,
        c_serial_joint_accuracy_min_per_admitted_class=dict(min=.6), d_T1_reference_serial_type_accuracy_min=.7)))


def test_distinct_serial_fingerprints_are_recovered_blind():
    data, bm = serial_world()
    neurons, _ = s.labels(bm)
    prints, _, _ = s.fingerprints(data, neurons)
    result = s.evaluate(neurons, prints, spec())
    assert result['pooled_serial_type_accuracy'] == 1 and result['T1_reference_serial_type_accuracy'] == 1
    assert result['permutation']['p'] <= .1
    # Too few scorable neurons for the admitted classes -> INCONCLUSIVE, never PASS.
    assert result['verdict'] == 'INCONCLUSIVE' and result['admitted_class_serial_n']['femur_twist'] == 0


def test_segment_with_swapped_wiring_lowers_accuracy():
    data, bm = serial_world(swap=True)
    neurons, _ = s.labels(bm)
    prints, _, _ = s.fingerprints(data, neurons)
    result = s.evaluate(neurons, prints, spec())
    assert result['pooled_serial_type_accuracy'] < 1
    assert result['per_pair']['serial']['T1L->T2L']['type_accuracy'] == 0
    assert result['per_pair']['serial']['T1L->T3L']['type_accuracy'] == 1


def test_assignment_ties_choose_first_sorted_population():
    names, unit = ['a', 'b'], np.array([[1., 0.], [1., 0.]])
    assert s.assign(np.array([2., 0.]), names, unit) == 'a'


def test_protocol_lock_and_exclusive_output(tmp_path, monkeypatch):
    assert s.protocol()['null']['seed'] == 20261101
    out = tmp_path/'result.json'; out.write_text('{}')
    monkeypatch.setattr(s, 'run', lambda cache: dict(verdict='FAIL'))
    with pytest.raises(FileExistsError):
        s.main(['--cache', str(tmp_path), '--output', str(out)])
