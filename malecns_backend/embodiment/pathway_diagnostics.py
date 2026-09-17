"""Sparse, read-only diagnostics for selected MaleCNS motor pathways.

CSR rows are presynaptic.  This module never materializes a dense adjacency
matrix or a time-by-edge tensor; it retains trajectories only for the audited
motor neurons and sparse spike metadata for neurons that fired.
"""
from __future__ import annotations

from collections import deque
import time

import numpy as np

from .six_tibia import LEG_ORDER


PROVENANCE = {
    "membrane_and_input": "MODELED_NEURAL_STATE",
    "connectivity": "CONNECTOME_DERIVED",
    "motor_identity": "ANNOTATION_DERIVED",
    "interpretation": "OBSERVATIONAL_NOT_CAUSAL",
}


def selected_motor_inventory(interfaces):
    """Return the exact audited populations without discovering new labels."""
    return {leg: [{"population_name": p.name, "body_ids": list(p.body_ids),
                   "dense_indices": list(p.dense_indices), "side": interface.side,
                   "segment": interface.segment, "role": p.function,
                   "direction": p.direction, "confidence": p.confidence,
                   "provenance": p.provenance}
                  for p in interface.motor_populations]
            for leg, interface in interfaces.items()}


def targeted_incoming(brain, target_indices):
    """Extract only CSR edges ending at selected targets (pre row -> post)."""
    targets = set(map(int, target_indices)); result = {target: [] for target in targets}
    for pre in range(brain.n):
        a, b = map(int, brain.indptr[pre:pre + 2])
        for edge in range(a, b):
            post = int(brain.indices[edge])
            if post in targets and brain.weights[edge] != 0:
                result[post].append((pre, edge))
    return result


class PathwayObserver:
    """Observer that only copies state and performs no random operations."""
    def __init__(self, interfaces):
        self.interfaces = interfaces
        self.inventory = selected_motor_inventory(interfaces)
        self.targets = tuple(dict.fromkeys(
            i for leg in LEG_ORDER for p in interfaces[leg].motor_populations
            for i in p.dense_indices))
        self.trajectories = {i: [] for i in self.targets}
        self.delivered = {i: {"excitatory": 0., "inhibitory": 0., "net": 0.,
                              "peak_excitatory": 0., "peak_inhibitory": 0.,
                              "peak_net": 0., "first_input_ms": None}
                          for i in self.targets}
        self.first_spike = {}
        self.spike_times = {i: [] for i in self.targets}
        self.active_spikes = {}
        self.active_first = {}
        self.contributions = {i: {} for i in self.targets}
        self.incoming = None
        self.started_at = time.perf_counter()

    def before_delivery(self, brain, arriving):
        if self.incoming is None:
            self.incoming = targeted_incoming(brain, self.targets)
        step = {i: [0., 0.] for i in self.targets}
        target_set = set(self.targets)
        p = brain.config
        for pre in arriving:
            pre = int(pre)
            scale = float(brain.pre_sign[pre] * p.psp_scale * brain.depression_resource[pre])
            if scale == 0: continue
            a, b = map(int, brain.indptr[pre:pre + 2])
            for edge in range(a, b):
                post = int(brain.indices[edge])
                if post not in target_set: continue
                value = float(brain.weights[edge]) * scale
                bucket = 0 if value > 0 else 1
                step[post][bucket] += value
                c = self.contributions[post].setdefault(pre, {"delivered_events": 0,
                                                               "effective_contribution": 0.})
                c["delivered_events"] += 1; c["effective_contribution"] += value
        for post, (exc, inh) in step.items():
            net = exc + inh; d = self.delivered[post]
            d["excitatory"] += exc; d["inhibitory"] += inh; d["net"] += net
            d["peak_excitatory"] = max(d["peak_excitatory"], exc)
            d["peak_inhibitory"] = min(d["peak_inhibitory"], inh)
            if abs(net) > abs(d["peak_net"]): d["peak_net"] = net
            if d["first_input_ms"] is None and (exc or inh): d["first_input_ms"] = brain.time_ms

    def after_step(self, brain, fired):
        now = float(brain.time_ms); fired_set = set(map(int, fired))
        for index in fired_set:
            self.active_spikes[index] = self.active_spikes.get(index, 0) + 1
            self.active_first.setdefault(index, now)
        for index in self.targets:
            threshold = float(brain.config.v_threshold + brain.adaptation[index] +
                              brain.threshold_offset[index])
            row = {"time_ms": now, "voltage_mV": float(brain.v[index]),
                   "threshold_mV": threshold,
                   "threshold_minus_voltage_mV": threshold - float(brain.v[index]),
                   "refractory_ms": float(brain.refractory[index]),
                   "adaptation_mV": float(brain.adaptation[index]),
                   "g_exc": float(brain.g_exc[index]), "g_inh": float(brain.g_inh[index])}
            self.trajectories[index].append(row)
            if index in fired_set:
                self.spike_times[index].append(now); self.first_spike.setdefault(index, now)

    def report(self, brain):
        incoming = self.incoming or targeted_incoming(brain, self.targets)
        neurons = {}
        for index in self.targets:
            trajectory = self.trajectories[index]
            closest = min(trajectory, key=lambda x: x["threshold_minus_voltage_mV"])
            contributors = []
            for pre, edge in incoming[index]:
                if pre not in self.active_spikes: continue
                item = self.contributions[index].get(pre, {})
                contributors.append({"body_id": int(brain.data.body_ids[pre]),
                    "dense_index": pre, "target_body_id": int(brain.data.body_ids[index]),
                    "connection_sign": float(brain.pre_sign[pre]),
                    "represented_synapse_count": int(brain.data.synapse_counts[edge]),
                    "effective_weight": float(brain.weights[edge] * brain.pre_sign[pre] * brain.config.psp_scale),
                    "spike_count": self.active_spikes[pre], "first_spike_ms": self.active_first[pre],
                    "delivered_events": item.get("delivered_events", 0),
                    "effective_modeled_contribution": item.get("effective_contribution", 0.),
                    "type": str(brain.data.types[pre]),
                    "class": str(brain.data.classes[brain.data.class_ids[pre]]),
                    "superclass": str(brain.data.superclasses[brain.data.superclass_ids[pre]])})
            contributors.sort(key=lambda x: (-abs(x["effective_modeled_contribution"]),
                                              -x["represented_synapse_count"], x["body_id"]))
            neurons[str(int(brain.data.body_ids[index]))] = {
                "dense_index": index, "spike_times_ms": self.spike_times[index],
                "spike_count": len(self.spike_times[index]),
                "closest_to_threshold_mV": closest["threshold_minus_voltage_mV"],
                "closest_to_threshold_time_ms": closest["time_ms"],
                "voltage_immediately_before_spike_mV": None,
                "pre_spike_voltage_limitation": "runtime resets threshold spikes before after_step callback",
                "input": self.delivered[index], "trajectory": trajectory,
                "active_direct_presynaptic_contributors": contributors}
        return {"provenance": PROVENANCE, "motor_neurons": neurons,
                "active_neuron_count": len(self.active_spikes),
                "diagnostic_wall_seconds": time.perf_counter() - self.started_at}


def directed_distances(brain, sources, allowed=None):
    """Sparse forward BFS; optional allowed set defines observed-active graph."""
    distance = np.full(brain.n, -1, dtype=np.int32)
    for source in sources: distance[int(source)] = 0
    queue = deque(map(int, sources))
    while queue:
        pre = queue.popleft(); depth = int(distance[pre])
        a, b = map(int, brain.indptr[pre:pre + 2])
        for post in brain.indices[a:b]:
            post = int(post)
            if distance[post] >= 0 or (allowed is not None and post not in allowed): continue
            distance[post] = depth + 1; queue.append(post)
    return distance


def pathway_graph_report(brain, interfaces, observer):
    """Separate anatomical reachability from observed-active compatibility."""
    target_by_leg = {leg: set(i for p in interfaces[leg].motor_populations for i in p.dense_indices)
                     for leg in LEG_ORDER}
    active = set(observer.active_spikes)
    result = {leg: {"anatomical_distance_from_sensory": {},
                    "observed_active_distance_from_sensory": {}} for leg in LEG_ORDER}
    reach = {}
    for source_leg in LEG_ORDER:
        sources = interfaces[source_leg].sensor.dense_indices
        anatomical = directed_distances(brain, sources)
        dynamic = directed_distances(brain, sources, active | set(sources))
        reach[source_leg] = anatomical
        for target_leg in LEG_ORDER:
            values = [int(anatomical[x]) for x in target_by_leg[target_leg] if anatomical[x] >= 0]
            observed = [int(dynamic[x]) for x in target_by_leg[target_leg] if dynamic[x] >= 0]
            result[target_leg]["anatomical_distance_from_sensory"][source_leg] = min(values) if values else None
            result[target_leg]["observed_active_distance_from_sensory"][source_leg] = min(observed) if observed else None
    for target_leg in LEG_ORDER:
        direct = set()
        for target in target_by_leg[target_leg]: direct.update(p for p, _ in observer.incoming.get(target, []))
        shared = []
        for neuron in sorted(direct & active):
            legs = [leg for leg in LEG_ORDER if reach[leg][neuron] >= 0]
            if len(legs) > 1:
                shared.append({"body_id": int(brain.data.body_ids[neuron]),
                               "reachable_from_sensory_legs": legs})
        result[target_leg]["candidate_convergence_direct_contributors"] = shared
        result[target_leg]["interpretation"] = "observational candidate convergence; not causal proof"
    return result
