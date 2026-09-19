"""Observational adapter around the locked M5D-5B scientific runner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np

from malecns_backend import load_malecns
from ._windows_proprioceptive_closed_loop_adapter import _run_condition
from .proprioceptive_closed_loop import CONDITIONS, analyze as analyze_m5d5b
from .tactile_motor_loop import validated_interfaces
from . import tactile_targeted_contact_calibration as contact
from .instrumented_proprioceptive_closed_loop import TELEMETRY_SCHEMA, classify, sensory_attribution
from .instrumented_proprioceptive_closed_loop_post_audit import divergent_neurons, reachability


def _neural_rows(rows): return [r for r in rows if r["neural_step"] is not None]


def _pack(enabled, disabled):
    """Losslessly pack all-neuron cadence arrays and the complete object trace."""
    packed = {"schema": np.asarray(TELEMETRY_SCHEMA),
        "conditions": np.asarray(CONDITIONS),
        "body_ids": np.asarray(load_malecns().body_ids, dtype=np.int64)}
    for label, rows in zip(("enabled", "disabled"), (enabled, disabled)):
        neural = _neural_rows(rows)
        packed[label + "_time_ms"] = np.asarray([r["time_ms"] for r in neural], dtype=np.float64)
        packed[label + "_neural_state"] = np.stack([r["neural_state"] for r in neural])
        counts = np.zeros((len(neural), len(packed["body_ids"])), dtype=np.uint16)
        for i, row in enumerate(neural):
            if row["cns_spikes"]: np.add.at(counts[i], np.asarray(row["cns_spikes"]), 1)
        packed[label + "_spike_events"] = counts
        packed[label + "_tactile_source_magnitude"] = np.asarray([
            np.linalg.norm(np.asarray(r["tactile"]["source_forces"], dtype=np.float64))
            for r in rows], dtype=np.float64)
        # The existing trace contains every 0.1-ms physical/control sample,
        # tactile/proprio RNG identities, candidates, deliveries and decoder data.
        packed[label + "_trace_json"] = np.asarray(json.dumps(rows, default=_json_default,
            separators=(",", ":")), dtype=np.str_)
    return packed


def _json_default(value):
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, (set, tuple)): return list(value)
    if isinstance(value, np.generic): return value.item()
    raise TypeError(type(value).__name__)


def run_canonical_pair(*, provenance, telemetry_path: Path):
    """Run once per condition via M5D-5B, then observe without replay or RNG."""
    import importlib
    flygym = importlib.import_module("flygym")
    interfaces = validated_interfaces(); data = load_malecns()
    enabled = _run_condition(flygym, data, interfaces, CONDITIONS[0])
    disabled = _run_condition(flygym, data, interfaces, CONDITIONS[1])
    report = analyze_m5d5b(enabled, disabled, provenance)
    telemetry_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(telemetry_path, **_pack(enabled, disabled))
    digest = hashlib.sha256(telemetry_path.read_bytes()).hexdigest()
    old_class = report["classification"]
    report.update(schema="M5D-5D.0", m5d5b_replication_classification=old_class,
        telemetry={"schema": TELEMETRY_SCHEMA, "format": "npz", "path": telemetry_path.name,
            "sha256": digest, "sample_counts": {"physical_per_condition": len(enabled),
                "neural_per_condition": len(_neural_rows(enabled))}})
    m = report["milestones"]
    en = _neural_rows(enabled); dis = _neural_rows(disabled)
    body_ids = np.asarray(data.body_ids, dtype=np.int64)
    left_state = np.stack([r["neural_state"] for r in en]); right_state = np.stack([r["neural_state"] for r in dis])
    left_spikes = np.zeros(left_state.shape, dtype=np.uint16); right_spikes = np.zeros(right_state.shape, dtype=np.uint16)
    for matrix, rows in ((left_spikes,en),(right_spikes,dis)):
        for i,row in enumerate(rows):
            if row["cns_spikes"]: np.add.at(matrix[i], np.asarray(row["cns_spikes"]), 1)
    excluded = set(enabled[0]["direct_proprio_indices"]) | set(enabled[0]["direct_tactile_indices"])
    sources = divergent_neurons(body_ids, np.asarray([r["time_ms"] for r in en]), left_state,
        right_state, left_spikes, right_spikes, m["C10"], excluded) if m["C10"] is not None else []
    for item in sources:
        i=item["dense_index"]
        item.update(annotation=str(data.types[i]), directly_driven_proprioceptive=False,
            directly_driven_tactile=False, mapped_tibia_motor=False)
    interface_map=json.loads((Path(__file__).resolve().parents[1]/"interface_map.json").read_text())
    motor_records=[p for p in interface_map["populations"] if p["category"]=="muscles" and
        (p["name"].startswith("Ti extensor MN T") or p["name"].startswith("Ti flexor MN T"))]
    targets={int(i) for p in motor_records for i in p["dense_indices"]}
    by_index={int(i):p["name"] for p in motor_records for i in p["dense_indices"]}
    for item in sources:
        if item["dense_index"] in targets:
            item.update(mapped_tibia_motor=True, mapped_motor_population=by_index[item["dense_index"]])
    report["post_feedback_source_set"]={"state_divergent":[x for x in sources if x["first_state_divergence_ms"] is not None],
        "spike_divergent":[x for x in sources if x["first_spike_divergence_ms"] is not None],
        "direct_sensory_neurons_excluded":True}
    report["anatomical_reachability"]={"orientation":"presynaptic_to_postsynaptic",
        "depths":reachability(data,[x["dense_index"] for x in sources],targets),
        "targets_only_existing_mapped_tibia_motor_populations":True,
        "anatomical_reachability_is_not_dynamic_recruitment":True}
    first_raw=next((r for r in en if any(v != 0 for v in r["raw_neural_contributions"].values())),None)
    if first_raw:
        leg=next(k for k,v in first_raw["raw_neural_contributions"].items() if v != 0)
        position=en.index(first_raw); before=en[position-1]["observer_states"].get(leg) if position else None
        increments=first_raw["motor_spikes"][leg]
        new_spike=any(increments.values())
        population_names=list(first_raw["observer_states"][leg]["filtered_hz"])
        extensor_population=next((x for x in population_names if "extensor" in x),None)
        flexor_population=next((x for x in population_names if "flexor" in x),None)
        report["c1_resolution"]={"classification":"NEW_MAPPED_MOTOR_SPIKE_TRIGGERED" if new_spike else "DECODER_CARRYOVER_WITHOUT_NEW_SPIKE",
            "time_ms":first_raw["time_ms"], "leg":leg, "mapped_extensor_population":extensor_population,
            "mapped_flexor_population":flexor_population, "new_extensor_spikes":increments["extensor"],
            "new_flexor_spikes":increments["flexor"], "observer_state_before":before,
            "observer_state_after":first_raw["observer_states"][leg], "decoder_filtered_state":first_raw["decoder_states"][leg],
            "raw_contribution":first_raw["raw_neural_contributions"][leg],
            "admitted_contribution":first_raw["admitted_neural_contributions"][leg]}
    qualified=min((x for x in (m["C11"],m["C12"]) if x is not None),default=None)
    motor_state=next((r["time_ms"] for r,s in zip(en,dis) if qualified is not None and r["time_ms"]>qualified and
        any(r["neural_state"][i] != s["neural_state"][i] for i in targets)),None)
    decoder_div=next((r["time_ms"] for r,s in zip(en,dis) if qualified is not None and r["time_ms"]>qualified and
        r["decoder_states"] != s["decoder_states"]),None)
    c13_class=("MAPPED_MOTOR_SPIKE_DIVERGENCE" if m["C13"] is not None else
        "MAPPED_MOTOR_SUBTHRESHOLD_DIVERGENCE" if motor_state is not None else
        "DECODER_STATE_DIVERGENCE_ONLY" if decoder_div is not None else
        "NO_POST_FEEDBACK_MOTOR_DIVERGENCE_WITHIN_WINDOW")
    report["c13_resolution"]={"classification":c13_class,"mapped_motor_spike_divergence_ms":m["C13"],
        "mapped_motor_state_divergence_ms":motor_state,"decoder_state_divergence_ms":decoder_div}
    prefix = all(m[x] is not None for x in ("C3", "C4", "C6", "C7", "C8", "C10", "C11")) and (
        m["C3"] < m["C4"] <= m["C6"] <= m["C7"] <= m["C8"] <= m["C10"] < m["C11"])
    report["replication_guard"] = {"passed": report["pre_intervention_equivalence"]["passed"] and prefix,
        "comparison": "M5D-5B Scientific Run #2", "exact_pre_intervention_equivalence": report["pre_intervention_equivalence"]["passed"],
        "causal_prefix_ordered": prefix}
    def tactile_first(field):
        return next((a["time_ms"] for a,b in zip(enabled,disabled)
            if a["tactile"].get(field) != b["tactile"].get(field)),None)
    tactile_stages={"physical_source_vector_ms":tactile_first("source_forces"),
        "modeled_rate_ms":tactile_first("modeled_rate_hz"),
        "candidate_events_ms":tactile_first("generated"),
        "delivered_events_ms":tactile_first("delivered")}
    tactile=min((x for x in tactile_stages.values() if x is not None),default=None)
    report["sensory_attribution"] = {"classification": sensory_attribution(m["C10"], tactile),
        "first_tactile_any_stage_divergence_ms": tactile, "tactile_stage_divergence":tactile_stages}
    report["classification"] = classify({"provenance": True, "physics_stable": report["physics_safety"]["stable"],
        "rng_aligned": report["rng"]["aligned"], "instrumentation_complete": True,
        "pre_equal": report["pre_intervention_equivalence"]["passed"], "prefix": prefix,
        "C11": m["C11"], "C12": m["C12"], "C13": m["C13"]})
    return report
