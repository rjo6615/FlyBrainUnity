"""M5D-3 matched tactile-delivery experiment and analysis primitives.

This module deliberately separates candidate generation from delivery.  The
disabled arm runs the same encoder and consumes the same random stream; only
the normal :meth:`MaleCNSBrain.set_external_drive` boundary is withheld.
Nothing in this module writes neural state or produces a motor command.
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from .mappings import INTERFACE_MAP
from .six_leg_audit import OUTPUT as AUTHORITATIVE_MOTOR_MAP
from .tactile_contact import TactileContactConfig, TactileContactEncoder, load_tactile_populations
from .tactile_targeted_contact_calibration import (
    CONTACT_PENETRATION, DEFAULT_TIMESTEP_S, ENGINEERING_THRESHOLD, SURFACE_NAME,
)

LEG = "LM"
SEGMENT = "Tarsus5"
CONTACT_FORCE_ROW = 11
POPULATION_NAME = "tactile T2 left"
POPULATION_SIZE = 378
DEFAULT_DURATION_MS = 100
DEFAULT_NEURAL_DT_MS = 0.5
PHYSICAL_TOLERANCE = 0.0


def serialized_report(report: Mapping[str, Any]) -> str:
    """Canonical, strict JSON used for both checked-in and live artifacts."""
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False,
                      allow_nan=False) + "\n"


def rng_digest(rng) -> str:
    state = json.dumps(rng.bit_generator.state, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(state.encode("ascii")).hexdigest()


def locked_hashes(root: Path | None = None) -> dict[str, str]:
    """Read-only provenance for the three artifacts locked by M5D-2C."""
    root = root or Path(__file__).resolve().parents[2]
    names = (
        "malecns_backend/embodiment/tactile_contact.py",
        "malecns_backend/embodiment/tactile_contact_calibration.py",
        "malecns_backend/embodiment/interface_output/tactile_contact_calibration.json",
    )
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in names}


def tactile_population():
    population = load_tactile_populations()[LEG]
    if population.name != POPULATION_NAME or len(population.body_ids) != POPULATION_SIZE:
        raise RuntimeError("locked complete tactile T2-left population changed")
    if len(set(population.body_ids)) != POPULATION_SIZE:
        raise RuntimeError("tactile T2-left body IDs are not unique")
    return population


def motor_populations(map_path=AUTHORITATIVE_MOTOR_MAP,
                      interface_path=INTERFACE_MAP) -> dict[str, tuple[int, ...]]:
    """Load the mapped leg-motor observer set established by M4A/M4B.

    The M4A inventory, rather than every broad ``muscles`` record, determines
    membership.  Names are retained only as authoritative identifiers; they
    are never parsed to infer a leg, joint, or motor role.
    """
    audit = json.loads(Path(map_path).read_text(encoding="utf-8"))
    if audit.get("schema") != "flybrain.six_leg_anatomical_map":
        raise ValueError("authoritative M4A motor map has an unexpected schema")
    mapped = audit["population_inventory"]["leg_motor"]

    interface = json.loads(Path(interface_path).read_text(encoding="utf-8"))
    dense_by_body_id: dict[int, int] = {}
    for record in interface["populations"]:
        for body_id, dense_index in zip(record["body_ids"], record["dense_indices"]):
            body_id, dense_index = int(body_id), int(dense_index)
            previous = dense_by_body_id.setdefault(body_id, dense_index)
            if previous != dense_index:
                raise ValueError(f"body ID {body_id} has conflicting dense indices")

    result: dict[str, tuple[int, ...]] = {}
    for record in mapped:
        name = record["name"]
        if name in result:
            raise ValueError(f"duplicate mapped M4A motor population {name!r}")
        try:
            result[name] = tuple(dense_by_body_id[int(value)]
                                 for value in record["body_ids"])
        except KeyError as error:
            raise ValueError(f"mapped motor body ID {error.args[0]} does not resolve") from error
    return result


def physical_match(enabled: Iterable[Mapping], disabled: Iterable[Mapping],
                   tolerance: float = PHYSICAL_TOLERANCE) -> dict:
    """Compare the passive physical traces; contact truth is the exact pair."""
    a, b = tuple(enabled), tuple(disabled)
    if len(a) != len(b):
        return {"matched": False, "classification": "PHYSICAL_MATCH_FAILED",
                "reason": "sample counts differ", "tolerance": tolerance}
    fields = ("simulation_time_s", "force_magnitude", "selected_pair_present")
    first = None
    max_qpos = max_force = 0.0
    for i, (left, right) in enumerate(zip(a, b)):
        qdelta = float(np.max(np.abs(np.asarray(left["qpos"]) - np.asarray(right["qpos"]))))
        fdelta = abs(float(left["force_magnitude"]) - float(right["force_magnitude"]))
        max_qpos, max_force = max(max_qpos, qdelta), max(max_force, fdelta)
        unequal = (qdelta > tolerance or fdelta > tolerance or
                   any(left[k] != right[k] for k in fields if k != "force_magnitude"))
        if unequal and first is None:
            first = i
    matched = first is None
    return {"matched": matched,
            "classification": "PHYSICAL_MATCH_CONFIRMED" if matched else "PHYSICAL_MATCH_FAILED",
            "tolerance": tolerance, "first_differing_sample": first,
            "maximum_qpos_absolute_difference": max_qpos,
            "maximum_force_magnitude_difference": max_force}


def downstream_indices(neuron_count: int, tactile_indices: Iterable[int]) -> np.ndarray:
    mask = np.ones(int(neuron_count), dtype=bool)
    mask[np.asarray(tuple(tactile_indices), dtype=np.intp)] = False
    return np.flatnonzero(mask)


def classify_causal(*, physical_contact: bool, sensor_correspondence: bool,
                    candidate_count: int, delivered_count: int,
                    non_tactile_state_diverged: bool,
                    non_tactile_spikes_diverged: bool,
                    mapped_motor_diverged: bool,
                    mapped_motor_observation_valid: bool = True) -> str:
    if not physical_contact: return "P0"
    if not sensor_correspondence: return "P1"
    if not candidate_count: return "P2"
    if not delivered_count: return "P3"
    if not non_tactile_state_diverged: return "P4"
    if not non_tactile_spikes_diverged: return "P5"
    if mapped_motor_observation_valid and mapped_motor_diverged: return "P7"
    return "P6"


def shortest_directed_distances(indptr, indices, sources: Iterable[int],
                                targets: Iterable[int]) -> dict[int, int | None]:
    """Multi-source CSR BFS.  Anatomical reachability is not dynamic causality."""
    wanted = set(map(int, targets)); found = {}
    distance = {int(source): 0 for source in sources}
    queue = deque(distance)
    while queue and wanted:
        pre = queue.popleft()
        if pre in wanted:
            found[pre] = distance[pre]; wanted.remove(pre)
        for post in indices[indptr[pre]:indptr[pre + 1]]:
            post = int(post)
            if post not in distance:
                distance[post] = distance[pre] + 1; queue.append(post)
    return {target: found.get(target) for target in map(int, targets)}


def matched_encoder_candidates(force_frames: Iterable[np.ndarray], times_ms: Iterable[float],
                               *, dt_ms: float, seed: int) -> dict:
    """Execute both encoders and prove candidate/RNG parity without delivery."""
    population = tactile_population()
    config = TactileContactConfig(seed=seed)
    encoders = (TactileContactEncoder(config=config), TactileContactEncoder(config=config))
    streams = [[], []]
    checkpoints = [[], []]
    frames = tuple(force_frames); times = tuple(times_ms)
    if len(frames) != len(times): raise ValueError("force/timing schedules differ")
    for condition, encoder in enumerate(encoders):
        for forces, time_ms in zip(frames, times):
            frame = encoder.encode(forces, time_ms, dt_ms)[LEG]
            streams[condition].append(frame.generated_dense_indices)
            checkpoints[condition].append(rng_digest(encoder.rng[LEG]))
    parity = streams[0] == streams[1] and checkpoints[0] == checkpoints[1]
    return {"parity": parity, "candidate_events": streams[0],
            "rng_checkpoints": checkpoints[0], "population_size": len(population.body_ids)}


def base_report(duration_ms=DEFAULT_DURATION_MS, seed=1) -> dict:
    population = tactile_population()
    return {
        "schema_version": "M5D-3.0", "run_status": "NOT_RUN",
        "reason": "requires validated Windows FlyGym/MuJoCo/MaleCNS runtime; invoke with --live",
        "protocol_configuration": {"conditions": ["TACTILE_ENABLED", "TACTILE_DISABLED"],
          "duration_ms": duration_ms, "seed": seed, "physics_timestep_s": DEFAULT_TIMESTEP_S,
          "neural_timestep_ms": DEFAULT_NEURAL_DT_MS, "neural_motor_output": False,
          "only_intended_difference": "delivery of identical candidate tactile events"},
        "locked_provenance": {"artifact_sha256": locked_hashes(),
          "threshold_interpretation": "engineering zero/nonzero threshold; not biological"},
        "physical_contact_verification": {"leg": LEG, "segment": SEGMENT,
          "contact_forces_row": CONTACT_FORCE_ROW, "surface": SURFACE_NAME,
          "penetration_model_units": CONTACT_PENETRATION, "threshold": ENGINEERING_THRESHOLD,
          "exact_unordered_geom_pair_required": True, "verified": False},
        "physical_match_verification": {"matched": None, "classification": "NOT_RUN"},
        "rng_parity_checkpoints": {"parity": None, "checkpoints": []},
        "tactile_candidate_events": {"count": None, "events": []},
        "tactile_delivered_events": {"enabled_count": None, "disabled_count": 0},
        "timing_milestones_ms": {name: None for name in (
          "first_mujoco_contact", "first_nonzero_force", "first_modeled_rate",
          "first_candidate_spike", "first_delivered_spike", "first_neural_state_divergence",
          "first_non_tactile_divergence", "first_non_tactile_spike_divergence",
          "first_mapped_motor_divergence")},
        "enabled_neural_summary": None, "disabled_neural_summary": None,
        "non_tactile_cns_divergence_summary": None, "first_differing_neurons": [],
        "mapped_motor_observational_summary": {"motor_output_decoded": False,
          "motor_output_applied": False, "result": "NOT_RUN"},
        "anatomical_context": {"result": "NOT_RUN",
          "warning": "directed paths are anatomical context, not proof of dynamic causality"},
        "causal_classification": "NOT_RUN",
        "population": {"name": population.name, "size": len(population.body_ids),
          "body_ids": list(population.body_ids), "dense_indices": list(population.dense_indices),
          "subsampled": False},
        "limitations": ["Modeled 120 Hz/20 ms onset transient is not a biological response parameter.",
          "The 1e-12 engineering threshold is not a biological tactile threshold.",
          "No live scientific result was generated in this environment."],
    }
