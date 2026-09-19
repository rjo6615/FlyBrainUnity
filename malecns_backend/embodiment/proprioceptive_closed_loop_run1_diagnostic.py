"""Read-only helpers for the M5D-5B Scientific Run #1 diagnosis.

These functions operate on already captured rows.  They never invoke FlyGym,
MuJoCo, or the canonical runner.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .tactile_motor_boundary_diagnostic import compare_contact_sets
from .tactile_motor_equivalence_diagnostic import compare_value, mujoco_object_identity


INITIAL_FIELDS = ("qpos", "qvel", "qacc", "ctrl", "action_joints",
                  "physical_tibia_angles", "baseline_targets",
                  "previous_physical_targets", "contact_forces")


def contact_inventory(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expose raw and conservative semantic identities without guessing names."""
    result = []
    for contact in value.get("contacts", []):
        left, right = contact.get("geom1_name"), contact.get("geom2_name")
        result.append({
            "raw_geom1_id": contact.get("geom1", contact.get("geom1_id")),
            "raw_geom2_id": contact.get("geom2", contact.get("geom2_id")),
            "raw_geom1_name": left, "raw_geom2_name": right,
            "semantic_geom1": (mujoco_object_identity(left) if left is not None
                               else {"unresolved_raw_id": contact.get("geom1", contact.get("geom1_id"))}),
            "semantic_geom2": (mujoco_object_identity(right) if right is not None
                               else {"unresolved_raw_id": contact.get("geom2", contact.get("geom2_id"))}),
            "position": contact.get("position"), "distance": contact.get("distance"),
            "force": contact.get("force", contact.get("mujoco_contact_wrench")),
        })
    return result


def diagnose_initial(enabled: Mapping[str, Any], disabled: Mapping[str, Any]) -> dict[str, Any]:
    """Perform exact initial-state comparisons and classify their differences."""
    comparisons = {field: compare_value(enabled.get(field), disabled.get(field))
                   for field in INITIAL_FIELDS}
    contact = compare_contact_sets(enabled.get("contact_set"), disabled.get("contact_set"))
    divergent = [field for field, result in comparisons.items()
                 if not result["exactly_equal"]]
    if divergent:
        categories = {
            "qpos": "INITIAL_QPOS_DIFFERENCE", "qvel": "INITIAL_QVEL_DIFFERENCE",
            "ctrl": "INITIAL_CTRL_DIFFERENCE", "action_joints": "INITIAL_ACTION_DIFFERENCE",
            "baseline_targets": "INITIAL_TARGET_HISTORY_DIFFERENCE",
            "previous_physical_targets": "INITIAL_TARGET_HISTORY_DIFFERENCE",
            "contact_forces": "INITIAL_FORCE_DIFFERENCE",
        }
        labels = {categories.get(field, "UNRESOLVED_INITIAL_DIFFERENCE") for field in divergent}
        classification = next(iter(labels)) if len(labels) == 1 else "MULTIPLE_INITIAL_DIFFERENCES"
    elif not contact["exactly_equal"]:
        classification = "REAL_CONTACT_SET_DIFFERENCE"
    elif enabled.get("contact_set") != disabled.get("contact_set"):
        classification = "CONTACT_NAMESPACE_ONLY"
    else:
        classification = None
    return {"comparisons": comparisons, "semantic_contact_comparison": contact,
            "classification": classification}


def first_tactile_divergences(enabled: Sequence[Mapping[str, Any]],
                              disabled: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    fields = ("source_forces", "modeled_rate_hz", "generated", "delivered")
    result = {field: None for field in fields}
    for left, right in zip(enabled, disabled):
        for field in fields:
            if result[field] is None and not compare_value(
                    left["tactile"].get(field), right["tactile"].get(field))["exactly_equal"]:
                result[field] = left["time_ms"]
    return result
