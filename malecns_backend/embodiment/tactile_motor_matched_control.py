"""Exact matched-control primitives and evidence analysis for M5D-4C.

This module is deliberately independent of FlyGym.  The Windows runner owns
live construction; the functions here make the intervention semantics small,
testable, and fail-closed.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

from .motor import MotorSafety
from .six_tibia import LEG_ORDER
from .tactile_motor_boundary_diagnostic import compare_contact_sets, semantic_digest
from .tactile_motor_equivalence_diagnostic import compare_value
from .tactile_motor_loop import ACTUATOR_INDICES, NEURAL_DT_MS
from .tactile_targeted_contact_calibration import DEFAULT_TIMESTEP_S

SCHEMA = "M5D-4C.0"
DURATION_MS = 25.0
SEED = 1
CONDITIONS = ("TACTILE_MOTOR_ENABLED", "TACTILE_MOTOR_DISABLED")
CLASSIFICATIONS = (
    "PREFLIGHT_PASS", "NO_NEURAL_INTERVENTION",
    "PRE_INTERVENTION_COMMAND_DIVERGENCE",
    "PRE_INTERVENTION_PHYSICAL_DIVERGENCE", "DECODER_STATE_DIVERGENCE",
    "BASELINE_STATE_DIVERGENCE", "RNG_OR_SENSORY_DIVERGENCE",
    "PROVENANCE_FAILURE", "PHYSICS_FAILURE", "UNRESOLVED_PREFLIGHT_FAILURE",
)


@dataclass(frozen=True)
class PipelineResult:
    measured_position: float
    baseline_target: float
    raw_neural_contribution: float
    admitted_neural_contribution: float
    candidate_target: float
    range_clamped_target: float
    previous_physical_target: float
    slew_limited_target: float
    actuator_command: float


class MatchedControlPipeline:
    """The sole physical command path for either experimental condition.

    The condition is consulted once, to calculate ``admitted``.  Baseline,
    clamps, slew, and physical history are otherwise literally common code.
    Each condition owns an instance, since physical history may properly
    diverge after intervention.
    """
    def __init__(self, enabled: bool, safety: MotorSafety = MotorSafety()):
        self.enabled = bool(enabled)
        self.safety = safety
        self.previous_physical_target: float | None = None

    def update(self, measured_position: float, raw_neural_contribution: float,
               control_dt_s: float) -> PipelineResult:
        if not all(map(math.isfinite, (measured_position, raw_neural_contribution))):
            raise ValueError("control inputs must be finite")
        if control_dt_s <= 0:
            raise ValueError("control_dt_s must be positive")
        # Locked M5D-4 convention: sample measured position at each neural
        # update and use it as that update's baseline/hold target.
        baseline = float(measured_position)
        admitted = float(raw_neural_contribution) if self.enabled else 0.0
        candidate = baseline + admitted
        bounded = min(self.safety.joint_max_rad,
                      max(self.safety.joint_min_rad, candidate))
        previous = baseline if self.previous_physical_target is None else self.previous_physical_target
        maximum_delta = self.safety.max_velocity_rad_s * control_dt_s
        slew = min(previous + maximum_delta, max(previous - maximum_delta, bounded))
        final = min(self.safety.joint_max_rad,
                    max(self.safety.joint_min_rad, slew))
        result = PipelineResult(baseline, baseline, float(raw_neural_contribution),
            admitted, candidate, bounded, previous, slew, final)
        self.previous_physical_target = final
        return result


def decode_raw(decoder: Any, rates: Mapping[str, float]) -> dict[str, float]:
    """Calculate the existing decoder signal without touching physical state."""
    ext_hz = float(rates[decoder.pathway.extensor.name])
    flex_hz = float(rates[decoder.pathway.flexor.name])
    ext = decoder.activation(ext_hz); flex = decoder.activation(flex_hz)
    antagonist = ext - flex
    raw = decoder.safety.max_offset_rad * antagonist
    return {"extensor_hz": ext_hz, "flexor_hz": flex_hz,
            "extensor_activation": ext, "flexor_activation": flex,
            "antagonist_signal": antagonist, "raw_neural_contribution": raw}


def base_report() -> dict[str, Any]:
    milestone = lambda: {"time_ms": None, "physical_step": None,
                         "neural_step": None, "leg": None, "value": None}
    return {
        "schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "reason": "Live M5D-4C preflight has not been run on validated Windows FlyGym/MuJoCo",
        "protocol": {"seed": SEED, "duration_ms": DURATION_MS,
            "physics_timestep_s": DEFAULT_TIMESTEP_S,
            "neural_timestep_ms": NEURAL_DT_MS, "conditions": list(CONDITIONS),
            "exact_comparison": True, "canonical_100ms_run_permitted": False,
            "contact_setup": "locked M5D-2C LM Tarsus5 calibration"},
        "provenance": {"verified": False, "m5d2c_and_m5d3": None,
            "m5d4_semantic_digest": None, "m5d4a_semantic_digest": None,
            "m5d4b_semantic_digest": None},
        "control_pipeline_definition": {"single_common_path": True,
            "order": ["measured_position", "baseline_target",
                "raw_decoded_neural_contribution", "experimental_gate",
                "admitted_neural_contribution", "sum", "range_clamp",
                "slew_limiter", "final_range_clamp", "actuator_command", "MuJoCo_ctrl"],
            "joint_range_rad": [-1.35, 1.30], "slew_rate_rad_s": 4.0,
            "condition_dependent_value": "admitted_neural_contribution"},
        "baseline_definition": {"source": "current measured joint position (locked M5D-4 convention)",
            "sampling_time": "at each 0.5-ms neural update before command calculation",
            "update_cadence_ms": NEURAL_DT_MS,
            "persistence": "last actuator command persists between neural updates",
            "condition_independent": True},
        "intervention_definition": {"boundary": "first enabled admitted_neural_contribution != 0",
            "enabled": "admitted = raw", "disabled": "admitted = 0.0",
            "disabled_decoder_continues": True},
        "pre_intervention_equivalence": None, "decoder_state_equivalence": None,
        "first_mapped_motor_spike": milestone(),
        "first_raw_neural_contribution": milestone(),
        "first_enabled_admitted_neural_contribution": milestone(),
        "first_raw_neural_contribution_ms": None,
        "first_enabled_admitted_neural_contribution_ms": None,
        "first_action_divergence": milestone(), "first_ctrl_divergence": milestone(),
        "first_action_divergence_ms": None, "first_ctrl_divergence_ms": None,
        "first_physical_divergence_ms": None,
        "first_qacc_divergence": milestone(), "first_qvel_divergence": milestone(),
        "first_qpos_divergence": milestone(), "first_force_divergence": milestone(),
        "first_contact_divergence": milestone(),
        "first_sensory_encoding_divergence": milestone(),
        "first_post_feedback_cns_divergence": milestone(),
        "first_subsequent_mapped_motor_divergence": milestone(),
        "causal_ordering": {"established": False, "sequence_ms": None,
            "physical_divergence_did_not_precede_intervention": None},
        "per_leg_summary": {leg: {"actuator_index": ACTUATOR_INDICES[leg],
            "first_raw_neural_contribution_ms": None,
            "first_enabled_admitted_neural_contribution_ms": None,
            "first_action_divergence_ms": None} for leg in LEG_ORDER},
        "limitations": ["Preflight only; no neural motor-causality claim.",
            "Feedback closure is not required within 25 ms.",
            "Canonical M5D-4 is neither run nor overwritten."],
    }


FIELDS = {
    "baseline": ("measured_positions", "baseline_targets", "previous_physical_targets"),
    "decoder": ("raw_neural_contributions", "observer_states", "decoder_states"),
    "sensory": ("sensory_encoding", "rng_state"),
    "action": ("action_joints", "six_tibia_action", "adhesion"),
    "ctrl": ("ctrl",), "qacc": ("qacc",), "qvel": ("qvel",), "qpos": ("qpos",),
    "force": ("contact_forces",), "contact": ("contact_set",),
}


def _first_difference(enabled: Sequence[Mapping[str, Any]], disabled: Sequence[Mapping[str, Any]],
                      fields: Sequence[str], before_ms: float | None = None,
                      contact: bool = False) -> dict[str, Any] | None:
    if len(enabled) != len(disabled):
        raise ValueError("condition trace lengths differ")
    for step, (left, right) in enumerate(zip(enabled, disabled)):
        if left["time_ms"] != right["time_ms"]:
            raise ValueError("condition sample schedules differ")
        if before_ms is not None and left["time_ms"] >= before_ms:
            break
        for field in fields:
            comparison = (compare_contact_sets if contact else compare_value)(left[field], right[field])
            if not comparison["exactly_equal"]:
                return {"time_ms": left["time_ms"], "physical_step": step,
                        "variable": field, **comparison}
    return None


def classify_traces(enabled: Sequence[Mapping[str, Any]], disabled: Sequence[Mapping[str, Any]],
                    intervention_ms: float | None) -> tuple[str, dict[str, Any]]:
    """Apply fail-fast classification precedence to exact recorded traces."""
    pre = {group: _first_difference(enabled, disabled, fields, intervention_ms,
           contact=group == "contact") for group, fields in FIELDS.items()}
    evidence = {"before_intervention_ms": intervention_ms, "differences": pre,
                "exactly_equal": not any(pre.values())}
    if pre["baseline"]: return "BASELINE_STATE_DIVERGENCE", evidence
    if pre["decoder"]: return "DECODER_STATE_DIVERGENCE", evidence
    if pre["sensory"]: return "RNG_OR_SENSORY_DIVERGENCE", evidence
    if pre["action"] or pre["ctrl"]: return "PRE_INTERVENTION_COMMAND_DIVERGENCE", evidence
    if any(pre[x] for x in ("qacc", "qvel", "qpos", "force", "contact")):
        return "PRE_INTERVENTION_PHYSICAL_DIVERGENCE", evidence
    if intervention_ms is None: return "NO_NEURAL_INTERVENTION", evidence
    # Raw decoding, observer state, baseline, and prior physical history must
    # still match at the intervention update itself. Only admitted contribution
    # (not included in these groups) may differ there.
    through_boundary = intervention_ms + (DEFAULT_TIMESTEP_S * 1000.0) / 2.0
    boundary_baseline = _first_difference(enabled, disabled, FIELDS["baseline"], through_boundary)
    boundary_decoder = _first_difference(enabled, disabled, FIELDS["decoder"], through_boundary)
    boundary_sensory = _first_difference(enabled, disabled, FIELDS["sensory"], through_boundary)
    evidence["intervention_boundary_state"] = {"baseline": boundary_baseline,
        "decoder": boundary_decoder, "sensory": boundary_sensory}
    if boundary_baseline: return "BASELINE_STATE_DIVERGENCE", evidence
    if boundary_decoder: return "DECODER_STATE_DIVERGENCE", evidence
    if boundary_sensory: return "RNG_OR_SENSORY_DIVERGENCE", evidence
    first_action = _first_difference(enabled, disabled, FIELDS["action"])
    first_ctrl = _first_difference(enabled, disabled, FIELDS["ctrl"])
    physical = [_first_difference(enabled, disabled, FIELDS[x], contact=x == "contact")
                for x in ("qacc", "qvel", "qpos", "force", "contact")]
    ordered = [first_action, first_ctrl, *physical[:3]]
    times = [x["time_ms"] for x in ordered if x]
    if any(t < intervention_ms for t in times):
        return "UNRESOLVED_PREFLIGHT_FAILURE", evidence
    if times != sorted(times):
        return "UNRESOLVED_PREFLIGHT_FAILURE", evidence
    return "PREFLIGHT_PASS", evidence


def semantic_lock(document: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
    return semantic_digest(document, manifest)


def serialize(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def atomic_write(path: Path, report: Mapping[str, Any]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialize(report)); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def legacy_bug_command(measured: float, retained_decoder_target: float, enabled: bool) -> float:
    """Minimal reproduction of the forbidden M5D-4 branch (tests only)."""
    return retained_decoder_target if enabled else measured
