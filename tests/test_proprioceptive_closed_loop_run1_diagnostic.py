from copy import deepcopy

from malecns_backend.embodiment import proprioceptive_closed_loop as reducer
from malecns_backend.embodiment import proprioceptive_closed_loop_run1_diagnostic as diagnostic


def _contact(prefix="0", geom2="RHCoxa"):
    return {"contacts": [{"geom1": 20, "geom2": 36,
        "geom1_name": f"{prefix}/LHCoxa", "geom2_name": f"{prefix}/{geom2}",
        "position": [1.0, 2.0, 3.0], "distance": -0.1,
        "mujoco_contact_wrench": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0]}]}


def _initial(contact=None):
    return {field: [0.0] for field in diagnostic.INITIAL_FIELDS} | {
        "physical_tibia_angles": {"LM": 0.0}, "baseline_targets": {"LM": 0.0},
        "previous_physical_targets": {"LM": None}, "contact_set": contact or _contact()}


def test_namespace_and_unordered_pair_are_semantically_equal():
    left, right = _contact("0"), _contact("1")
    right["contacts"][0].update(geom1=136, geom2=120,
        geom1_name="1/RHCoxa", geom2_name="1/LHCoxa")
    assert diagnostic.diagnose_initial(_initial(left), _initial(right))[
        "classification"] == "CONTACT_NAMESPACE_ONLY"


def test_real_geometry_and_unresolved_ids_fail_closed():
    assert not diagnostic.diagnose_initial(_initial(), _initial(_contact("1", "RHTibia")))[
        "semantic_contact_comparison"]["exactly_equal"]
    left, right = _contact(), _contact("1")
    for item in (left["contacts"][0], right["contacts"][0]):
        item["geom1_name"] = None
    right["contacts"][0]["geom1"] = 120
    assert not diagnostic.diagnose_initial(_initial(left), _initial(right))[
        "semantic_contact_comparison"]["exactly_equal"]


def test_numeric_contact_state_difference_remains_detectable():
    right = _contact("1")
    right["contacts"][0]["distance"] = -0.2
    assert diagnostic.diagnose_initial(_initial(), _initial(right))[
        "classification"] == "REAL_CONTACT_SET_DIFFERENCE"


def test_m5d5b_reducer_uses_validated_semantic_comparator(monkeypatch):
    row = {"time_ms": 0.0, "contact_set": _contact(), "raw_neural_contributions": {},
           "proprio": {}, "motor_spikes": {}}
    other = deepcopy(row); other["contact_set"] = _contact("1")
    # Directly exercise the comparator selected at the repaired source line;
    # full reducer rows are intentionally not synthesized as scientific data.
    assert reducer.compare_contact_sets(row["contact_set"], other["contact_set"])[
        "exactly_equal"]


def test_tactile_divergence_stages_are_independent():
    base = {"time_ms": 0.0, "tactile": {"source_forces": [0],
        "modeled_rate_hz": 0.0, "generated": (), "delivered": ()}}
    changed = deepcopy(base); changed["time_ms"] = 0.1
    changed["tactile"]["delivered"] = (4,)
    result = diagnostic.first_tactile_divergences([base, base], [base, changed])
    assert result == {"source_forces": None, "modeled_rate_hz": None,
                      "generated": None, "delivered": 0.1}
