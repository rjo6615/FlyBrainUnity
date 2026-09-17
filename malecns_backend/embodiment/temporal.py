"""Passive temporal/connectome diagnostics for the Milestone 3C replay."""
from collections import deque
from dataclasses import asdict, dataclass

import numpy as np

from malecns_backend.loader import SIDE_NAMES


@dataclass(frozen=True)
class MotorInputResult:
    body_id: int
    dense_index: int
    presynaptic_spiking_neurons: int
    excitatory_events: int
    inhibitory_events: int
    peak_excitatory_state: float
    peak_inhibitory_state: float
    peak_voltage: float
    closest_threshold_margin: float
    threshold_crossed: bool
    first_spike_ms: float | None


def neuron_metadata(data, index, pathway=None):
    """Return only exact fields present in MaleCNS metadata plus audited flags."""
    superclass = data.superclasses[data.superclass_ids[index]]
    body_id = int(data.body_ids[index])
    motor_ids = set() if pathway is None else set(pathway.extensor.body_ids + pathway.flexor.body_ids)
    selected = None
    if pathway is not None:
        if body_id in pathway.extensor.body_ids:
            selected = "extensor"
        elif body_id in pathway.flexor.body_ids:
            selected = "flexor"
    lower = superclass.lower()
    return {
        "body_id": body_id,
        "dense_index": int(index),
        "class": data.classes[data.class_ids[index]],
        "superclass": superclass,
        "cell_type": data.types[index],
        "instance": data.instances[index],
        "side": SIDE_NAMES[data.side_ids[index]],
        "neurotransmitter": data.neurotransmitters[data.neurotransmitter_ids[index]],
        "ascending": "ascending" in lower,
        "descending": "descending" in lower,
        "sensory": "sensory" in lower,
        "motor": body_id in motor_ids or any(x in lower for x in ("motor", "efferent")),
        "selected_tibia_motor_population": selected,
    }


def directed_distances(data, sources):
    """Breadth-first minimum hop counts following presynaptic -> postsynaptic edges."""
    distance = np.full(data.neuron_count, -1, dtype=np.int32)
    queue = deque(int(x) for x in sources)
    distance[np.asarray(tuple(queue), dtype=np.intp)] = 0
    while queue:
        pre = queue.popleft()
        for post in data.target_indices[data.row_ptr[pre]:data.row_ptr[pre + 1]]:
            post = int(post)
            if distance[post] < 0:
                distance[post] = distance[pre] + 1
                queue.append(post)
    return distance


def motor_connectivity(data, brain, sensor_indices, motor_indices, distances=None):
    """Describe anatomical reachability and direct sensory input without inference."""
    distances = directed_distances(data, sensor_indices) if distances is None else distances
    sensors = set(int(x) for x in sensor_indices)
    incoming = {int(x): [] for x in motor_indices}
    for pre in sensors:
        a, b = data.row_ptr[pre], data.row_ptr[pre + 1]
        for slot in range(a, b):
            post = int(data.target_indices[slot])
            if post in incoming:
                incoming[post].append({
                    "presynaptic_body_id": int(data.body_ids[pre]),
                    "synapse_count": int(data.synapse_counts[slot]),
                    "effective_weight": float(brain.weights[slot] * brain.pre_sign[pre] *
                                              brain.config.psp_scale),
                })
    return [{
        "body_id": int(data.body_ids[index]), "dense_index": int(index),
        "reachable": bool(distances[index] >= 0),
        "minimum_hops": None if distances[index] < 0 else int(distances[index]),
        "direct_sensory_inputs": incoming[int(index)],
        "direct_sensory_synapse_count": sum(x["synapse_count"] for x in incoming[int(index)]),
        "strongest_direct_effective_weight": max(
            (abs(x["effective_weight"]) for x in incoming[int(index)]), default=0.0),
    } for index in motor_indices]


class TemporalRecorder:
    """Read-only brain hook retaining bounded spikes and seven-neuron diagnostics."""
    def __init__(self, data, sensor_indices, motor_indices, pathway=None, distances=None):
        self.data, self.pathway = data, pathway
        self.sensors = set(int(x) for x in sensor_indices)
        self.motors = tuple(int(x) for x in motor_indices)
        self.motor_set = set(self.motors)
        self.distances = directed_distances(data, sensor_indices) if distances is None else distances
        self.downstream_events = []
        self.all_spike_events = []
        self._presynaptic = {x: set() for x in self.motors}
        self._exc_events = {x: 0 for x in self.motors}
        self._inh_events = {x: 0 for x in self.motors}
        self._peak_exc = {x: 0.0 for x in self.motors}
        self._peak_inh = {x: 0.0 for x in self.motors}
        self._peak_v = {x: -np.inf for x in self.motors}
        self._margin = {x: np.inf for x in self.motors}
        self._first_spike = {x: None for x in self.motors}

    def before_delivery(self, brain, arriving):
        for pre in arriving:
            a, b = brain.indptr[pre], brain.indptr[pre + 1]
            sign = brain.pre_sign[pre]
            if sign == 0:
                continue
            for slot in range(a, b):
                post = int(brain.indices[slot])
                if post in self.motor_set and brain.weights[slot] != 0:
                    self._presynaptic[post].add(int(pre))
                    if sign > 0:
                        self._exc_events[post] += 1
                    else:
                        self._inh_events[post] += 1

    def after_step(self, brain, fired):
        fired_set = set(int(x) for x in fired)
        time_ms = float(brain.time_ms)
        for index in fired_set:
            self.all_spike_events.append((time_ms, index))
            if index not in self.sensors:
                event = neuron_metadata(self.data, index, self.pathway)
                event.update(time_ms=time_ms,
                             hop_distance_from_selected_sensory_population=(
                                 None if self.distances[index] < 0 else int(self.distances[index])))
                self.downstream_events.append(event)
        for index in self.motors:
            self._peak_exc[index] = max(self._peak_exc[index], float(brain.g_exc[index]))
            self._peak_inh[index] = max(self._peak_inh[index], abs(float(brain.g_inh[index])))
            threshold = float(brain.config.v_threshold + brain.adaptation[index] +
                              brain.threshold_offset[index])
            if index in fired_set:
                self._first_spike[index] = self._first_spike[index] or time_ms
                self._peak_v[index] = max(self._peak_v[index], threshold)
                self._margin[index] = 0.0
            else:
                voltage = float(brain.v[index])
                self._peak_v[index] = max(self._peak_v[index], voltage)
                self._margin[index] = min(self._margin[index], threshold - voltage)

    def motor_results(self):
        return [asdict(MotorInputResult(
            int(self.data.body_ids[x]), x, len(self._presynaptic[x]), self._exc_events[x],
            self._inh_events[x], self._peak_exc[x], self._peak_inh[x], self._peak_v[x],
            self._margin[x], self._first_spike[x] is not None, self._first_spike[x]))
            for x in self.motors]


def classify_temporal(motor_results, peak_decoded_command, displacement, passive_displacement,
                      epsilon=1e-12):
    """Classify measured stages T1--T5; reachability alone is intentionally ignored."""
    spikes = any(x["threshold_crossed"] for x in motor_results)
    inputs = any(x["excitatory_events"] + x["inhibitory_events"] > 0 for x in motor_results)
    if not inputs:
        return "T1"
    if not spikes:
        return "T2"
    if abs(peak_decoded_command) <= epsilon:
        return "T3"
    if displacement <= passive_displacement + epsilon:
        return "T4"
    return "T5"
