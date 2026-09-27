"""Implementation tests only; synthetic fixtures are not M8 evidence."""
from __future__ import annotations

import hashlib
import sys

import numpy as np
import pytest

from malecns_backend.embodiment import m8_lf_proximal_replay_extraction as extraction


def synthetic_source(dtype=np.float32):
    return np.arange(10_000 * 41, dtype=dtype).reshape(10_000, 41)


def test_selection_has_exact_rows_columns_shape_and_dtype():
    source = synthetic_source(np.float32)
    before = source.copy()
    selected = extraction.select_exact(source, np)
    assert selected.shape == (1000, 6)
    assert selected.dtype == source.dtype
    assert np.array_equal(selected[:, 0], source[::10, 5])
    assert np.array_equal(selected[37], source[370, [5, 12, 19, 26, 33, 40]])
    assert np.array_equal(source, before)


def test_validation_rejects_wrong_shape_and_nonfinite():
    with pytest.raises(extraction.ExtractionFailure, match="shape"):
        extraction.validate_selected(np.zeros((999, 6)), np.dtype("float64"), np)
    bad = np.zeros((1000, 6))
    bad[12, 3] = np.nan
    with pytest.raises(extraction.ExtractionFailure, match="nonfinite"):
        extraction.validate_selected(bad, bad.dtype, np)


def test_npy_round_trip_is_exact_and_source_unchanged(tmp_path):
    source = synthetic_source(np.int64)
    before = source.copy()
    path = tmp_path / "synthetic-selection.npy"
    np.save(path, extraction.select_exact(source, np), allow_pickle=False)
    replay = np.load(path, allow_pickle=False)
    extraction.validate_round_trip(replay, source, np)
    assert np.array_equal(replay, extraction.select_exact(source, np))
    assert np.array_equal(source, before)


def test_source_identity_failure_precedes_numpy_or_scientific_access(tmp_path, monkeypatch):
    source = tmp_path / "pointer"
    source.write_bytes(b"not an npz")
    addendum = tmp_path / "addendum.json"
    addendum.write_bytes(b"must not be read")
    monkeypatch.setitem(sys.modules, "numpy", None)
    with pytest.raises(extraction.ExtractionFailure, match="source identity"):
        extraction.identity_gates(source, addendum)


def test_addendum_identity_failure_precedes_scientific_access(tmp_path, monkeypatch):
    source = tmp_path / "synthetic-bytes"
    source.write_bytes(b"source")
    addendum = tmp_path / "addendum.json"
    addendum.write_bytes(b"wrong\r\n")
    monkeypatch.setattr(extraction, "SOURCE_SIZE", source.stat().st_size)
    monkeypatch.setattr(extraction, "SOURCE_SHA256", hashlib.sha256(source.read_bytes()).hexdigest())
    monkeypatch.setitem(sys.modules, "numpy", None)
    with pytest.raises(extraction.ExtractionFailure, match="addendum identity"):
        extraction.identity_gates(source, addendum)
