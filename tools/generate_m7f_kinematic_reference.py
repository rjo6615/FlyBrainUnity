#!/usr/bin/env python3
"""Generate M7F static kinematics and, optionally, cross-check native MuJoCo FK.

The ordinary path is dependency-free and preserves the frozen VIS1B artifact.  The
optional path reconstructs *the same Fly call made by M7D*, serializes that live
FlyGym model in memory (including FlyGym's edits), and calls only ``mj_forward``.
It deliberately never calls any simulation step method.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.resources
import inspect
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / "fly-brain-main/body/flybody/fruitfly.xml"
MANIFEST = ROOT / "FlyBrainUnity/Assets/StreamingAssets/M7FReplay/m7f_manifest.json"
REPLAY = ROOT / "FlyBrainUnity/Assets/StreamingAssets/M7FReplay/m7f_enabled_replay.bin"
OUTPUT = ROOT / "FlyBrainUnity/Assets/StreamingAssets/M7FValidation/m7f_frame0_kinematic_reference.json"
CROSSCHECK = ROOT / "m7f_mujoco_crosscheck.json"
FRAMES = (0, 540, 541, 785, 1210, 1570, 2500, 3980, 5000)
LEGS = (("LF", 1, "left"), ("LM", 2, "left"), ("LH", 3, "left"),
        ("RF", 1, "right"), ("RM", 2, "right"), ("RH", 3, "right"))
SUFFIX = ("Coxa", "Coxa_roll", "Coxa_yaw", "Femur", "Femur_roll", "Tibia", "Tarsus1")
EXPECTED_JOINTS = tuple(f"joint_{leg}{suffix}" for leg, _, _ in LEGS for suffix in SUFFIX)
FLYGYM_VERSION = "1.2.1"
MUJOCO_VERSION = "3.2.7"
FLYGYM_MJCF = "neuromechfly_seqik_kinorder_ypr.xml"


def mul(a, b):
    w, x, y, z = a; W, X, Y, Z = b
    return [w*W-x*X-y*Y-z*Z, w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W]


def rot(q, v): return mul(mul(q, [0., *v]), [q[0], -q[1], -q[2], -q[3]])[1:]
def axisq(axis, angle):
    s = math.sin(angle / 2)
    return [math.cos(angle / 2), axis[0]*s, axis[1]*s, axis[2]*s]


def vec(text, default): return [float(x) for x in text.split()] if text else list(default)
def add(a, b): return [x+y for x, y in zip(a, b)]
def sub(a, b): return [x-y for x, y in zip(a, b)]
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def length(v): return math.sqrt(dot(v, v))
def norm(q):
    n = length(q)
    return [x/n for x in q]


def rounded(v): return [round(float(x), 12) for x in v]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def arrays():
    manifest = json.loads(MANIFEST.read_text())
    layout = {x["name"]: x for x in manifest["binary"]["layout"]}
    raw = REPLAY.read_bytes(); n = manifest["frame_counts"]["physics"]
    def read(name, width):
        item = layout[name]
        flat = struct.unpack_from("<" + "d"*(n*width), raw, item["offset_bytes"])
        return [flat[i*width:(i+1)*width] for i in range(n)]
    return manifest, read("physics_body_position", 3), read("physics_body_orientation", 4), read("physics_joint_position", 42)


def element_index():
    thorax = ET.parse(XML).getroot().find("worldbody/body[@name='thorax']")
    return {body.attrib["name"]: body for body in thorax.iter("body")}


def evaluate(frame, root_p, root_q, qvalues, names, bodies):
    """Legacy dependency-free VIS1B evaluator (kept byte-stable by default)."""
    qi = dict(zip(names, qvalues)); records = []
    for code, tier, side in LEGS:
        body_names = [f"coxa_T{tier}_{side}", f"femur_T{tier}_{side}", f"tibia_T{tier}_{side}", f"tarsus_T{tier}_{side}"]
        p = list(root_p); q = list(root_q)
        canonical = ((f"joint_{code}Coxa_roll", f"joint_{code}Coxa_yaw", f"joint_{code}Coxa"),
                     (f"joint_{code}Femur_roll", f"joint_{code}Femur"), (f"joint_{code}Tibia",), (f"joint_{code}Tarsus1",))
        for si, (bn, jns) in enumerate(zip(body_names, canonical)):
            body = bodies[bn]; bp = vec(body.get("pos"), [0, 0, 0]); bq = norm(vec(body.get("quat"), [1, 0, 0, 0]))
            p = add(p, rot(q, bp)); q = mul(q, bq); pivot = list(p); joints_out = []
            axes = ((0, 0, 1), (0, 1, 0), (1, 0, 0)) if si == 0 else ((0, 1, 0), (1, 0, 0)) if si == 1 else ((1, 0, 0),)
            for joint_name, axis in zip(jns, axes):
                joints_out.append({"canonical_name": joint_name, "pivot": rounded(pivot), "axis": rounded(rot(q, axis))})
                q = norm(mul(q, axisq(axis, qi[joint_name])))
            if si < 3:
                endpoint = add(p, rot(q, vec(bodies[body_names[si+1]].get("pos"), [0, 0, 0])))
            else:
                geom = next(g for g in body.findall("geom") if g.get("name") == bn + "_collision")
                endpoint = add(p, rot(q, vec(geom.get("fromto"), [0, 0, 0, 0, 0, 0])[3:]))
            records.append({"leg": code, "segment": ("coxa", "femur", "tibia", "tarsus1")[si], "body": bn,
                "parent_body": "thorax" if si == 0 else body_names[si-1], "position": rounded(p),
                "orientation_wxyz": rounded(q), "endpoint": rounded(endpoint), "joints": joints_out})
    return records


def _name(mujoco, model, kind, index):
    return mujoco.mj_id2name(model, kind, int(index))


def _flygym_model():
    """Construct exactly M7D's Fly and return a native, in-memory MuJoCo model."""
    flygym = importlib.import_module("flygym")
    mujoco = importlib.import_module("mujoco")
    fv = importlib.metadata.version("flygym")
    mv = getattr(mujoco, "__version__", importlib.metadata.version("mujoco"))
    if (fv, mv) != (FLYGYM_VERSION, MUJOCO_VERSION):
        raise RuntimeError(f"requires FlyGym {FLYGYM_VERSION} / MuJoCo {MUJOCO_VERSION}, found {fv} / {mv}")

    signature = inspect.signature(flygym.Fly)
    variant = signature.parameters.get("xml_variant")
    if variant is None or variant.default != "seqik":
        raise RuntimeError(f"FlyGym Fly default model is not the M7D-proven seqik variant: {variant}")
    resource = importlib.resources.files("flygym").joinpath("data", "mjcf", FLYGYM_MJCF)
    if not resource.is_file():
        raise RuntimeError(f"authoritative FlyGym MJCF missing: {resource}")
    package_root = Path(flygym.__file__).resolve().parent
    stl_paths = sorted(package_root.joinpath("data").rglob("*.stl"))
    required_stls = {"Thorax.stl", "Head.stl", *(f"{leg}{part}.stl" for leg, _, _ in LEGS
        for part in ("Coxa", "Femur", "Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5"))}
    if not required_stls.issubset({path.name for path in stl_paths}):
        raise RuntimeError("installed FlyGym geometry is incomplete for the authoritative embodiment")

    placements = [f"{leg}{segment}" for leg, _, _ in LEGS for segment in
                  ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")]
    # This is byte-for-byte the scientific configuration in m7c_b4_stability._make_sim.
    # Delegate to the frozen construction function used by M7D.  In particular,
    # arena.spawn_entity supplies the root freejoint and namespace; serializing
    # fly.model alone would silently omit that essential part of the model.
    b4 = importlib.import_module("malecns_backend.embodiment.m7c_b4_stability")
    simulation = b4._make_sim(flygym, b4._surface())
    fly = getattr(simulation, "fly", None)
    if fly is None:
        fly = getattr(simulation, "_fly", None)
    recorder_names = tuple(getattr(fly, "actuated_joints", ()))
    if len(recorder_names) != 42:
        raise RuntimeError("cannot establish FlyGym actuated-joint order used by the M7D observation")
    arena = simulation.arena
    root = arena.root_element
    xml_bytes = root.to_xml_string()
    if isinstance(xml_bytes, bytes):
        xml_text = xml_bytes.decode("utf-8")
    else:
        xml_text = xml_bytes
    assets = root.get_assets()
    model = mujoco.MjModel.from_xml_string(xml_text, assets)
    provenance = {
        "flygym_version": fv, "mujoco_version": mv, "fly_class_source": inspect.getsourcefile(flygym.Fly),
        "fly_signature": str(signature), "xml_variant_default": variant.default,
        "installed_mjcf": str(resource), "installed_mjcf_sha256": hashlib.sha256(resource.read_bytes()).hexdigest(),
        "assembled_xml_sha256": hashlib.sha256(xml_text.encode()).hexdigest(),
        "installed_stl_assets": [{"path": str(path.relative_to(package_root)), "sha256": sha(path)} for path in stl_paths],
        "construction": {"init_pose": "tripod", "spawn_pos": [0.0, 0.0, 0.6045752232266313],
            "spawn_orientation": [0.0, 0.0, 0.0], "enable_adhesion": False, "control": "position",
            "contact_sensor_placements": placements},
        "assembly": "M7D's m7c_b4_stability._make_sim parsed seqik, applied FlyGym edits, and attached it to FlatTerrain in memory; no assets copied",
        "recorder_semantics": {
            "verified": recorder_names == EXPECTED_JOINTS,
            "m7d_recorder_expression": "measured = _joint_positions(obs); telemetry.record(... physics_joint_position=measured)",
            "m6c_extractor_expression": "np.asarray(obs['joints'], dtype=np.float64); joints[0] if ndim == 2 else joints",
            "flygym_observation_order": list(recorder_names),
            "meaning": "column i is obs['joints'] coordinate i, in Fly.actuated_joints order",
        },
    }
    return mujoco, model, provenance


def _id_by_base(mujoco, model, kind, count, expected):
    matches = [index for index in range(count)
               if (_name(mujoco, model, kind, index) or "").replace("\\", "/").rsplit("/", 1)[-1] == expected]
    if len(matches) != 1:
        raise RuntimeError(f"authoritative model maps {expected!r} {len(matches)} times, expected exactly once")
    return matches[0]


def _joint_mapping(mujoco, model, replay_names, *, recorder_semantics_verified):
    """Map recorder columns to scalar hinges without assuming model order."""
    if not recorder_semantics_verified:
        raise RuntimeError("M7D recorder semantics are unverified")
    if not replay_names or len(set(replay_names)) != len(replay_names):
        raise RuntimeError("canonical replay contains duplicate or missing joint names")
    rows = []
    hinge = int(mujoco.mjtJoint.mjJNT_HINGE)
    for canonical_index, name in enumerate(replay_names):
        jid = _id_by_base(mujoco, model, mujoco.mjtObj.mjOBJ_JOINT, model.njnt, name)
        joint_type = int(model.jnt_type[jid])
        if joint_type != hinge:
            raise RuntimeError(f"canonical joint {name!r} is not a scalar hinge")
        qadr = int(model.jnt_qposadr[jid]); bid = int(model.jnt_bodyid[jid])
        rows.append({"canonical_index": canonical_index, "canonical_name": name,
            "source_expression": "np.asarray(obs['joints'])[0 if ndim == 2 else ...]",
            "source_array_index": canonical_index, "mj_joint_id": int(jid),
            "mj_qpos_address": qadr, "mj_joint_type": "hinge",
            "mj_body_id": bid, "mj_body_name": _name(mujoco, model, mujoco.mjtObj.mjOBJ_BODY, bid)})
    qaddrs = [row["mj_qpos_address"] for row in rows]
    if len(set(qaddrs)) != len(qaddrs):
        raise RuntimeError("two canonical joints map to the same MuJoCo qpos address")
    return rows


def _validate_model(mujoco, model, replay_names, *, recorder_names=None,
                    recorder_semantics_verified=False):
    if tuple(replay_names) != EXPECTED_JOINTS:
        raise RuntimeError("canonical replay joint ordering is not the frozen FlyGym 42-position order")
    recorder_names = tuple(recorder_names or ())
    if recorder_names != tuple(replay_names):
        affected = [{"index": i,
                     "canonical": replay_names[i] if i < len(replay_names) else None,
                     "recorder": recorder_names[i] if i < len(recorder_names) else None}
                    for i in range(max(len(replay_names), len(recorder_names)))
                    if (replay_names[i] if i < len(replay_names) else None) !=
                       (recorder_names[i] if i < len(recorder_names) else None)]
        raise RuntimeError(f"CANONICAL_REPLAY_JOINT_SEMANTICS_MISMATCH: {affected}")
    rows = _joint_mapping(mujoco, model, replay_names,
                          recorder_semantics_verified=recorder_semantics_verified)
    ids = [row["mj_joint_id"] for row in rows]
    qaddrs = [row["mj_qpos_address"] for row in rows]
    free = [jid for jid in range(model.njnt) if int(model.jnt_type[jid]) == int(mujoco.mjtJoint.mjJNT_FREE)]
    if len(free) != 1 or int(model.jnt_qposadr[free[0]]) != 0:
        raise RuntimeError("authoritative model must contain exactly one root freejoint at qpos[0:7]")
    return ids, qaddrs, free[0], rows


def _print_mapping(rows):
    print("CANONICAL INDEX | CANONICAL NAME | MJ JOINT ID | MJ QPOS ADR | TYPE | BODY")
    for row in rows:
        print(f"{row['canonical_index']:>15} | {row['canonical_name']:<22} | "
              f"{row['mj_joint_id']:>11} | {row['mj_qpos_address']:>11} | "
              f"{row['mj_joint_type']} | {row['mj_body_id']}:{row['mj_body_name']}")
    print("MUJOCO QPOS ORDER")
    for row in sorted(rows, key=lambda item: item["mj_qpos_address"]):
        print(f"{row['mj_qpos_address']:>11} | {row['canonical_index']:>2} | {row['canonical_name']}")
    ordered = [r["mj_qpos_address"] for r in rows] == sorted(r["mj_qpos_address"] for r in rows)
    print(f"Canonical order matches MuJoCo qpos order: {'YES' if ordered else 'NO'}")
    print("Canonical order is explicitly and uniquely mappable by joint name: YES")
    print("M7D recorder semantics verified: YES")


def _mujoco_records(mujoco, model, data, joint_ids):
    records = []
    for leg, _, _ in LEGS:
        for index, segment in enumerate(("Coxa", "Femur", "Tibia", "Tarsus1")):
            body_name = leg + segment
            bid = _id_by_base(mujoco, model, mujoco.mjtObj.mjOBJ_BODY, model.nbody, body_name)
            parent = _name(mujoco, model, mujoco.mjtObj.mjOBJ_BODY, model.body_parentid[bid])
            next_name = leg + (("Femur", "Tibia", "Tarsus1", "Tarsus2")[index])
            next_id = _id_by_base(mujoco, model, mujoco.mjtObj.mjOBJ_BODY, model.nbody, next_name)
            body_joint_ids = [jid for jid in joint_ids if int(model.jnt_bodyid[jid]) == bid]
            records.append({"leg": leg, "segment": segment.lower(), "body": body_name, "parent_body": parent,
                "position": rounded(data.xpos[bid]), "orientation_wxyz": rounded(data.xquat[bid]),
                "endpoint": rounded(data.xpos[next_id]), "joints": [{"canonical_name": (_name(mujoco, model, mujoco.mjtObj.mjOBJ_JOINT, jid) or "").rsplit("/", 1)[-1],
                    "pivot": rounded(data.xanchor[jid]), "axis": rounded(data.xaxis[jid])} for jid in body_joint_ids]})
    return records


def _angle(a, b): return math.acos(max(-1.0, min(1.0, dot(a, b)/(length(a)*length(b)))))
def _qangle(a, b): return 2*math.acos(max(-1.0, min(1.0, abs(dot(norm(a), norm(b))))))


def _errors(static, reference):
    sb = {(x["leg"], x["segment"]): x for x in static}; rb = {(x["leg"], x["segment"]): x for x in reference}
    values = {key: [] for key in ("pivot_position", "axis_angular", "body_position", "body_orientation", "segment_endpoint")}
    for key, actual in rb.items():
        expected = sb[key]
        values["body_position"].append(length(sub(actual["position"], expected["position"])))
        values["body_orientation"].append(_qangle(actual["orientation_wxyz"], expected["orientation_wxyz"]))
        values["segment_endpoint"].append(length(sub(actual["endpoint"], expected["endpoint"])))
        sj = {j["canonical_name"]: j for j in expected["joints"]}
        for joint in actual["joints"]:
            if joint["canonical_name"] not in sj: raise RuntimeError("static evaluator and MuJoCo joint/body assignment differ")
            values["pivot_position"].append(length(sub(joint["pivot"], sj[joint["canonical_name"]]["pivot"])))
            values["axis_angular"].append(_angle(joint["axis"], sj[joint["canonical_name"]]["axis"]))
    return {key: {"maximum": max(vals), "rms": math.sqrt(sum(x*x for x in vals)/len(vals)),
                  "unit": "radian" if "angular" in key or "orientation" in key else "model_length"} for key, vals in values.items()}


def _classification(a, b, tolerance=1e-12):
    if a is None or b is None: return "MISSING"
    if a == b: return "EXACT_MATCH"
    try:
        av = [float(x) for x in a] if isinstance(a, (list, tuple)) else [float(a)]
        bv = [float(x) for x in b] if isinstance(b, (list, tuple)) else [float(b)]
        if len(av) == len(bv) and max(abs(x-y) for x, y in zip(av, bv)) <= tolerance: return "NUMERICALLY_EQUIVALENT"
    except (TypeError, ValueError): pass
    return "DIFFERENT"


def _model_comparison(mujoco, model, joint_ids):
    """Field-level MaleCNS/FlyGym comparison; emitted by authoritative Windows run."""
    old_bodies = element_index(); rows = []
    old_joint_names = {}
    for code, tier, side in LEGS:
        old_joint_names.update({f"joint_{code}Coxa": f"coxa_T{tier}_{side}", f"joint_{code}Coxa_roll": f"coxa_abduct_T{tier}_{side}",
            f"joint_{code}Coxa_yaw": f"coxa_twist_T{tier}_{side}", f"joint_{code}Femur": f"femur_T{tier}_{side}",
            f"joint_{code}Femur_roll": f"femur_twist_T{tier}_{side}", f"joint_{code}Tibia": f"tibia_T{tier}_{side}",
            f"joint_{code}Tarsus1": f"tarsus_T{tier}_{side}"})
    old_joints = {j.get("name"): (body, j) for body in old_bodies.values() for j in body.findall("joint")}
    for order, (canonical, jid) in enumerate(zip(EXPECTED_JOINTS, joint_ids)):
        bid = int(model.jnt_bodyid[jid]); body_name = _name(mujoco, model, mujoco.mjtObj.mjOBJ_BODY, bid)
        parent_name = _name(mujoco, model, mujoco.mjtObj.mjOBJ_BODY, model.body_parentid[bid])
        old = old_joints.get(old_joint_names[canonical]); old_body, old_joint = old if old else (None, None)
        old_parent = None
        if old_body is not None:
            old_parent = next((name for name, candidate in old_bodies.items() if old_body in list(candidate)), "thorax")
        fly_range = list(model.jnt_range[jid]) if bool(model.jnt_limited[jid]) else None
        old_hinge_order = list(old_body.findall("joint")).index(old_joint) if old_joint is not None else None
        fly_hinge_order = [x for x in range(model.njnt) if int(model.jnt_bodyid[x]) == bid].index(jid)
        fields = {
            "joint_name": (old_joint.get("name") if old_joint is not None else None, canonical),
            "parent_body": (old_parent, parent_name), "child_body": (old_body.get("name") if old_body is not None else None, body_name),
            "hinge_order": (old_hinge_order, fly_hinge_order), "joint_position": (vec(old_joint.get("pos"), [0, 0, 0]) if old_joint is not None else None, list(model.jnt_pos[jid])),
            "joint_axis": (vec(old_joint.get("axis"), [0, 0, 1]) if old_joint is not None else None, list(model.jnt_axis[jid])),
            "body_local_position": (vec(old_body.get("pos"), [0, 0, 0]) if old_body is not None else None, list(model.body_pos[bid])),
            "body_local_quaternion": (vec(old_body.get("quat"), [1, 0, 0, 0]) if old_body is not None else None, list(model.body_quat[bid])),
            "range": (vec(old_joint.get("range"), []) if old_joint is not None and old_joint.get("range") else None, fly_range),
        }
        rows.append({"canonical_name": canonical, "fields": {name: {"malecns": rounded(a) if isinstance(a, list) else a,
            "flygym": rounded(b) if isinstance(b, list) else b, "classification": _classification(a, b)} for name, (a, b) in fields.items()}})
    return rows


def verify_mujoco(pos, quat, joints, names, static_frames, output_path):
    mujoco, model, provenance = _flygym_model()
    recorder = provenance["recorder_semantics"]
    joint_ids, qaddrs, free_id, mapping = _validate_model(mujoco, model, names,
        recorder_names=recorder["flygym_observation_order"],
        recorder_semantics_verified=recorder["verified"])
    _print_mapping(mapping)
    data = mujoco.MjData(model); frame_results = []
    for frame, static in zip(FRAMES, static_frames):
        data.qpos[:] = 0
        data.qpos[:3] = pos[frame]; data.qpos[3:7] = norm(quat[frame])
        for address, value in zip(qaddrs, joints[frame]): data.qpos[address] = value
        mujoco.mj_forward(model, data)
        root_bid = int(model.jnt_bodyid[free_id])
        root_error = {"position": length(sub(data.xpos[root_bid], pos[frame])),
                      "orientation": _qangle(data.xquat[root_bid], quat[frame])}
        reference = _mujoco_records(mujoco, model, data, joint_ids)
        frame_results.append({"frame": frame, "root_error": root_error, "errors": _errors(static, reference),
                              "mujoco_reference": reference})
    metrics = ("pivot_position", "axis_angular", "body_position", "body_orientation", "segment_endpoint")
    overall = {metric: {"maximum": max(x["errors"][metric]["maximum"] for x in frame_results),
        "rms": math.sqrt(sum(x["errors"][metric]["rms"]**2 for x in frame_results)/len(frame_results)),
        "unit": frame_results[0]["errors"][metric]["unit"]} for metric in metrics}
    result = {"schema": "M7F-VIS1C-MUJOCO-CROSSCHECK.1", "status": "COMPLETE", "provenance": provenance,
        "model_validation": {"expected_mjcf": FLYGYM_MJCF, "canonical_joint_order": list(names),
            "mujoco_qpos_order": [row["canonical_name"] for row in sorted(mapping, key=lambda x: x["mj_qpos_address"])],
            "canonical_order_equals_mujoco_qpos_order": qaddrs == sorted(qaddrs),
            "canonical_name_qpos_mapping_unique": True, "m7d_recorder_semantics_verified": True,
            "joint_provenance_mapping": mapping, "root_freejoint_qpos_address": 0,
            "body_hierarchy_source": "compiled FlyGym model"},
        "malecns_comparison": _model_comparison(mujoco, model, joint_ids), "frames": frame_results, "overall": overall,
        "counters": {"mj_forward_calls": len(FRAMES), "mj_step_calls": 0, "physics_transitions": 0, "neural_transitions": 0}}
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify-mujoco", action="store_true")
    parser.add_argument("--crosscheck-output", type=Path, default=CROSSCHECK)
    args = parser.parse_args()
    manifest, pos, quat, joints = arrays(); names = manifest["joint_names"]; bodies = element_index()
    frames = [{"frame": frame, "time_ms": round(frame*.1, 1), "root_position": rounded(pos[frame]),
        "root_orientation_wxyz": rounded(quat[frame]), "segments": evaluate(frame, pos[frame], norm(quat[frame]), joints[frame], names, bodies)} for frame in FRAMES]
    out = {"schema": "m7f-kinematic-reference-v1", "purpose": "visualization validation only",
        "source_xml": str(XML.relative_to(ROOT)), "source_xml_sha256": sha(XML),
        "source_replay": str(REPLAY.relative_to(ROOT)), "source_replay_sha256": sha(REPLAY),
        "coordinate_convention": "frozen MJCF source coordinates and model units; quaternion wxyz", "frames": frames,
        "evaluation": {"method": "deterministic static MJCF tree forward kinematics", "mj_forward_calls": 0,
            "mj_step_calls": 0, "physics_transitions": 0, "MaleCNS_updates": 0}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    if args.verify_mujoco:
        args.crosscheck_output.parent.mkdir(parents=True, exist_ok=True)
        result = verify_mujoco(pos, quat, joints, names, [x["segments"] for x in frames], args.crosscheck_output)
        print(f"wrote {args.crosscheck_output}; model={result['provenance']['installed_mjcf']}; mj_forward={len(FRAMES)}; mj_step=0")
        # Package the compiled constants and native reference frames immediately,
        # so the one authoritative Windows command cannot leave Unity artifacts
        # out of sync with its cross-check.
        from build_m7f_vis2_artifacts import build, RIG, REFERENCE
        rig, reference = build(result)
        for path, value in ((RIG, rig), (REFERENCE, reference)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            print(f"wrote {path}")
    print(f"wrote {args.output}; frames={len(FRAMES)}; mj_step=0; physics transitions=0; MaleCNS updates=0")


if __name__ == "__main__": main()
