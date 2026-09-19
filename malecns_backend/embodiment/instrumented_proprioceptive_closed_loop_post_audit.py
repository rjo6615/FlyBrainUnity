"""Deterministic M5D-5D per-neuron and directed-path telemetry reducer."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def divergent_neurons(body_ids, times, left_state, right_state, left_spikes,
                      right_spikes, after_ms, excluded=()):
    """Return exact first divergence and cumulative paired spike counts."""
    import numpy as np
    excluded = set(map(int, excluded)); result = []
    mask = np.asarray(times) > after_ms
    for index in np.flatnonzero(np.any(left_state[mask] != right_state[mask], axis=0) |
                               np.any(left_spikes[mask] != right_spikes[mask], axis=0)):
        if int(index) in excluded: continue
        state_at = np.flatnonzero(mask & np.any(left_state[:, index:index+1] != right_state[:, index:index+1], axis=1))
        spike_at = np.flatnonzero(mask & (left_spikes[:, index] != right_spikes[:, index]))
        enabled_count = int(left_spikes[mask, index].sum())
        disabled_count = int(right_spikes[mask, index].sum())
        result.append({"dense_index": int(index), "body_id": int(body_ids[index]),
            "first_state_divergence_ms": float(times[state_at[0]]) if len(state_at) else None,
            "first_spike_divergence_ms": float(times[spike_at[0]]) if len(spike_at) else None,
            "enabled_spike_count": enabled_count,
            "disabled_spike_count": disabled_count,
            "spike_count_difference": enabled_count-disabled_count})
    return result


def reachability(data, sources, targets, max_depth=5):
    """Traverse MaleCNS CSR in its documented pre -> post orientation."""
    target_set=set(map(int, targets)); frontier=set(map(int,sources)); seen=set(frontier); out={}
    for depth in range(1,max_depth+1):
        nxt=set()
        for pre in frontier:
            nxt.update(map(int, data.target_indices[data.row_ptr[pre]:data.row_ptr[pre+1]]))
        reached=sorted(nxt & target_set)
        out[str(depth)]={"source_neurons":len(sources), "reachable_mapped_motor_dense_indices":reached,
            "reachable_mapped_motor_neurons":len(reached), "shortest_path_length":depth if reached else None}
        frontier=nxt-seen; seen.update(nxt)
    return out


def audit_npz(path: Path, c10_ms: float, excluded=(), targets=(), data=None) -> dict[str, Any]:
    import numpy as np
    with np.load(path, allow_pickle=False) as z:
        rows=divergent_neurons(z["body_ids"], z["enabled_time_ms"], z["enabled_neural_state"],
            z["disabled_neural_state"], z["enabled_spike_events"], z["disabled_spike_events"], c10_ms, excluded)
    sources=[x["dense_index"] for x in rows]
    return {"post_feedback_source_set":rows,
        "anatomical_reachability":reachability(data,sources,targets) if data is not None else None,
        "anatomical_is_not_dynamic_recruitment":True}
