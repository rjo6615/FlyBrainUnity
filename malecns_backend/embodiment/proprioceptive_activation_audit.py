"""Canonical single-attempt Windows runner for M5D-5A."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback

import numpy as np

from .proprioceptive_activation import (DURATION_MS, LEG_ORDER, NEURAL_DT_MS,
    PHYSICS_DT_MS, SEED, analyze, base_report, proprio_rngs, sample_candidates,
    verify_provenance)

DEFAULT_OUTPUT = Path(__file__).with_name("interface_output") / "proprioceptive_activation_100ms.json"


def atomic_write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _run_condition(flygym, data, interfaces, proprio_enabled):
    """Run one condition; actuator commands never depend on MaleCNS output."""
    from malecns_backend import MaleCNSBrain
    from .sensory import LegSensoryFrame, SensoryEncoder
    from .tactile_contact import TactileContactConfig, TactileContactEncoder
    from .tactile_motor_loop import ACTUATOR_INDICES
    from .tactile_motor_loop_audit import _forces, _joint_positions, _make_live, _state_tuple

    sim, physics, obs, _tarsus, _surface = _make_live(flygym, interfaces)
    brain = MaleCNSBrain(data); brain.reset(SEED)
    tactile_encoder = TactileContactEncoder(config=TactileContactConfig(seed=SEED))
    encoders = {leg: SensoryEncoder(interfaces[leg]) for leg in LEG_ORDER}
    rngs = proprio_rngs(SEED)
    # Fixed initial command is the physical control in both conditions. No
    # observer or decoder is connected to this array.
    commands = _joint_positions(obs).copy()
    pending_tactile = set(); rows = []
    stride = int(round(NEURAL_DT_MS / PHYSICS_DT_MS))
    direct = np.asarray([i for leg in LEG_ORDER for i in interfaces[leg].sensor.dense_indices], np.intp)
    for step in range(int(round(DURATION_MS / PHYSICS_DT_MS)) + 1):
        time_ms = float(physics.data.time * 1000); measured = _joint_positions(obs)
        forces = _forces(obs)
        tactile = tactile_encoder.encode(forces, time_ms, PHYSICS_DT_MS)["LM"]
        pending_tactile.update(map(int, tactile.generated_dense_indices))
        proprio = {leg: {"angle_rad": float(measured[ACTUATOR_INDICES[leg]]),
            "rates_hz": [], "candidate": [], "delivered": []} for leg in LEG_ORDER}
        fired = (); tactile_delivered = (); neural_state = _state_tuple(brain)
        if step and step % stride == 0:
            brain.clear_external_drive()
            tactile_candidates = tuple(sorted(pending_tactile)); pending_tactile.clear()
            candidate_by_leg = {}
            for leg in LEG_ORDER:
                encoded = encoders[leg].encode(LegSensoryFrame(time_ms / 1000,
                    proprio[leg]["angle_rad"]))
                local = sample_candidates(encoded.rates_hz, rngs[leg])
                candidate_by_leg[leg] = tuple(int(encoded.indices[i]) for i in local)
                proprio[leg]["rates_hz"] = encoded.rates_hz.tolist()
                proprio[leg]["candidate"] = list(candidate_by_leg[leg])
            all_candidates = tuple(sorted(set(tactile_candidates).union(
                *(set(x) for x in candidate_by_leg.values()))))
            if all_candidates:
                brain.set_external_drive(all_candidates, 1000.0 / brain.config.dt)
            brain.external_drive_withheld_indices = (np.empty(0, np.intp) if proprio_enabled else direct)
            fired = tuple(map(int, brain.step())); delivered = set(map(int, brain._last_external_delivered))
            tactile_delivered = tuple(i for i in tactile_candidates if i in delivered)
            for leg in LEG_ORDER:
                proprio[leg]["delivered"] = [i for i in candidate_by_leg[leg] if i in delivered]
            neural_state = _state_tuple(brain)
        # Motor populations are observed only. They cannot influence commands.
        motor = {p.name: int(brain.spike_counts[list(p.dense_indices)].sum())
            for item in interfaces.values() for p in item.motor_populations}
        rows.append({"time_ms": time_ms, "physics": {"qpos": np.asarray(physics.data.qpos).tolist(),
            "qvel": np.asarray(physics.data.qvel).tolist(), "qacc": np.asarray(physics.data.qacc).tolist(),
            "ctrl": np.asarray(physics.data.ctrl).tolist()},
            "tactile": {"modeled_rate_hz": tactile.modeled_rate_hz,
                "candidate": list(map(int, tactile.generated_dense_indices)),
                "delivered": list(tactile_delivered)}, "proprio": proprio,
            "neural_state": neural_state, "cns_spikes": list(fired), "motor": motor})
        if step == int(round(DURATION_MS / PHYSICS_DT_MS)): break
        obs = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})[0]
    if getattr(sim, "close", None): sim.close()
    return rows


def run_live(duration_ms=DURATION_MS, seed=SEED):
    if (duration_ms, seed) != (DURATION_MS, SEED):
        raise ValueError("M5D-5A protocol is fixed at 100.0 ms and seed 1")
    provenance = verify_provenance()
    import importlib
    from malecns_backend import load_malecns
    from .tactile_motor_loop import validated_interfaces
    flygym = importlib.import_module("flygym"); data = load_malecns(); interfaces = validated_interfaces()
    enabled = _run_condition(flygym, data, interfaces, True)
    disabled = _run_condition(flygym, data, interfaces, False)
    return analyze(enabled, disabled, provenance)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration-ms", type=float, default=DURATION_MS); parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT); args = parser.parse_args(argv)
    report = base_report()
    if args.live:
        try: report = run_live(args.duration_ms, args.seed)
        except (ImportError, ModuleNotFoundError) as error:
            report.update(run_status="UNAVAILABLE", reason=f"{type(error).__name__}: {error}")
        except Exception as error:
            category = "PROVENANCE_FAILURE" if "provenance" in str(error).lower() else "PHYSICS_FAILURE"
            report.update(run_status="FAILED", classification=category,
                reason=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
    atomic_write(args.json, report)
    print(f"M5D-5A {report['run_status']}: {report['classification']}")
    return 0 if report["run_status"] in ("COMPLETE", "NOT_RUN", "UNAVAILABLE") else 1


if __name__ == "__main__": raise SystemExit(main())
