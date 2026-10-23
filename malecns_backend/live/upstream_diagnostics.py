"""Opt-in, read-only identity and post-step state probes for v3 candidates."""
import json
from collections.abc import Mapping

import numpy as np
from .presynaptic_trace import PresynapticTrace, excitatory_paths


def _neuron_row(brain, index, population):
    return {"population": population, "body_id": int(brain.data.body_ids[index]),
            "dense_index": index, "type": str(brain.data.types[index]),
            "initial_spikes": int(brain.spike_counts[index]), "spikes": 0,
            "exc_steps": 0, "inh_steps": 0, "peak_abs_g_exc": 0., "peak_abs_g_inh": 0.,
            "min_v": None, "max_v": None, "min_post_step_threshold_gap": None}


def _sample_neuron(brain, row, presynaptic):
    """Shared post-step sampler for motors, intermediates and sensory nodes."""
    index = row["dense_index"]
    v = float(brain.v[index])
    threshold = float(brain.config.v_threshold + brain.adaptation[index] + brain.threshold_offset[index])
    exc, inh = float(brain.g_exc[index]), float(brain.g_inh[index])
    gap = threshold - v
    if not all(np.isfinite(x) for x in (v, threshold, exc, inh)):
        raise RuntimeError(f"nonfinite upstream state: {row['body_id']}/{index}")
    spikes = int(brain.spike_counts[index]) - row["initial_spikes"]
    if spikes < 0:
        raise RuntimeError(f"upstream counts decreased: {row['body_id']}/{index}")
    row.update(v=v, threshold=threshold, g_exc=exc, g_inh=inh,
               presynaptic=presynaptic.sample(brain, index),
               external_drive=float(brain.external_drive[index]), spikes=spikes)
    row["exc_steps"] += exc != 0.
    row["inh_steps"] += inh != 0.
    row["peak_abs_g_exc"] = max(row["peak_abs_g_exc"], abs(exc))
    row["peak_abs_g_inh"] = max(row["peak_abs_g_inh"], abs(inh))
    row["min_v"] = v if row["min_v"] is None else min(row["min_v"], v)
    row["max_v"] = v if row["max_v"] is None else max(row["max_v"], v)
    old_gap = row["min_post_step_threshold_gap"]
    row["min_post_step_threshold_gap"] = gap if old_gap is None else min(old_gap, gap)


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
                    rows.append(_neuron_row(brain, index, population))
            if set(map(int, channel["observer"].used)) != expected_used:
                raise RuntimeError(f"upstream observer index mismatch: {name}")
            self.rows[name] = rows

        # Restrict the one-time graph scan to the watched targets. CSR rows are
        # presynaptic; effective edges use the runtime's already-filtered weight
        # and transmitter sign, rather than raw anatomical synapse counts.
        watched = [row["dense_index"] for rows in self.rows.values() for row in rows]
        paths = excitatory_paths(brain, sensory_sources, watched)
        self.path_indices = {
            target: np.asarray([brain.data.body_id_to_index[body] for body in path.get("body_ids", ())], dtype=np.intp)
            for target, path in paths.items()}
        self.path_initial_counts = {
            target: brain.spike_counts[indices].astype(np.int64)
            for target, indices in self.path_indices.items()}
        path_nodes = sorted({int(index) for indices in self.path_indices.values() for index in indices})
        sensor_nodes = {int(index) for indices in (sensory_sources or {}).values() for index in indices}
        self.pathway_nodes = {}
        for index in path_nodes:
            if int(brain.data.body_id_to_index[int(brain.data.body_ids[index])]) != index:
                raise RuntimeError(f"pathway body ID round-trip mismatch: {index}")
            if index not in watched:
                row = _neuron_row(brain, index, "sensory" if index in sensor_nodes else "intermediate")
                row.update(is_sensory=index in sensor_nodes, encoded_rate_samples=0,
                           encoded_positive_steps=0, peak_encoded_rate_hz=None,
                           external_candidate_steps=0, external_delivered_steps=0)
                self.pathway_nodes[index] = row
        # Reuse one incoming-edge inventory for motors and selected path nodes.
        slots = np.flatnonzero(np.isin(brain.indices, sorted(set(watched) | set(path_nodes))))
        pres = np.searchsorted(brain.indptr, slots, side="right") - 1
        effective = brain.weights[slots] * brain.pre_sign[pres] * brain.config.psp_scale
        targets = brain.indices[slots]
        self.presynaptic = PresynapticTrace(brain, pres, effective, targets)
        self.pathway_edges = []
        anatomical_counts = np.asarray(brain.data.synapse_counts)
        pairs = sorted({(int(a), int(b)) for indices in self.path_indices.values()
                        for a, b in zip(indices, indices[1:])})
        for pre, post in pairs:
            start, end = brain.indptr[pre:pre + 2]
            local = np.flatnonzero(brain.indices[start:end] == post) + start
            self.pathway_edges.append({"pre_body_id": int(brain.data.body_ids[pre]),
                "post_body_id": int(brain.data.body_ids[post]),
                "anatomical_synapses": int(np.sum(anatomical_counts[local])),
                "static_effective_weight": float(np.sum(brain.weights[local] * brain.pre_sign[pre]
                                                         * brain.config.psp_scale))})
        for row in self.pathway_nodes.values():
            values = effective[targets == row["dense_index"]]
            row.update(incoming_edges=len(values), effective_exc_edges=int(np.count_nonzero(values > 0)),
                       effective_inh_edges=int(np.count_nonzero(values < 0)))
        for rows in self.rows.values():
            for row in rows:
                values = effective[targets == row["dense_index"]]
                row.update(incoming_edges=len(values),
                           sensory_path=paths[row["dense_index"]],
                           effective_exc_edges=int(np.count_nonzero(values > 0)),
                           effective_inh_edges=int(np.count_nonzero(values < 0)))

    def sample(self, brain, *, encoded_sensory=None):
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
                _sample_neuron(brain, row, self.presynaptic)
                row.update(sensory_path_spikes=tuple(map(int,
                               brain.spike_counts[self.path_indices[index]].astype(np.int64)
                               - self.path_initial_counts[index])))
        candidates = set(map(int, brain._last_external_candidates))
        delivered = set(map(int, brain._last_external_delivered))
        for index, row in self.pathway_nodes.items():
            _sample_neuron(brain, row, self.presynaptic)
            row["external_candidate_steps"] += index in candidates
            row["external_delivered_steps"] += index in delivered
            row["encoded_rate_hz"] = None
            if row["is_sensory"] and encoded_sensory is not None and index in encoded_sensory:
                rate = float(encoded_sensory[index])
                if not np.isfinite(rate) or rate < 0:
                    raise RuntimeError(f"invalid encoded sensory rate: {index}")
                row["encoded_rate_hz"] = rate
                row["encoded_rate_samples"] += 1
                row["encoded_positive_steps"] += rate > 0.
                row["peak_encoded_rate_hz"] = max(row["peak_encoded_rate_hz"] or 0., rate)
        return {"samples": self.samples, "identity_verified": True,
                "readout_verified": True, "phase": "post_step_post_observer",
                "pathway_nodes": tuple(dict(row) for row in self.pathway_nodes.values()),
                "pathway_edges": tuple(dict(edge) for edge in self.pathway_edges),
                "pathway_identity_verified": True,
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
    nodes = state.get("pathway_nodes", ())
    silent = sum(row["spikes"] == 0 and not row["is_sensory"] for row in nodes)
    return (f"upstream_samples={state['samples']} identity=verified readout=verified upstream=["
            + "; ".join(parts) + "]"
            + (f" pathway_nodes={len(nodes)} silent_intermediates={silent}" if nodes else ""))


def report_json(state):
    # Kernel telemetry is recursively immutable; serialize detached plain data.
    def plain(value):
        if isinstance(value, Mapping):
            return {key: plain(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [plain(item) for item in value]
        return value
    return json.dumps(plain(state), sort_keys=True, allow_nan=False)
