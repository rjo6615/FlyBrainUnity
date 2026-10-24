"""Prospective descriptive recovery bands; never a biological-balance classifier."""
import numpy as np

from ..embodiment.m10c_m10b_analysis import quaternion_shortest_arc_deg

BANDS = dict(orientation_deg=5., height_mm=.05, linear_speed_mm_s=1., angular_speed_rad_s=1.,
             minimum_up_z=.5, minimum_height_fraction=.5, minimum_ground_contacts=3, dwell_steps=1000)
RESOLUTION = dict(orientation_deg=.25, position_mm=.005)


def up_z(q):
    q = np.asarray(q, dtype=float)
    norm = np.linalg.norm(q, axis=1)
    if not np.isfinite(q).all() or np.any(norm <= 0):
        raise ValueError('finite nonzero root quaternions required')
    q = q / norm[:, None]
    return 1. - 2. * (q[:, 1]**2 + q[:, 2]**2)


def sustained_entry(mask, start, dwell_steps):
    """A dwell of N transitions needs N+1 consecutive stored states."""
    mask = np.asarray(mask, dtype=bool)
    width = int(dwell_steps) + 1
    values = mask[int(start):].astype(int)
    if len(values) < width:
        return None
    cumulative = np.r_[0, np.cumsum(values)]
    indices = np.flatnonzero(cumulative[width:] - cumulative[:-width] == width)
    return None if not len(indices) else int(start) + int(indices[0])


def angular_velocity_world(quaternion, local_velocity):
    """MuJoCo free-joint rotational qvel is body-local; compare in world axes."""
    q=np.asarray(quaternion,dtype=float)
    v=np.asarray(local_velocity,dtype=float)
    norm=np.linalg.norm(q,axis=1)
    if q.shape!=(len(v),4) or v.shape!=(len(q),3) or not np.isfinite(q).all() or not np.isfinite(v).all() or np.any(norm<=0):
        raise ValueError('finite quaternion/angular-velocity arrays required')
    q=q/norm[:,None]
    cross=np.cross(q[:,1:],v)
    return v+2.*(q[:,0,None]*cross+np.cross(q[:,1:],cross))


def trace(arm, supports):
    qpos = np.asarray([s['qpos'] for s in arm['samples']], dtype=float)
    qvel = np.asarray([s['qvel'] for s in arm['samples']], dtype=float)
    if qpos.ndim != 2 or qpos.shape[1] < 7 or qvel.ndim != 2 or qvel.shape[1] < 6:
        raise ValueError('native root pose and free-joint velocity required')
    if not np.isfinite(qpos).all() or not np.isfinite(qvel).all():
        raise ValueError('nonfinite physical trace')
    velocity=np.column_stack((qvel[:,:3],angular_velocity_world(qpos[:,3:7],qvel[:,3:6])))
    return dict(position=qpos[:, :3], quaternion=qpos[:, 3:7], velocity=velocity,
                up_z=up_z(qpos[:, 3:7]), supports=np.asarray(supports, dtype=int))


def response(pushed, control, *, dt=.0001, start=5000, stop=5200, bands=BANDS):
    if len(pushed['position']) != len(control['position']):
        raise ValueError('aligned complete push/control traces required')
    orientation = quaternion_shortest_arc_deg(pushed['quaternion'], control['quaternion'])
    position = np.linalg.norm(pushed['position'] - control['position'], axis=1)
    height = np.abs(pushed['position'][:, 2] - control['position'][:, 2])
    linear = np.linalg.norm(pushed['velocity'][:, :3] - control['velocity'][:, :3], axis=1)
    angular = np.linalg.norm(pushed['velocity'][:, 3:] - control['velocity'][:, 3:], axis=1)
    relative = ((orientation <= bands['orientation_deg']) & (height <= bands['height_mm'])
                & (linear <= bands['linear_speed_mm_s']) & (angular <= bands['angular_speed_rad_s']))
    absolute = ((pushed['up_z'] > bands['minimum_up_z'])
                & (pushed['position'][:, 2] > pushed['position'][0, 2]*bands['minimum_height_fraction'])
                & (pushed['supports'] >= bands['minimum_ground_contacts']))
    first_post = stop + 1
    exited = bool(np.any(~relative[start:]))
    entry = sustained_entry(relative & absolute, first_post, bands['dwell_steps']) if exited else None
    baseline = slice(max(0, start - bands['dwell_steps']), start + 1)
    baseline_ok = bool(np.all(control['up_z'][baseline] > bands['minimum_up_z'])
        and np.all(control['position'][baseline, 2] > control['position'][0, 2]*bands['minimum_height_fraction'])
        and np.mean(control['supports'][baseline]) >= bands['minimum_ground_contacts'])
    post = slice(first_post, None)
    observed = slice(start, None)
    # Trapezoidal integration includes the entire fixed cleared-force window.
    integral = float(np.sum((orientation[first_post:-1] + orientation[first_post+1:]) * .5) * dt)
    return dict(baseline_qualified=baseline_ok,
        resolved_perturbation=bool(np.max(orientation[observed]) > RESOLUTION['orientation_deg']
                                  or np.max(position[observed]) > RESOLUTION['position_mm']),
        relative_band_exited=exited,
        recovery_status='NO_BAND_EXIT' if not exited else 'NOT_RECOVERED_IN_WINDOW' if entry is None else 'SUSTAINED_BAND_RETURN',
        recovery_entry_ms=None if entry is None else entry*dt*1000,
        recovery_confirmation_ms=None if entry is None else (entry + bands['dwell_steps'])*dt*1000,
        post_peak_orientation_deg=float(np.max(orientation[post])),
        post_mean_orientation_deg=float(np.mean(orientation[post])), post_orientation_integral_deg_s=integral,
        post_peak_position_deviation_mm=float(np.max(position[post])),
        post_peak_height_error_mm=float(np.max(height[post])),
        post_peak_linear_speed_error_mm_s=float(np.max(linear[post])),
        post_peak_angular_speed_error_rad_s=float(np.max(angular[post])),
        post_below_three_support_samples=int(np.count_nonzero(pushed['supports'][post] < 3)),
        post_rollover_samples=int(np.count_nonzero(pushed['up_z'][post] <= 0)),
        post_low_height_samples=int(np.count_nonzero(pushed['position'][post, 2] <= pushed['position'][0, 2]*.5)),
        minimum_support_contacts=int(np.min(pushed['supports'][post])),
        post_absolute_tilt_peak_deg=float(np.max(np.degrees(np.arccos(np.clip(pushed['up_z'][post], -1., 1.))))))


def contrast(on, off):
    peak = on['post_peak_orientation_deg'] - off['post_peak_orientation_deg']
    mean = on['post_mean_orientation_deg'] - off['post_mean_orientation_deg']
    r = RESOLUTION['orientation_deg']
    label = ('ATTENUATED_ORIENTATION_RESPONSE_WITH_TACTILE' if peak < -r and mean < -r else
             'AMPLIFIED_ORIENTATION_RESPONSE_WITH_TACTILE' if peak > r and mean > r else 'MIXED_OR_UNRESOLVED')
    limits = []
    for name, value in (('ON', on), ('OFF', off)):
        if not value['baseline_qualified']: limits.append(f'{name}_BASELINE_NOT_QUALIFIED')
        if not value['resolved_perturbation']: limits.append(f'{name}_PERTURBATION_BELOW_RESOLUTION')
        if not value['relative_band_exited']: limits.append(f'{name}_NO_RECOVERY_BAND_EXIT')
    return dict(orientation_label=label, orientation_peak_on_minus_off_deg=peak,
                orientation_mean_on_minus_off_deg=mean,
                height_peak_on_minus_off_mm=on['post_peak_height_error_mm']-off['post_peak_height_error_mm'],
                interpretation_limits=limits, active_balance_proven=False)
