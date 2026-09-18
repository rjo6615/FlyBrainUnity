import json
import unittest
from array import array
from types import SimpleNamespace

import numpy as np

from malecns_backend.neural import MaleCNSBrain, ModelConfig
from malecns_backend.embodiment.lh_lm_pathway import (
    CANONICAL_DURATION_MS, CANONICAL_SEED, EARLY_WINDOW_END_MS,
    LH_WITHHELD_LM_DELTA, LM_BASELINE_SPIKES, LM_TARGET_BASELINE,
    MAX_GROUP_SIZE, MAX_PATH_EDGES, SOURCE_LEG, TARGET_BODY_IDS,
    _bounded_distances, configure_transmission_withholding,
    discover_candidates, early_window_summary, make_groups)
from malecns_backend.embodiment.lh_lm_pathway_audit import _run_condition


def graph_fixture():
    # 100(LH)->200->800911 and ->300->400->801234; 900 is reverse-only.
    ids = [100, 200, 300, 400, 800911, 801234, 900]
    edges = [[1, 2], [4], [3], [5], [], [], [0]]
    flat = [x for row in edges for x in row]; ptr = [0]
    for row in edges: ptr.append(ptr[-1] + len(row))
    return SimpleNamespace(neuron_count=len(ids), row_ptr=array('I', ptr),
        target_indices=array('I', flat), synapse_counts=array('H', [10] * len(flat)),
        neuron_sizes=array('f', [1] * len(ids)), nt_signs=array('f', [1] * len(ids)),
        neurotransmitter_ids=array('B', [1] * len(ids)), superclass_ids=array('B', [0] * len(ids)),
        superclasses=['central'], class_ids=array('H', [0] * len(ids)), classes=['interneuron'],
        types=['sensory', 'A', 'B', 'B', 'motor', 'motor', 'reverse'], body_ids=array('q', ids),
        body_id_to_index={body: i for i, body in enumerate(ids)},
        neurotransmitters=['unknown', 'acetylcholine'],
        dense_index=lambda body: ids.index(int(body)))


def config():
    return ModelConfig(min_synapses=1, psp_scale=1, size_alpha=0, inhibitory_gain=1,
        conductance_based=False, neuromodulation=False, sensory_mask=False,
        kc_threshold_offset=0, lamina_bias=0, delay_ms=.5)


class PathwayTests(unittest.TestCase):
    def test_canonical_scope_and_constants(self):
        self.assertEqual(SOURCE_LEG, 'LH'); self.assertEqual(TARGET_BODY_IDS, (800911, 801234))
        self.assertEqual((CANONICAL_SEED, CANONICAL_DURATION_MS), (1, 500))
        self.assertEqual((LM_BASELINE_SPIKES, LM_TARGET_BASELINE, LH_WITHHELD_LM_DELTA),
                         (34, {800911: 17, 801234: 17}, -18))
        self.assertEqual((MAX_PATH_EDGES, EARLY_WINDOW_END_MS), (3, 49.0))

    def test_directed_bounded_traversal_and_candidate_evidence(self):
        brain = MaleCNSBrain(graph_fixture(), config())
        distances = _bounded_distances(brain.indptr, brain.indices, [0])
        self.assertEqual(distances[5], 3); self.assertNotIn(6, distances)
        candidates = discover_candidates(brain, [0], {1: [10., 36.], 2: [35.]})
        self.assertEqual([x.body_id for x in candidates], [200, 300, 400])
        first = candidates[0].to_dict()
        self.assertTrue(first['observed_active']); self.assertEqual(first['evidence_class'], 'OBSERVATIONAL_CANDIDATE_NOT_CAUSAL')
        with self.assertRaises(ValueError): discover_candidates(brain, [0], max_path_edges=4)

    def test_transmission_withholding_preserves_neuron_graph_weights_and_threshold(self):
        brain = MaleCNSBrain(graph_fixture(), config()); before = brain.weights.copy()
        ptr, edges, threshold = brain.indptr.copy(), brain.indices.copy(), brain.config.v_threshold
        configure_transmission_withholding(brain, [200]); brain.v[1] = -44
        fired = brain.step()
        self.assertIn(1, fired); self.assertIn(1, brain._last_transmission_withheld)
        self.assertEqual(brain.spike_counts[1], 1)  # counterfactual activity observable
        for _ in range(2): brain.step()
        self.assertEqual(brain.g_exc[4], 0)  # outgoing event was never delivered
        np.testing.assert_array_equal(brain.weights, before); np.testing.assert_array_equal(brain.indptr, ptr)
        np.testing.assert_array_equal(brain.indices, edges); self.assertEqual(brain.config.v_threshold, threshold)
        self.assertEqual(brain.data.dense_index(200), 1)  # neuron remains addressable

    def test_non_target_transmission_and_input_remain_functional(self):
        brain = MaleCNSBrain(graph_fixture(), config()); configure_transmission_withholding(brain, [200])
        brain.v[0] = -44
        brain.step(); brain.step()
        self.assertGreater(brain.g_exc[1], 0)  # withheld cell still receives its input
        self.assertGreater(brain.g_exc[2], 0)  # unrelated output from neuron 100 unchanged

    def test_rng_consumption_is_identical(self):
        a = MaleCNSBrain(graph_fixture(), config()); b = MaleCNSBrain(graph_fixture(), config())
        configure_transmission_withholding(b, [200]); a.set_external_drive([0], 500); b.set_external_drive([0], 500)
        for _ in range(10): a.step(); b.step()
        self.assertEqual(a.rng.bit_generator.state, b.rng.bit_generator.state)

    def test_early_window_is_separate_and_flags_feedback(self):
        rows = [{'time_ms': 31, 'spiking_neuron_indices': (4, 1)},
                {'time_ms': 49, 'spiking_neuron_indices': (5, 1)},
                {'time_ms': 50, 'spiking_neuron_indices': (4,)}]
        value = early_window_summary(rows, [4, 5], [1], 40)
        self.assertEqual(value['lm_mapped_motor_spikes'], 2); self.assertEqual(value['first_lm_motor_spike_ms'], 31)
        self.assertEqual(value['candidate_counterfactual_spikes'], 2)
        self.assertTrue(value['feedback_contaminated_before_window_end'])
        json.dumps(value)

    def test_groups_are_explicit_and_oversized_groups_are_ineligible(self):
        brain = MaleCNSBrain(graph_fixture(), config())
        candidates = discover_candidates(brain, [0], {1: [1], 2: [1], 3: [1]})
        groups = make_groups(candidates, max_group_size=1)
        self.assertEqual(groups[0]['body_ids'], [300, 400]); self.assertFalse(groups[0]['eligible'])
        self.assertEqual(MAX_GROUP_SIZE, 6)

    def test_physics_failure_is_partial_closes_and_programming_errors_propagate(self):
        class PhysicsError(Exception): pass
        class Brain:
            def __init__(self, data): self.data=data; self.transmission_withheld_indices=[]
        class Body:
            closed = False
            def close(self): self.closed=True
        body = Body()
        class Runtime:
            pass
        # Validate the narrow exception/finally structure directly with patched constructor.
        import malecns_backend.embodiment.lh_lm_pathway_audit as audit
        original = audit.SixTibiaRuntime
        class FakeRuntime:
            def __init__(self, brain, body, interfaces, seed, apply, diagnostic_observer=None):
                self.brain=brain; self.body=body; self.interfaces={}; self.withheld_sensory=None
            def step(self, t): raise PhysicsError('unstable')
        audit.SixTibiaRuntime = FakeRuntime
        try:
            with self.assertRaises((AttributeError, KeyError)):
                # Summary cannot understand this intentionally tiny fake, but finally still executes.
                _run_condition([], {}, object(), Brain, lambda _: body, duration_ms=1,
                               physics_errors=(PhysicsError,))
            self.assertTrue(body.closed)
            body.closed=False
            class BugRuntime(FakeRuntime):
                def step(self, t): raise ValueError('bug')
            audit.SixTibiaRuntime=BugRuntime
            with self.assertRaises(ValueError):
                _run_condition([], {}, object(), Brain, lambda _: body, duration_ms=1,
                               physics_errors=(PhysicsError,))
            self.assertTrue(body.closed)
        finally: audit.SixTibiaRuntime=original


if __name__ == '__main__': unittest.main()
