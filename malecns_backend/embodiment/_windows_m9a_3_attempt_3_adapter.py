"""Pinned Windows physics boundary for M9A-3. No neural imports."""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import io
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping

from . import m7d_corrected_spontaneous as m7d
from . import m8_contact_kinematics as contact
from . import m9a_3_attempt_3_calibration as m9a
from . import _windows_m7d_corrected_spontaneous_adapter as m7d_live


def _modules() -> tuple[Any, Any, dict[str, Any]]:
    np, flygym = (importlib.import_module(x) for x in ("numpy", "flygym"))
    versions = {x: importlib.metadata.version(x) for x in ("flygym", "mujoco")}
    if versions != {"flygym": "1.2.1", "mujoco": "3.2.7"}: raise RuntimeError(f"pinned versions required; found {versions}")
    versions["module_paths"] = {x: str(Path(importlib.import_module(x).__file__).resolve()) for x in ("numpy", "flygym", "mujoco")}
    return np, flygym, versions


def _body_identity(model: Any) -> dict[str, Any]:
    names = {i: contact.compiled_name(model, "body", i) for i in range(int(model.nbody))}
    matches = [i for i, name in names.items() if contact.namespace_component(name) == m9a.APPLICATION_BODY_SOURCE]
    if len(matches) != 1 or matches[0] == 0: raise RuntimeError("authoritative Thorax must resolve uniquely to a non-world body")
    i = matches[0]
    return {"body_id": i, "body_name": names[i], "source_body_name": m9a.APPLICATION_BODY_SOURCE,
            "resolution": "unique exact terminal slash-delimited component", "all_body_names": names}


def _runtime(flygym: Any) -> tuple[Any, Any, Any]:
    sim, physics, obs, _, _ = m7d_live._runtime(flygym, None)
    np = importlib.import_module("numpy"); commands = np.asarray(obs["joints"], dtype=float)
    if commands.ndim == 2: commands = commands[0]
    if commands.shape != (42,): raise RuntimeError("frozen baseline is not 42 joints")
    return sim, physics, commands.copy()


def _inspect(np: Any, physics: Any, identity: Mapping[str, Any], body_id: int) -> dict[str, Any]:
    qpos, qvel = np.asarray(physics.data.qpos), np.asarray(physics.data.qvel)
    quat = qpos[3:7].copy(); up = 1.0 - 2.0 * (quat[1]**2 + quat[2]**2)
    flags, feet = contact.sample(physics, identity); cvel = np.asarray(physics.data.cvel[body_id], dtype=float)
    return {"time_ms": float(physics.data.time * 1000), "root_position": qpos[:3].copy(),
        "orientation_wxyz": quat, "body_up_z": float(up), "linear_velocity": cvel[3:6].copy(),
        "angular_velocity": cvel[:3].copy(), "ground_contact": flags.copy(),
        "distal_tarsus_positions": feet.copy(),
        "finite": bool(all(np.isfinite(x).all() for x in (qpos, qvel, cvel, feet)))}


def _run_condition(np: Any, flygym: Any, magnitude: float, condition: str) -> tuple[dict[str, Any], dict[str, Any]]:
    sim, physics, commands = _runtime(flygym)
    try:
        body, identity = _body_identity(physics.model), contact.resolve(physics.model)
        if not identity["available"]: raise RuntimeError("authoritative contact identity unavailable")
        rows = []
        for step in range(m9a.STATES):
            state = _inspect(np, physics, identity, body["body_id"]); scheduled = step * m9a.DT_MS
            if not math.isclose(state["time_ms"], scheduled, abs_tol=1e-7): raise RuntimeError("clock/cadence mismatch")
            force = np.asarray(m9a.force_at(scheduled, magnitude, condition), dtype=float)
            state["applied_force"] = force.copy(); state["fixed_actuator_commands"] = commands.copy(); rows.append(state)
            if step == m9a.TRANSITIONS: break
            physics.data.xfrc_applied[:] = 0.0
            physics.data.xfrc_applied[body["body_id"], :3] = force
            physics.data.xfrc_applied[body["body_id"], 3:] = 0.0
            nz = np.flatnonzero(np.any(np.asarray(physics.data.xfrc_applied) != 0, axis=1))
            if (force.any() and nz.tolist() != [body["body_id"]]) or (not force.any() and nz.size): raise RuntimeError("force escaped body/window")
            sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})
        arrays = {k: np.asarray([r[k] for r in rows]) for k in rows[0]}
        provenance = {"condition": condition, "force_body": {k:v for k,v in body.items() if k != "all_body_names"},
            "contact_identity": identity, "actuator_commands_sha256": hashlib.sha256(commands.tobytes()).hexdigest()}
        return arrays, provenance
    finally: sim.close()


def _norm(np: Any, x: Any) -> Any: return np.linalg.norm(x.reshape((len(x), -1)), axis=1)


def _reduce_pair(np: Any, p: Mapping[str, Any], c: Mapping[str, Any], magnitude: float) -> dict[str, Any]:
    start_index, stop_index = _audit_pair_schedule(np, p, c, magnitude)
    t = p["time_ms"]
    indices = np.arange(m9a.STATES)
    pre = indices < start_index
    post = indices > start_index
    exact_fields = ("root_position", "orientation_wxyz", "body_up_z", "linear_velocity", "angular_velocity",
                    "ground_contact", "distal_tarsus_positions", "fixed_actuator_commands")
    if any(not np.array_equal(p[k][pre], c[k][pre]) for k in exact_fields): raise RuntimeError("P/C pre-force trajectories are not exactly equivalent")
    dp = p["root_position"] - c["root_position"]; dv = p["linear_velocity"] - c["linear_velocity"]
    dw = p["angular_velocity"] - c["angular_velocity"]
    dots = np.abs(np.sum(p["orientation_wxyz"] * c["orientation_wxyz"], axis=1))
    qangle = np.degrees(2*np.arccos(np.clip(dots, 0, 1)))
    upangle = np.degrees(np.arccos(np.clip(p["body_up_z"],-1,1))-np.arccos(np.clip(c["body_up_z"],-1,1)))
    feet = np.linalg.norm(p["distal_tarsus_positions"]-c["distal_tarsus_positions"], axis=2)
    contact_xor = np.logical_xor(p["ground_contact"], c["ground_contact"])
    different = np.zeros(len(t), dtype=bool)
    for k in exact_fields[:-1]:
        d = p[k] != c[k]; different |= d if d.ndim == 1 else np.any(d.reshape((len(t),-1)),axis=1)
    idx = np.flatnonzero(different); initial = p["root_position"][0]
    abs_disp = max(float(_norm(np,p["root_position"]-initial).max()), float(_norm(np,c["root_position"]-initial).max()))
    ptilt=np.degrees(np.arccos(np.clip(p["body_up_z"],-1,1))); ctilt=np.degrees(np.arccos(np.clip(c["body_up_z"],-1,1)))
    abs_speed=max(float(_norm(np,p["linear_velocity"]).max()),float(_norm(np,c["linear_velocity"]).max()))
    early=t<=750; catastrophic=bool(np.any(((p["root_position"][:,2] <= initial[2]*.5)|(c["root_position"][:,2] <= initial[2]*.5)
        |(p["body_up_z"]<=0)|(c["body_up_z"]<=0)|(_norm(np,p["root_position"]-initial)>1.5)|(_norm(np,c["root_position"]-initial)>1.5)
        |False) & early))
    continuous=max(float(_norm(np,dp)[post].max()),float(_norm(np,dv)[post].max()),float(qangle[post].max()),
                   float(np.abs(upangle[post]).max()),float(_norm(np,dw)[post].max()),float(feet[post].max()))
    return {"magnitude_native": magnitude, "pre_force_exact_equivalence": True,
        "first_physical_divergence_ms": None if not idx.size else float(t[idx[0]]),
        "max_continuous_divergence": continuous, "max_root_position_divergence_mm": float(_norm(np,dp).max()),
        "max_root_linear_velocity_divergence": float(_norm(np,dv).max()),
        "max_orientation_divergence_deg": float(qangle.max()), "max_body_up_tilt_divergence_deg": float(np.abs(upangle).max()),
        "max_angular_velocity_divergence": float(_norm(np,dw).max()), "contact_pattern_diverged": bool(contact_xor.any()),
        "first_contact_divergence_ms": None if not contact_xor.any() else float(t[np.flatnonzero(np.any(contact_xor,axis=1))[0]]),
        "max_distal_tarsus_divergence_mm": float(feet.max()), "per_leg_max_distal_tarsus_divergence_mm": feet.max(axis=0).tolist(),
        "finite_both": bool(p["finite"].all() and c["finite"].all()), "catastrophic_through_750ms": catastrophic,
        "max_absolute_root_displacement_mm": abs_disp, "max_absolute_tilt_deg": float(max(ptilt.max(),ctilt.max())),
        "baseline_characterization": {condition: {
            "max_absolute_root_linear_speed": float(_norm(np, data["linear_velocity"])[pre].max()),
            "max_absolute_root_displacement_mm": float(_norm(np, data["root_position"]-data["root_position"][0])[pre].max()),
            "max_tilt_deg": float(tilt[pre].max()),
            "fall": bool(np.any(data["root_position"][pre,2] <= data["root_position"][0,2]*.5)),
            "rollover": bool(np.any(data["body_up_z"][pre] <= 0)),
            "contact_state": data["ground_contact"][pre].tolist(),
        } for condition, data, tilt in (("P",p,ptilt),("C",c,ctilt))},
        "max_absolute_root_linear_speed_descriptive_only": abs_speed,
        "post_force_observation_ms": m9a.OBSERVE_MS-m9a.STOP_MS}


def _audit_pair_schedule(np: Any, p: Mapping[str, Any], c: Mapping[str, Any], magnitude: float) -> tuple[int, int]:
    """Audit recorded force against execution's integer-index schedule."""
    if m9a.STATES != m9a.TRANSITIONS + 1:
        raise RuntimeError("state/transition count mismatch")
    if len(p["time_ms"]) != m9a.STATES or len(c["time_ms"]) != m9a.STATES:
        raise RuntimeError("recording does not contain the frozen state count")
    if not np.array_equal(p["time_ms"], c["time_ms"]):
        raise RuntimeError("P/C timestamps differ")
    expected_times = np.arange(m9a.STATES, dtype=float) * m9a.DT_MS
    if not np.all(np.isclose(p["time_ms"], expected_times, rtol=0.0, atol=1e-7)):
        raise RuntimeError("clock/cadence mismatch")
    start_quotient, stop_quotient = m9a.START_MS / m9a.DT_MS, m9a.STOP_MS / m9a.DT_MS
    if not start_quotient.is_integer() or not stop_quotient.is_integer():
        raise RuntimeError("force boundaries are not integral transition indices")
    start_index, stop_index = int(start_quotient), int(stop_quotient)
    if (start_index, stop_index) != (5000, 5200):
        raise RuntimeError("frozen force boundary mismatch")
    expected_p = np.asarray([
        m9a.force_at(step * m9a.DT_MS, magnitude, "P") for step in range(m9a.STATES)
    ])
    expected_c = np.asarray([
        m9a.force_at(step * m9a.DT_MS, magnitude, "C") for step in range(m9a.STATES)
    ])
    if not np.array_equal(p["applied_force"], expected_p) or not np.array_equal(c["applied_force"], expected_c):
        raise RuntimeError("recorded P/C force schedule mismatch")
    return start_index, stop_index


def windows_preflight() -> dict[str, Any]:
    m9a.validate_protocol(m9a.protocol()); m7d.verify_b4(); m7d.verify_m7()
    np, flygym, env = _modules(); snapshots=[]
    for condition in ("P","C"):
        sim, physics, commands = _runtime(flygym)
        try:
            body, identity = _body_identity(physics.model), contact.resolve(physics.model)
            if not identity["available"] or tuple(physics.data.qpos[:3]) != m7d.SPAWN_POS: raise RuntimeError("initialization/identity mismatch")
            snapshots.append((np.asarray(physics.data.qpos).copy(),np.asarray(physics.data.qvel).copy(),commands.copy()))
        finally: sim.close()
    if any(not np.array_equal(a,b) for a,b in zip(snapshots[0],snapshots[1])): raise RuntimeError("fresh P/C initialization differs")
    allowed = {m9a.PREREGISTRATION_PATH.resolve()}
    existing = {p.resolve() for p in m9a.OUTPUT_DIR.iterdir()} if m9a.OUTPUT_DIR.exists() else set()
    if existing - allowed: raise FileExistsError("Attempt 3 namespace contains prior scientific execution evidence")
    return {"schema":m9a.SCHEMA,"status":"PREFLIGHT_PASS","experiment_namespace":"M9A-3-Attempt-3",
            "output_namespace_scientific_evidence_absent":True,"protocol":m9a.protocol(),"historical_provenance_verified":True,
            "environment":env,"force_body":{k:v for k,v in body.items() if k!="all_body_names"},
            "contact_resolution":identity["method"],"p_c_initialization_exact":True,"physics_transitions":0,"neural_transitions":0,"male_cns_constructed":False}


def _exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644),"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())


def run_windows() -> dict[str, Any]:
    allowed = {m9a.PREREGISTRATION_PATH.resolve()}
    existing = {p.resolve() for p in m9a.OUTPUT_DIR.iterdir()} if m9a.OUTPUT_DIR.exists() else set()
    if existing - allowed: raise FileExistsError("M9A-3 Attempt 2 evidence namespace already contains execution output")
    preflight=windows_preflight(); np,flygym,env=_modules(); results=[]; raw=[]
    for magnitude in m9a.CANDIDATE_FORCE_NATIVE:
        pair={}; provenance={}
        for condition in ("P","C"):
            pair[condition],provenance[condition]=_run_condition(np,flygym,magnitude,condition)
            path=m9a.OUTPUT_DIR/f"candidate_{magnitude:.6f}_{condition}_raw.npz"; buf=io.BytesIO(); np.savez_compressed(buf,**pair[condition]); _exclusive(path,buf.getvalue())
            raw.append({"path":str(path.resolve()),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"byte_size":path.stat().st_size})
        row=_reduce_pair(np,pair["P"],pair["C"],magnitude); row["provenance"]=provenance; results.append(row)
    selected=m9a.choose_candidate(results)
    report={"schema":m9a.SCHEMA,"status":"COMPLETE","protocol":m9a.protocol(),"preflight":preflight,"environment":env,
        "candidate_results":results,"selected_force_magnitude_native":selected,"selection_used_neural_behavior":False,
        "physics_only":True,"neural_transitions":0,"male_cns_constructed":False,
        "source_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()}
    _exclusive(m9a.REPORT_PATH,(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n").encode())
    manifest={"schema":m9a.SCHEMA,"status":"COMPLETE","report":{"sha256":hashlib.sha256(m9a.REPORT_PATH.read_bytes()).hexdigest(),"byte_size":m9a.REPORT_PATH.stat().st_size},"raw":raw}
    _exclusive(m9a.MANIFEST_PATH,(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode()); return report


__all__ = ["windows_preflight", "run_windows"]
