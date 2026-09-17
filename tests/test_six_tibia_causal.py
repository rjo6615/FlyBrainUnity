import math
import unittest
from types import SimpleNamespace
import numpy as np

from malecns_backend.embodiment.body import SixTibiaBodySnapshot
from malecns_backend.embodiment.six_tibia import LEG_ORDER, load_six_tibia_interfaces
from malecns_backend.embodiment.six_tibia_causal import (SixTibiaRuntime, analyze_matched,
                                                         run_experiment)


class Brain:
    instances = []
    def __init__(self, _=None):
        self.config=SimpleNamespace(dt=.5); self.spike_counts=np.zeros(165200,dtype=np.uint32)
        self.external_drive=np.zeros(165200); self.instances.append(self)
    def reset(self,seed): self.seed=seed; self.time_ms=0.; self.spike_counts.fill(0)
    def clear_external_drive(self): self.external_drive.fill(0)
    def set_external_drive(self,indices,rates): self.external_drive[indices]=rates
    def step(self):
        self.time_ms += .5
        fired=np.empty(0,dtype=np.intp)
        if self.diagnostic_observer:self.diagnostic_observer.after_step(self,fired)
        return fired


class Body:
    timestep_s=.0001; instances=[]
    def __init__(self,interfaces):
        self.interfaces=interfaces; self.time=0.; self.angles={l:0. for l in LEG_ORDER}; self.commands=[]; self.instances.append(self)
    def observe(self): return SixTibiaBodySnapshot(self.time,self.angles.copy(),{l:0. for l in LEG_ORDER})
    def step(self,commands,count):
        self.commands.append(commands); self.time += count*self.timestep_s
        self.angles={l:c.target_position_rad for l,c in commands.items()}; return self.observe()
    def close(self): self.closed=True


class SixTibiaCausalTests(unittest.TestCase):
    def setUp(self): self.interfaces=load_six_tibia_interfaces()

    def test_exactly_six_encoders_one_shared_brain_and_independent_states(self):
        brain=Brain(); runtime=SixTibiaRuntime(brain,Body(self.interfaces),self.interfaces,1,True)
        self.assertEqual(tuple(runtime.encoders),LEG_ORDER); self.assertIs(runtime.brain,brain)
        self.assertEqual(len({id(x) for x in runtime.observers.values()}),6)
        self.assertEqual(len({id(x) for x in runtime.decoders.values()}),6)
        runtime.decoders["LF"].previous_target=.2
        self.assertIsNone(runtime.decoders["LM"].previous_target)

    def test_closed_applies_and_control_computes_but_zeros_six_offsets(self):
        for apply in (True,False):
            rt=SixTibiaRuntime(Brain(),Body(self.interfaces),self.interfaces,1,apply)
            for decoder in rt.decoders.values():
                decoder.decode=lambda rates,pos,dt,enabled,d=decoder: SimpleNamespace(
                    actuator=d.pathway.actuator_name,target_position_rad=pos+(.1 if enabled else 0),
                    unclamped_position_rad=pos+(.1 if enabled else 0),magnitude_clamped_output_rad=.1,
                    range_clamped_position_rad=pos+(.1 if enabled else 0))
                decoder.directional_rates=lambda rates: {}
            row=rt.step(1)
            self.assertTrue(all(x["decoded_offset_rad"]==.1 for x in row["actuation"].values()))
            self.assertTrue(all(x["applied_neural_contribution_rad"]==(.1 if apply else 0)
                                for x in row["actuation"].values()))

    def test_fresh_runs_match_seed_initial_conditions_and_passive_is_not_s4(self):
        Brain.instances.clear(); Body.instances.clear()
        result=run_experiment(500,7,interfaces=self.interfaces,data=object(),brain_factory=Brain,body_factory=Body)
        self.assertEqual([x.seed for x in Brain.instances],[7,7]); self.assertEqual(len(Brain.instances),2)
        self.assertTrue(result["pre_motor_equivalence"]); self.assertNotIn(result["classification"],("S4","S5","S6","S7"))
        self.assertEqual(result["trajectory"]["maximum_norm_rad"],0)

    def test_ordering_and_s5_s6_s7_prerequisites(self):
        def row(t,angle=0,rate=0,cns=0,motor=0,decoded=0,applied=0):
            snap=SixTibiaBodySnapshot(t/1000,{l:(angle if l=="LF" else 0) for l in LEG_ORDER},{l:0 for l in LEG_ORDER})
            return {"time_ms":t,"after":snap,"encoded":{l:SimpleNamespace(rates_hz=np.array([rate if l=="LF" else 0])) for l in LEG_ORDER},
              "sensory_increments":{l:0 for l in LEG_ORDER},"cns_spike_increment":cns,
              "motor":{l:{"increments":{"x":motor if l=="LF" else 0}} for l in LEG_ORDER},
              "actuation":{l:{"decoded_offset_rad":decoded if l=="LF" else 0,"applied_neural_contribution_rad":applied if l=="LF" else 0} for l in LEG_ORDER}}
        control=[row(t) for t in range(1,8)]
        closed=[row(1),row(2,motor=1,decoded=.1,applied=.1),row(3,angle=.01),row(4,angle=.01,rate=1),row(5,angle=.01,rate=1,cns=1),row(6,angle=.01,rate=1,cns=1,motor=1),row(7,angle=.01,rate=1,cns=1)]
        result=analyze_matched(closed,control)
        self.assertEqual(result["classification"],"S7")
        self.assertEqual(list(result["global_causal_order_ms"].values()),[2,2,2,3,4,5,6])

        # Later divergence signals cannot skip the physical and sensory prerequisites.
        no_sensory=[row(1,decoded=.1,applied=.1),row(2,angle=.01,cns=1)]
        self.assertEqual(analyze_matched(no_sensory,control[:2])["classification"],"S4")

    def test_physics_or_encoding_before_cause_is_invalid(self):
        # Reuse a real zero-activity row and corrupt its closed physical state.
        b1,b2=Brain(),Brain(); x=SixTibiaRuntime(b1,Body(self.interfaces),self.interfaces,1,True).step(1)
        y=SixTibiaRuntime(b2,Body(self.interfaces),self.interfaces,1,False).step(1)
        x["after"]=SixTibiaBodySnapshot(.001,{**x["after"].angles_rad,"LF":.1},x["after"].velocities_rad_s)
        self.assertEqual(analyze_matched([x],[y])["classification"],"INVALID")

    def test_angle_differences_include_all_tibiae_at_specified_checkpoints(self):
        def row(t, differences=None, applied=False):
            differences = differences or {leg: 0. for leg in LEG_ORDER}
            snap=SixTibiaBodySnapshot(t/1000,differences,{leg:0. for leg in LEG_ORDER})
            return {"time_ms":t,"after":snap,
              "encoded":{leg:SimpleNamespace(rates_hz=np.array([0.])) for leg in LEG_ORDER},
              "sensory_increments":{leg:0 for leg in LEG_ORDER},"cns_spike_increment":0,
              "motor":{leg:{"increments":{"x":0}} for leg in LEG_ORDER},
              "actuation":{leg:{"decoded_offset_rad":.01 if applied else 0.,
                                 "applied_neural_contribution_rad":.01 if applied else 0.}
                           for leg in LEG_ORDER}}

        control=[row(t) for t in range(1,501)]
        closed=[]
        for t in range(1,501):
            differences={leg:(index+1)*t/10000 for index,leg in enumerate(LEG_ORDER)}
            closed.append(row(t,differences,applied=t == 1))
        result=analyze_matched(closed,control)

        for index,leg in enumerate(LEG_ORDER):
            expected={str(t):(index+1)*t/10000 for t in (50,100,250,500)}
            self.assertEqual(result["per_leg"][leg]["angle_differences_rad"],expected)
            self.assertAlmostEqual(result["per_leg"][leg]["maximum_absolute_angle_difference_rad"],
                                   expected["500"])
            expected_rms=math.sqrt(sum(((index+1)*t/10000)**2 for t in range(1,501))/500)
            self.assertAlmostEqual(result["per_leg"][leg]["rms_post_motor_angle_difference_rad"],
                                   expected_rms)
            self.assertAlmostEqual(result["per_leg"][leg]["final_angle_difference_rad"],
                                   expected["500"])
        scale=math.sqrt(sum((index+1)**2 for index in range(len(LEG_ORDER))))
        expected_norms=[scale*t/10000 for t in range(1,501)]
        self.assertAlmostEqual(result["trajectory"]["maximum_norm_rad"],expected_norms[-1])
        self.assertAlmostEqual(result["trajectory"]["rms_post_motor_norm_rad"],
                               math.sqrt(sum(x*x for x in expected_norms)/len(expected_norms)))
        self.assertAlmostEqual(result["trajectory"]["final_norm_rad"],expected_norms[-1])

    def test_no_controller_vocabulary_or_changed_constants(self):
        from pathlib import Path
        from malecns_backend.embodiment.motor import MotorDecoder
        from malecns_backend.embodiment.sensory import SensoryEncoder
        source=Path("malecns_backend/embodiment/six_tibia_causal.py").read_text().lower()
        for invocation in ("preprogrammedsteps", "hybridturningcontroller", "from flygym.examples.locomotion"):
            self.assertNotIn(invocation,source)
        self.assertEqual((SensoryEncoder.maximum_rate_hz,SensoryEncoder.width_normalized,SensoryEncoder.cutoff_hz),(120.,.25,5.))
        self.assertEqual(MotorDecoder.half_activation_hz,17.)


if __name__ == "__main__": unittest.main()
