import hashlib
import json
from pathlib import Path

from malecns_backend.embodiment.m5d_tarsal_contact_load import (
    LEGS, build_audit, live_introspection, serialized_audit,
)

ROOT = Path(__file__).parents[1]
LOCKED = {
    "malecns_backend/embodiment/six_leg_map.json": "575186602ac1e5a6e3b2c6d680309880266f5d80e18fff44f989440f6cd0a4bc",
    "malecns_backend/embodiment/interface_output/full_leg_interface_audit.json": "758850ea659e49fd93a36a9606bea07a1d329739fbf6be8089060ee6d706c52e",
    "malecns_backend/embodiment/interface_output/m5b_proprioceptive_dissection.json": "9fd5cbac34273e4c37f06646a86b1a370ce2769515b58f7414a78c7ea95e0c91",
    "malecns_backend/embodiment/interface_output/m5b_multi_axis_coxa_audit.json": "1f68bfcc06dc5aa9c904fcd27ed8b9e08a1b8a8345611739896606ca247ec973",
    "malecns_backend/embodiment/interface_output/m5c_leg_sensory_inventory.json": "9909bbe8d6871f678f9bc90bd68403b442e786ff0443ec2396fe85ff8793fc81",
}


def test_exactly_twelve_m5c_unused_populations_are_consumed():
    audit = build_audit()
    populations = audit["biological_populations"]
    assert len(populations) == 12
    assert len({x["population_name"] for x in populations}) == 12
    assert {x["sensory_kind"] for x in populations} == {"contact", "load"}


def test_six_tactile_six_load_and_every_leg_once_per_mechanism():
    populations = build_audit()["biological_populations"]
    for mechanism in ("contact", "load"):
        selected = [x for x in populations if x["mechanism"] == mechanism]
        assert len(selected) == 6
        assert [x["leg"] for x in selected] == list(LEGS)


def test_contact_and_load_are_distinct_but_not_independent_measurements():
    audit = build_audit()
    assert audit["contact_vs_load"] == {
        "separable_concepts": True, "independent_measurements": False,
        "finding": "contact can be thresholded from force, while load uses its magnitude/direction; both derive from contact_forces",
    }
    for row in audit["summary"]["per_leg"]:
        assert row["CONTACT PHYSICAL SIGNAL"] != row["LOAD PHYSICAL SIGNAL"]
        assert row["contact"]["raw_observable"] == row["load"]["raw_observable"]


def test_physical_metadata_cannot_create_tuning_or_joint_angle_mapping():
    for population in build_audit()["biological_populations"]:
        assert population["joint_angle_mapped"] is False
        assert population["explicit_thresholds_or_ranges"] == {}
        assert population["magnitude_or_tuning_fields"] == {
            "tuning": None, "preferred_angle": None, "range": None}


def test_summary_classification_and_deterministic_json_serialization():
    first, second = build_audit(), build_audit()
    assert first["summary"] | {} == second["summary"]
    assert {k: first["summary"][k] for k in (
        "biological_population_count", "tactile_population_count", "load_population_count",
        "direct_physical_correspondence", "modeled_transduction_required", "proxy_only",
        "no_physical_signal", "physical_signal_ready", "physical_proxy_ready",
        "needs_physical_model")} == {
            "biological_population_count": 12, "tactile_population_count": 6,
            "load_population_count": 6, "direct_physical_correspondence": 0,
            "modeled_transduction_required": 6, "proxy_only": 6,
            "no_physical_signal": 0, "physical_signal_ready": 6,
            "physical_proxy_ready": 6, "needs_physical_model": 0,
        }
    assert serialized_audit(first) == serialized_audit(second)
    assert json.loads(serialized_audit(first)) == first


def test_non_live_has_no_runtime_claim_and_no_intervention():
    audit = build_audit()
    assert audit["runtime_observable_state"]["status"] == "NOT_RUN"
    assert not any(audit["non_intervention"].values())


def test_live_introspection_resets_but_never_steps_neural_or_controller_state(monkeypatch):
    calls = {"reset": 0, "step": 0, "controller": 0, "neural": 0, "closed": 0}

    class FakeValue:
        shape = (36, 3)

    class FakeSimulation:
        observation_space = "fake-space"

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def reset(self):
            calls["reset"] += 1
            return {"contact_forces": FakeValue()}, {"reset": True}

        def step(self, action):
            calls["step"] += 1
            raise AssertionError("read-only introspection must not step")

        def close(self):
            calls["closed"] += 1

    class FakeFlyGym:
        SingleFlySimulation = FakeSimulation

        @staticmethod
        def Fly(**kwargs):
            return kwargs

    monkeypatch.setattr(
        "malecns_backend.embodiment.m5d_tarsal_contact_load.importlib.import_module",
        lambda name: FakeFlyGym if name == "flygym" else None,
    )
    result = live_introspection()
    assert result["status"] == "RESET_ONLY"
    assert result["physics_steps"] == 0
    assert result["neural_runtime_touched"] is False
    assert result["controller_touched"] is False
    assert calls == {"reset": 1, "step": 0, "controller": 0, "neural": 0, "closed": 1}


def test_locked_artifact_hashes_are_unchanged():
    for relative, expected in LOCKED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
