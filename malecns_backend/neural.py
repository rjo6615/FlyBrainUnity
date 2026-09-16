"""CPU implementation of the calibrated MaleCNS LIF model.

The equations and ordering in this module are a literal port of ``src/lif.js``.
CSR rows are presynaptic and entries in a row are postsynaptic targets.
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path

import numpy as np


NT_SIGN = np.asarray([0, 1, -1, -1, 1, 1, 1, -1], dtype=np.float32)
NT_NAMES = ("unknown", "acetylcholine", "GABA", "glutamate", "dopamine",
            "serotonin", "octopamine", "histamine")


@dataclass(frozen=True)
class ModelConfig:
    # lif.js DEFAULTS, overridden below where brainmodel.js/brain_params.json do so.
    dt: float = .5
    v_rest: float = -52
    v_threshold: float = -45
    v_reset: float = -52
    tau_mem: float = 20
    tau_syn: float = 5
    refractory_ms: float = 3.76
    delay_ms: float = 1.8
    psp_scale: float = .55
    trace_tau: float = 30
    adaptation_increment: float = 0
    adaptation_tau: float = 100
    depression_u: float = 0
    depression_tau: float = 200
    min_synapses: int = 6
    size_alpha: float = .609
    max_size_scale: float = 20
    boost_cap: float = 1
    conductance_based: bool = True
    e_exc: float = 0
    e_inh: float = -76.382
    inhibitory_gain: float = .606
    graded_sign: bool = True
    sensory_mask: bool = True
    neuromodulation: bool = True
    kc_threshold_offset: float = 10.887
    lamina_bias: float = 5.281

    @classmethod
    def calibrated(cls, path=None):
        """Read authoritative checked-in calibration rather than trusting prompt values."""
        path = Path(path or Path(__file__).parents[1] / "fly-brain-main/public/data/brain_params.json")
        raw = json.loads(path.read_text())
        mapping = {"coba": "conductance_based", "wSyn": "psp_scale", "sizeAlpha": "size_alpha",
                   "kcThreshold": "kc_threshold_offset", "inhGain": "inhibitory_gain",
                   "eInh": "e_inh", "minSyn": "min_synapses", "adaptInc": "adaptation_increment",
                   "tRef": "refractory_ms", "laminaBias": "lamina_bias", "neuromod": "neuromodulation"}
        values = {mapping[k]: v for k, v in raw.items() if k in mapping}
        return cls(**values)


def region_scales(data, config):
    names = data.superclasses
    regions = np.fromiter((0 if __import__('re').match(r"^(ol_|visual_projection|visual_centrifugal)", names[x])
                           else 2 if __import__('re').match(r"^(vnc_|descending|ascending|sensory_ascending|sensory_descending|efferent_)", names[x])
                           else 1 for x in data.superclass_ids), np.uint8, data.neuron_count)
    size = np.asarray(data.neuron_sizes, dtype=np.float32)
    med = np.asarray([np.median(size[(regions == r) & (size > 0)]) for r in range(3)], np.float32)
    ratio = np.where(size > 0, size / med[regions], 1)
    ratio = np.clip(ratio, 1 / config.max_size_scale, config.max_size_scale)
    return np.minimum(config.boost_cap, ratio ** -config.size_alpha).astype(np.float32), regions, med


class MaleCNSBrain:
    """Contiguous-array, event-driven CPU reference runtime."""
    def __init__(self, data, config=None, *, effective_weights=None, pre_sign=None):
        self.data = data
        self.config = config or ModelConfig.calibrated()
        p = self.config; self.n = data.neuron_count
        self.indptr = np.asarray(data.row_ptr, dtype=np.int64)
        self.indices = np.asarray(data.target_indices, dtype=np.int32)
        counts = np.asarray(data.synapse_counts, dtype=np.float32)
        scale, self.region, self.region_medians = region_scales(data, p)
        sensory = np.fromiter(("sensory" in data.superclasses[x] for x in data.superclass_ids), bool, self.n)
        self.sensory = sensory
        if effective_weights is None:
            valid = counts >= p.min_synapses
            if p.sensory_mask: valid &= ~sensory[self.indices]
            w = np.where(valid, counts * scale[self.indices], 0).astype(np.float32)
        else: w = np.asarray(effective_weights, dtype=np.float32)
        nt = np.asarray(data.neurotransmitter_ids, dtype=np.intp)
        sign = np.asarray(data.nt_signs if p.graded_sign else NT_SIGN[nt], np.float32).copy() if pre_sign is None else np.asarray(pre_sign, np.float32).copy()
        if p.neuromodulation:
            sign[np.fromiter((str(t).startswith("OA-") for t in data.types), bool, self.n)] = 0
        self.pre_sign = sign
        if p.inhibitory_gain != 1:
            for pre in np.flatnonzero(sign < 0):
                w[self.indptr[pre]:self.indptr[pre+1]] *= p.inhibitory_gain
        self.weights = w
        self.v = np.empty(self.n, np.float32); self.g_exc = np.zeros(self.n, np.float32); self.g_inh = np.zeros(self.n, np.float32)
        self.refractory = np.zeros(self.n, np.float32); self.activity_trace = np.zeros(self.n, np.float32)
        self.adaptation = np.zeros(self.n, np.float32); self.depression_resource = np.ones(self.n, np.float32)
        self.bias = np.zeros(self.n, np.float32); self.threshold_offset = np.zeros(self.n, np.float32)
        self.external_drive = np.zeros(self.n, np.float32); self.spike_counts = np.zeros(self.n, np.uint32)
        classes = data.classes
        self.threshold_offset[np.fromiter((classes[x] == "Kenyon_Cell" for x in data.class_ids), bool, self.n)] = p.kc_threshold_offset
        self.bias[np.fromiter((bool(__import__('re').match(r"^L[1-5]$", str(t))) for t in data.types), bool, self.n)] = p.lamina_bias
        self.delay_steps = max(1, round(p.delay_ms / p.dt)); self._ring = [[] for _ in range(self.delay_steps + 1)]; self._head = 0
        self.reset(1)

    def reset(self, seed=1):
        self.rng = np.random.default_rng(seed); p = self.config
        self.v.fill(p.v_rest); self.g_exc.fill(0); self.g_inh.fill(0); self.refractory.fill(0)
        self.activity_trace.fill(0); self.adaptation.fill(0); self.depression_resource.fill(1); self.spike_counts.fill(0)
        self._ring = [[] for _ in range(self.delay_steps + 1)]; self._head = 0; self.time_ms = 0.; self._last_spikes = np.empty(0, np.int32)

    def set_external_drive(self, indices, rates_or_drive): self.external_drive[np.asarray(indices, dtype=np.intp)] = rates_or_drive
    def clear_external_drive(self): self.external_drive.fill(0)

    def _deliver(self, arriving):
        p = self.config
        for pre in arriving:                 # sparse in spikes, never loops over all 6.2M edges
            s = np.float32(self.pre_sign[pre] * p.psp_scale * self.depression_resource[pre])
            if s == 0: continue
            self.depression_resource[pre] -= p.depression_u * self.depression_resource[pre]
            a, b = self.indptr[pre:pre + 2]; targets = self.indices[a:b]; values = self.weights[a:b] * s
            np.add.at(self.g_exc if s > 0 else self.g_inh, targets, values)

    def step(self):
        p = self.config; self._deliver(self._ring[self._head]); self._ring[self._head] = []
        refractory = self.refractory > 0
        self.refractory[refractory] -= p.dt; self.v[refractory] = p.v_reset
        available = ~refractory
        forced = np.zeros(self.n, dtype=bool)
        driven = np.flatnonzero(available & (self.external_drive > 0))
        forced[driven] = self.rng.random(len(driven)) < self.external_drive[driven] * (p.dt / 1000)
        self.v[forced] = p.v_reset; self.refractory[forced] = p.refractory_ms
        integrate = available & ~forced
        if p.conductance_based:
            dv = (p.v_rest - self.v + self.g_exc * (p.e_exc-self.v)/(p.e_exc-p.v_rest) + self.g_inh * (self.v-p.e_inh)/(p.v_rest-p.e_inh) + self.bias) * (p.dt/p.tau_mem)
        else: dv = (p.v_rest-self.v+self.g_exc+self.g_inh+self.bias) * (p.dt/p.tau_mem)
        self.v[integrate] += dv[integrate].astype(np.float32)
        threshold = integrate & (self.v >= p.v_threshold + self.adaptation + self.threshold_offset)
        fired = np.flatnonzero(forced | threshold).astype(np.int32)
        self.v[threshold] = p.v_reset; self.refractory[threshold] = p.refractory_ms
        self.spike_counts[fired] += 1; self.activity_trace[fired] = 1; self.adaptation[fired] += p.adaptation_increment
        self.g_exc *= np.float32(math.exp(-p.dt/p.tau_syn)); self.g_inh *= np.float32(math.exp(-p.dt/p.tau_syn))
        self.activity_trace *= np.float32(math.exp(-p.dt/p.trace_tau)); self.adaptation *= np.float32(math.exp(-p.dt/p.adaptation_tau))
        self.depression_resource += (1-self.depression_resource) * np.float32(p.dt/p.depression_tau)
        slot = (self._head + len(self._ring)-1) % len(self._ring); self._ring[slot] = fired.tolist(); self._head = (self._head+1) % len(self._ring)
        self.time_ms += p.dt; self._last_spikes = fired; return fired

    def step_ms(self, duration_ms):
        if duration_ms < 0 or duration_ms % self.config.dt: raise ValueError("duration must be a nonnegative multiple of dt")
        return [self.step() for _ in range(round(duration_ms/self.config.dt))]
    def get_spikes(self): return self._last_spikes.copy()
    def population_rate(self, indices, window_ms):
        ix = np.asarray(indices, dtype=np.intp); return float(self.spike_counts[ix].sum()*1000/(len(ix)*window_ms))
    def diagnostics(self):
        finite = np.isfinite(self.v) & np.isfinite(self.g_exc) & np.isfinite(self.g_inh)
        return {"time_ms": self.time_ms, "spikes": int(self.spike_counts.sum()), "active_fraction": float(np.count_nonzero(self.spike_counts)/self.n),
                "mean_voltage": float(self.v.mean()), "min_voltage": float(self.v.min()), "max_voltage": float(self.v.max()), "nonfinite": int((~finite).sum())}

    def weight_examples(self, limit=5):
        nz = np.flatnonzero(self.weights)[:limit]; out=[]
        for k in nz:
            pre = int(np.searchsorted(self.indptr, k, side="right")-1); post=int(self.indices[k])
            out.append({"pre_body_id": int(self.data.body_ids[pre]), "post_body_id": int(self.data.body_ids[post]), "synapse_count": int(self.data.synapse_counts[k]),
                        "transmitter": self.data.neurotransmitters[self.data.neurotransmitter_ids[pre]], "sign": float(self.pre_sign[pre]),
                        "volume_factor_and_inh_gain": float(self.weights[k]/self.data.synapse_counts[k]), "effective_weight": float(self.weights[k]*self.pre_sign[pre]*self.config.psp_scale)})
        return out
