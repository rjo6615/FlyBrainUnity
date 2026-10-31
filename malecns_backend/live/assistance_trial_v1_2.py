"""V1.2 assistance Trial: V1.1 guard plus the exact snapshot model-phase check.

Original encoders, gate-before-safety, RNG, decoder, pulse and kernel remain
owned by the frozen balance Trial; qualification is the V1.1 one. Only the
per-state model identity uses exact byte comparison instead of re-hashing.
"""
from . import assistance_native_v1_1 as guard
from . import assistance_native_v1_2 as phases
from . import assistance_trial_v1_1 as v11

mechanical, base = v11.mechanical, v11.base
SCHEMA = 'assistance-arm-adapter-v1.2'


class Trial(v11.Trial):
    def bind(self, sim, physics, obs):
        base.Trial.bind(self, sim, physics, obs)
        original = mechanical.model_record(physics.model, physics.data)
        mechanical.validate_binding(self.inventory, original)
        self.intervention = phases.Intervention(self.arm_id, physics.model, physics.data, self.inventory, original)
        self.mechanical_context = dict(schema=mechanical.SCHEMA, live_guard=guard.GUARD,
            model_phase_check=phases.CHECK, arm_id=self.arm_id, inventory=self.inventory,
            original=original, neutral=self.intervention.neutral)
        self._capture_mechanical(physics)  # initial base capture precedes intervention binding

    def _capture_mechanical(self, physics):
        import mujoco
        before = guard.data_fields(physics.data)
        index = len(self.mechanical_samples)
        sample = dict(state_index=index, time_s=float(physics.data.time),
            model_sha256=self.intervention.phases.phase_sha(physics.model,
                                                            mechanical.plan.expected_model_phase(self.arm_id, index)),
            **mechanical.force_record(mujoco, getattr(physics.model, 'ptr', physics.model),
                                      getattr(physics.data, 'ptr', physics.data)))
        guard.require_unchanged(before, physics.data, 'mechanical capture mutated native data')
        self.mechanical_samples.append(sample)


def run_arm(arm_id, physical_protocol, table, stop_path, *, qualification=None, **kwargs):
    """Internal lifecycle adapter; preserve mechanical partials on driver failure."""
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
    result.update(schema=SCHEMA, arm_id=arm_id, live_guard=guard.GUARD, model_phase_check=phases.CHECK,
                  assistance=trials[0].mechanical_evidence() if trials else None,
                  full_scientific_audit_completed=False)
    return result, display
