"""Validated, deterministic local NumPy cache for canonical MaleCNS artifacts."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from .loader import ARTIFACTS, DEFAULT_DATA_DIR, MaleCNSData, load_malecns

CACHE_VERSION = 1

def _fingerprints(root):
    result = {}
    for name in ARTIFACTS:
        p = Path(root)/name; h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
        result[name] = {"size": p.stat().st_size, "sha256": h.hexdigest()}
    return result

def create_cache(cache_dir, data_dir=DEFAULT_DATA_DIR):
    """Decode and validate canonical files first; never cache unvalidated input."""
    started=time.perf_counter(); data=load_malecns(data_dir, validate=True); decoded=time.perf_counter()-started
    root=Path(cache_dir); root.mkdir(parents=True, exist_ok=True)
    arrays={"body_ids":data.body_ids,"soma":data.soma,"class_ids":data.class_ids,"neurotransmitter_ids":data.neurotransmitter_ids,
            "superclass_ids":data.superclass_ids,"side_ids":data.side_ids,"row_ptr":data.row_ptr,"target_indices":data.target_indices,
            "synapse_counts":data.synapse_counts,"neuron_sizes":data.neuron_sizes,"nt_signs":data.nt_signs}
    for name,value in arrays.items(): np.save(root/f"{name}.npy", np.asarray(value), allow_pickle=False)
    metadata={"cache_version":CACHE_VERSION,"source":_fingerprints(data_dir),"types":data.types,"instances":data.instances,"classes":data.classes,
              "superclasses":data.superclasses,"neurotransmitters":data.neurotransmitters,"bodymap":data.bodymap,"artifact_sizes":data.artifact_sizes}
    (root/"metadata.json").write_text(json.dumps(metadata,separators=(",",":")))
    return {"canonical_load_seconds":decoded,"cache_creation_seconds":time.perf_counter()-started-decoded,
            "cache_bytes":sum(p.stat().st_size for p in root.iterdir() if p.is_file())}

def load_cache(cache_dir, data_dir=DEFAULT_DATA_DIR, mmap=True):
    started=time.perf_counter(); root=Path(cache_dir); meta=json.loads((root/"metadata.json").read_text())
    if meta["cache_version"] != CACHE_VERSION or meta["source"] != _fingerprints(data_dir): raise ValueError("stale or wrong MaleCNS cache")
    a=lambda name: np.load(root/f"{name}.npy", mmap_mode="r" if mmap else None, allow_pickle=False)
    body=a("body_ids")
    data=MaleCNSData(len(body),body,{int(v):i for i,v in enumerate(body)},a("soma"),a("class_ids"),a("neurotransmitter_ids"),a("superclass_ids"),a("side_ids"),
        meta["types"],meta["instances"],meta["classes"],meta["superclasses"],meta["neurotransmitters"],a("row_ptr"),a("target_indices"),a("synapse_counts"),
        a("neuron_sizes"),a("nt_signs"),meta["bodymap"],(),meta["artifact_sizes"])
    data.timings["cache_load"] = time.perf_counter()-started
    return data
