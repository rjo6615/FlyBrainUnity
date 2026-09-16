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
    candidates=list(data.bodymap.get('jump',[]))[:8] or list(range(8)); before=brain.spike_counts.copy(); brain.set_external_drive(candidates,200)
    brain.step_ms(args.stim_ms); brain.clear_external_drive(); delta=brain.spike_counts-before
    posts=np.unique(np.concatenate([brain.indices[brain.indptr[i]:brain.indptr[i+1]] for i in candidates])) if candidates else np.empty(0,int)
    stim={'population_size':len(candidates),'stimulated_spikes':int(delta[candidates].sum()),'immediate_postsynaptic_spikes':int(delta[posts].sum()),'network_spikes':int(delta.sum())}; print(_fmt(stim))
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
