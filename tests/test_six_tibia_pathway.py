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
from malecns_backend.embodiment.six_tibia_causal import (
    CANONICAL_SEED, EventObserver, _ObserverFanout, rng_state_digest)
from malecns_backend.embodiment.six_tibia_differential import first_divergence
from malecns_backend.embodiment.six_tibia_pathway_audit import (
    CANONICAL, CANONICAL_CAUSAL, run_pathway_audit, validate_baseline)


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
    def test_a_b_c_observers_are_exactly_equivalent(self):
        outcomes=[]
        for observer_kind in ("none", "noop", "full"):
            brain=MaleCNSBrain(data(),config()); brain.reset(CANONICAL_SEED)
            events=EventObserver(interfaces())
            passive=(SimpleNamespace(before_delivery=lambda *_: None, after_step=lambda *_: None)
                     if observer_kind == "noop" else PathwayObserver(interfaces()))
            brain.diagnostic_observer=(events if observer_kind == "none" else
                                       _ObserverFanout(events,passive))
            brain.v[0]=-44
            sequence=[tuple(map(int,brain.step())) for _ in range(10)]
            outcomes.append((sequence,brain.spike_counts.copy(),rng_state_digest(brain.rng),
                             copy.deepcopy(events.first_sensory)))
        for outcome in outcomes[1:]:
            self.assertEqual(outcomes[0][0],outcome[0])
            np.testing.assert_array_equal(outcomes[0][1],outcome[1])
            self.assertEqual(outcomes[0][2:],outcome[2:])

    def test_callback_cannot_mutate_fired_events_seen_by_canonical_observer(self):
        class Mutator:
            def before_delivery(self,*_): pass
            def after_step(self,brain,fired): fired[:] = 3
        brain=MaleCNSBrain(data(),config()); brain.reset(1); brain.v[0]=-44
        events=EventObserver(interfaces()); brain.diagnostic_observer=_ObserverFanout(events,Mutator())
        fired=brain.step()
        self.assertEqual(tuple(fired),(0,))
        self.assertEqual(events.first_sensory["LF"],.5)

    def test_rng_digest_does_not_advance_generator(self):
        left=np.random.default_rng(7); right=np.random.default_rng(7)
        before=rng_state_digest(left); self.assertEqual(before,rng_state_digest(left))
        np.testing.assert_array_equal(left.random(20),right.random(20))

    def test_first_divergence_finds_injected_sensory_value(self):
        snapshot=SimpleNamespace(angles_rad={x:0. for x in LEG_ORDER},
                                 velocities_rad_s={x:0. for x in LEG_ORDER})
        def row():
            return {"time_ms":1,"before":snapshot,
                "encoded":{x:SimpleNamespace(rates_hz=np.array([1.,2.])) for x in LEG_ORDER},
                "sensory_increments":{x:0 for x in LEG_ORDER},"cns_spike_increment":0,
                "spiking_neuron_indices":(),
                "motor":{x:{"increments":{},"filtered_hz":{}} for x in LEG_ORDER},
                "actuation":{x:{"decoded_offset_rad":0.,"final_target_rad":0.} for x in LEG_ORDER},
                "rng_before_sensory":"same","rng_after_stochastic_drive":"same"}
        a=row(); b=copy.deepcopy(a); b["encoded"]["LH"].rates_hz[1]=9
        self.assertEqual(first_divergence([a],[b]),{
            "first_divergence_time_ms":1,"first_divergence_stage":"sensory",
            "first_divergence_leg":"LH","first_divergence_quantity":"encoded_rate[1]",
            "canonical_value":2.0,"instrumented_value":9.0})

    def test_strict_baseline_rejects_each_discrete_or_causal_change(self):
        legs={leg:{"sensory_spikes":x[0],"selected_motor_spikes":x[1],
              "first_motor_spike_ms":x[2],"peak_decoded_offset_rad":x[3],
              "active":x[1]>0} for leg,x in CANONICAL.items()}
        self.assertTrue(validate_baseline(legs,CANONICAL_CAUSAL)[2])
        for field in ("sensory_spikes","selected_motor_spikes"):
            changed=copy.deepcopy(legs); changed["LF"][field]+=1
            self.assertFalse(validate_baseline(changed,CANONICAL_CAUSAL)[2])
        causal=dict(CANONICAL_CAUSAL); causal["cns_divergence"]+=1
        self.assertFalse(validate_baseline(legs,causal)[2])

    def test_pathway_default_is_production_canonical_seed(self):
        self.assertEqual(run_pathway_audit.__defaults__,(500,CANONICAL_SEED))

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
