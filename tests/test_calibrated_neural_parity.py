"""Compare the actual JS calibrated brain constructor and integration to Python."""
import json
import subprocess
from types import SimpleNamespace

import numpy as np

from malecns_backend.neural import MaleCNSBrain, ModelConfig, region_scales


def test_calibrated_constructor_and_mixed_input_reference_parity():
    # Each region has an even number of positive sizes, including the upper
    # median/averaged median distinction. Include capped, missing-size, sensory,
    # graded inhibitory, octopaminergic, Kenyon, and biased lamina neurons.
    sizes = [1, 3, 9, 27, 2, 6, 18, 54, 4, 12, 36, 108, 0]
    sc = [0] * 4 + [1] * 4 + [2] * 5
    types = ['L1', 'visual', 'visual', 'visual', 'KC', 'OA-VUMa1', 'central',
             'central', 'sensor', 'IN', 'MN', 'MN', 'missing']
    # Mixed converging inputs; sub-cutoff and sensory-target edges are included.
    edges = {0: [(9, 6), (10, 40)], 1: [(9, 5), (11, 100)],
             2: [(9, 35), (10, 30)], 5: [(10, 60)],
             8: [(9, 20), (10, 100), (11, 80), (4, 60), (8, 80)],
             9: [(10, 12), (11, 8)], 10: [(11, 9)]}
    indptr, indices, counts = [0], [], []
    for i in range(len(sizes)):
        for target, count in edges.get(i, []):
            indices.append(target); counts.append(count)
        indptr.append(len(indices))
    signs = [1, 1, -.7, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    classes = [0] * len(sizes); classes[4] = 1
    payload = dict(sizes=sizes, superclass=sc, cls=classes, nt=[1] * len(sizes),
                   meta=dict(superclasses=['ol_intrinsic', 'cb_intrinsic', 'vnc_sensory'],
                             classes=['other', 'Kenyon_Cell'], types=types),
                   indptr=indptr, indices=indices, counts=counts, signs=signs,
                   steps=160, events={str(t): [0, 1, 2, 5, 8] for t in range(0, 100, 10)})
    # Only cell 8 should be sensory: use a fourth superclass for other VNC cells.
    payload['meta']['superclasses'].append('vnc_intrinsic')
    payload['superclass'][9:] = [3] * 4
    expected = json.loads(subprocess.check_output(
        ['node', 'tests/js/calibrated_lif_audit.mjs'], input=json.dumps(payload), text=True))
    data = SimpleNamespace(neuron_count=len(sizes), neuron_sizes=np.array(sizes, np.float32),
        superclasses=payload['meta']['superclasses'], superclass_ids=np.array(sc),
        classes=payload['meta']['classes'], class_ids=np.array(classes), types=types,
        nt_signs=np.array(signs, np.float32), neurotransmitter_ids=np.array(payload['nt']),
        row_ptr=np.array(indptr), target_indices=np.array(indices), synapse_counts=np.array(counts))
    brain = MaleCNSBrain(data)
    scale, region, _ = region_scales(data, brain.config)
    np.testing.assert_allclose(scale, expected['scales'], rtol=2e-6)
    np.testing.assert_array_equal(region, expected['region'])
    np.testing.assert_array_equal(brain.sensory, expected['sensory'])
    for actual, key in ((brain.weights, 'weights'), (brain.pre_sign, 'sign'),
                        (brain.threshold_offset, 'threshold'), (brain.bias, 'bias')):
        np.testing.assert_allclose(actual, expected[key], rtol=2e-6)
    for t, state in enumerate(expected['states']):
        brain.clear_external_drive()
        brain.set_external_drive(payload['events'].get(str(t), []), 1000 / brain.config.dt)
        fired = brain.step()
        for key, name in (('v', 'v'), ('e', 'g_exc'), ('i', 'g_inh'), ('r', 'refractory')):
            np.testing.assert_allclose(getattr(brain, name), state[key], atol=2e-5, rtol=2e-6,
                                       err_msg=f'{name} at step {t}')
        np.testing.assert_array_equal(brain.spike_counts, state['counts'])
        assert fired.tolist() == state['spikes']
    assert brain.spike_counts[9:].sum() > 0
    assert brain.g_inh[9] < 0
