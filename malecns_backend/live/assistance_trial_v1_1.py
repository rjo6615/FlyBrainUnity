"""V1.1 assistance Trial: the executed V1 adapter with the corrected live-data guard.

Original encoders, neural gate before safety, RNG, decoder, pulse and kernel
remain owned by the frozen balance Trial. Only the mechanical capture/
qualification/boundary guard uses assistance_native_v1_1. Not a launcher.
"""
from . import assistance_native_v1_1 as guard
from . import assistance_trial as v1

mechanical, base = v1.mechanical, v1.base
SCHEMA = 'assistance-arm-adapter-v1.1'


class Trial(v1.Trial):
    def bind(self, sim, physics, obs):
        base.Trial.bind(self, sim, physics, obs)
        original = mechanical.model_record(physics.model, physics.data)
        mechanical.validate_binding(self.inventory, original)
        self.intervention = guard.Intervention(self.arm_id, physics.model, physics.data, self.inventory, original)
        self.mechanical_context = dict(schema=mechanical.SCHEMA, live_guard=guard.GUARD, arm_id=self.arm_id,
            inventory=self.inventory, original=original, neutral=self.intervention.neutral)
        self._capture_mechanical(physics)  # initial base capture precedes intervention binding

    def _capture_mechanical(self, physics):
        import mujoco
        before = guard.data_fields(physics.data)
        sample = dict(state_index=len(self.mechanical_samples), time_s=float(physics.data.time),
            model_sha256=mechanical.digest(mechanical.components(physics.model, physics.data)),
            **mechanical.force_record(mujoco, getattr(physics.model, 'ptr', physics.model),
                                      getattr(physics.data, 'ptr', physics.data)))
        guard.require_unchanged(before, physics.data, 'mechanical capture mutated native data')
        self.mechanical_samples.append(sample)

    def state_boundary(self):
        base.Trial.state_boundary(self)
        index = self.session._state['physics_transition']
        if index == 0:
            if self.arm_id == 'A_NC' and not self.qualification:
                import mujoco
                guard.qualify(mujoco, getattr(self.physics.model, 'ptr', self.physics.model),
                    getattr(self.physics.data, 'ptr', self.physics.data), self.inventory,
                    self.intervention.original, self.protected_state, self.qualification)
            self.intervention.accept_qualification(self.qualification)
        mechanical.require(len(self.mechanical_samples) == index+1, 'mechanical sample coverage mismatch')
        self.intervention.boundary(index, self.protected_state)


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
    result.update(schema=SCHEMA, arm_id=arm_id, live_guard=guard.GUARD,
                  assistance=trials[0].mechanical_evidence() if trials else None,
                  full_scientific_audit_completed=False)
    return result, display
