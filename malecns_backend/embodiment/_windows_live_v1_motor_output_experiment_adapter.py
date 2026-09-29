"""Windows execution boundary for Experiment 3.

Importing this module constructs no neural or physics runtime.  Scientific
execution remains guarded by the separately reviewed authorization verifier in
``live_v1_motor_output_experiment``.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from . import live_v1_motor_output_experiment as experiment


CONTRACT_PATH = (
    experiment.OUTPUT_DIR / "scientific_execution_contract.json"
)
ANALYSIS_SPEC_PATH = (
    experiment.OUTPUT_DIR / "analysis_specification.json"
)
PASSIVITY_PATH = (
    experiment.OUTPUT_DIR / "telemetry_passivity_validation.json"
)

EXPECTED_CONTRACT_SHA256 = (
    "5a821012e77b7080d20b5bac0e99c117"
    "88bf2480237cbbab915d75f135018fe7"
)
EXPECTED_ANALYSIS_SPEC_SHA256 = (
    "5a2394b587ec2ea2f11f6ddfc33ac737"
    "04d87731244fd281c2f19ebd0220efa4"
)
EXPECTED_PASSIVITY_SHA256 = (
    "6bb7cda0e343e495773360e0a6f55e09"
    "67190860f3d701b783f87980763a2f14"
)
EXPECTED_RUNTIME_SHA256 = (
    "fa716a14e1502bc5ad18e735022aa4d4"
    "1363786b987311ddc5850e8502afbf3d"
)

EXPECTED_PHYSICS_RECORDS = 5000
EXPECTED_NEURAL_RECORDS = 1000
DURATION_MS = 500.0
SEED = 1

CHANNEL_NAMES = tuple(row[0] for row in experiment.MOTOR_CHANNELS)
CHANNEL_INDEX = {
    name: int(index)
    for name, index, _sign in experiment.MOTOR_CHANNELS
}
BASELINE_ONLY_INDICES = tuple(
    index
    for index in range(experiment.ACTION_COUNT)
    if index not in set(CHANNEL_INDEX.values())
)


def _canonical_text_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read frozen Experiment 3 artifact: {path}") from exc


def _verify_frozen_static_inputs() -> dict[str, Any]:
    if _canonical_text_sha256(CONTRACT_PATH) != EXPECTED_CONTRACT_SHA256:
        raise RuntimeError("Experiment 3 execution-contract SHA-256 mismatch")

    if _canonical_text_sha256(ANALYSIS_SPEC_PATH) != EXPECTED_ANALYSIS_SPEC_SHA256:
        raise RuntimeError("Experiment 3 analysis-specification SHA-256 mismatch")

    if _canonical_text_sha256(PASSIVITY_PATH) != EXPECTED_PASSIVITY_SHA256:
        raise RuntimeError("Experiment 3 passivity-validation SHA-256 mismatch")

    runtime_path = experiment.HERE / "_windows_m8_live_condition.py"
    if _raw_sha256(runtime_path) != EXPECTED_RUNTIME_SHA256:
        raise RuntimeError(
            "validated Live Fly v1 runtime differs from passivity-validated identity"
        )

    contract = _load_json(CONTRACT_PATH)
    analysis = _load_json(ANALYSIS_SPEC_PATH)
    passivity = _load_json(PASSIVITY_PATH)

    if (
        contract.get("schema")
        != "LIVE-V1-MOTOR-OUTPUT-SCIENTIFIC-EXECUTION-CONTRACT.1"
        or contract.get("status") != "PROSPECTIVELY_FROZEN_NOT_AUTHORIZED"
    ):
        raise RuntimeError("Experiment 3 execution contract content mismatch")

    if (
        analysis.get("schema")
        != "LIVE-V1-MOTOR-OUTPUT-ANALYSIS-SPECIFICATION.1"
        or analysis.get("status") != "PROSPECTIVELY_FROZEN_NOT_AUTHORIZED"
    ):
        raise RuntimeError("Experiment 3 analysis specification content mismatch")

    if (
        analysis.get("parent_execution_contract", {}).get("sha256")
        != EXPECTED_CONTRACT_SHA256
    ):
        raise RuntimeError("Experiment 3 analysis parent-contract mismatch")

    if (
        passivity.get("STATUS")
        != "PASSIVE_TELEMETRY_VALIDATED_FOR_AUTHORIZATION_REVIEW"
        or passivity.get("EXPERIMENT_3_STATUS") != "NOT_READY_UNAUTHORIZED"
    ):
        raise RuntimeError("Experiment 3 passivity-validation status mismatch")

    long_validation = passivity.get("long_validation", {})
    if (
        long_validation.get("physics_transitions_per_run")
        != EXPECTED_PHYSICS_RECORDS
        or long_validation.get("neural_transitions_per_run")
        != EXPECTED_NEURAL_RECORDS
        or long_validation.get("A_B_STATE_IDENTICAL") is not True
        or long_validation.get("CROSS_STREAM_CLOCK_VALID") is not True
    ):
        raise RuntimeError("Experiment 3 long passivity validation mismatch")

    design_sha = experiment.verify_design()

    return {
        "design_sha256": design_sha,
        "execution_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "analysis_specification_sha256": EXPECTED_ANALYSIS_SPEC_SHA256,
        "passivity_validation_sha256": EXPECTED_PASSIVITY_SHA256,
        "validated_runtime_sha256": EXPECTED_RUNTIME_SHA256,
    }


def enabled_gate(
    values: dict[str, float],
    admitted: tuple[str, ...],
) -> dict[str, float]:
    expected = CHANNEL_NAMES
    if tuple(admitted) != expected or tuple(values) != expected:
        raise RuntimeError("Live Fly v1 channel identity/order mismatch")
    return {name: float(values[name]) for name in admitted}


def matched_control_gate(
    values: dict[str, float],
    admitted: tuple[str, ...],
) -> dict[str, float]:
    """Existing matched control: zero only the final 11 contributions."""
    enabled_gate(values, admitted)
    return {name: 0.0 for name in admitted}


def _final_gate(*, zero: bool) -> Callable[[str, int, float, str], float]:
    def gate(
        name: str,
        action_index: int,
        value: float,
        _underlying_condition: str,
    ) -> float:
        if name not in CHANNEL_INDEX:
            raise RuntimeError("unexpected Live Fly v1 motor channel")
        if int(action_index) != CHANNEL_INDEX[name]:
            raise RuntimeError("Live Fly v1 action-index identity mismatch")
        return 0.0 if zero else float(value)

    return gate


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]

    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return _jsonable(tolist())

    item = getattr(value, "item", None)
    if callable(item):
        return _jsonable(item())

    return value


class _TelemetryCollector:
    def __init__(self) -> None:
        self.neural: list[dict[str, Any]] = []
        self.physics: list[dict[str, Any]] = []

    def __call__(self, record: Mapping[str, Any]) -> None:
        plain = _jsonable(record)

        if "neural_transition_index" in plain:
            if tuple(plain) != experiment.NEURAL_FIELDS:
                raise RuntimeError("Experiment 3 neural telemetry inventory mismatch")
            self.neural.append(plain)
            return

        if "physics_transition_index" in plain:
            if tuple(plain) != experiment.PHYSICS_FIELDS:
                raise RuntimeError("Experiment 3 physics telemetry inventory mismatch")
            self.physics.append(plain)
            return

        raise RuntimeError("unrecognized Experiment 3 telemetry record")


def _load_runtime_bundle() -> dict[str, Any]:
    from . import _windows_m7d_corrected_spontaneous_adapter as m7d_adapter
    from . import _windows_m8_live_condition as live_kernel
    from . import integrated_whole_leg_readiness as m6c
    from . import m7d_corrected_spontaneous as m7d

    if int(m7d.SEED) != SEED or int(m6c.SEED) != SEED:
        raise RuntimeError("Live Fly v1 frozen seed mismatch")

    if float(m7d.DURATION_MS) != DURATION_MS:
        raise RuntimeError("Live Fly v1 frozen duration mismatch")

    if tuple(m7d.SPAWN_POS) != (
        0.0,
        0.0,
        0.6045752232266313,
    ):
        raise RuntimeError("Live Fly v1 frozen spawn mismatch")

    if m7d.CONDITIONS[0] != "CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT":
        raise RuntimeError("Live Fly v1 enabled-condition identity mismatch")

    environment = m7d_adapter._environment()
    protocol, records, table = m7d_adapter._protocol()

    return {
        "runner": live_kernel.run_condition,
        "protocol": protocol,
        "records": records,
        "table": table,
        "condition": m7d.CONDITIONS[0],
        "condition_names": m7d.CONDITIONS,
        "contribution_gate": m7d_adapter.gate_contributions,
        "runtime_factory": m7d_adapter._runtime,
        "admission_assertion": m6c.assert_physical_admission,
        "pre_intervention_equivalent": m6c.pre_intervention_equivalent,
        "environment": environment,
    }


def _run_condition(
    bundle: Mapping[str, Any],
    condition_name: str,
    condition_number: int,
) -> dict[str, Any]:
    if condition_name not in experiment.CONDITIONS:
        raise RuntimeError("unknown Experiment 3 condition")

    collector = _TelemetryCollector()

    zero = condition_name == "matched_control_final_11_zeroed"

    result = bundle["runner"](
        protocol=bundle["protocol"],
        condition=bundle["condition"],
        condition_number=condition_number,
        progress=lambda *_args: "",
        cached_admission_assertion=bundle["admission_assertion"],
        cached_records=bundle["records"],
        cached_table=bundle["table"],
        initialize_only=False,
        duration_ms=DURATION_MS,
        condition_names=bundle["condition_names"],
        contribution_gate=bundle["contribution_gate"],
        compact_telemetry=False,
        runtime_factory=bundle["runtime_factory"],
        proprioception_only=True,
        fixed_initial_baseline=True,
        m8_extended_telemetry=False,
        motor_channel_names=CHANNEL_NAMES,
        final_contribution_gate=_final_gate(zero=zero),
        telemetry_observer=collector,
    )

    if len(collector.neural) != EXPECTED_NEURAL_RECORDS:
        raise RuntimeError(
            "Experiment 3 neural telemetry count mismatch"
        )

    if len(collector.physics) != EXPECTED_PHYSICS_RECORDS:
        raise RuntimeError(
            "Experiment 3 physics telemetry count mismatch"
        )

    experiment.validate_telemetry_clocks(
        collector.neural,
        collector.physics,
    )

    if int(result.get("neural_steps", -1)) != EXPECTED_NEURAL_RECORDS:
        raise RuntimeError("Experiment 3 runtime neural-step count mismatch")

    if int(result.get("physics_steps", -1)) != EXPECTED_PHYSICS_RECORDS:
        raise RuntimeError("Experiment 3 runtime physics-step count mismatch")

    if result.get("physics_instability"):
        raise RuntimeError("Experiment 3 runtime reported physics instability")

    if int(result.get("unauthorized_contribution_count", 0)) != 0:
        raise RuntimeError(
            "Experiment 3 runtime reported unauthorized contribution"
        )

    return {
        "condition": condition_name,
        "neural": collector.neural,
        "physics": collector.physics,
        "runtime_result": result,
    }


def _verify_pairing(
    enabled: Mapping[str, Any],
    control: Mapping[str, Any],
) -> None:
    for stream, index_field in (
        ("neural", "neural_transition_index"),
        ("physics", "physics_transition_index"),
    ):
        first = enabled[stream]
        second = control[stream]

        if len(first) != len(second):
            raise RuntimeError(
                f"Experiment 3 paired {stream} length mismatch"
            )

        for left, right in zip(first, second):
            if left[index_field] != right[index_field]:
                raise RuntimeError(
                    f"Experiment 3 paired {stream} index mismatch"
                )


def _first_activity_time(
    neural: Sequence[Mapping[str, Any]],
    channel: str,
) -> float | None:
    for record in neural:
        increments = record["per_neuron_spike_increments"][channel]
        if any(int(value) > 0 for value in increments):
            return float(record["neural_time_ms"])
    return None


def _first_decoder_time(
    neural: Sequence[Mapping[str, Any]],
    channel: str,
) -> float | None:
    for record in neural:
        if float(record["raw_signed_contribution_rad"][channel]) != 0.0:
            return float(record["neural_time_ms"])
    return None


def _spike_distribution(
    neural: Sequence[Mapping[str, Any]],
    channel: str,
) -> list[dict[str, int]]:
    counter: Counter[int] = Counter()

    for record in neural:
        counter.update(
            int(value)
            for value in record["per_neuron_spike_increments"][channel]
        )

    return [
        {"increment": int(value), "count": int(counter[value])}
        for value in sorted(counter)
    ]


def _filtered_rate_distribution(
    neural: Sequence[Mapping[str, Any]],
    channel: str,
) -> list[float]:
    values: list[float] = []

    for record in neural:
        values.extend(
            float(value)
            for value in record["per_neuron_filtered_rate_hz"][channel]
        )

    return sorted(values)


def _directional_balance(
    neural: Sequence[Mapping[str, Any]],
    channel: str,
) -> list[dict[str, Any]]:
    output = []

    for record in neural:
        positive_rate = float(
            record["pooled_positive_rate_hz"][channel]
        )
        negative_rate = float(
            record["pooled_negative_rate_hz"][channel]
        )
        positive_activation = float(
            record["positive_activation"][channel]
        )
        negative_activation = float(
            record["negative_activation"][channel]
        )

        output.append({
            "neural_transition_index": int(
                record["neural_transition_index"]
            ),
            "neural_time_ms": float(record["neural_time_ms"]),
            "pooled_positive_rate_hz": positive_rate,
            "pooled_negative_rate_hz": negative_rate,
            "positive_activation": positive_activation,
            "negative_activation": negative_activation,
            "activation_difference": (
                positive_activation - negative_activation
            ),
        })

    return output


def _condition_channel_metrics(
    neural: Sequence[Mapping[str, Any]],
    channel: str,
) -> dict[str, Any]:
    total = len(neural)

    if total != EXPECTED_NEURAL_RECORDS:
        raise RuntimeError(
            "Experiment 3 channel analysis received wrong neural count"
        )

    raw_values = sorted(
        float(record["raw_signed_contribution_rad"][channel])
        for record in neural
    )
    final_values = sorted(
        float(record["final_contribution_rad"][channel])
        for record in neural
    )

    nonzero_final = sum(value != 0.0 for value in final_values)
    clamp_count = sum(
        bool(record["range_clamped"][channel])
        for record in neural
    )
    slew_count = sum(
        bool(record["slew_limited"][channel])
        for record in neural
    )

    first_activity = _first_activity_time(neural, channel)
    first_decoder = _first_decoder_time(neural, channel)

    return {
        "first_motor_population_activity_time_ms": first_activity,
        "first_nonzero_decoder_output_time_ms": first_decoder,
        "spike_increment_distribution": _spike_distribution(
            neural,
            channel,
        ),
        "filtered_rate_distribution": _filtered_rate_distribution(
            neural,
            channel,
        ),
        "positive_negative_directional_balance": _directional_balance(
            neural,
            channel,
        ),
        "raw_contribution_distribution": raw_values,
        "final_contribution_distribution": final_values,
        "nonzero_output_duty_fraction": nonzero_final / total,
        "range_clamp_occupancy": clamp_count / total,
        "slew_limit_occupancy": slew_count / total,
        "activity_classification": (
            "OBSERVED_ACTIVE"
            if first_activity is not None
            else "OBSERVED_INACTIVE"
        ),
        "decoder_classification": (
            "DECODER_OUTPUT"
            if first_decoder is not None
            else "NO_DECODER_OUTPUT"
        ),
    }


def _first_physical_divergence(
    enabled_physics: Sequence[Mapping[str, Any]],
    control_physics: Sequence[Mapping[str, Any]],
    action_index: int,
) -> float | None:
    for enabled, control in zip(enabled_physics, control_physics):
        left = float(enabled["measured_joint_positions"][action_index])
        right = float(control["measured_joint_positions"][action_index])

        if left != right:
            return float(enabled["physics_time_ms"])

    return None


def _command_response_lag(
    enabled_neural: Sequence[Mapping[str, Any]],
    control_neural: Sequence[Mapping[str, Any]],
    enabled_physics: Sequence[Mapping[str, Any]],
    control_physics: Sequence[Mapping[str, Any]],
    action_index: int,
) -> dict[str, float | None]:
    command_time = None

    for enabled, control in zip(enabled_neural, control_neural):
        left = float(enabled["commanded_joint_targets"][action_index])
        right = float(control["commanded_joint_targets"][action_index])

        if left != right:
            command_time = float(enabled["neural_time_ms"])
            break

    response_time = None

    if command_time is not None:
        for enabled, control in zip(enabled_physics, control_physics):
            time_ms = float(enabled["physics_time_ms"])

            if time_ms < command_time:
                continue

            left = float(
                enabled["measured_joint_positions"][action_index]
            )
            right = float(
                control["measured_joint_positions"][action_index]
            )

            if left != right:
                response_time = time_ms
                break

    lag = (
        None
        if command_time is None or response_time is None
        else response_time - command_time
    )

    return {
        "first_command_divergence_time_ms": command_time,
        "first_measured_response_divergence_time_ms": response_time,
        "command_to_measured_response_lag_ms": lag,
    }


def _channel_results(
    enabled: Mapping[str, Any],
    control: Mapping[str, Any],
) -> dict[str, Any]:
    output: dict[str, Any] = {}

    for channel in CHANNEL_NAMES:
        action_index = CHANNEL_INDEX[channel]

        enabled_metrics = _condition_channel_metrics(
            enabled["neural"],
            channel,
        )
        control_metrics = _condition_channel_metrics(
            control["neural"],
            channel,
        )

        first_physical = _first_physical_divergence(
            enabled["physics"],
            control["physics"],
            action_index,
        )

        lag = _command_response_lag(
            enabled["neural"],
            control["neural"],
            enabled["physics"],
            control["physics"],
            action_index,
        )

        physically_divergent = first_physical is not None

        output[channel] = {
            "action_index": action_index,
            "coordinate_sign": next(
                sign
                for name, _index, sign in experiment.MOTOR_CHANNELS
                if name == channel
            ),
            "conditions": {
                "live_v1_enabled": enabled_metrics,
                "matched_control_final_11_zeroed": control_metrics,
            },
            "first_physical_divergence_time_ms": first_physical,
            **lag,
            "enabled_control_physical_divergence": physically_divergent,
            "physics_classification": (
                "PHYSICALLY_DIVERGENT"
                if physically_divergent
                else "NOT_PHYSICALLY_DIVERGENT"
            ),
        }

    return output


def _passive_motion_report(
    enabled: Mapping[str, Any],
    control: Mapping[str, Any],
) -> dict[str, Any]:
    enabled_initial = enabled["runtime_result"][
        "initial_physical_state_audit"
    ]["joint_configuration"]
    control_initial = control["runtime_result"][
        "initial_physical_state_audit"
    ]["joint_configuration"]

    if enabled_initial != control_initial:
        raise RuntimeError(
            "Experiment 3 matched initial joint configuration mismatch"
        )

    report: list[dict[str, Any]] = []

    for action_index in BASELINE_ONLY_INDICES:
        by_condition: dict[str, Any] = {}

        for condition_name, run in (
            ("live_v1_enabled", enabled),
            ("matched_control_final_11_zeroed", control),
        ):
            initial = float(
                run["runtime_result"]["initial_physical_state_audit"][
                    "joint_configuration"
                ][action_index]
            )
            values = [
                float(record["measured_joint_positions"][action_index])
                for record in run["physics"]
            ]

            by_condition[condition_name] = {
                "initial_position": initial,
                "minimum_measured_position": min(values),
                "maximum_measured_position": max(values),
                "final_measured_position": values[-1],
                "net_change_from_initial": values[-1] - initial,
                "ever_changed_from_initial_exactly": any(
                    value != initial
                    for value in values
                ),
            }

        paired_time = _first_physical_divergence(
            enabled["physics"],
            control["physics"],
            action_index,
        )

        report.append({
            "action_index": action_index,
            "conditions": by_condition,
            "first_enabled_control_exact_divergence_time_ms": paired_time,
        })

    if len(report) != 31:
        raise RuntimeError(
            "Experiment 3 baseline-only joint count mismatch"
        )

    return {
        "joint_count": len(report),
        "joints": report,
    }


def _runtime_summary(run: Mapping[str, Any]) -> dict[str, Any]:
    result = run["runtime_result"]

    return {
        "physics_steps": int(result["physics_steps"]),
        "neural_steps": int(result["neural_steps"]),
        "physics_instability": bool(
            result.get("physics_instability", False)
        ),
        "unauthorized_contribution_count": int(
            result.get("unauthorized_contribution_count", 0)
        ),
        "initial_physical_state_audit": _jsonable(
            result["initial_physical_state_audit"]
        ),
    }


def _build_result(
    enabled: Mapping[str, Any],
    control: Mapping[str, Any],
    provenance: Mapping[str, Any],
    environment: Mapping[str, Any],
) -> dict[str, Any]:
    _verify_pairing(enabled, control)

    return {
        "schema": "LIVE-V1-MOTOR-OUTPUT-RESULT.1",
        "status": "SCIENTIFIC_EXECUTION_COMPLETE",
        "conditions": list(experiment.CONDITIONS),
        "channels": list(CHANNEL_NAMES),
        "seed": SEED,
        "duration_ms": DURATION_MS,
        "expected_physics_transitions_per_condition": (
            EXPECTED_PHYSICS_RECORDS
        ),
        "expected_neural_transitions_per_condition": (
            EXPECTED_NEURAL_RECORDS
        ),
        "provenance": dict(provenance),
        "environment": _jsonable(environment),
        "runtime_summaries": {
            "live_v1_enabled": _runtime_summary(enabled),
            "matched_control_final_11_zeroed": _runtime_summary(control),
        },
        "channel_results": _channel_results(enabled, control),
        "baseline_only_joint_count": len(BASELINE_ONLY_INDICES),
        "passive_motion_report": _passive_motion_report(
            enabled,
            control,
        ),
        "raw_telemetry": {
            "live_v1_enabled": {
                "neural": enabled["neural"],
                "physics": enabled["physics"],
            },
            "matched_control_final_11_zeroed": {
                "neural": control["neural"],
                "physics": control["physics"],
            },
        },
    }


def execute(
    *,
    runtime_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the frozen Experiment 3 assay only after authorization succeeds."""
    experiment.assert_execution_authorized()

    provenance = _verify_frozen_static_inputs()
    bundle = (
        _load_runtime_bundle()
        if runtime_bundle is None
        else dict(runtime_bundle)
    )

    # Everything above this line is zero-transition preflight.  Once this
    # exclusive marker exists, the scientific attempt is consumed even if the
    # process later fails; deleting it must never be used to authorize a rerun.
    experiment.assert_result_available()
    attempt = experiment.claim_execution_attempt(provenance)

    enabled = _run_condition(
        bundle,
        "live_v1_enabled",
        1,
    )
    control = _run_condition(
        bundle,
        "matched_control_final_11_zeroed",
        2,
    )

    equivalent = bundle["pre_intervention_equivalent"](
        enabled["runtime_result"]["pre_intervention_state"],
        control["runtime_result"]["pre_intervention_state"],
    )

    if not equivalent:
        raise RuntimeError(
            "Experiment 3 pre-intervention state mismatch"
        )

    result = _build_result(
        enabled,
        control,
        provenance,
        bundle["environment"],
    )
    result["execution_attempt"] = attempt
    return result
