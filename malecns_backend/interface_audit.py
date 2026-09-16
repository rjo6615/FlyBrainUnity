"""Build and validate the Milestone 3A MaleCNS interface inventory.

This module is deliberately an audit tool, not an embodiment interface.  It
decodes neuron annotations and the reference application's body map without
constructing or changing the neural runtime.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import sys

from .codec import decode_neurons
from .loader import DEFAULT_DATA_DIR, SIDE_NAMES


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "fly-brain-main"
OUTPUT = Path(__file__).with_name("interface_map.json")
SCHEMA_VERSION = 1

SOURCE_CONSUMERS = [
    {"source": "fly-brain-main/src/sim/senses.js", "symbol": "Senses.constructor/bindTypes/update", "categories": ["sensors"], "value": "physical state -> rate (Hz) -> Brain.setDriveOne", "transformation": "modality-specific modeled transduction; max-combine coincident drives", "effect": "external Poisson drive on identified sensory indices", "normal_reference_application": True},
    {"source": "fly-brain-main/src/sim/senses.js", "symbol": "CompoundEye.update", "categories": ["eyes"], "value": "MuJoCo ray luminance", "transformation": "300 ms log-luminance adaptation; clamp(40 + 90*(log(L+.001)-adapt), 0, 250) Hz", "effect": "photoreceptor external drive", "normal_reference_application": True},
    {"source": "fly-brain-main/src/sim/motor.js", "symbol": "Motor.readBrain/apply", "categories": ["muscles", "jump", "feeding"], "value": "cumulative spike-count increments", "transformation": "40 ms rate low-pass; population mean; saturating force-frequency curve", "effect": "MuJoCo controls, feeding scalar, jump trigger/program", "normal_reference_application": True},
    {"source": "fly-brain-main/src/sim/motor.js", "symbol": "Motor.constructor", "categories": ["unmappedMotor"], "value": "none", "transformation": "not consumed", "effect": "documentation-only inventory", "normal_reference_application": False},
    {"source": "fly-brain-main/scripts/prep_bodymap.py", "symbol": "module body-map compiler", "categories": ["muscles", "wing", "jump", "feeding", "sensors", "unmappedMotor", "eyes"], "value": "MaleCNS annotation rows and photoreceptor skeletons", "transformation": "manually authored rules over annotations; fitted/remapped visual axes", "effect": "writes bodymap.json", "normal_reference_application": False},
    {"source": "fly-brain-main/src/sim/flight.js", "symbol": "Flight", "categories": ["wing"], "value": "no bodymap wing population is read", "transformation": "engineered wing kinematics/aerodynamics", "effect": "wing pose and applied forces", "normal_reference_application": True},
    {"source": "fly-brain-main/src/sim/groups.js", "symbol": "buildGroups", "categories": ["sensors", "eyes", "feeding"], "value": "population membership", "transformation": "left/right aggregation", "effect": "telemetry groups", "normal_reference_application": True},
]

COMPATIBILITY = [
    {"malecns": "chordotonal T1/T2/T3 left/right", "flygym": "joint angles (tibia/femur-tibia)", "confidence": "STRONG CANDIDATE", "missing_transformation": "calibrated joint-angle population code", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "hair plate T1/T2/T3 left/right", "flygym": "joint angles (coxa)", "confidence": "STRONG CANDIDATE", "missing_transformation": "joint range and directional tuning calibration", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "campaniform T1/T2/T3 left/right", "flygym": "contact forces/load", "confidence": "STRONG CANDIDATE", "missing_transformation": "force projection, units, thresholds and tuning", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "tactile T1/T2/T3 left/right", "flygym": "segment contact forces / ground contact", "confidence": "STRONG CANDIDATE", "missing_transformation": "anatomical bristle location and adaptation model", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "MaleCNS photoreceptors with side/azimuth/elevation/class", "flygym": "compound-eye pixels (721 per eye in old backend)", "confidence": "STRONG CANDIDATE", "missing_transformation": "retinotopic resampling, spectral mapping, adaptation and timing", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "ORN glomerular populations", "flygym": "odor source identity, position, fly pose", "confidence": "STRONG CANDIDATE", "missing_transformation": "plume/concentration model and receptor response matrix", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "tarsal/labellar/pharyngeal gustatory populations", "flygym": "taste-zone identity plus end-effector/contact", "confidence": "STRONG CANDIDATE", "missing_transformation": "GRN class/location selection and concentration-response model", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "JO wind/gravity", "flygym": "body velocity plus environment wind / antenna contact", "confidence": "WEAK CANDIDATE", "missing_transformation": "antennal mechanics and JO subgroup directional tuning", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "haltere", "flygym": "body angular velocity/orientation", "confidence": "STRONG CANDIDATE", "missing_transformation": "wingbeat phase and haltere afferent tuning", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "JO auditory", "flygym": "no standard old-backend observation; authored vibration/song sources only", "confidence": "NO CURRENT MATCH", "missing_transformation": "physical sound/antennal vibration sensor", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "hygrosensory", "flygym": "none", "confidence": "NO CURRENT MATCH", "missing_transformation": "humidity field and receptor model", "provenance": ["ANNOTATION_DERIVED", "MODELED_TRANSDUCTION"]},
    {"malecns": "mapped leg motor-neuron populations", "flygym": "leg joint position actuators", "confidence": "STRONG CANDIDATE", "missing_transformation": "muscle dynamics, antagonistic mixing, moment arms and actuator calibration", "provenance": ["ANNOTATION_DERIVED", "MANUAL_BODYMAP_RULE", "MODELED_MOTOR_DECODER"]},
    {"malecns": "proboscis and antennal motor-neuron populations", "flygym": "old backend has no equivalent actuator surface", "confidence": "NO CURRENT MATCH", "missing_transformation": "body actuators/model support", "provenance": ["ANNOTATION_DERIVED", "MANUAL_BODYMAP_RULE"]},
    {"malecns": "descending-neuron weighted readouts", "flygym": "preprogrammed gait speed/turn commands", "confidence": "WEAK CANDIDATE", "missing_transformation": "an engineered behavior decoder; not a direct anatomical mapping", "provenance": ["ANNOTATION_DERIVED", "LITERATURE_DERIVED_MODEL", "ENGINEERED_CONTROL"]},
    {"malecns": "wing motor-neuron populations", "flygym": "old walking backend has no wing actuators", "confidence": "NO CURRENT MATCH", "missing_transformation": "a flight-capable body and muscle/force model", "provenance": ["ANNOTATION_DERIVED", "MANUAL_BODYMAP_RULE"]},
]


def _unique(values):
    return sorted({str(v) for v in values if str(v)})


def _annotations(indices, decoded, meta):
    _, body_ids, _, class_ids, nt_ids, superclass_ids, side_ids = decoded
    return {
        "types": _unique(meta["types"][i] for i in indices),
        "instances": _unique(meta["instances"][i] for i in indices),
        "classes": _unique(meta["classes"][class_ids[i]] for i in indices),
        "superclasses": _unique(meta["superclasses"][superclass_ids[i]] for i in indices),
        "sides": _unique(SIDE_NAMES[side_ids[i]] for i in indices),
        "neurotransmitters": _unique(meta["nts"][nt_ids[i]] for i in indices),
        "body_ids": [int(body_ids[i]) for i in indices],
    }


def _population(category, name, indices, metadata, decoded, meta):
    ann = _annotations(indices, decoded, meta)
    return {"category": category, "name": name, "count": len(indices),
            "dense_indices": list(indices), **ann, "bodymap_metadata": metadata,
            "source_consumers": [c["source"] + "::" + c["symbol"] for c in SOURCE_CONSUMERS if category in c["categories"]],
            "mapping_provenance": "ANNOTATION_DERIVED"}


def build_map(data_dir=DEFAULT_DATA_DIR):
    root = Path(data_dir)
    decoded = decode_neurons(root / "neurons.flyn")
    n = decoded[0]
    with (root / "meta.json").open(encoding="utf-8") as f:
        meta = json.load(f)
    with (root / "bodymap.json").open(encoding="utf-8") as f:
        bm = json.load(f)
    pops = []
    for category in ("muscles", "sensors", "eyes"):
        for ordinal, item in enumerate(bm[category]):
            name = item.get("name", item.get("side", str(ordinal)))
            md = {k: v for k, v in item.items() if k != "idx"}
            pops.append(_population(category, name, item["idx"], md, decoded, meta))
    for name, indices in bm["wing"].items():
        pops.append(_population("wing", name, indices, {}, decoded, meta))
    pops.append(_population("jump", "TTMn", bm["jump"], {}, decoded, meta))
    pops.append(_population("feeding", "feeding motor neurons", bm["feeding"], {}, decoded, meta))
    # unmappedMotor deliberately has no indices in bodymap; retain every compiler
    # inventory row without pretending it is an addressable population.
    for i, item in enumerate(bm["unmappedMotor"]):
        pops.append({"category": "unmappedMotor", "name": f'{item["type"]} {item["side"]}',
                     "count": item["n"], "dense_indices": [], "body_ids": [], "types": [item["type"]],
                     "instances": [], "classes": [], "superclasses": ["motor (compiler selection)"],
                     "sides": [item["side"]], "neurotransmitters": [], "bodymap_metadata": item,
                     "source_consumers": ["fly-brain-main/scripts/prep_bodymap.py::module body-map compiler"],
                     "mapping_provenance": "ANNOTATION_DERIVED_UNMAPPED_INVENTORY"})

    super_counts = Counter(meta["superclasses"][x] for x in decoded[5])
    class_counts = Counter(meta["classes"][x] for x in decoded[3])
    reference_inventory = []
    for path in sorted(REFERENCE.rglob("*")):
        if path.suffix not in {".js", ".mjs", ".py", ".md"} or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, 1):
            if "bodymap" in line.lower():
                reference_inventory.append({"source": path.relative_to(ROOT).as_posix(),
                                            "line": line_no, "text": line.strip()})
    category_summary = {}
    for category in bm:
        ps = [p for p in pops if p["category"] == category]
        addressed = {i for p in ps for i in p["dense_indices"]}
        category_summary[category] = {"population_records": len(ps), "member_entries": sum(p["count"] for p in ps),
                                      "addressed_dense_indices": sum(len(p["dense_indices"]) for p in ps),
                                      "distinct_addressed_neurons": len(addressed)}
    return {
        "schema_version": SCHEMA_VERSION,
        "purpose": "Milestone 3A audit only; no runtime embodiment mapping",
        "dataset": {"name": "Male CNS v1.0", "neuron_count": n, "bodymap_source": "fly-brain-main/public/data/bodymap.json"},
        "category_summary": category_summary,
        "populations": pops,
        "neuron_inventory": {"superclass_counts": dict(sorted(super_counts.items())), "class_counts": dict(sorted(class_counts.items())),
                             "descending_neurons": super_counts["descending_neuron"], "ascending_neurons": super_counts["ascending_neuron"]},
        "source_consumers": SOURCE_CONSUMERS,
        "bodymap_source_reference_inventory": reference_inventory,
        "compatibility": COMPATIBILITY,
        "provenance_vocabulary": ["CONNECTOME_DERIVED", "ANNOTATION_DERIVED", "MANUAL_BODYMAP_RULE", "MODELED_TRANSDUCTION", "BIOLOGICAL_PLUS_MODELED_LIF", "LITERATURE_DERIVED_MODEL", "CALIBRATED_MODEL_ASSUMPTION", "MODELED_MOTOR_DECODER", "ENGINEERED_CONTROL", "UNKNOWN"],
        "limitations": [
            "bodymap actuator and direction assignments are authored rules, not connectome edges",
            "unmappedMotor records contain aggregate counts but no dense indices/body IDs",
            "bodymap wing populations are compiled but are not consumed by the normal flight controller",
            "no calibrated MaleCNS-to-NeuroMechFly muscle dynamics, moment arms, or sensory transfer functions exist",
            "reference visual axes are inferred from skeleton entry points and manually remapped to a measured field of view",
            "sensory rate functions and DN behavior readouts are modeled/engineered rather than connectome-derived",
        ],
    }


def validate(report, data_dir=DEFAULT_DATA_DIR):
    errors = []
    n = report["dataset"]["neuron_count"]
    bodymap = json.loads((Path(data_dir) / "bodymap.json").read_text(encoding="utf-8"))
    for pop in report["populations"]:
        ix = pop["dense_indices"]
        if pop["category"] != "unmappedMotor" and not ix:
            errors.append(f'empty mapped population: {pop["category"]}/{pop["name"]}')
        if len(ix) != len(set(ix)):
            errors.append(f'duplicate dense index within {pop["category"]}/{pop["name"]}')
        if any(i < 0 or i >= n for i in ix):
            errors.append(f'out-of-range index in {pop["category"]}/{pop["name"]}')
        if len(ix) != len(pop["body_ids"]):
            errors.append(f'body ID resolution mismatch in {pop["category"]}/{pop["name"]}')
        if pop["category"] != "unmappedMotor" and not pop["sides"]:
            errors.append(f'missing available side metadata in {pop["category"]}/{pop["name"]}')
    expected = {"muscles": len(bodymap["muscles"]), "sensors": len(bodymap["sensors"]), "eyes": len(bodymap["eyes"]),
                "wing": len(bodymap["wing"]), "jump": 1, "feeding": 1, "unmappedMotor": len(bodymap["unmappedMotor"])}
    for cat, count in expected.items():
        actual = sum(p["category"] == cat for p in report["populations"])
        if actual != count:
            errors.append(f'{cat} population count {actual} != bodymap {count}')
    for consumer in report["source_consumers"]:
        if not (ROOT / consumer["source"]).is_file():
            errors.append(f'missing source reference: {consumer["source"]}')
    for reference in report["bodymap_source_reference_inventory"]:
        path = ROOT / reference["source"]
        if not path.is_file() or reference["line"] > len(path.read_text(encoding="utf-8").splitlines()):
            errors.append(f'invalid bodymap source occurrence: {reference["source"]}:{reference["line"]}')
    allowed = {"DIRECT", "STRONG CANDIDATE", "WEAK CANDIDATE", "NO CURRENT MATCH"}
    for mapping in report["compatibility"]:
        if mapping.get("confidence") not in allowed or not mapping.get("provenance"):
            errors.append(f'invalid candidate mapping: {mapping.get("malecns")}')
        if "ENGINEERED_CONTROL" in mapping["provenance"] and "CONNECTOME_DERIVED" in mapping["provenance"]:
            errors.append(f'engineered mapping mislabeled connectome-derived: {mapping["malecns"]}')
    return errors


def main():
    try:
        generated = build_map()
        if not OUTPUT.is_file():
            raise ValueError(f"missing generated artifact: {OUTPUT}")
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if stored != generated:
            raise ValueError("interface_map.json is stale; regenerate with build_map()")
        errors = validate(stored)
        if errors:
            raise ValueError("; ".join(errors))
        mapped = [p for p in stored["populations"] if p["dense_indices"]]
        distinct = {i for p in mapped for i in p["dense_indices"]}
        print("=== MaleCNS Sensory / Motor Interface Audit ===")
        for name, row in stored["category_summary"].items():
            print(f'{name}: {row["population_records"]:,} records, {row["member_entries"]:,} members, {row["distinct_addressed_neurons"]:,} distinct addressed neurons')
        print(f"Mapped populations: {len(mapped):,}; distinct referenced neurons: {len(distinct):,}")
        print("Source references, population counts, ID resolution, side metadata, duplicates, and provenance: PASS")
        print("MALECNS INTERFACE AUDIT PASSED")
        return 0
    except Exception as exc:
        print(f"Failure reason: {exc}", file=sys.stderr)
        print("MALECNS INTERFACE AUDIT FAILED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
