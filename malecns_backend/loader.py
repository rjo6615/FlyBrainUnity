"""Validated, simulation-free in-memory representation of Male CNS v1.0."""

from dataclasses import dataclass, field
from pathlib import Path
from array import array
import json
import math
import mmap
import os
import random
import resource
import struct
import sys
import time

from .codec import decode_graph, decode_neurons

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "fly-brain-main" / "public" / "data"
ARTIFACTS = ("neurons.flyn", "graph.flyg", "neuron_size.bin", "ntsign.bin", "bodymap.json", "meta.json")
SIDE_NAMES = ("unknown", "left", "right", "midline")


@dataclass
class MaleCNSData:
    neuron_count: int
    body_ids: array
    body_id_to_index: dict
    soma: array
    class_ids: array
    neurotransmitter_ids: array
    superclass_ids: array
    side_ids: array
    types: list
    instances: list
    classes: list
    superclasses: list
    neurotransmitters: list
    row_ptr: array
    target_indices: array
    synapse_counts: array
    neuron_sizes: array
    nt_signs: array
    bodymap: dict
    bodymap_dense_indices: tuple
    artifact_sizes: dict
    timings: dict = field(default_factory=dict)
    memory_sizes: dict = field(default_factory=dict)
    peak_ram_bytes: int = 0
    final_ram_bytes: int = 0

    @property
    def edge_count(self):
        return len(self.target_indices)

    def dense_index(self, body_id):
        if isinstance(body_id, float):
            raise TypeError("body IDs must never be supplied as floating-point values")
        return self.body_id_to_index[int(body_id)]

    def body_id(self, dense_index):
        return self.body_ids[dense_index]


def _read_float32(path):
    result = array("f")
    with path.open("rb") as handle:
        result.fromfile(handle, path.stat().st_size // result.itemsize)
    if sys.byteorder != "little":
        result.byteswap()
    return result


def _bodymap_indices(bodymap):
    """Return indices from fields that prep_bodymap.py writes as neuron indices."""
    values = []
    values.extend(bodymap.get("jump", []))
    values.extend(bodymap.get("feeding", []))
    for population in bodymap.get("muscles", []):
        values.extend(population.get("idx", []))
    for population in bodymap.get("sensors", []):
        values.extend(population.get("idx", []))
    for population in bodymap.get("eyes", []):
        values.extend(population.get("idx", []))
    for population in bodymap.get("wing", {}).values():
        values.extend(population)
    return tuple(values)


def bodymap_population_count(bodymap):
    return (len(bodymap.get("muscles", [])) + len(bodymap.get("sensors", [])) +
            len(bodymap.get("eyes", [])) + len(bodymap.get("wing", {})) +
            int(bool(bodymap.get("jump"))) + int(bool(bodymap.get("feeding"))))


def current_rss_bytes():
    with open("/proc/self/statm", encoding="ascii") as handle:
        resident_pages = int(handle.read().split()[1])
    return resident_pages * os.sysconf("SC_PAGE_SIZE")


def peak_rss_bytes():
    # Linux ru_maxrss is KiB (unlike macOS, where it is bytes).
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def deep_size(value, seen=None):
    seen = set() if seen is None else seen
    identity = id(value)
    if identity in seen:
        return 0
    seen.add(identity)
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(deep_size(k, seen) + deep_size(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple, set)):
        size += sum(deep_size(item, seen) for item in value)
    return size


def load_malecns(data_dir=DEFAULT_DATA_DIR, validate=True):
    started = time.perf_counter()
    root = Path(data_dir)
    missing = [name for name in ARTIFACTS if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing MaleCNS artifacts: {', '.join(missing)}")
    artifact_sizes = {name: (root / name).stat().st_size for name in ARTIFACTS}

    t = time.perf_counter()
    count, body_ids, soma, classes, nts, superclasses, sides = decode_neurons(root / "neurons.flyn")
    neuron_time = time.perf_counter() - t
    t = time.perf_counter()
    graph_count, _, _, row_ptr, targets, weights = decode_graph(root / "graph.flyg")
    graph_time = time.perf_counter() - t
    t = time.perf_counter()
    with (root / "meta.json").open(encoding="utf-8") as handle:
        meta = json.load(handle)
    with (root / "bodymap.json").open(encoding="utf-8") as handle:
        bodymap = json.load(handle)
    neuron_sizes = _read_float32(root / "neuron_size.bin")
    nt_signs = _read_float32(root / "ntsign.bin")
    metadata_time = time.perf_counter() - t
    if graph_count != count:
        raise ValueError(f"FLYN neuron count {count} differs from FLYG count {graph_count}")
    body_index = {body_id: i for i, body_id in enumerate(body_ids)}
    data = MaleCNSData(
        count, body_ids, body_index, soma, classes, nts, superclasses, sides,
        meta["types"], meta["instances"], meta["classes"], meta["superclasses"], meta["nts"],
        row_ptr, targets, weights, neuron_sizes, nt_signs, bodymap,
        _bodymap_indices(bodymap), artifact_sizes,
    )
    data.timings.update(neuron_decode=neuron_time, graph_decode=graph_time, metadata_decode=metadata_time)
    if validate:
        t = time.perf_counter()
        validate_data(data, root)
        data.timings["validation"] = time.perf_counter() - t
    data.memory_sizes = {
        "neuron metadata": sum(map(deep_size, (data.soma, data.class_ids, data.neurotransmitter_ids,
                                                data.superclass_ids, data.side_ids, data.types, data.instances))),
        "body ID arrays and index": deep_size(data.body_ids) + deep_size(data.body_id_to_index),
        "CSR row pointers": deep_size(data.row_ptr),
        "CSR targets": deep_size(data.target_indices),
        "synapse counts": deep_size(data.synapse_counts),
        "neuron sizes": deep_size(data.neuron_sizes),
        "NT signs": deep_size(data.nt_signs),
        "bodymap": deep_size(data.bodymap),
    }
    data.timings["total"] = time.perf_counter() - started
    data.peak_ram_bytes = peak_rss_bytes()
    data.final_ram_bytes = current_rss_bytes()
    return data


def _flat_graph_samples(data, path):
    """Compare deterministic packed entries to the original flat processed table."""
    examples = []
    with path.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        n, e = struct.unpack_from("<II", raw, 0)
        if (n, e) != (data.neuron_count, data.edge_count):
            raise ValueError("flat graph header differs from decoded FLYG header")
        ptr_offset, target_offset = 8, 8 + (n + 1) * 4
        weight_offset = target_offset + e * 4
        candidates = [0, n // 4, n // 2, (3 * n) // 4, n - 1]
        for pre in candidates:
            start, end = data.row_ptr[pre], data.row_ptr[pre + 1]
            if start == end:
                continue
            slot = start + (end - start) // 2
            flat_start, flat_end = struct.unpack_from("<II", raw, ptr_offset + pre * 4)
            if (flat_start, flat_end) != (start, end):
                raise ValueError(f"orientation/source row mismatch at presynaptic index {pre}")
            flat_target = struct.unpack_from("<I", raw, target_offset + slot * 4)[0]
            flat_weight = struct.unpack_from("<H", raw, weight_offset + slot * 2)[0]
            if (flat_target, flat_weight) != (data.target_indices[slot], data.synapse_counts[slot]):
                raise ValueError(f"orientation/source entry mismatch at presynaptic index {pre}")
            examples.append((data.body_ids[pre], data.body_ids[flat_target], flat_weight))
    return examples


def validate_data(data, root=DEFAULT_DATA_DIR):
    errors = []
    n, e = data.neuron_count, data.edge_count
    if len(data.row_ptr) != n + 1: errors.append("row pointer length is not neuron_count + 1")
    if not data.row_ptr or data.row_ptr[0] != 0: errors.append("row_ptr[0] is not zero")
    if data.row_ptr and data.row_ptr[-1] != e: errors.append("row_ptr[-1] is not edge count")
    if any(a > b for a, b in zip(data.row_ptr, data.row_ptr[1:])): errors.append("row pointers decrease")
    if any(target >= n for target in data.target_indices): errors.append("target outside neuron table")
    if any(weight <= 0 for weight in data.synapse_counts): errors.append("nonpositive synapse count")
    if len(data.synapse_counts) != e: errors.append("target and synapse arrays differ in length")
    if len(data.neuron_sizes) != n: errors.append("neuron_size.bin does not contain one float32 per neuron")
    if len(data.nt_signs) != n: errors.append("ntsign.bin does not contain one float32 per neuron")
    if len(data.body_id_to_index) != n: errors.append("body IDs are not unique")
    if any(index < 0 or index >= n for index in data.bodymap_dense_indices): errors.append("bodymap contains unresolved dense index")
    sample = [0, n - 1] + random.Random(0x4D414C45).sample(range(1, n - 1), 8)
    for index in sample:
        if data.body_id(data.dense_index(data.body_id(index))) != data.body_id(index):
            errors.append(f"64-bit body ID round trip failed at {index}")
    if root and (Path(root) / "graph_w3.bin").exists():
        data.orientation_examples = _flat_graph_samples(data, Path(root) / "graph_w3.bin")
    else:
        errors.append("graph_w3.bin unavailable for graph orientation source comparison")
    expected = (165122, 10511038, 104213652, 6235682, 89731551)
    actual = (n, e, sum(data.synapse_counts),
              sum(weight >= 5 for weight in data.synapse_counts),
              sum(weight for weight in data.synapse_counts if weight >= 5))
    if actual != expected:
        errors.append(f"decoded count tuple {actual} != audited expectation {expected}")
    if errors:
        raise ValueError("MaleCNS validation failed:\n- " + "\n- ".join(errors))
    data.validation_counts = actual
    return actual


def numeric_summary(values):
    finite = [value for value in values if math.isfinite(value)]
    return min(finite), max(finite), math.fsum(finite) / len(finite), len(values) - len(finite)
