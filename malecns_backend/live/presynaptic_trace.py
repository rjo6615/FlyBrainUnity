"""Read-only direct-input activity and excitatory sensory-path diagnostics."""
from collections import deque

import numpy as np


def excitatory_paths(brain, sensory_sources, targets):
    """Shortest paths from any supplied sensor over positive effective edges.

    This is a structural search, not a simulation. Inhibitory/disinhibitory
    paths are outside its scope. Missing sensory configuration is unavailable.
    """
    targets = tuple(map(int, targets))
    if any(target < 0 or target >= brain.n for target in targets):
        raise ValueError("motor target index outside brain")
    if sensory_sources is None:
        return {int(target): {"status": "unavailable"} for target in targets}
    parent = np.full(brain.n, -1, dtype=np.int64)
    owner = {}
    queue = deque()
    for leg, indices in sensory_sources.items():
        for raw in indices:
            index = int(raw)
            if not 0 <= index < brain.n:
                raise ValueError("sensory source index outside brain")
            if parent[index] == -1:
                parent[index] = index
                owner[index] = str(leg)
                queue.append(index)
    remaining = set(map(int, targets))
    remaining.difference_update(queue)
    while queue and remaining:
        pre = queue.popleft()
        sign = brain.pre_sign[pre] * brain.config.psp_scale
        if sign == 0:
            continue
        start, end = brain.indptr[pre:pre + 2]
        edges = brain.indices[start:end][brain.weights[start:end] * sign > 0]
        for raw in edges:
            post = int(raw)
            if parent[post] != -1:
                continue
            parent[post] = pre
            owner[post] = owner[pre]
            remaining.discard(post)
            queue.append(post)
    result = {}
    for target in targets:
        target = int(target)
        if parent[target] == -1:
            result[target] = {"status": "no_positive_path"}
            continue
        path = [target]
        while parent[path[-1]] != path[-1]:
            path.append(int(parent[path[-1]]))
        path.reverse()
        result[target] = {"status": "positive_path", "source_leg": owner[target],
                          "hops": len(path) - 1,
                          "body_ids": tuple(int(brain.data.body_ids[i]) for i in path)}
    return result


class PresynapticTrace:
    """Fixed direct-edge inventory with source counts read from the real brain.

    Source spike counts are not delivered-event counts. Effective weights are
    static and do not model delay, depression or temporal summation here.
    """

    def __init__(self, brain, pres, effective, targets):
        self.inputs = {}
        for target in np.unique(targets):
            mask = targets == target
            neurons, values = pres[mask], effective[mask]
            directions = {}
            for direction, sign in (("exc", 1), ("inh", -1)):
                mask = values * sign > 0
                unique, inverse = np.unique(neurons[mask], return_inverse=True)
                weights = np.zeros(len(unique))
                np.add.at(weights, inverse, np.abs(values[mask]))
                directions[direction] = (unique, weights, brain.spike_counts[unique].astype(np.int64))
            self.inputs[int(target)] = directions

    def sample(self, brain, target):
        result = {}
        for direction in ("exc", "inh"):
            neurons, weights, initial = self.inputs.get(target, {}).get(
                direction, (np.empty(0, dtype=int), np.empty(0), np.empty(0, dtype=int)))
            counts = brain.spike_counts[neurons].astype(np.int64) - initial
            if np.any(counts < 0):
                raise RuntimeError("presynaptic counts decreased during run")
            result[direction + "_source_neurons"] = len(neurons)
            result[direction + "_active_sources"] = int(np.count_nonzero(counts))
            result[direction + "_source_spikes"] = int(counts.sum())
            source = None
            if len(neurons):
                # Prefer observed activity; if all silent, identify the largest
                # static effective source weight to guide the next inspection.
                score = counts * weights if np.any(counts) else weights
                best = int(np.argmax(score))
                pre = int(neurons[best])
                source = {"body_id": int(brain.data.body_ids[pre]), "dense_index": pre,
                          "type": str(brain.data.types[pre]),
                          "spikes": int(counts[best]), "abs_effective_weight": float(weights[best]),
                          "selection": "spikes_times_weight" if np.any(counts) else "largest_silent_weight"}
            result[direction + "_representative_source"] = source
        return result
