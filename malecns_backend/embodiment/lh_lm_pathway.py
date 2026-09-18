"""Bounded LH-to-LM pathway discovery and transmission-withholding primitives.

Candidate ordering is an observational experiment-planning aid, never a
biological-importance or causal ranking.  Only a matched withholding run can
support an engineering causal statement about the modeled runtime.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np

SOURCE_LEG = "LH"
TARGET_BODY_IDS = (800911, 801234)
MAX_PATH_EDGES = 3
TEMPORAL_CUTOFF_MS = 35.0
EARLY_WINDOW_END_MS = 49.0
MAX_CANDIDATES = 6
MAX_GROUP_SIZE = 6
CANONICAL_SEED = 1
CANONICAL_DURATION_MS = 500
LM_BASELINE_SPIKES = 34
LM_TARGET_BASELINE = {800911: 17, 801234: 17}
LH_WITHHELD_LM_DELTA = -18


@dataclass
class Candidate:
    body_id: int
    cell_type: str
    anatomical_class: str
    sign: float
    path_length_from_lh: int
    path_length_to_800911: int | None
    path_length_to_801234: int | None
    lh_input_synapses: int
    downstream_synapses: int
    effective_modeled_weight: float
    first_canonical_spike_ms: float | None
    canonical_spikes_before_35_ms: int
    canonical_total_spikes: int
    directly_contacts_800911: bool
    directly_contacts_801234: bool
    m4c1_active_direct_contributor: bool
    modeled_contribution: float | None = None
    evidence_class: str = "OBSERVATIONAL_CANDIDATE_NOT_CAUSAL"

    def to_dict(self):
        result = asdict(self)
        result["contacts_both"] = self.directly_contacts_800911 and self.directly_contacts_801234
        result["observed_active"] = (self.first_canonical_spike_ms is not None and
                                     self.first_canonical_spike_ms < TEMPORAL_CUTOFF_MS)
        return result


class SpikeTimelineObserver:
    """Sparse canonical spike telemetry; no dense neuron-by-time allocation."""
    def __init__(self): self.times = defaultdict(list)
    def before_delivery(self, brain, arriving): pass
    def after_step(self, brain, fired):
        for index in fired: self.times[int(index)].append(float(brain.time_ms))


def _bounded_distances(indptr, indices, starts, max_depth=MAX_PATH_EDGES):
    """Directed presynaptic->postsynaptic BFS with a hard depth boundary."""
    distance = {int(i): 0 for i in starts}; frontier = list(distance)
    for depth in range(1, max_depth + 1):
        following = []
        for pre in frontier:
            for post in indices[indptr[pre]:indptr[pre + 1]]:
                post = int(post)
                if post not in distance:
                    distance[post] = depth; following.append(post)
        frontier = following
        if not frontier: break
    return distance


def _bounded_reverse_distances(indptr, indices, targets, max_depth=MAX_PATH_EDGES):
    """Reverse reachability without materializing a CNS-wide transpose."""
    distance = {int(i): 0 for i in targets}; frontier = set(distance)
    for depth in range(1, max_depth + 1):
        predecessors = set()
        for pre in range(len(indptr) - 1):
            if pre in distance: continue
            if any(int(post) in frontier for post in indices[indptr[pre]:indptr[pre + 1]]):
                predecessors.add(pre)
        for pre in predecessors: distance[pre] = depth
        frontier = predecessors
        if not frontier: break
    return distance


def _candidate_sort_key(candidate):
    """Return the documented M4C-3 candidate priority as an ascending key."""
    complete_route_length = candidate.path_length_from_lh + min(
        distance for distance in (
            candidate.path_length_to_800911, candidate.path_length_to_801234)
        if distance is not None)
    observed_active = (candidate.first_canonical_spike_ms is not None and
                       candidate.first_canonical_spike_ms < TEMPORAL_CUTOFF_MS)
    direct_target_count = (candidate.directly_contacts_800911 +
                           candidate.directly_contacts_801234)
    return (not observed_active, complete_route_length, -direct_target_count,
            -candidate.lh_input_synapses, -abs(candidate.effective_modeled_weight),
            candidate.body_id)


def discover_candidates(brain, lh_indices: Iterable[int], spike_times=None,
                        active_direct_contributors=(), max_path_edges=MAX_PATH_EDGES):
    """Return short-path intermediates, prioritized by explicit observational evidence."""
    if max_path_edges > MAX_PATH_EDGES:
        raise ValueError(f"candidate paths are bounded to {MAX_PATH_EDGES} edges")
    data = brain.data; targets = [data.dense_index(x) for x in TARGET_BODY_IDS]
    forward = _bounded_distances(brain.indptr, brain.indices, lh_indices, max_path_edges)
    reverse = [_bounded_reverse_distances(brain.indptr, brain.indices, [t], max_path_edges)
               for t in targets]
    lh_set = set(map(int, lh_indices)); target_set = set(targets); active = set(map(int, active_direct_contributors))
    times = spike_times or {}; candidates = []
    for index, from_lh in forward.items():
        if index in lh_set or index in target_set: continue
        to = [r.get(index) for r in reverse]
        if not any(x is not None and from_lh + x <= max_path_edges for x in to): continue
        outgoing = range(brain.indptr[index], brain.indptr[index + 1])
        direct = [any(int(brain.indices[k]) == target for k in outgoing) for target in targets]
        lh_syn = sum(int(data.synapse_counts[k]) for pre in lh_set
                     for k in range(brain.indptr[pre], brain.indptr[pre + 1])
                     if int(brain.indices[k]) == index)
        downstream_edges = [k for k in outgoing if int(brain.indices[k]) in target_set or
                            any(int(brain.indices[k]) in r for r in reverse)]
        event_times = list(times.get(index, ()))
        candidates.append(Candidate(int(data.body_ids[index]), str(data.types[index]),
            str(data.classes[data.class_ids[index]]), float(brain.pre_sign[index]), from_lh,
            to[0], to[1], lh_syn, sum(int(data.synapse_counts[k]) for k in downstream_edges),
            sum(float(brain.weights[k] * brain.pre_sign[index] * brain.config.psp_scale)
                for k in downstream_edges), min(event_times, default=None),
            sum(t < TEMPORAL_CUTOFF_MS for t in event_times), len(event_times), direct[0], direct[1],
            (int(data.body_ids[index]) in active) or (bool(event_times) and any(direct))))
    # Active-before-35, shorter complete route, dual/direct target contact, and
    # stronger connectivity are deterministic non-causal prioritization keys.
    candidates.sort(key=_candidate_sort_key)
    return candidates


def make_groups(candidates, max_group_size=MAX_GROUP_SIZE):
    """Group by cell type, serializing membership in numeric body-ID order."""
    grouped = defaultdict(list)
    for candidate in candidates: grouped[candidate.cell_type].append(candidate.body_id)
    return [{"cell_type": kind, "body_ids": sorted(ids), "eligible": 1 < len(ids) <= max_group_size,
             "reason": "explicit short-path candidate body IDs" if len(ids) <= max_group_size else "OVERSIZED_NOT_INTERVENED"}
            for kind, ids in sorted(grouped.items()) if len(ids) > 1]


def configure_transmission_withholding(brain, body_ids):
    """Suppress only outgoing events; anatomy, weights and state stay intact."""
    brain.transmission_withheld_indices = np.asarray(
        [brain.data.dense_index(body_id) for body_id in body_ids], dtype=np.intp)


def early_window_summary(rows, target_indices, withheld_indices, physical_divergence_ms=None):
    early = [row for row in rows if row["time_ms"] <= EARLY_WINDOW_END_MS]
    counts = Counter(i for row in early for i in row["spiking_neuron_indices"])
    target_counts = {str(body): counts[index] for body, index in zip(TARGET_BODY_IDS, target_indices)}
    first = next((row["time_ms"] for row in early
                  if any(index in row["spiking_neuron_indices"] for index in target_indices)), None)
    return {"window_ms": [0, EARLY_WINDOW_END_MS], "candidate_counterfactual_spikes":
            sum(counts[i] for i in withheld_indices), "candidate_transmitted_spikes_withheld":
            sum(counts[i] for i in withheld_indices), "lm_target_spikes": target_counts,
            "lm_mapped_motor_spikes": sum(target_counts.values()), "first_lm_motor_spike_ms": first,
            "physical_divergence_ms": physical_divergence_ms,
            "feedback_contaminated_before_window_end": physical_divergence_ms is not None and physical_divergence_ms < EARLY_WINDOW_END_MS}
