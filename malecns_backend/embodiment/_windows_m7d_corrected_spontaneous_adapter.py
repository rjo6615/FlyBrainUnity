"""Windows execution boundary for M7D; importing it never constructs a runtime."""
from __future__ import annotations

import importlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import m7d_corrected_spontaneous as m7d
from . import m7c_b2_pose_geometry_audit as b2
from . import m7c_b4_stability as b4
from . import integrated_whole_leg_readiness as m6c
from . import _windows_m7_spontaneous_locomotion_adapter as old


def gate_contributions(values: Mapping[str, float], condition: str,
                       admitted: Sequence[str]) -> dict[str, float]:
    if condition not in m7d.CONDITIONS or tuple(values) != tuple(admitted):
        raise RuntimeError("M7D contribution inventory or condition mismatch")
    return {name: (float(values[name]) if condition == m7d.CONDITIONS[0] else 0.0) for name in admitted}


def _runtime(flygym: Any, _interfaces: Any):
    """Reproduce B4's exact tripod/spawn/surface construction."""
    np = importlib.import_module("numpy")
    surface = b4._surface()
    sim = b4._make_sim(flygym, surface)
    reset = sim.reset(); obs = reset[0] if isinstance(reset, tuple) else reset
    physics = b2._physics(sim)
    forward = getattr(physics, "forward", None)
    if forward: forward()
    refresh = getattr(sim, "get_observation", None)
    if refresh: obs = refresh()
    initial = np.asarray(obs["joints"]); initial = initial[0] if initial.ndim == 2 else initial
    expected = json.loads(b4.B3_PATH.read_text(encoding="utf-8"))["zero_step_reconstruction"]["controlled_joint_positions"]
    if (initial.shape != (42,) or not np.array_equal(initial, expected) or
            tuple(physics.data.qpos[:3]) != m7d.SPAWN_POS or
            not b4._calibration_unchanged(sim, np, importlib.import_module("mujoco"), surface)):
        sim.close(); raise RuntimeError("exact B4 corrected initialization not reproduced")
    return sim, physics, obs, None, None


def _protocol() -> tuple[Mapping[str, Any], Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]]]:
    value = m7d.protocol(); m7d.validate_protocol(value); m7d.verify_b4(); m7d.verify_m7()
    # This verifies the current runtime's canonical M6C evidence locks and
    # rebuilds the admission table rather than copying it into M7D.
    live = old.build_live_protocol(); records, table = old._inventory(live)
    if tuple(live["admitted_motor_interfaces"]) != m7d.ADMITTED_MOTOR:
        raise RuntimeError("frozen M6C/M7 interface mismatch")
    return live, records, table


def _invoke(runner: Any, protocol: Mapping[str, Any], records: Any, table: Any,
            condition: str, number: int, initialize_only: bool) -> Mapping[str, Any]:
    return runner(protocol=protocol, condition=condition, condition_number=number,
        progress=lambda n, c, f, s, cw, tw, eta: f"[{n}/2] {c} {f:.0%} step {s}/5000",
        cached_admission_assertion=m6c.assert_physical_admission, cached_records=records,
        cached_table=table, initialize_only=initialize_only, duration_ms=m7d.DURATION_MS,
        condition_names=m7d.CONDITIONS, contribution_gate=gate_contributions,
        compact_telemetry=True, runtime_factory=_runtime, proprioception_only=True,
        fixed_initial_baseline=True)


def _environment() -> dict[str, str]:
    flygym = importlib.metadata.version("flygym"); mujoco = importlib.metadata.version("mujoco")
    if (flygym, mujoco) != ("1.2.1", "3.2.7"):
        raise RuntimeError(f"requires FlyGym 1.2.1 / MuJoCo 3.2.7, found {flygym} / {mujoco}")
    return {"flygym": flygym, "mujoco": mujoco}


def windows_preflight(runner: Any = old._runner) -> dict[str, Any]:
    if not m7d.output_available(): raise FileExistsError("canonical M7D output already exists")
    provenance = {"b4": m7d.verify_b4(), "m7": m7d.verify_m7()}
    environment = _environment(); protocol, records, table = _protocol()
    states = [_invoke(runner, protocol, records, table, c, i, True) for i, c in enumerate(m7d.CONDITIONS, 1)]
    if any(x["physics_steps"] or x["neural_steps"] for x in states):
        raise RuntimeError("M7D preflight crossed a transition boundary")
    snapshots = [x["pre_intervention_state"] for x in states]
    if not m6c.pre_intervention_equivalent(*snapshots): raise RuntimeError("pre-intervention equivalence failure")
    audits = [x["initial_physical_state_audit"] for x in states]
    if audits[0] != audits[1] or audits[0]["body_position"] != list(m7d.SPAWN_POS):
        raise RuntimeError("matched corrected initialization mismatch")
    schemas = [x["telemetry_schema"] for x in states]
    if schemas[0] != schemas[1] or any(x.get("telemetry_object_dtype") or not x.get("telemetry_npz_roundtrip") for x in states):
        raise RuntimeError("telemetry schema validation failure")
    return {"schema": m7d.SCHEMA, "status": "PREFLIGHT_PASS", "provenance": provenance,
        "environment": environment, "physics_transitions": 0, "neural_transitions": 0,
        "strict_pre_intervention_equivalence": True, "fresh_runtime_count": 2,
        "hidden_assistance_absent": True, "telemetry_schema": schemas[0]}


def _first(mask: Any, times: Any) -> float | None:
    np = importlib.import_module("numpy"); indices = np.flatnonzero(mask)
    return None if not indices.size else float(times[int(indices[0])])


def _reduce(results: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    np = importlib.import_module("numpy"); a, b = (results[c]["raw_arrays"] for c in m7d.CONDITIONS)
    pt, nt = a["physics_time_ms"], a["neural_time_ms"]
    joint = np.any(a["physics_joint_position"] != b["physics_joint_position"], axis=1)
    whole = np.any(a["physics_qpos"] != b["physics_qpos"], axis=1) | np.any(a["physics_qvel"] != b["physics_qvel"], axis=1)
    sensory = np.any(a["neural_sensory_encoded"] != b["neural_sensory_encoded"], axis=1)
    cns = a["neural_aggregate_spikes"] != b["neural_aggregate_spikes"]
    action = np.any(a["physics_action"] != b["physics_action"], axis=1)
    admitted = np.any(a["neural_admitted_contributions"] != b["neural_admitted_contributions"], axis=1)
    observer = np.any(a["neural_observer_outputs"] != b["neural_observer_outputs"], axis=1)
    decoder = np.any(a["neural_decoder_outputs"] != b["neural_decoder_outputs"], axis=1)
    motor_activity = np.any(a["neural_observer_outputs"] != 0, axis=1)
    milestones = {"D0_pre_intervention_equivalent": True, "D1_first_mapped_motor_activity_ms": _first(motor_activity, nt),
        "D2_first_observer_divergence_ms": _first(observer, nt), "D3_first_decoder_or_admitted_divergence_ms": _first(decoder | admitted, nt),
        "D4_first_action_divergence_ms": _first(action, pt), "D5_first_admitted_joint_divergence_ms": _first(joint, pt),
        "D6_first_whole_body_divergence_ms": _first(whole, pt), "D7_first_tibial_sensory_divergence_ms": _first(sensory, nt),
        "D8_first_delivered_sensory_drive_divergence_ms": _first(a["neural_delivered_drive_count"] != b["neural_delivered_drive_count"], nt),
        "D9_first_downstream_cns_divergence_ms": _first(cns & (nt >= (_first(sensory, nt) or float("inf"))), nt),
        "D10_first_later_motor_divergence_ms": _first(observer & (nt >= (_first(sensory, nt) or float("inf"))), nt)}
    per = {}
    for condition, arrays in ((m7d.CONDITIONS[0], a), (m7d.CONDITIONS[1], b)):
        xyz, quat = arrays["physics_body_position"], arrays["physics_body_orientation"]
        up = 1 - 2*(quat[:, 1]**2 + quat[:, 2]**2); fall = xyz[:, 2] <= xyz[0, 2] * .5; roll = up <= 0
        ft, rt = _first(fall, pt), _first(roll, pt)
        per[condition] = {"first_fall_time_ms": ft, "first_rollover_time_ms": rt,
            "minimum_body_height": float(xyz[:, 2].min()), "minimum_body_up_z": float(up.min()),
            "net_body_displacement": (xyz[-1]-xyz[0]).tolist(),
            "body_path_length": float(np.linalg.norm(np.diff(xyz, axis=0), axis=1).sum()),
            "survival": {str(x): ft is None or ft > x for x in (7.2, 13.0, 100.0, 500.0)}}
    physical = milestones["D6_first_whole_body_divergence_ms"] is not None
    feedback = milestones["D7_first_tibial_sensory_divergence_ms"] is not None
    classes = ["CORRECTED_EMBODIMENT_SPONTANEOUS_EXPERIMENT_COMPLETE"]
    if physical and feedback: classes.append("CORRECTED_EMBODIMENT_NEURAL_MOTOR_CAUSALITY_CONFIRMED")
    elif physical: classes.append("PHYSICAL_DIVERGENCE_WITHOUT_FEEDBACK_DIVERGENCE")
    elif milestones["D1_first_mapped_motor_activity_ms"] is None: classes.append("NO_ADMITTED_MOTOR_ACTIVITY")
    else: classes.append("ADMITTED_ACTIVITY_WITHOUT_PHYSICAL_DIVERGENCE")
    return {"schema": m7d.SCHEMA, "status": "COMPLETE", "classification": classes,
        "condition_completion": {c: True for c in m7d.CONDITIONS}, "physics_transitions_per_condition": 5000,
        "physics_states_per_condition": 5001, "neural_updates_per_condition": 1000,
        "pre_intervention_equivalence": True, "causal_milestones": milestones, "per_condition": per,
        "walking": None, "tripod_gait_classification": None,
        "movement_categories": ["NET_BODY_DISPLACEMENT"] if physical else ["NO_SUBSTANTIAL_MOVEMENT"],
        "b4_first_100ms_comparison": {"diagnostic_only": True, "control_survival_consistent": per[m7d.CONDITIONS[1]]["survival"]["100.0"]}}


def _publish(path: Path, payload: Mapping[str, Any]) -> None:
    # Tracked NOT_RUN placeholders are the only replaceable state.
    if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") != "NOT_RUN":
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
    temporary.replace(path)


def run_windows(runner: Any = old._runner) -> Mapping[str, Any]:
    preflight = windows_preflight(runner); protocol, records, table = _protocol(); results = {}
    for i, condition in enumerate(m7d.CONDITIONS, 1):
        result = _invoke(runner, protocol, records, table, condition, i, False)
        if result["physics_steps"] != 5000 or result["neural_steps"] != 1000:
            raise RuntimeError("wrong frozen transition count")
        results[condition] = result
    if not m6c.pre_intervention_equivalent(*(results[c]["pre_intervention_state"] for c in m7d.CONDITIONS)):
        raise RuntimeError("pre-intervention equivalence failure")
    arrays = {f"{c}__{k}": v for c, result in results.items() for k, v in result["raw_arrays"].items()}
    digest = old._write_npz_exclusive(m7d.RAW_PATH, arrays); summary = _reduce(results)
    summary["raw_telemetry"] = {"path": str(m7d.RAW_PATH.resolve()), "byte_size": m7d.RAW_PATH.stat().st_size, "sha256": digest}
    manifest = {"schema": m7d.SCHEMA, "status": "COMPLETE", "source_commit": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "b4": preflight["provenance"], "raw": summary["raw_telemetry"], "environment": preflight["environment"],
        "arrays": {k: {"shape": list(v.shape), "dtype": str(v.dtype)} for k, v in arrays.items()}}
    _publish(m7d.SUMMARY_PATH, summary); _publish(m7d.MANIFEST_PATH, manifest)
    for key in ("classification", "condition_completion", "physics_transitions_per_condition", "neural_updates_per_condition", "pre_intervention_equivalence", "causal_milestones", "per_condition", "movement_categories", "raw_telemetry"): print(f"{key}: {summary[key]}")
    return summary
