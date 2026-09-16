"""Command-line scientific audit of the headless MaleCNS neural runtime."""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from .cache import create_cache, load_cache
from .loader import process_memory_bytes
from .neural import MaleCNSBrain, ModelConfig

def _fmt(d): return json.dumps(d, indent=2, sort_keys=True)


def controlled_propagation_audit(brain, minimum_targets=6):
    """Trace one forced spike across real, non-masked edges and their delay.

    Selection is deliberately based only on stable graph data (lowest body ID
    with enough effective outgoing edges), rather than on whether a target can
    be made to spike.  A 2000 Hz drive forces exactly one spike at a 0.5 ms
    timestep through the normal DEBUG EXTERNAL STIMULUS code path.
    """
    chosen = None
    for pre in range(brain.n):
        a, b = brain.indptr[pre:pre + 2]
        edge_indices = np.arange(a, b, dtype=np.int64)
        edge_indices = edge_indices[brain.weights[a:b] != 0]
        if (brain.pre_sign[pre] != 0 and
                np.unique(brain.indices[edge_indices]).size >= minimum_targets):
            candidate = (int(brain.data.body_ids[pre]), pre, edge_indices)
            if chosen is None or candidate[0] < chosen[0]:
                chosen = candidate
    if chosen is None:
        raise RuntimeError(f"no presynaptic neuron has {minimum_targets} effective postsynaptic targets")
    _, pre, edge_indices = chosen
    # One record per immediate target. Canonical CSR normally has one edge per
    # pair; grouping also makes the trace correct for synthetic/multigraph data.
    target_edges = {}
    for edge in edge_indices:
        target_edges.setdefault(int(brain.indices[edge]), []).append(int(edge))
    selected = sorted(target_edges, key=lambda i: int(brain.data.body_ids[i]))[:8]
    target_edges = {target: target_edges[target] for target in selected}
    targets = np.asarray(selected, dtype=np.intp)

    brain.reset(1)
    before = {name: getattr(brain, name)[targets].copy() for name in ("v", "g_exc", "g_inh")}
    spike_counts_before = brain.spike_counts.copy()
    brain.set_external_drive([pre], 2000)  # probability 1 at calibrated dt=.5 ms
    fired = brain.step()
    brain.clear_external_drive()
    stimulated_spikes = int(brain.spike_counts[pre] - spike_counts_before[pre])
    if stimulated_spikes != 1 or pre not in fired:
        raise RuntimeError("DEBUG EXTERNAL STIMULUS did not produce exactly one traced spike")

    early_max = {"excitatory_state": 0.0, "inhibitory_state": 0.0}
    # Delivery occurs after delay_steps subsequent step calls. Check every
    # preceding state explicitly, rather than merely assuming the ring works.
    for _ in range(brain.delay_steps - 1):
        brain.step()
        early_max["excitatory_state"] = max(early_max["excitatory_state"], float(np.max(np.abs(brain.g_exc[targets] - before["g_exc"]))))
        early_max["inhibitory_state"] = max(early_max["inhibitory_state"], float(np.max(np.abs(brain.g_inh[targets] - before["g_inh"]))))
    brain.step()

    dv = brain.v[targets] - before["v"]
    de = brain.g_exc[targets] - before["g_exc"]
    di = brain.g_inh[targets] - before["g_inh"]
    spiked = brain.spike_counts[targets] > spike_counts_before[targets]
    transmitter = brain.data.neurotransmitters[brain.data.neurotransmitter_ids[pre]]
    sign = float(brain.pre_sign[pre])
    records = []
    for pos, target in enumerate(targets):
        edges = target_edges[int(target)]
        synapses = sum(int(brain.data.synapse_counts[e]) for e in edges)
        effective_weight = sum(float(brain.weights[e] * sign * brain.config.psp_scale) for e in edges)
        consistent = bool(np.all(np.isfinite((dv[pos], de[pos], di[pos], effective_weight))) and
                          ((sign > 0 and de[pos] > 0 and di[pos] == 0 and effective_weight > 0) or
                           (sign < 0 and di[pos] < 0 and de[pos] == 0 and effective_weight < 0)))
        records.append({
            "body_id": int(brain.data.body_ids[target]), "synapse_count": synapses,
            "transmitter": transmitter, "sign": sign, "effective_weight": effective_weight,
            "before": {"voltage": float(before["v"][pos]), "excitatory_state": float(before["g_exc"][pos]), "inhibitory_state": float(before["g_inh"][pos])},
            "delayed": {"voltage": float(brain.v[target]), "excitatory_state": float(brain.g_exc[target]), "inhibitory_state": float(brain.g_inh[target])},
            "delta_voltage": float(dv[pos]), "delta_excitatory_state": float(de[pos]), "delta_inhibitory_state": float(di[pos]),
            "response_consistent_with_sign_and_weight": consistent, "spiked": bool(spiked[pos]),
        })
    response = (de != 0) | (di != 0)
    return {
        "stimulated_body_ids": [int(brain.data.body_ids[pre])], "stimulated_neurons": 1,
        "stimulated_spikes": stimulated_spikes, "configured_delay_ms": brain.config.delay_ms,
        "scheduled_delay_steps": brain.delay_steps, "scheduled_delay_ms": brain.delay_steps * brain.config.dt,
        "pre_delay_steps_checked": brain.delay_steps - 1, "pre_delay_max_abs_delta": early_max,
        "immediate_postsynaptic_targets_examined": len(targets),
        "targets_receiving_nonzero_synaptic_response": int(np.count_nonzero(response)),
        "targets_with_finite_sign_consistent_response": sum(r["response_consistent_with_sign_and_weight"] for r in records),
        "targets_depolarized": int(np.count_nonzero(dv > 0)), "targets_hyperpolarized": int(np.count_nonzero(dv < 0)),
        "targets_spiked": int(np.count_nonzero(spiked)), "maximum_absolute_postsynaptic_voltage_delta": float(np.max(np.abs(dv))),
        "maximum_excitatory_state_delta": float(np.max(np.abs(de))), "maximum_inhibitory_state_delta": float(np.max(np.abs(di))),
        "targets": records,
    }

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--cache',default='.cache/malecns-v1'); ap.add_argument('--zero-ms',type=float,default=5); ap.add_argument('--stim-ms',type=float,default=10)
    args=ap.parse_args(argv); print('=== MaleCNS Neural Runtime Audit ==='); failures=[]; cache=Path(args.cache)
    print('\nModel configuration'); p=ModelConfig.calibrated(); print(_fmt(p.__dict__))
    print('\nGraph configuration')
    try:
        if not (cache/'metadata.json').exists():
            timing=create_cache(cache); print('Created cache:',_fmt(timing))
        data=load_cache(cache); print(_fmt({'neurons':data.neuron_count,'edges':data.edge_count,'warm_cache_seconds':data.timings['cache_load'],'cache_bytes':sum(x.stat().st_size for x in cache.iterdir())}))
        t=time.perf_counter(); brain=MaleCNSBrain(data,p); init=time.perf_counter()-t
    except Exception as exc:
        print('FAILED:',exc); print('\nMALECNS NEURAL RUNTIME FAILED'); return 1
    print('Weight examples:',_fmt(brain.weight_examples()))
    print('\nReference parity')
    # The detailed same-state Node fixture is also enforced by tests/test_neural_runtime.py.
    print('JS lif.js fixture: test harness installed; tolerance atol=rtol=2e-6. WASM ordering differences documented in README.')
    print('\nWhole-CNS zero-input test'); t=time.perf_counter(); brain.step_ms(args.zero_ms); elapsed=time.perf_counter()-t; zero=brain.diagnostics(); print(_fmt(zero))
    if zero['spikes'] != 0: failures.append('zero-input calibrated CNS unexpectedly spiked')
    print('\nControlled stimulation test (DEBUG EXTERNAL STIMULUS; not biological sensory input)')
    try:
        stim=controlled_propagation_audit(brain); print(_fmt(stim))
        if stim['pre_delay_max_abs_delta']['excitatory_state'] or stim['pre_delay_max_abs_delta']['inhibitory_state']:
            failures.append('synaptic response arrived before modeled delay')
        if not stim['targets_receiving_nonzero_synaptic_response']:
            failures.append('controlled spike produced no postsynaptic synaptic-state response')
        if not stim['targets_with_finite_sign_consistent_response']:
            failures.append('controlled spike produced no finite sign-consistent response')
        if not stim['maximum_absolute_postsynaptic_voltage_delta']:
            failures.append('controlled spike produced no postsynaptic membrane response')
    except Exception as exc:
        print('FAILED:',exc); failures.append('whole-CNS controlled propagation audit failed')
    print('\nNumerical health'); health=brain.diagnostics(); runaway=health['active_fraction']>.95; bounds=health['min_voltage'] < -200 or health['max_voltage'] > 100
    print(_fmt({**health,'runaway_or_synchronous':runaway,'voltage_out_of_bounds':bounds}));
    if health['nonfinite'] or runaway or bounds: failures.append('numerical health check failed')
    steps=args.zero_ms/p.dt; per=elapsed/steps; rss,peak=process_memory_bytes()
    print('\nPerformance'); print(_fmt({'initialization_seconds':init,'seconds_per_step':per,'steps_per_second':1/per,'simulated_ms_per_real_second':p.dt/per,'real_time_factor':p.dt/(per*1000),'rss_bytes':rss,'peak_rss_bytes':peak}))
    print('\nScientific provenance'); print('CONNECTOME-DERIVED: identities, CSR connectivity/counts, transmitter predictions, annotations, sizes.')
    print('MODELED: LIF equations, calibration, sign interpretation, cutoff, volume scaling, sensory masking, class physiology.')
    print('DEBUG INPUT: artificial Poisson forced spikes above; no natural behavior claim.')
    print('\nMALECNS NEURAL RUNTIME '+('FAILED\n- '+'\n- '.join(failures) if failures else 'PASSED')); return bool(failures)

if __name__ == '__main__': raise SystemExit(main())
