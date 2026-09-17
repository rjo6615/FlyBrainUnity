import copy
import json
import unittest
from array import array
from types import SimpleNamespace

import numpy as np

from malecns_backend.neural import MaleCNSBrain, ModelConfig
from malecns_backend.embodiment.pathway_diagnostics import (
    PathwayObserver, directed_distances, pathway_graph_report,
    selected_motor_inventory, targeted_incoming)
from malecns_backend.embodiment.six_tibia import LEG_ORDER, load_six_tibia_interfaces


def data():
    # 0 -> 1 excitatory, 2 -> 1 inhibitory, 1 -> 3. Rows are presynaptic.
    return SimpleNamespace(neuron_count=4, row_ptr=array('I', [0, 1, 2, 3, 3]),
        target_indices=array('I', [1, 3, 1]), synapse_counts=array('H', [6, 6, 8]),
        neuron_sizes=array('f', [1]*4), nt_signs=array('f', [1, 1, -1, 1]),
        neurotransmitter_ids=array('B', [1, 1, 2, 1]), superclass_ids=array('B', [0]*4),
        superclasses=['central'], class_ids=array('H', [0]*4), classes=['other'],
        types=['source', 'motor', 'inhibitor', 'downstream'], body_ids=array('q', [10,20,30,40]),
        neurotransmitters=['unknown','acetylcholine','GABA'])


def config():
    return ModelConfig(min_synapses=1, psp_scale=1, size_alpha=0, inhibitory_gain=1,
        conductance_based=False, delay_ms=.5, refractory_ms=2, sensory_mask=False,
        neuromodulation=False, adaptation_increment=0, kc_threshold_offset=0, lamina_bias=0)


def interfaces():
    result = {}
    for leg in LEG_ORDER:
        pop = SimpleNamespace(name=f'{leg} tibia extensor', body_ids=(20,), dense_indices=(1,),
            direction=1, function='tibia extensor', confidence='SUPPORTED',
            provenance='ANNOTATION_DERIVED')
        result[leg] = SimpleNamespace(side=leg[0], segment=leg[1], motor_populations=(pop,),
            sensor=SimpleNamespace(dense_indices=(0,)))
    return result


class SixTibiaPathwayTests(unittest.TestCase):
    def test_inventory_uses_exact_validated_mapping(self):
        real = load_six_tibia_interfaces(); inventory = selected_motor_inventory(real)
        self.assertEqual(tuple(inventory), LEG_ORDER)
        for leg in LEG_ORDER:
            expected = [(p.name, list(p.body_ids)) for p in real[leg].motor_populations]
            self.assertEqual([(p['population_name'], p['body_ids']) for p in inventory[leg]], expected)

    def test_passive_observer_does_not_mutate_state_or_consume_rng(self):
        plain = MaleCNSBrain(data(), config()); watched = MaleCNSBrain(data(), config())
        observer = PathwayObserver(interfaces()); watched.diagnostic_observer = observer
        plain.reset(7); watched.reset(7); plain.v[0] = watched.v[0] = -44
        for _ in range(8): np.testing.assert_array_equal(plain.step(), watched.step())
        for name in ('v','g_exc','g_inh','refractory','adaptation','depression_resource','spike_counts'):
            np.testing.assert_array_equal(getattr(plain,name), getattr(watched,name))
        self.assertEqual(plain.rng.bit_generator.state, watched.rng.bit_generator.state)

    def test_direct_contributor_requires_edge_and_observed_spike_and_signs_match(self):
        brain = MaleCNSBrain(data(), config()); observer = PathwayObserver(interfaces())
        brain.diagnostic_observer = observer; brain.v[0] = brain.v[2] = -44
        for _ in range(5): brain.step()
        report = observer.report(brain); motor = report['motor_neurons']['20']
        contributors = {x['body_id']: x for x in motor['active_direct_presynaptic_contributors']}
        self.assertEqual(set(contributors), {10, 30})
        self.assertGreater(contributors[10]['effective_modeled_contribution'], 0)
        self.assertLess(contributors[30]['effective_modeled_contribution'], 0)
        self.assertGreater(motor['input']['excitatory'], 0); self.assertLess(motor['input']['inhibitory'], 0)
        self.assertTrue(np.isfinite(motor['closest_to_threshold_mV']))
        self.assertEqual(targeted_incoming(brain, [1])[1][0][0], 0)

    def test_spikes_and_population_roles_remain_separate_and_json_serializes(self):
        brain = MaleCNSBrain(data(), config()); observer = PathwayObserver(interfaces())
        brain.diagnostic_observer = observer; brain.v[1] = -44; brain.step()
        report = observer.report(brain)
        self.assertEqual(report['motor_neurons']['20']['spike_times_ms'], [.5])
        self.assertIn('extensor', selected_motor_inventory(interfaces())['LF'][0]['role'])
        json.dumps(report)

    def test_directed_anatomical_and_dynamic_distances_are_distinct(self):
        brain = MaleCNSBrain(data(), config())
        distance = directed_distances(brain, [0]); reverse = directed_distances(brain, [3])
        self.assertEqual(distance[3], 2); self.assertEqual(reverse[0], -1)
        observer = PathwayObserver(interfaces()); brain.diagnostic_observer = observer
        brain.v[0] = -44
        for _ in range(4): brain.step()
        graph = pathway_graph_report(brain, interfaces(), observer)
        self.assertIn('anatomical_distance_from_sensory', graph['LF'])
        self.assertIn('observed_active_distance_from_sensory', graph['LF'])
        self.assertIn('not causal proof', graph['LF']['interpretation'])

    def test_no_dense_adjacency_or_intervention_vocabulary(self):
        from pathlib import Path
        source = Path('malecns_backend/embodiment/pathway_diagnostics.py').read_text().lower()
        self.assertNotIn('np.zeros((brain.n, brain.n', source)
        for forbidden in ('descending_drive', 'leave_one_out', 'artificial_motor_stimulation'):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__': unittest.main()
