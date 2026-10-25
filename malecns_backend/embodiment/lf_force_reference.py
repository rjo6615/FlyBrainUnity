"""Four local tendon-force hypotheses; isolated reference fixture only, no decoder."""
import json

import numpy as np

from . import remaining_leg_admission_audit as audit
from . import lf_anatomical_crosswalk as crosswalk
from . import lf_proximal_binding_review as binding

ROOT = audit.ROOT
FIXTURE = 'docs/fixtures/lf-force-reference-v1.xml'
BASIS = ('joint_LFCoxa_yaw', 'joint_LFCoxa', 'joint_LFCoxa_roll')
BODY_NAMES = ('fixture_yaw_link', 'fixture_pitch_link', 'fixture_roll_link')
TENDONS = ('LFC_pleural_remotor_and_abductor_tendon', 'LFC_sternal_adductor_tendon',
           'LFC_sternal_anterior_rotator_tendon', 'LFC_sternal_posterior_rotator_tendon')


def load_reference():
    _, now = crosswalk.verify(ROOT/(crosswalk.DIRECTORY+'crosswalk.json'))
    read = lambda p: json.loads((ROOT/p).read_text(encoding='utf-8'))
    reg = read(audit.PATHS['registration'])
    candidates = read(audit.PATHS['candidates'])
    identities = read(crosswalk.UPSTREAM)['lf_reference']['candidate_identities']
    all_rows = binding.reference_rows(reg, candidates['candidate_population_inventory'], identities)
    selected = [r for r in all_rows if len(r['tendon_hypotheses']) == 1]
    if tuple(r['tendon_hypotheses'][0]['tendon'] for r in selected) != TENDONS:
        raise ValueError('exact four single-class hypotheses required; promotor remains excluded')
    mechanics = {r['flymimic_tendon']: r for r in reg['muscle_mechanics']}
    return dict(basis=list(BASIS), tendons=list(TENDONS), hypotheses=selected,
        R_G=np.asarray([mechanics[t]['flygym_covector']['values'] for t in TENDONS]).T.tolist(),
        R_M=np.asarray([mechanics[t]['flymimic_covector']['values'] for t in TENDONS]).T.tolist(),
        J=reg['local_differential_registration']['J_GM'],
        original_raw_freezes_satisfied=now['current_original_raw_freezes_satisfied'])


class ReferenceForceAdapter:
    """Explicit known tensions at one reference pose; no neuron activation mapping."""
    def __init__(self, model, data, reference):
        from .six_tibia_physics_diagnostic import resolve_dof
        self.model, self.data = model, data
        if reference['basis'] != list(BASIS) or reference['tendons'] != list(TENDONS):
            raise ValueError('reference basis/tendon order mismatch')
        self.coefficients = np.array(reference['R_G'], dtype=float, copy=True)
        if self.coefficients.shape != (3, 4) or not np.isfinite(self.coefficients).all():
            raise ValueError('finite 3x4 reference coefficients required')
        self.reference_qpos = np.zeros(11)
        self.reference_qpos[3] = 1.
        self.metadata = []
        for name, body in zip(BASIS, BODY_NAMES):
            jid = model.joint(name).id
            row = resolve_dof(model, int(model.jnt_dofadr[jid]))
            if (not row['resolved'] or row['joint_name'] != name or row['body_name'] != body
                    or row['joint_type'] != 'hinge' or row['actuators']
                    or row['dof_address_range'][1]-row['dof_address_range'][0] != 1
                    or row['qpos_address_range'][1]-row['qpos_address_range'][0] != 1):
                raise ValueError('exact compiled hinge/body/address ownership required')
            self.metadata.append(row)
        self.dofs = [r['dof_index'] for r in self.metadata]
        self.jids = [r['joint_id'] for r in self.metadata]
        if self.dofs != [7, 8, 9] or [r['qpos_address_range'][0] for r in self.metadata] != [8, 9, 10]:
            raise ValueError('reference fixture address contract mismatch')
        self.owned = None
        self._guard()

    def _guard(self):
        m, d = self.model, self.data
        if (m.nu != 0 or m.nq != 11 or m.nv != 10 or m.ngeom != 0 or m.ntendon != 0
                or m.neq != 0 or m.nbody != 6 or np.any(m.opt.gravity)
                or np.any(m.dof_damping) or np.any(m.dof_frictionloss)
                or np.any(m.jnt_stiffness) or np.any(m.dof_armature)):
            raise ValueError('isolated zero-actuator/passive/contact fixture required')
        if (not np.array_equal(m.qpos0, self.reference_qpos)
                or not np.array_equal(d.qpos, self.reference_qpos)
                or np.any(d.qvel) or d.time != 0 or d.ncon != 0
                or not np.array_equal(m.jnt_axis[self.jids], np.eye(3))
                or not np.allclose(d.xaxis[self.jids], np.eye(3), atol=1e-12, rtol=0)):
            raise ValueError('only the exact zero-velocity reference pose/time is supported')
        expected = np.zeros(m.nv) if self.owned is None else self.owned
        if not np.array_equal(d.qfrc_applied, expected) or np.any(d.xfrc_applied):
            raise ValueError('foreign or modified applied force buffer')

    def project(self, tensions):
        values = np.asarray(tensions, dtype=float)
        if values.shape != (4,) or not np.isfinite(values).all() or np.any(values < 0):
            raise ValueError('four finite nonnegative explicit tensions required')
        result = self.coefficients @ values
        if not np.isfinite(result).all():
            raise ValueError('nonfinite projected torque')
        return result

    def apply(self, tensions):
        self._guard()
        if self.owned is not None:
            raise ValueError('clear owned force before another application')
        projected = self.project(tensions)
        expected = np.zeros(self.model.nv)
        expected[self.dofs] = projected
        self.data.qfrc_applied[self.dofs] = projected
        self.owned = expected
        return projected.copy()

    def clear(self):
        self._guard()
        if self.owned is None:
            raise ValueError('no owned application to clear')
        self.data.qfrc_applied[self.dofs] = 0.
        self.owned = None
