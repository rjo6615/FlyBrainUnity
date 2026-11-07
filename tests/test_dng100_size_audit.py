import math

import numpy as np

from malecns_backend.embodiment import dng100_size_audit as audit


def test_neck_plane_separates_and_takes_lower_middle_minimiser():
    brain = np.array([1., 2., 3., 10.])
    cord = np.array([20., 21., 30.])
    p = audit.neck_plane(brain, cord)
    # minimisers 10..20 (error 0; cord counts as wrong only strictly below z*); lower-middle of 11 -> 15
    assert p['misclassified'] == 0 and p['minimiser_range'] == [10., 20.] and p['z_star'] == 15.
    # one brain outlier at 25 cannot be fixed without misclassifying cord vertices
    p = audit.neck_plane(np.append(brain, 25.), cord)
    assert p['misclassified'] == 1 and p['brain_above'] == 1 and math.isclose(p['rate'], 1/8)


def test_cable_split_splits_crossing_segments_at_the_plane():
    # neuron 0: vertical 0 -> 10 (crosses z*=4: 6 above) then 10 -> (3,0,14) (length 5, all above)
    # neuron 1: entirely below; neuron 2: single vertex, no cable
    pos = np.array([[0, 0, 0], [0, 0, 10], [3, 0, 14], [0, 0, 1], [0, 0, 2], [5, 5, 5]], float)
    seg = np.array([[0, 1], [1, 2], [3, 4]])
    voff = np.array([0, 3, 5, 6])
    total, above = audit.cable_split(voff, pos, seg, 4.)
    assert np.allclose(total, [15, 1, 0]) and np.allclose(above, [11, 0, 0])
    # a segment exactly on the plane counts as below; reversed direction gives the same split
    total, above = audit.cable_split(voff, pos[[1, 0, 2, 3, 4, 5]], np.array([[1, 0], [0, 2], [3, 4]]), 4.)
    assert np.allclose(above[0], 6 + 5)


def test_median_rule_is_upper_middle_of_positive_values():
    assert audit.median_rule([0, -1, 1, 2, 3, 4]) == 3.
    assert audit.median_rule([5, 1, 3]) == 3.


def test_scaling_rho_matches_closed_form():
    size = np.array([100., 10., 10., 10., 50.])
    f = np.array([.25, 1., 1., 1., 0.])
    region2 = np.array([True, True, True, True, False])
    s_r1, s_vnc, rho, m_vnc = audit.scaling(size, f, region2, m_r1=10.)
    assert m_vnc == 10.  # positive size*f in region 2: sorted [10, 10, 10, 25] -> upper middle (index 2)
    assert np.allclose(s_r1[:4], [10, 1, 1, 1]) and np.allclose(s_vnc[:4], [2.5, 1, 1, 1])
    # rho = (m_vnc / m_r1) / f
    assert np.allclose(rho[:4], [4, 1, 1, 1]) and np.isinf(rho[4])
    _, _, rho, _ = audit.scaling(np.array([10., 10.]), np.array([np.nan, 1.]), np.array([True, True]), m_r1=10.)
    assert np.isnan(rho[0]) and rho[1] == 1.


def test_label_rules():
    core = {k: 1. for k in audit.CORE}
    assert audit.label(.02, 5., [5.], core)[0] == 'INCONCLUSIVE'
    assert audit.label(.0, 5., [5.], {**core, 'E1': 0.})[0] == 'INCONCLUSIVE'
    assert audit.label(.0, 5., [5.], core, sources_ok=False)[0] == 'INCONCLUSIVE'
    v, d = audit.label(.005, 2., [1., 1., 1.], core)
    assert v == 'SIZE_MISMATCH_MATERIAL' and d['checks'] == dict(a_dng100_L=True, b_network_dn_median=False)
    v, d = audit.label(.005, 1.9, [1., 3., np.inf, np.nan], core)
    assert v == 'SIZE_MISMATCH_MATERIAL' and d['checks']['b_network_dn_median'] and d['network_dns_scored'] == 3
    v, _ = audit.label(.005, 1.9, [1., 1.5, 3.], core)
    assert v == 'SIZE_MISMATCH_MINOR'


def test_brain_cord_sets_follow_declared_superclass_rule():
    names = ['cb_intrinsic', 'cb_sensory', 'cb_efferent', 'ol_intrinsic', 'visual_projection', 'descending_neuron',
             'vnc_intrinsic', 'vnc_motor', 'unknown', 'ENS', 'sensory_ascending']
    brain, cord = audit.brain_cord_sets(names)
    assert [names[k] for k in brain] == ['cb_intrinsic', 'ol_intrinsic', 'visual_projection']
    assert [names[k] for k in cord] == ['vnc_intrinsic', 'vnc_motor']


def test_jsonable_keeps_infinity_readable():
    assert audit.jsonable({'a': [np.inf, np.float64('nan'), np.int64(2)]}) == {'a': ['inf', None, 2]}
