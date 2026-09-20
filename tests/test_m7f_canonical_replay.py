import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from malecns_backend.embodiment import m7f_canonical_replay as m7f


def _write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def evidence(tmp_path, *, p=11, n=2):
    tmp_path.mkdir(parents=True, exist_ok=True)
    raw = tmp_path / "m7d_raw.npz"; md = tmp_path / "m7d_manifest.json"; sd = tmp_path / "m7d_summary.json"
    em = tmp_path / "m7e_manifest.json"; ea = tmp_path / "m7e_analysis.json"
    pt = np.arange(p, dtype=np.float64) * .1; nt = pt[5::5]
    assert len(nt) == n
    arrays = {}
    for cindex, condition in enumerate(m7f.CONDITIONS):
        for field, dtype, tail in m7f.FIELDS:
            count = p if field.startswith("physics_") else n
            if field == "physics_time_ms": value = pt
            elif field == "neural_time_ms": value = nt
            else: value = np.arange(count * max(1, int(np.prod(tail))), dtype=np.dtype(dtype)).reshape((count, *tail)) + cindex * 100
            arrays[f"{condition}__{field}"] = value.astype(dtype)
    np.savez(raw, **arrays)
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    declared = {key: {"shape": list(value.shape), "dtype": str(value.dtype)} for key, value in arrays.items()}
    _write_json(md, {"status": "COMPLETE", "schema": "M7D-CORRECTED-SPONTANEOUS.1",
                     "raw": {"sha256": digest, "byte_size": raw.stat().st_size}, "arrays": declared})
    milestones = {"D1_first_mapped_motor_activity_ms": 54.0, "D3_first_decoder_or_admitted_divergence_ms": 54.0,
                  "D4_first_action_divergence_ms": 54.0, "D5_first_admitted_joint_divergence_ms": 54.1,
                  "D6_first_whole_body_divergence_ms": 54.1, "D7_first_tibial_sensory_divergence_ms": 54.5,
                  "D8_first_delivered_sensory_drive_divergence_ms": 78.5,
                  "D9_first_downstream_cns_divergence_ms": 78.5, "D10_first_later_motor_divergence_ms": 157.0}
    _write_json(sd, {"status": "COMPLETE", "schema": "M7D-CORRECTED-SPONTANEOUS.1",
                     "raw_telemetry": {"sha256": digest}, "causal_milestones": milestones})
    _write_json(ea, {"status": "COMPLETE", "schema": "M7E-POSTRUN-ANALYSIS.1"})
    adigest = hashlib.sha256(ea.read_bytes()).hexdigest()
    _write_json(em, {"status": "COMPLETE", "schema": "M7E-POSTRUN-ANALYSIS.1",
        "analysis": {"sha256": adigest, "byte_size": ea.stat().st_size},
        "source": {"input_sha256": m7f.CANONICAL_SHA256}, "physics_transitions": 0, "neural_transitions": 0})
    return raw, md, sd, em, ea, arrays, digest


def validate(files, **changes):
    raw, md, sd, _, _, _, digest = files
    return m7f.validate_m7d(raw, md, sd, expected_sha=changes.get("sha", digest),
                            expected_size=changes.get("size", raw.stat().st_size), physics_count=11, neural_count=2)


def test_sha_and_byte_size_rejection(tmp_path):
    files = evidence(tmp_path)
    with pytest.raises(m7f.EvidenceError, match="byte-size"): validate(files, size=1)
    with pytest.raises(m7f.EvidenceError, match="SHA-256"): validate(files, sha="0" * 64)


@pytest.mark.parametrize("which", [1, 2])
def test_m7d_status_rejection(tmp_path, which):
    files = evidence(tmp_path); path = files[which]; value = json.loads(path.read_text()); value["status"] = "NOT_COMPLETE"; _write_json(path, value)
    with pytest.raises(m7f.EvidenceError, match="status COMPLETE"): validate(files)


def test_m7e_status_and_provenance_rejection(tmp_path):
    _, _, _, em, ea, _, _ = evidence(tmp_path); value = json.loads(em.read_text()); value["status"] = "FAILED"; _write_json(em, value)
    with pytest.raises(m7f.EvidenceError, match="status/schema"): m7f.validate_m7e(em, ea)


def test_missing_array_wrong_shape_and_nonfinite_rejected(tmp_path):
    files = evidence(tmp_path); raw, md = files[:2]
    manifest = json.loads(md.read_text()); manifest["arrays"].pop(next(iter(manifest["arrays"]))); _write_json(md, manifest)
    with pytest.raises(m7f.EvidenceError, match="lacks required"): validate(files)
    files = evidence(tmp_path / "shape"); raw, md, sd, _, _, arrays, _ = files
    key = f"{m7f.CONDITIONS[0]}__physics_body_position"; arrays[key] = arrays[key][:, :2]; np.savez(raw, **arrays)
    digest = hashlib.sha256(raw.read_bytes()).hexdigest(); manifest = json.loads(md.read_text()); manifest["raw"] = {"sha256": digest, "byte_size": raw.stat().st_size}; _write_json(md, manifest)
    summary = json.loads(sd.read_text()); summary["raw_telemetry"]["sha256"] = digest; _write_json(sd, summary)
    with pytest.raises(m7f.EvidenceError, match="shape/dtype"): m7f.validate_m7d(raw, md, sd, expected_sha=digest, expected_size=raw.stat().st_size, physics_count=11, neural_count=2)
    files = evidence(tmp_path / "finite"); raw, md, sd, _, _, arrays, _ = files
    arrays[f"{m7f.CONDITIONS[0]}__physics_body_position"][0, 0] = np.nan; np.savez(raw, **arrays)
    digest = hashlib.sha256(raw.read_bytes()).hexdigest(); manifest = json.loads(md.read_text()); manifest["raw"] = {"sha256": digest, "byte_size": raw.stat().st_size}; manifest["arrays"] = {k:{"shape":list(v.shape),"dtype":str(v.dtype)} for k,v in arrays.items()}; _write_json(md, manifest)
    summary = json.loads(sd.read_text()); summary["raw_telemetry"]["sha256"] = digest; _write_json(sd, summary)
    with pytest.raises(m7f.EvidenceError, match="nonfinite"): m7f.validate_m7d(raw, md, sd, expected_sha=digest, expected_size=raw.stat().st_size, physics_count=11, neural_count=2)


def test_coordinate_transform():
    np.testing.assert_array_equal(m7f.flygym_to_unity([10., 20., 30.]), [1., 3., 2.])


def test_binary_round_trip_is_exact_deterministic_and_preserves_conditions(tmp_path):
    files = evidence(tmp_path); arrays = files[5]
    enabled = m7f.serialize_condition(arrays, m7f.CONDITIONS[0]); disabled = m7f.serialize_condition(arrays, m7f.CONDITIONS[1])
    assert enabled == m7f.serialize_condition(arrays, m7f.CONDITIONS[0]); assert enabled != disabled
    parsed = m7f.parse_replay(enabled)
    for field, _, _ in m7f.FIELDS:
        assert np.array_equal(parsed[field], arrays[f"{m7f.CONDITIONS[0]}__{field}"])


def test_neural_alignment_and_milestone_import_and_manifest_hash(tmp_path):
    files = evidence(tmp_path); arrays, _, summary = validate(files); em = m7f.validate_m7e(files[3], files[4])[0]
    artifact = tmp_path / "m7f_enabled_replay.bin"; artifact.write_bytes(m7f.serialize_condition(arrays, m7f.CONDITIONS[0]))
    manifest = m7f.build_manifest(arrays, summary, em, [artifact], m7f.contact_audit())
    assert manifest["milestones"]["D7_first_tibial_sensory_divergence_ms"] == 54.5
    assert manifest["artifacts"][0]["sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert np.array_equal(arrays[f"{m7f.CONDITIONS[0]}__neural_time_ms"], arrays[f"{m7f.CONDITIONS[0]}__physics_time_ms"][5::5])


def test_joint_names_and_contact_fail_closed():
    assert len(m7f.JOINT_NAMES) == 42 and m7f.JOINT_NAMES[0] == "joint_LFCoxa"
    audit = m7f.contact_audit(); assert audit["classification"] == "CONTACT_IDENTITY_MAPPING_UNRESOLVED"
    assert not audit["contacts_available"] and len(audit["unresolved_channels"]) == 36
    assert all(x["associated_leg"] == "UNKNOWN" for x in audit["exact_channel_ordering"])


def test_overwrite_protection(tmp_path):
    _write_json(tmp_path / "m7f_manifest.json", {"status": "CANONICAL_REPLAY_EXPORT_COMPLETE"})
    with pytest.raises(FileExistsError): m7f.ensure_output_available(tmp_path)


def test_export_synthetic_and_no_pickle(tmp_path):
    files = evidence(tmp_path / "evidence"); out = tmp_path / "out"
    manifest = m7f.export(raw_path=files[0], m7d_manifest=files[1], m7d_summary=files[2],
        m7e_manifest_path=files[3], m7e_analysis_path=files[4], output_dir=out,
        expected_sha=files[6], expected_size=files[0].stat().st_size, physics_count=11, neural_count=2)
    assert manifest["physics_transitions"] == manifest["neural_transitions"] == 0
    assert (out / "m7f_manifest.json").is_file() and all((out / name).is_file() for name in m7f.FILE_NAMES)
    source = Path(m7f.__file__).read_text()
    assert "allow_pickle=False" in source and "allow_pickle=True" not in source


def test_exporter_has_no_simulation_or_neural_stepping_calls():
    import ast
    tree = ast.parse(Path(m7f.__file__).read_text())
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute): calls.append(node.func.attr)
            elif isinstance(node.func, ast.Name): calls.append(node.func.id)
    assert not ({"step", "mj_step"} & set(calls))
