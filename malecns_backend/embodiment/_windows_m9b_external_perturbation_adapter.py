"""Windows-only M9B execution boundary; import and preflight never step."""
from __future__ import annotations
import hashlib, importlib, importlib.metadata, io, json, os, subprocess
from typing import Any

from . import m9b_external_perturbation as m9b
from . import m7d_corrected_spontaneous as m7d
from . import _windows_m7d_corrected_spontaneous_adapter as m7da
from . import _windows_m8_extended_spontaneous_adapter as m8a
from . import integrated_whole_leg_readiness as m6c


def _runner(**kwargs: Any):
    from ._windows_m8_live_condition import run_condition
    return run_condition(**kwargs)


def _invoke(runner: Any, live: Any, records: Any, table: Any,
            condition: str, number: int, initialize_only: bool):
    return runner(protocol=live, condition=condition, condition_number=number,
        progress=lambda n,c,f,s,cw,tw,eta: f"[{n}/4] {c} {f:.1%} step {s}/15000",
        cached_admission_assertion=m6c.assert_physical_admission, cached_records=records,
        cached_table=table, initialize_only=initialize_only, duration_ms=m9b.DURATION_MS,
        condition_names=m9b.CONDITIONS, contribution_gate=m9b.gate_contributions,
        compact_telemetry=True, runtime_factory=m7da._runtime, proprioception_only=True,
        fixed_initial_baseline=True, m8_extended_telemetry=True,
        external_force_by_transition=m9b.force_at_transition,
        m9b_extended_telemetry=True)


def _environment() -> dict[str, Any]:
    result = {}
    for name, required in (("flygym", "1.2.1"), ("mujoco", "3.2.7"), ("numpy", None)):
        module = importlib.import_module(name); version = importlib.metadata.version(name)
        if required is not None and version != required: raise RuntimeError(f"requires {name} {required}, found {version}")
        result[name] = {"version": version, "module_path": str(module.__file__)}
    return result


def windows_preflight(runner: Any = _runner) -> dict[str, Any]:
    """Construct four matched runtimes, validate configuration, execute zero steps."""
    m9b.validate_protocol(m9b.protocol())
    if not m9b.output_available(): raise FileExistsError("canonical M9B output namespace is not clean")
    live, records, table = m7da._protocol()
    states = [_invoke(runner, live, records, table, c, i, True)
              for i, c in enumerate(m9b.CONDITIONS, 1)]
    if any(x["physics_steps"] or x["neural_steps"] for x in states):
        raise RuntimeError("M9B preflight crossed a transition boundary")
    snapshots = [x["pre_intervention_state"] for x in states]
    if not all(m6c.pre_intervention_equivalent(snapshots[0], x) for x in snapshots[1:]):
        raise RuntimeError("M9B state-zero equivalence failure")
    audits = [x["initial_physical_state_audit"] for x in states]
    if any(x != audits[0] for x in audits[1:]) or audits[0]["body_position"] != list(m7d.SPAWN_POS):
        raise RuntimeError("M9B corrected initialization mismatch")
    force_body = [i for i, name in audits[0]["m8_contact_identity"].get("body_names", {}).items()
                  if str(name).split("/")[-1] == "Thorax"]
    if len(force_body) != 1: raise RuntimeError("authoritative Thorax identity is not unique")
    return {"schema": m9b.SCHEMA, "status": "PREFLIGHT_PASS", "selected_design": "four-condition factorial",
        "design_rationale": m9b.protocol()["design"]["rationale"], "m9a_attempt_3_provenance_verified": True,
        "m9a_evidence": m9b.verify_m9a_provenance(), "selected_perturbation_native": m9b.MAGNITUDE_NATIVE,
        "force_schedule": {"transition_indices": "5000-5199", "count": 200, "direction_world": [0,1,0]},
        "environment": _environment(), "malecns_runtime": {"seed": m9b.protocol()["seed"],
            "neural_dt_ms": m9b.NEURAL_DT_MS, "configuration": "frozen M7D/M8 scientific runtime"},
        "motor_interfaces": m9b.protocol()["admitted_motor_interfaces"],
        "proprioceptive_interfaces": list(m9b.SENSORY_INTERFACES),
        "physical_initialization": m9b.protocol()["physical_initialization"],
        "identity_resolution": {"thorax": {"body_id": force_body[0],
            "body_name": audits[0]["m8_contact_identity"]["body_names"][force_body[0]],
            "method": "unique exact terminal slash-delimited body component"},
            "contacts": audits[0]["m8_contact_identity"]},
        "canonical_output_namespace_clean": True, "hidden_assistance": False,
        "initial_state_equivalence": True, "fresh_runtime_count": 4,
        "physics_transitions": 0, "neural_transitions": 0}


def _publish(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False); f.write("\n")


def run_windows(runner: Any = _runner):
    """Execute only after explicit ``--run-windows``; publish exclusively."""
    import numpy as np
    pre = windows_preflight(runner); live, records, table = m7da._protocol(); results = {}
    for i, condition in enumerate(m9b.CONDITIONS, 1):
        result = _invoke(runner, live, records, table, condition, i, False)
        if (result["physics_steps"], result["neural_steps"]) != (m9b.PHYSICS_TRANSITIONS, m9b.NEURAL_UPDATES):
            raise RuntimeError("M9B wrong cadence/state count")
        if result["physics_instability"] or result["unauthorized_contribution_count"]:
            raise RuntimeError("M9B nonfinite telemetry or unauthorized motor contribution")
        results[condition] = result
    arrays = {f"{c}__{k}": v for c, r in results.items() for k, v in r["raw_arrays"].items()}
    for left, right in (("A_P", "B_P"),):
        if not np.array_equal(arrays[f"{left}__physics_external_force"], arrays[f"{right}__physics_external_force"]):
            raise RuntimeError("perturbed force arrays differ")
    for c in ("A_C", "B_C"):
        if np.any(arrays[f"{c}__physics_external_force"]): raise RuntimeError("control force is nonzero")
    for c in ("B_P", "B_C"):
        if np.any(arrays[f"{c}__neural_motor_post_zero"]): raise RuntimeError("disabled motor was physically admitted")
    payload = io.BytesIO(); np.savez_compressed(payload, **arrays); raw = payload.getvalue()
    m9b.RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    with m9b.RAW_PATH.open("xb") as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    report = {"schema": m9b.SCHEMA, "status": "COMPLETE_UNCLASSIFIED", "classification": None,
        "analysis_required": True, "claim_boundary": m9b.protocol()["claim_boundary"]}
    _publish(m9b.REPORT_PATH, report)
    manifest = {"schema": m9b.SCHEMA, "status": "COMPLETE", "source_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True).strip(), "protocol": m9b.protocol(), "preflight": pre,
        "raw": {"byte_size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
        "report": {"byte_size": m9b.REPORT_PATH.stat().st_size,
            "sha256": hashlib.sha256(m9b.REPORT_PATH.read_bytes()).hexdigest()}}
    _publish(m9b.MANIFEST_PATH, manifest)
    return report
