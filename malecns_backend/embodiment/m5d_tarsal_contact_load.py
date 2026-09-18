"""Read-only M5D inventory of distal contact/load interfaces.

Nothing in this module writes neural state, constructs an encoder, or advances a
simulation.  The optional live function performs construction and reset only.
"""
from __future__ import annotations

from collections import Counter
import importlib
import json
from pathlib import Path
from typing import Any

from .m5c_leg_sensory_inventory import build_inventory

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "interface_output" / "m5d_tarsal_contact_load_audit.json"
LEGS = ("LF", "LM", "LH", "RF", "RM", "RH")
LEG_TO_SOURCE = {
    "LF": ("T1", "left"), "LM": ("T2", "left"), "LH": ("T3", "left"),
    "RF": ("T1", "right"), "RM": ("T2", "right"), "RH": ("T3", "right"),
}
CONTACT_SEGMENTS = ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")


def _physical_signal(leg: str, mechanism: str) -> dict[str, Any]:
    indices = list(range(LEGS.index(leg) * 6, LEGS.index(leg) * 6 + 6))
    if mechanism == "contact":
        return {
            "observable": f"contact_forces[{indices}, :] != 0 (derived contact state)",
            "raw_observable": "observation['contact_forces']", "raw_shape": [36, 3],
            "leg_slice": indices, "segments": list(CONTACT_SEGMENTS),
            "quantity": "3-D external contact-force vectors on six instrumented leg segments",
            "units": "FlyGym/NMF model force units; local source does not establish conversion to N",
            "direction": "three components; frame not established by local static evidence",
            "sampling": "one observation per reset/physics step; M5D does not step",
            "preprocessing_required": "select distal rows and threshold force magnitude; threshold is not biologically supplied",
            "independent_from_load": False,
            "source": "FlyGym 1.2.1 API usage in fly-brain-interactive/fly_embodied.py",
        }
    return {
        "observable": f"norm(contact_forces[{indices}, :]) (derived distal load proxy)",
        "raw_observable": "observation['contact_forces']", "raw_shape": [36, 3],
        "leg_slice": indices, "segments": list(CONTACT_SEGMENTS),
        "quantity": "magnitude/direction of external segment contact force; not cuticular strain",
        "units": "FlyGym/NMF model force units; local source does not establish conversion to N",
        "direction": "raw vector preserves 3 components; norm discards sign/direction",
        "sampling": "one observation per reset/physics step; M5D does not step",
        "preprocessing_required": "select distal segment(s), aggregate vectors, optionally project onto surface normal",
        "independent_from_contact": False,
        "source": "FlyGym 1.2.1 API usage in fly-brain-interactive/fly_embodied.py",
    }


def _population_record(source: dict[str, Any], mechanism: str) -> dict[str, Any]:
    metadata = source["source_provenance"]["metadata"]
    terminology = {k: v for k, v in metadata.items()
                   if any(term in k.lower() or term in str(v).lower()
                          for term in ("contact", "load", "force", "strain", "claw", "tars"))}
    return {
        "population_name": source["population_name"], "body_ids": source["body_ids"],
        "distinct_body_count": source["distinct_body_id_count"], "leg": source["leg"],
        "side": source["side"], "segment": source["segment"],
        "joint": source["joint"], "biological_structure": source["biological_structure"],
        "sensory_kind": source["sensory_kind"], "classes": source["classes"],
        "subclasses": source["subclasses"], "types": source["types"],
        "source_provenance": source["source_provenance"], "terminology": terminology,
        "direction_fields": source["direction_axis_fields"],
        "magnitude_or_tuning_fields": source["tuning_fields"],
        "explicit_thresholds_or_ranges": {},
        "mechanism": mechanism, "joint_angle_mapped": False,
        "note": "No tuning is inferred from neuron count, body-ID order, or physical metadata.",
    }


def historical_female_audit() -> dict[str, Any]:
    return {
        "scope": "legacy browser female implementation; not FlyGym and not ported to MaleCNS",
        "contact": {
            "biological_annotation": "tactile T# side; source metadata says claw contact",
            "physical_observable": "st.touch[key] from scalar MuJoCo touch_claw_<key> sensor",
            "preprocessing": "binary on=(touch>0); onset/offset change starts burst; exponential decay exp(-dtMs/15)",
            "normalization": "none", "thresholds": {"touch": "> 0", "burst_delivery": "> 0.05"},
            "gain": "180 Hz * burst * (1 - 0.85 * stepping)", "saturation": "implicit initial 180 Hz",
            "population_allocation": "body-ID order modulo 4: k%4==0 tarsal (~25%); remaining ~75% obstacle bristles",
            "stochastic_encoding": False,
            "engineered_constants": {"adaptation_tau_ms": 15, "reafference": 0.85, "peak_hz": 180},
        },
        "load": {
            "biological_annotation": "campaniform T# side; source metadata says force_tarsus",
            "physical_observable": "Euclidean norm of 3-axis MuJoCo force_tarsus_<key> sensor",
            "preprocessing": "hypot(x,y,z); only positive values delivered", "normalization": "none",
            "thresholds": {"load": "> 0"}, "gain": "3000 Hz per model-force unit",
            "saturation": "200 Hz", "population_allocation": "same scalar rate to every population body ID",
            "stochastic_encoding": False,
            "engineered_constants": {"gain": 3000, "maximum_hz": 200},
        },
        "warning": "These are engineered transfer functions, not response functions supplied by the biological annotations.",
    }


def live_introspection() -> dict[str, Any]:
    """Construct/reset the configured body, without step/action/controller/neural calls."""
    result: dict[str, Any] = {"requested": True, "physics_steps": 0,
                              "neural_runtime_touched": False, "controller_touched": False}
    try:
        flygym = importlib.import_module("flygym")
    except ImportError as exc:
        return {**result, "status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}",
                "runtime_observable_state": "NOT_ESTABLISHED"}
    Fly = getattr(flygym, "Fly")
    Simulation = getattr(flygym, "SingleFlySimulation", None)
    if Simulation is None:
        Simulation = importlib.import_module("flygym.simulation").SingleFlySimulation
    fly = Fly(enable_adhesion=False, control="position")
    sim = Simulation(fly=fly, cameras=[], timestep=0.0001)
    try:
        reset_result = sim.reset()
        obs = reset_result[0] if isinstance(reset_result, tuple) else reset_result
        result.update(status="RESET_ONLY", runtime_observable_state="INITIAL_OBSERVATION",
                      observation_keys=sorted(obs),
                      observation_shapes={k: list(getattr(v, "shape", ())) for k, v in sorted(obs.items())},
                      observation_space=str(getattr(sim, "observation_space", None)))
        model = getattr(getattr(sim, "physics", None), "model", None)
        if model is None:
            model = getattr(sim, "model", None)
        result["mujoco_sensors"] = _mujoco_sensor_metadata(model)
    finally:
        close = getattr(sim, "close", None)
        if close:
            close()
    return result


def _mujoco_sensor_metadata(model: Any) -> list[dict[str, Any]]:
    if model is None or not hasattr(model, "nsensor"):
        return []
    rows = []
    for sensor_id in range(int(model.nsensor)):
        name = None
        try:
            name = model.sensor(sensor_id).name
        except Exception:
            pass
        rows.append({"sensor_id": sensor_id, "name": name,
                     "type": int(model.sensor_type[sensor_id]),
                     "object_type": int(model.sensor_objtype[sensor_id]),
                     "object_id": int(model.sensor_objid[sensor_id]),
                     "data_address": int(model.sensor_adr[sensor_id]),
                     "dimension": int(model.sensor_dim[sensor_id])})
    return rows


def build_audit(*, live: bool = False) -> dict[str, Any]:
    unused = [x for x in build_inventory()["interesting_unused"]
              if x["sensory_kind"] in {"contact", "load"}]
    populations = [_population_record(x, "contact" if x["sensory_kind"] == "contact" else "load")
                   for x in unused]
    populations.sort(key=lambda x: (LEGS.index(x["leg"]), x["mechanism"]))
    per_leg = []
    for leg in LEGS:
        contact = next(x for x in populations if x["leg"] == leg and x["mechanism"] == "contact")
        load = next(x for x in populations if x["leg"] == leg and x["mechanism"] == "load")
        per_leg.append({
            "LEG": leg, "CONTACT POPULATION": contact["population_name"],
            "CONTACT PHYSICAL SIGNAL": _physical_signal(leg, "contact")["observable"],
            "CONTACT CLASSIFICATION": "MODELED_TRANSDUCTION_REQUIRED",
            "LOAD POPULATION": load["population_name"],
            "LOAD PHYSICAL SIGNAL": _physical_signal(leg, "load")["observable"],
            "LOAD CLASSIFICATION": "PROXY_ONLY",
            "contact": _physical_signal(leg, "contact"), "load": _physical_signal(leg, "load"),
            "implementability": {"contact": "PHYSICAL_SIGNAL_READY", "load": "PHYSICAL_PROXY_READY"},
        })
    corr = Counter("MODELED_TRANSDUCTION_REQUIRED" if x["mechanism"] == "contact" else "PROXY_ONLY"
                   for x in populations)
    impl = Counter("PHYSICAL_SIGNAL_READY" if x["mechanism"] == "contact" else "PHYSICAL_PROXY_READY"
                   for x in populations)
    static = {
        "installed_packages": {"flygym": "not installed in audit environment", "mujoco": "not installed in audit environment"},
        "pinned_target": "flygym==1.2.1 (fly-brain-interactive/environment.yml)",
        "current_backend_configuration": "Fly(enable_adhesion=False, control='position'); 0.0001 s timestep",
        "interactive_configuration": {"contact_sensor_placements": [f"{leg}{seg}" for leg in LEGS for seg in CONTACT_SEGMENTS],
                                      "ordering": "LF, LM, LH, RF, RM, RH; six segments per leg"},
        "observation_evidence": {"contact_forces": {"shape": [36, 3], "meaning": "6 legs x 6 segment force vectors"},
                                 "end_effectors": {"shape": [6, 3], "meaning": "positions, not contact/load"}},
        "adhesion": "six-element action/command, not an observed contact or measured load; disabled in current backend",
        "geom_contacts_and_cfrc_ext": "MuJoCo can expose contacts/external forces, but no locally verified per-claw public observation beyond contact_forces",
        "contact_pair_metadata": "not established without a live model",
        "mujoco_sensor_ids_types_objects": "not established without a live model",
    }
    summary = {
        "biological_population_count": len(populations),
        "tactile_population_count": sum(x["mechanism"] == "contact" for x in populations),
        "load_population_count": sum(x["mechanism"] == "load" for x in populations),
        "direct_physical_correspondence": corr["DIRECT_PHYSICAL_CORRESPONDENCE"],
        "modeled_transduction_required": corr["MODELED_TRANSDUCTION_REQUIRED"],
        "proxy_only": corr["PROXY_ONLY"], "no_physical_signal": corr["NO_PHYSICAL_SIGNAL"],
        "physical_signal_ready": impl["PHYSICAL_SIGNAL_READY"],
        "physical_proxy_ready": impl["PHYSICAL_PROXY_READY"],
        "needs_physical_model": impl["NEEDS_PHYSICAL_MODEL"], "per_leg": per_leg,
    }
    return {
        "schema_version": "M5D-1.0", "purpose": "read-only tarsal contact/load physical-interface audit",
        "biological_populations": populations, "static_model_metadata": static,
        "runtime_observable_state": live_introspection() if live else {
            "requested": False, "status": "NOT_RUN", "reason": "use --live; non-live mode does not fabricate runtime metadata"},
        "contact_vs_load": {"separable_concepts": True, "independent_measurements": False,
                            "finding": "contact can be thresholded from force, while load uses its magnitude/direction; both derive from contact_forces"},
        "historical_female_implementation": historical_female_audit(), "summary": summary,
        "symmetry": {"all_six_legs": True, "physical_layout_symmetric": True,
                     "biological_population_sizes_symmetric": False},
        "non_intervention": {"neural_drive_added": False, "actuator_output_added": False,
                             "physics_stepped": False, "mapping_promoted": False, "controller_run": False},
    }


def serialized_audit(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
