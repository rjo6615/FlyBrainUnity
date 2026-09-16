import json
import subprocess
import unittest
import warnings
from array import array
from types import SimpleNamespace

import numpy as np

from malecns_backend.neural import MaleCNSBrain, ModelConfig, NT_NAMES, NT_SIGN
from malecns_backend.neural_audit import controlled_propagation_audit


def fixture(signs=(1, -1, 1), counts=(5, 5)):
    n=3
    return SimpleNamespace(neuron_count=n, row_ptr=array('I',[0,1,2,2]), target_indices=array('I',[1,2]),
        synapse_counts=array('H',counts), neuron_sizes=array('f',[1,1,1]), nt_signs=array('f',signs),
        neurotransmitter_ids=array('B',[1,2,1]), superclass_ids=array('B',[0,0,0]), superclasses=['central'],
        class_ids=array('H',[0,0,0]), classes=['other'], types=['x','x','x'], body_ids=array('q',[10,20,30]),
        neurotransmitters=['unknown','acetylcholine','GABA','glutamate','dopamine','serotonin','octopamine','histamine'])

def cfg(**kw):
    base=dict(min_synapses=5, psp_scale=1, size_alpha=0, inhibitory_gain=1, conductance_based=False,
              refractory_ms=2.2, kc_threshold_offset=0, lamina_bias=0, neuromodulation=False)
    base.update(kw); return ModelConfig(**base)

class NeuralRuntimeTests(unittest.TestCase):
    def test_authoritative_configuration(self):
        p=ModelConfig.calibrated(); self.assertEqual((p.dt,p.v_rest,p.v_threshold,p.tau_mem,p.tau_syn,p.delay_ms),(.5,-52,-45,20,5,1.8))
        self.assertEqual((p.psp_scale,p.min_synapses,p.refractory_ms),(.55,6,3.76)); self.assertTrue(p.conductance_based)

    def test_sign_table_and_effective_weight(self):
        np.testing.assert_array_equal(NT_SIGN,[0,1,-1,-1,1,1,1,-1])
        b=MaleCNSBrain(fixture(),cfg(psp_scale=.3)); self.assertAlmostEqual(float(b.weights[0]),5); self.assertAlmostEqual(b.weight_examples(1)[0]['effective_weight'],1.5)

    def test_cutoff_orientation_sign_and_delay(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            b=MaleCNSBrain(fixture(counts=(4,5)),cfg())
        self.assertEqual(b.weights[0],0)
        np.testing.assert_array_equal(b.region_medians, [1, 1, 1])
        b=MaleCNSBrain(fixture(),cfg()); b.v[0]=-44; self.assertEqual(b.step().tolist(),[0])
        for _ in range(3): b.step(); self.assertEqual(b.g_exc[1],0)
        b.step(); self.assertGreater(b.g_exc[1],0); self.assertEqual(b.g_exc[2],0)

    def test_inhibitory_propagation(self):
        b=MaleCNSBrain(fixture(signs=(-1,1,1)),cfg()); b.v[0]=-44; b.step()
        for _ in range(4): b.step()
        self.assertLess(b.g_inh[1],0); self.assertEqual(b.g_exc[1],0)

    def test_controlled_propagation_audit(self):
        d=fixture(); d.neuron_count=7; d.row_ptr=array('I',[0,6,6,6,6,6,6,6]); d.target_indices=array('I',range(1,7)); d.synapse_counts=array('H',[6]*6)
        d.neuron_sizes=array('f',[1]*7); d.nt_signs=array('f',[1]*7); d.neurotransmitter_ids=array('B',[1]*7)
        d.superclass_ids=array('B',[0]*7); d.class_ids=array('H',[0]*7); d.types=['x']*7; d.body_ids=array('q',range(10,80,10))
        b=MaleCNSBrain(d,cfg(min_synapses=6)); report=controlled_propagation_audit(b,minimum_targets=6)
        self.assertEqual(report['stimulated_body_ids'],[10]); self.assertEqual(report['stimulated_spikes'],1)
        self.assertEqual(report['pre_delay_max_abs_delta'],{'excitatory_state':0.0,'inhibitory_state':0.0})
        self.assertEqual(report['targets_receiving_nonzero_synaptic_response'],6)
        self.assertGreater(report['maximum_excitatory_state_delta'],0); self.assertGreater(report['maximum_absolute_postsynaptic_voltage_delta'],0)

    def test_threshold_reset_refractory_and_reset(self):
        b=MaleCNSBrain(fixture(),cfg()); b.v[0]=-44; b.step(); self.assertEqual(b.v[0],-52); self.assertGreater(b.refractory[0],0)
        b.v[0]=-40; self.assertNotIn(0,b.step()); b.reset(4); self.assertTrue(np.all(b.v == -52)); self.assertEqual(b.spike_counts.sum(),0)

    def test_optional_adaptation_and_depression(self):
        b=MaleCNSBrain(fixture(),cfg(adaptation_increment=2,depression_u=.2)); b.v[0]=-44; b.step()
        self.assertGreater(b.adaptation[0],0)
        for _ in range(4): b.step()
        self.assertLess(b.depression_resource[0],1)

    def test_sensory_mask(self):
        d=fixture(); d.superclasses=['sensory']; b=MaleCNSBrain(d,cfg(sensory_mask=True)); self.assertTrue(np.all(b.weights==0))

    def test_deterministic_and_health(self):
        a=MaleCNSBrain(fixture(),cfg()); b=MaleCNSBrain(fixture(),cfg()); a.set_external_drive([0],100); b.set_external_drive([0],100)
        for _ in range(30): np.testing.assert_array_equal(a.step(),b.step())
        np.testing.assert_array_equal(a.v,b.v); self.assertEqual(a.diagnostics()['nonfinite'],0)
        a.v[0]=np.nan; self.assertEqual(a.diagnostics()['nonfinite'],1)

    def test_whole_cns_sized_initialization(self):
        n=165_122; d=SimpleNamespace(neuron_count=n,row_ptr=np.zeros(n+1,np.uint32),target_indices=np.empty(0,np.uint32),synapse_counts=np.empty(0,np.uint16),
            neuron_sizes=np.ones(n,np.float32),nt_signs=np.ones(n,np.float32),neurotransmitter_ids=np.ones(n,np.uint8),superclass_ids=np.zeros(n,np.uint8),
            superclasses=['central'],class_ids=np.zeros(n,np.uint16),classes=['other'],types=['x']*n,body_ids=np.arange(n,dtype=np.int64),neurotransmitters=list(NT_NAMES))
        b=MaleCNSBrain(d,cfg()); self.assertEqual(len(b.v),165_122); self.assertEqual(b.step().size,0); self.assertEqual(b.diagnostics()['nonfinite'],0)

    def test_js_reference_parity_fixture(self):
        # Generated at test time by the actual lif.js class.  The runner documents
        # the crucial awake-list setup and also exposes the delayed queue state.
        js=json.loads(subprocess.check_output(
            ['node', 'tests/js/lif_reference_fixture.mjs'], text=True))
        py=MaleCNSBrain(fixture(),cfg()); py.v[0]=-44
        for expected in js:
            spikes=py.step(); np.testing.assert_allclose(py.v,expected['v'],rtol=2e-6,atol=2e-6); np.testing.assert_allclose(py.g_exc,expected['e'],rtol=2e-6,atol=2e-6)
            np.testing.assert_allclose(py.g_inh,expected['i'],rtol=2e-6,atol=2e-6); np.testing.assert_allclose(py.refractory,expected['r'],atol=2e-6)
            self.assertEqual(spikes.tolist(),expected['s']); self.assertEqual(py.spike_counts.tolist(),expected['c'])
            self.assertEqual(py._head,expected['head']); self.assertEqual(py._ring,expected['ring'])

    def test_empty_region_groups_are_finite_without_warnings(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            brain = MaleCNSBrain(fixture(), cfg())
        self.assertFalse([w for w in caught if issubclass(w.category, RuntimeWarning)])
        np.testing.assert_array_equal(brain.region_medians, [1, 1, 1])
        self.assertTrue(np.isfinite(brain.region_medians).all())
        self.assertEqual(brain.diagnostics()['nonfinite'], 0)

if __name__ == '__main__': unittest.main()
