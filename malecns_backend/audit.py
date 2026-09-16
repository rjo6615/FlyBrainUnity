"""Command-line MaleCNS processed-artifact audit."""

import collections
import sys

from .loader import (DEFAULT_DATA_DIR, SIDE_NAMES, bodymap_population_count,
                     load_malecns, numeric_summary)


def _bytes(value):
    return f"{value / (1024 ** 2):,.2f} MiB ({value:,} bytes)"


def _categories(names, ids):
    counts = collections.Counter(ids)
    return ", ".join(f"{name or '<blank>'}={counts.get(i, 0):,}" for i, name in enumerate(names))


def main():
    print("=== MaleCNS v1.0 Artifact Audit ===")
    try:
        data = load_malecns()
        n, e, synapses, effective_edges, effective_synapses = data.validation_counts
        print("\n[Scientific provenance]")
        print("DATASET: Male CNS v1.0")
        print("BIOLOGICAL DATA: neuron identities; connectivity; synapse counts; annotations; "
              "transmitter predictions; neuron size")
        print("PROCESSING: traced-neuron filtering; >=3 stored graph cutoff")
        print("RUNTIME CALIBRATION TO BE USED LATER: >=5 connection cutoff")
        print("No modeled neural dynamics are being executed during this milestone.")

        print("\n[Decoded counts]")
        print(f"Traced neurons: {n:,}")
        print(f"Stored >=3 directed connections: {e:,}")
        print(f"Represented anatomical synapses: {synapses:,}")
        print(f"Effective >=5 directed connections: {effective_edges:,}")
        print(f"Effective >=5 represented synapses: {effective_synapses:,}")
        print(f"Synapse count range: {min(data.synapse_counts):,} .. {max(data.synapse_counts):,}")

        print("\n[CSR and orientation]")
        print("CSR: PASS (N+1 row pointers, monotonic, zero origin, E terminus, valid targets/weights)")
        print("Orientation: PASS (CSR row is presynaptic; target is postsynaptic)")
        for pre, post, count in data.orientation_examples:
            print(f"  {pre} -> {post}: {count} synapses")
        print("64-bit body ID round trips: PASS (first, last, 8 deterministic random neurons)")

        print("\n[Metadata]")
        print(f"Class categories ({len(data.classes)}): {_categories(data.classes, data.class_ids)}")
        print(f"Superclass categories ({len(data.superclasses)}): "
              f"{_categories(data.superclasses, data.superclass_ids)}")
        type_counts = collections.Counter(data.types)
        print(f"Cell types: {len(type_counts):,} distinct ({type_counts.get('', 0):,} blank assignments)")
        print(f"Sides ({len(SIDE_NAMES)}): {_categories(SIDE_NAMES, data.side_ids)}")
        print(f"Neurotransmitter categories ({len(data.neurotransmitters)}): "
              f"{_categories(data.neurotransmitters, data.neurotransmitter_ids)}")
        unknown = sum(value == 0 for value in data.neurotransmitter_ids)
        print(f"Known transmitter: {n - unknown:,}; unknown transmitter: {unknown:,}")

        print("\n[Float32 companion arrays]")
        for label, values in (("neuron_size.bin", data.neuron_sizes), ("ntsign.bin", data.nt_signs)):
            low, high, mean, nonfinite = numeric_summary(values)
            print(f"{label}: n={len(values):,}, min={low:.9g}, max={high:.9g}, "
                  f"mean={mean:.9g}, nonfinite={nonfinite:,}")

        print("\n[Bodymap]")
        invalid = sum(i < 0 or i >= n for i in data.bodymap_dense_indices)
        resolved_ids = {data.body_ids[i] for i in data.bodymap_dense_indices if 0 <= i < n}
        print(f"Top-level categories: {', '.join(data.bodymap)}")
        print(f"Mapped populations: {bodymap_population_count(data.bodymap):,}")
        print(f"Referenced neuron entries: {len(data.bodymap_dense_indices):,}")
        print(f"Distinct referenced body IDs after dense-index resolution: {len(resolved_ids):,}")
        print(f"Referenced IDs absent from traced-neuron table: {invalid:,}")
        print("Representation note: bodymap.json stores dense `idx` values, not raw 64-bit body IDs; "
              "the audit resolves each index to its body ID and back.")

        print("\n[Disk and memory]")
        for name, size in data.artifact_sizes.items():
            print(f"Disk {name}: {_bytes(size)}")
        for name, size in data.memory_sizes.items():
            print(f"Memory {name}: {_bytes(size)}")
        print(f"Peak process RAM: {_bytes(data.peak_ram_bytes)}")
        print(f"Final process RAM: {_bytes(data.final_ram_bytes)}")

        print("\n[Performance]")
        for name in ("neuron_decode", "graph_decode", "metadata_decode", "validation", "total"):
            print(f"{name.replace('_', ' ').title()}: {data.timings[name]:.3f} s")
        print("\nMALECNS ARTIFACT AUDIT PASSED")
        return 0
    except Exception as exc:
        print(f"\nFailure reason: {exc}", file=sys.stderr)
        print("MALECNS ARTIFACT AUDIT FAILED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
