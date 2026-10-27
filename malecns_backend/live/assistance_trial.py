"""Injectable assistance Trial, not a campaign launcher or scientific evaluator.

The original Trial owns all neural gating/encoders/safety/kernel integration.
This subclass adds mechanical evidence and the predeclared between-step event.
"""
from dataclasses import asdict
import argparse
import hashlib

from . import assistance_native as mechanical
from . import balance_contribution as base

MANIFEST = 'docs/evidence/assistance-native-adapter-v1/implementation.json'
SOURCES = ('malecns_backend/live/assistance_native.py', 'malecns_backend/live/assistance_trial.py',
           'tests/test_assistance_native.py', 'tests/test_assistance_trial.py',
           'docs/ASSISTANCE_NATIVE_ADAPTER_V1.md')


def implementation_record():
    """Static source identity, deliberately not runtime/scientific readiness."""
    plan = mechanical.plan
    plan.verify(plan.ROOT/'docs/evidence/assistance-contribution-v1/protocol.json')
    return dict(schema='assistance-native-adapter-implementation-v1',
        status='MECHANICAL_COMPONENT_ONLY_CAMPAIGN_INTEGRATION_PENDING',
        sources_canonical_lf_sha256={path: hashlib.sha256((plan.ROOT/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                                    for path in SOURCES},
        native_qualification_executed=False, scientific_campaign_executed=False,
        full_scientific_evaluator_implemented=False, fresh_process_launcher_implemented=False,
        motor_coverage=[20,42], new_motor_admissions=0)


def source_check(path=None):
    record = mechanical.plan.read_json(path or mechanical.plan.ROOT/MANIFEST)
    mechanical.require(record == implementation_record(), 'implementation source checkpoint mismatch')
    return record


class Trial(base.Trial):
    def __init__(self, arm_id, qualification=None):
        mechanical.require(arm_id in mechanical.plan.ARM_IDS, 'declared assistance arm required')
        mechanical.require((arm_id == 'A_NC') == (qualification is None),
                           'first A_NC must qualify once; later arms require its qualification')
        super().__init__(arm_id.split('_')[1])
        self.arm_id = arm_id
        self.qualification = {} if qualification is None else qualification
        self.intervention = None
        self.mechanical_samples = []
        self.mechanical_context = None

    def bind(self, sim, physics, obs):
        super().bind(sim, physics, obs)
        original = mechanical.model_record(physics.model, physics.data)
        mechanical.validate_binding(self.inventory, original)
        # Existing full inventory validation was performed by base.Trial.bind.
        self.intervention = mechanical.Intervention(self.arm_id, physics.model, physics.data, self.inventory, original)
        self.mechanical_context = dict(schema=mechanical.SCHEMA, arm_id=self.arm_id,
            inventory=self.inventory, original=original, neutral=self.intervention.neutral)
        self._capture_mechanical(physics)  # initial base capture precedes intervention binding

    def _capture_mechanical(self, physics):
        import mujoco
        before = mechanical.data_digest(physics.data)
        sample = dict(state_index=len(self.mechanical_samples), time_s=float(physics.data.time),
            model_sha256=mechanical.digest(mechanical.components(physics.model, physics.data)),
            **mechanical.force_record(mujoco, getattr(physics.model, 'ptr', physics.model),
                                      getattr(physics.data, 'ptr', physics.data)))
        mechanical.require(before == mechanical.data_digest(physics.data), 'mechanical capture mutated native data')
        self.mechanical_samples.append(sample)

    def capture(self, physics, obs, action):
        super().capture(physics, obs, action)
        if self.intervention is not None:
            self._capture_mechanical(physics)

    def protected_state(self):
        frame = self.session._kernel.gi_frame.f_locals
        mechanical.require(self.session._state['brain'] is self.brain, 'session brain binding mismatch')
        return base.context.digest(dict(
            brain=base.neural_state_digest(self.brain), tick=self.tick,
            weights=base.array_digest(self.brain.weights, self.brain.pre_sign, self.brain.indices, self.brain.indptr),
            session=base.native({k: v for k, v in self.session._state.items() if k != 'brain'}),
            proprio_rng={leg: base.native(rng.bit_generator.state) for leg, rng in frame['rngs'].items()},
            encoders={leg: base.encoder_state(encoder) for leg, encoder in frame['encoders'].items()},
            motors={name: dict(safety=asdict(ch['pipeline'].safety),
                previous=ch['pipeline'].previous_physical_target, filtered=ch['observer'].filtered_hz.tolist(),
                counts=ch['observer'].last_counts.tolist(),
                decoder=base.native({k: ch[k] for k in ('index', 'positive', 'negative', 'sign', 'decoder_mode', 'bound', 'populations')}))
                    for name, ch in self.channels.items()}))

    def state_boundary(self):
        super().state_boundary()
        index = self.session._state['physics_transition']
        if index == 0:
            if self.arm_id == 'A_NC' and not self.qualification:
                import mujoco
                mechanical.qualify(mujoco, getattr(self.physics.model, 'ptr', self.physics.model),
                    getattr(self.physics.data, 'ptr', self.physics.data), self.inventory,
                    self.intervention.original, self.protected_state, self.qualification)
            self.intervention.accept_qualification(self.qualification)
        mechanical.require(len(self.mechanical_samples) == index+1, 'mechanical sample coverage mismatch')
        self.intervention.boundary(index, self.protected_state)

    def mechanical_evidence(self):
        return dict(context=self.mechanical_context, samples=self.mechanical_samples,
                    event=None if self.intervention is None else self.intervention.event,
                    qualification=self.qualification)


def run_arm(arm_id, physical_protocol, table, stop_path, *, qualification=None, **kwargs):
    """Internal lifecycle adapter; preserve mechanical partials on driver failure.

    No campaign authorization, source guards, child processes or full evaluator
    here yet. Do not use as a scientific launcher before those are integrated.
    """
    from . import controlled_live_balance as driver
    mechanical.require(arm_id in mechanical.plan.ARM_IDS, 'declared assistance arm required')
    mechanical.require('trial_factory' not in kwargs, 'assistance Trial factory is fixed')
    trials = []
    def factory(condition):
        mechanical.require(not trials and condition == arm_id.split('_')[1], 'single exact Trial binding required')
        trial = Trial(arm_id, qualification)
        trials.append(trial)
        return trial
    result, display = driver.run_arm(arm_id.split('_')[1], physical_protocol, table, stop_path,
                                    trial_factory=factory, **kwargs)
    result.update(schema='assistance-arm-adapter-v1', arm_id=arm_id,
                  assistance=trials[0].mechanical_evidence(), full_scientific_audit_completed=False)
    return result, display


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',required=True,help='static source check only')
    parser.parse_args(argv)
    source_check()
    print('ASSISTANCE ADAPTER SOURCE CHECK VERIFIED; mechanical component only; '
          'campaign launcher/evaluator pending; native qualification and physics/CNS not run.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
