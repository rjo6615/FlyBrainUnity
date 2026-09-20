#!/usr/bin/env python3
"""Build Unity-ready VIS2 artifacts from a COMPLETE native MuJoCo cross-check.

This program performs no kinematics and imports neither FlyGym nor MuJoCo.  It
packages constants and nine ``mj_forward`` results already emitted by the
authoritative exporter.  It fails closed rather than falling back to VIS1B.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from generate_m7f_kinematic_reference import arrays, rounded, FRAMES

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "m7f_mujoco_crosscheck.json"
RIG = ROOT / "FlyBrainUnity/Assets/StreamingAssets/M7FValidation/m7f_authoritative_rig.json"
REFERENCE = ROOT / "FlyBrainUnity/Assets/StreamingAssets/M7FValidation/m7f_mujoco_reference_frames.json"


def qconj(q):
    return [q[0], -q[1], -q[2], -q[3]]


def qmul(a, b):
    w, x, y, z = a; W, X, Y, Z = b
    return [w*W-x*X-y*Y-z*Z, w*X+x*W+y*Z-z*Y,
            w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W]


def rotate(q, v):
    return qmul(qmul(q, [0.0, *v]), qconj(q))[1:]


def sub(a, b): return [x-y for x, y in zip(a, b)]
def length(v): return math.sqrt(sum(x*x for x in v))


def build(source):
    if source.get("status") != "COMPLETE" or source.get("schema") != "M7F-VIS1C-MUJOCO-CROSSCHECK.1":
        raise RuntimeError("requires a COMPLETE native MuJoCo cross-check")
    validation = source["model_validation"]
    if not validation["canonical_name_qpos_mapping_unique"] or not validation["m7d_recorder_semantics_verified"]:
        raise RuntimeError("canonical replay semantics/mapping are not authoritative")

    mappings = {x["canonical_name"]: x for x in validation["joint_provenance_mapping"]}
    comparisons = {x["canonical_name"]: x for x in source["malecns_comparison"]}
    first = source["frames"][0]["mujoco_reference"]
    first_by_body = {x["body"]: x for x in first}
    bodies = []
    for record in first:
        names = [x["canonical_name"] for x in record["joints"]]
        rows = [comparisons[x] for x in names]
        # All joints on a body necessarily report the same compiled body constants.
        local_pos = rows[0]["fields"]["body_local_position"]["flygym"]
        local_quat = rows[0]["fields"]["body_local_quaternion"]["flygym"]
        if any(x["fields"]["body_local_position"]["flygym"] != local_pos or
               x["fields"]["body_local_quaternion"]["flygym"] != local_quat for x in rows):
            raise RuntimeError(f"inconsistent body constants for {record['body']}")
        world_q = record["orientation_wxyz"]
        endpoint_local = rotate(qconj(world_q), sub(record["endpoint"], record["position"]))
        joints = []
        for row in sorted(rows, key=lambda x: x["fields"]["hinge_order"]["flygym"]):
            name = row["canonical_name"]; mapping = mappings[name]; fields = row["fields"]
            joints.append({"name": name, "type": mapping["mj_joint_type"],
                "local_position": fields["joint_position"]["flygym"],
                "local_axis": fields["joint_axis"]["flygym"],
                "declaration_order": fields["hinge_order"]["flygym"],
                "canonical_replay_index": mapping["canonical_index"],
                "mj_joint_id": mapping["mj_joint_id"], "mj_qpos_address": mapping["mj_qpos_address"]})
        bodies.append({"name": record["body"], "parent_body": record["parent_body"].rsplit("/", 1)[-1],
            "local_position": local_pos, "local_quaternion_wxyz": local_quat,
            "segment_endpoint_local": rounded(endpoint_local), "joints": joints})

    provenance = source["provenance"]
    rig = {"schema": "M7F-VIS2-AUTHORITATIVE-RIG.1", "status": "AUTHORITATIVE_CONSTANTS_EXTRACTED",
        "provenance": {"flygym_version": provenance["flygym_version"], "mujoco_version": provenance["mujoco_version"],
            "mjcf_filename": validation["expected_mjcf"], "mjcf_sha256": provenance["installed_mjcf_sha256"],
            "assembled_xml_sha256": provenance["assembled_xml_sha256"],
            "source": "compiled FlyGym model attached exactly as M7D; extracted by native MuJoCo",
            "coordinate_convention": "MuJoCo RH Z-up [x,y,z] -> Unity LH Y-up [x,z,y]",
            "model_length_to_unity": 0.1, "model_length_unit": "millimetre presentation unit"},
        "canonical_joint_names": validation["canonical_joint_order"], "bodies": bodies}

    _, positions, orientations, replay_joints = arrays()
    name_index = {name: i for i, name in enumerate(validation["canonical_joint_order"])}
    # The freejoint moves FlyGym's spawned root; Thorax is its child and carries
    # a constant spawn-height offset. Recover that compiled constant from each
    # native frame (rather than silently treating the freejoint as Thorax).
    thorax_locals = []
    lf = next(body for body in bodies if body["name"] == "LFCoxa")
    for frame in source["frames"]:
        index = frame["frame"]
        coxa = next(body for body in frame["mujoco_reference"] if body["body"] == "LFCoxa")
        thorax_q = coxa["orientation_wxyz"]
        for joint in reversed(lf["joints"]):
            angle = replay_joints[index][name_index[joint["name"]]]
            thorax_q = qmul(thorax_q, qconj([math.cos(angle/2), *(x*math.sin(angle/2) for x in joint["local_axis"])]))
        thorax_q = qmul(thorax_q, qconj(lf["local_quaternion_wxyz"]))
        thorax_p = sub(coxa["position"], rotate(thorax_q, lf["local_position"]))
        root_q = orientations[index]; root_p = positions[index]
        thorax_locals.append((rotate(qconj(root_q), sub(thorax_p, root_p)), qmul(qconj(root_q), thorax_q)))
    base_p, base_q = thorax_locals[0]
    if max(length(sub(p, base_p)) for p, _ in thorax_locals) > 2e-9 or max(2*math.acos(min(1, abs(sum(x*y for x,y in zip(q, base_q))))) for _, q in thorax_locals) > 2e-7:
        raise RuntimeError("could not recover a constant root-to-Thorax compiled transform")
    rig["root_body"] = {"name": "Thorax", "parent_body": "freejoint_root",
        "local_position": rounded(base_p), "local_quaternion_wxyz": rounded(base_q)}

    refs = []
    for frame in source["frames"]:
        index = frame["frame"]
        if index not in FRAMES: raise RuntimeError(f"unexpected reference frame {index}")
        refs.append({"frame": index, "root_position": rounded(positions[index]),
            "root_orientation_wxyz": rounded(orientations[index]), "bodies": frame["mujoco_reference"]})
    if [x["frame"] for x in refs] != list(FRAMES): raise RuntimeError("native reference frame set/order is incomplete")
    reference = {"schema": "M7F-VIS2-MUJOCO-REFERENCE.1", "status": "NATIVE_MJ_FORWARD_COMPLETE",
        "source_crosscheck_schema": source["schema"], "frames": refs, "counters": source["counters"]}
    return rig, reference


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--rig-output", type=Path, default=RIG)
    parser.add_argument("--reference-output", type=Path, default=REFERENCE)
    args = parser.parse_args()
    rig, reference = build(json.loads(args.source.read_text(encoding="utf-8")))
    for path, value in ((args.rig_output, rig), (args.reference_output, reference)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__": main()
