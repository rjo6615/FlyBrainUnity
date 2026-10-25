"""Experimental source-law integration. No body integration or production hook."""
import numpy as np
from scipy.integrate import solve_ivp

SETTINGS = dict(method='Radau', rtol=1e-9, atol=1e-12)


def integrate_interval(native, initial, effective_control, dynprm, duration, sample_offsets):
    """Own only a copied activation vector on one constant-control interval.

    Adaptive Radau advances the existing native muscle ODE; there is no state
    clamp, derivative replacement, parameter fitting or native mj_step. The
    caller owns control boundaries, simulation time and force refresh.
    """
    initial = np.array(initial, dtype=float, copy=True)
    control = np.asarray(effective_control, dtype=float)
    params = np.asarray(dynprm, dtype=float)
    offsets = np.asarray(sample_offsets, dtype=float)
    if (initial.ndim != 1 or not initial.size or control.shape != initial.shape
            or params.ndim != 2 or params.shape[0] != initial.size or params.shape[1] < 3
            or not np.isfinite(duration) or duration <= 0 or offsets.ndim != 1
            or not offsets.size or offsets[0] < 0 or offsets[-1] > duration
            or np.any(np.diff(offsets) <= 0)
            or not all(np.isfinite(x).all() for x in (initial, control, params, offsets))):
        raise ValueError('finite, dimensionally consistent constant-control interval required')

    def rhs(t, activation):
        return np.array([native.mju_muscleDynamics(float(c), float(a), p[:3])
                         for c, a, p in zip(control, activation, params)])

    solved = solve_ivp(rhs, (0., duration), initial, **SETTINGS,
                       max_step=duration, dense_output=True)
    if not solved.success or solved.t[-1] != duration or not np.isfinite(solved.y).all():
        raise ValueError('activation solver failed: '+solved.message)
    samples = solved.sol(offsets).T
    if not np.isfinite(samples).all():
        raise ValueError('nonfinite dense activation samples')
    return dict(after=solved.y[:, -1].tolist(), sample_offsets=offsets.tolist(),
                samples=samples.tolist(), derivative_before=rhs(0., initial).tolist(),
                derivative_after=rhs(duration, solved.y[:, -1]).tolist(),
                solver=dict(success=True, status=int(solved.status), message=solved.message,
                            nfev=int(solved.nfev), njev=int(solved.njev), nlu=int(solved.nlu),
                            times=solved.t.tolist(), activations=solved.y.T.tolist()))


def advance_fixed_fixture(native, model, data, raw_control, duration, sample_offsets):
    """Commit one activation/time interval, restricted to the zero-DOF fixture.

    Native activation and actuator IDs must have an exact one-to-one mapping.
    This restriction prevents accidental use as a moving-body split integrator.
    There is deliberately no call to mj_step: it would integrate activation twice.
    """
    if (model.nq or model.nv or model.ngeom or model.nu != 4 or model.na != 4
            or model.ntendon != 4 or np.any(model.actuator_actearly)
            or np.any(model.actuator_actlimited) or not np.all(model.actuator_ctrllimited)
            or not np.all(model.actuator_dyntype == int(native.mjtDyn.mjDYN_MUSCLE))
            or not np.array_equal(model.actuator_actadr, np.arange(4))
            or not np.all(model.actuator_actnum == 1)):
        raise ValueError('only the four-state, unclamped zero-DOF source fixture is supported')
    if not np.isfinite(raw_control):
        raise ValueError('finite raw control required')
    before, start = data.act.copy(), float(data.time)
    control = np.clip(np.full(4, raw_control), *model.actuator_ctrlrange.T)
    result = integrate_interval(native, before, control, model.actuator_dynprm, duration, sample_offsets)
    data.ctrl[:] = raw_control
    native.mj_forward(model, data)
    result.update(before=before.tolist(), raw_control=raw_control, effective_control=control.tolist(),
                  time_before=start, force_before=data.actuator_force.tolist(),
                  native_derivative_before=data.act_dot.tolist())
    data.act[:] = result['after']
    data.time = start+duration
    native.mj_forward(model, data)
    result.update(time=float(data.time), force_after=data.actuator_force.tolist(),
                  native_derivative_after=data.act_dot.tolist(), length=data.actuator_length.tolist(),
                  qpos=data.qpos.tolist(), qvel=data.qvel.tolist(),
                  external_generalized=data.qfrc_applied.tolist(), external_body=data.xfrc_applied.tolist())
    return result
