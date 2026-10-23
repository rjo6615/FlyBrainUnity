"""Opt-in, read-only identity and post-step state probes for v3 candidates."""
import json
from collections.abc import Mapping

import numpy as np
from .presynaptic_trace import PresynapticTrace, excitatory_paths


class CandidateUpstreamProbe:
    """Audit exact runtime identities and retain bounded per-neuron extrema.

    Samples are taken after the neural step and observer update: voltage is
    post-reset and conductances are post-decay. They are not pre-spike peaks.
    No runtime arrays, RNG, weights, or observer state are modified.
    """

    def __init__(self, brain, channels, definitions=None, *, sensory_sources=None):
        if definitions is None:
            from malecns_backend.embodiment.live_v3_motor_interface import CANDIDATE_MOTOR_CHANNELS
            definitions = CANDIDATE_MOTOR_CHANNELS
        self.channels = channels
        self.rows = {}
        self.samples = 0
        for name, definition in definitions.items():
            channel = channels[name]
            populations = {**definition["positive_populations"], **definition["negative_populations"]}
            if set(channel["populations"]) != set(populations):
                raise RuntimeError(f"upstream population inventory mismatch: {name}")
            expected_used = set()
            rows = []
            for population, body_ids in populations.items():
                indices = tuple(int(brain.data.body_id_to_index[body]) for body in body_ids)
                if tuple(map(int, channel["populations"][population])) != indices:
                    raise RuntimeError(f"upstream population index mismatch: {name}/{population}")
                for body_id, index in zip(body_ids, indices):
                    if not 0 <= index < brain.n or int(brain.data.body_ids[index]) != int(body_id):
                        raise RuntimeError(f"upstream body ID round-trip mismatch: {body_id}")
                    if index in expected_used:
                        raise RuntimeError(f"duplicate upstream neuron: {name}/{index}")
                    expected_used.add(index)
                    rows.append({
                        "population": population, "body_id": int(body_id), "dense_index": index,
                        "initial_spikes": int(brain.spike_counts[index]),
                        "spikes": 0, "exc_steps": 0, "inh_steps": 0,
                        "peak_abs_g_exc": 0., "peak_abs_g_inh": 0.,
                        "min_v": None, "max_v": None, "min_post_step_threshold_gap": None,
                    })
            if set(map(int, channel["observer"].used)) != expected_used:
                raise RuntimeError(f"upstream observer index mismatch: {name}")
            self.rows[name] = rows

        # Restrict the one-time graph scan to the watched targets. CSR rows are
        # presynaptic; effective edges use the runtime's already-filtered weight
        # and transmitter sign, rather than raw anatomical synapse counts.
        watched = [row["dense_index"] for rows in self.rows.values() for row in rows]
        slots = np.flatnonzero(np.isin(brain.indices, watched))
        pres = np.searchsorted(brain.indptr, slots, side="right") - 1
        effective = brain.weights[slots] * brain.pre_sign[pres] * brain.config.psp_scale
        targets = brain.indices[slots]
        self.presynaptic = PresynapticTrace(brain, pres, effective, targets)
        paths = excitatory_paths(brain, sensory_sources, watched)
        for rows in self.rows.values():
            for row in rows:
                values = effective[targets == row["dense_index"]]
                row.update(incoming_edges=len(values),
                           sensory_path=paths[row["dense_index"]],
                           effective_exc_edges=int(np.count_nonzero(values > 0)),
                           effective_inh_edges=int(np.count_nonzero(values < 0)))

    def sample(self, brain):
        """Sample the actual arrays and independently check observer counts."""
        self.samples += 1
        for name, rows in self.rows.items():
            observer = self.channels[name]["observer"]
            observed = dict(zip(map(int, observer.used), map(int, observer.last_counts)))
            for row in rows:
                index = row["dense_index"]
                count = int(brain.spike_counts[index])
                if observed[index] != count:
                    raise RuntimeError(f"upstream spike readout mismatch: {name}/{index}")
                v = float(brain.v[index])
                threshold = float(brain.config.v_threshold + brain.adaptation[index]
                                  + brain.threshold_offset[index])
                exc, inh = float(brain.g_exc[index]), float(brain.g_inh[index])
                gap = threshold - v
                if not all(np.isfinite(x) for x in (v, threshold, exc, inh)):
                    raise RuntimeError(f"nonfinite upstream state: {name}/{index}")
                row.update(v=v, threshold=threshold, g_exc=exc, g_inh=inh,
                           presynaptic=self.presynaptic.sample(brain, index),
                           external_drive=float(brain.external_drive[index]),
                           spikes=count - row["initial_spikes"])
                row["exc_steps"] += exc != 0.
                row["inh_steps"] += inh != 0.
                row["peak_abs_g_exc"] = max(row["peak_abs_g_exc"], abs(exc))
                row["peak_abs_g_inh"] = max(row["peak_abs_g_inh"], abs(inh))
                row["min_v"] = v if row["min_v"] is None else min(row["min_v"], v)
                row["max_v"] = v if row["max_v"] is None else max(row["max_v"], v)
                old_gap = row["min_post_step_threshold_gap"]
                row["min_post_step_threshold_gap"] = gap if old_gap is None else min(old_gap, gap)
        return {"samples": self.samples, "identity_verified": True,
                "readout_verified": True, "phase": "post_step_post_observer",
                "channels": {name: tuple(dict(row) for row in rows)
                             for name, rows in self.rows.items()}}


def status_text(state):
    if not state:
        return ""
    parts = []
    for name, rows in state["channels"].items():
        parts.append(
            f"{name.removeprefix('joint_')}(spikes={sum(row['spikes'] for row in rows)} "
            f"exc_peak={max(row['peak_abs_g_exc'] for row in rows):.3g} "
            f"inh_peak={max(row['peak_abs_g_inh'] for row in rows):.3g} "
            f"min_gap={min(row['min_post_step_threshold_gap'] for row in rows):.3g})")
        # Sum across targets: a shared presynaptic neuron is counted once per
        # target, so these are source-to-target incidences, not unique neurons.
        if rows and "presynaptic" in rows[0]:
            exc_active = sum(row["presynaptic"]["exc_active_sources"] for row in rows)
            inh_active = sum(row["presynaptic"]["inh_active_sources"] for row in rows)
            paths = sum(row["sensory_path"]["status"] == "positive_path" for row in rows)
            coverage = ("unavailable" if any(row["sensory_path"]["status"] == "unavailable" for row in rows)
                        else f"{paths}/{len(rows)}")
            parts[-1] += f" inputs(exc_active_inputs={exc_active},inh_active_inputs={inh_active},sensory_reached={coverage})"
    return f"upstream_samples={state['samples']} identity=verified readout=verified upstream=[" + "; ".join(parts) + "]"


def report_json(state):
    # Kernel telemetry is recursively immutable; serialize detached plain data.
    def plain(value):
        if isinstance(value, Mapping):
            return {key: plain(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [plain(item) for item in value]
        return value
    return json.dumps(plain(state), sort_keys=True, allow_nan=False)
