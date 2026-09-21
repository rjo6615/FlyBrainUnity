"""Authoritative MuJoCo contact and distal-tarsus identity utilities for M8."""
from __future__ import annotations

from typing import Any

LEGS = ("LF", "LM", "LH", "RF", "RM", "RH")
GROUND_COMPONENTS = frozenset(("floor", "ground", "terrain", "surface", "platform", "m5d2c_calibration_surface"))


def namespace_component(name: str) -> str:
    """Return a dm_control attachment name's exact terminal component.

    FlyGym attaches each fly to the MJCF world through dm_control.  dm_control
    preserves the source name as the final slash-delimited component while
    prefixing an attachment namespace (for example ``0/LMTarsus5``).  Comparing
    this component, rather than searching the full string, preserves source
    identity without depending on a particular instance prefix.
    """
    return str(name).rsplit("/", 1)[-1]


def compiled_name(model: Any, kind: str, index: int) -> str:
    """Read an identity from the instantiated compiled model's name table.

    FlyGym exposes a ``dm_control`` MjModel, whose ``id2name`` method is the
    primary API used elsewhere in this project.  The native MuJoCo function is
    only valid with the wrapper's native ``ptr`` (when one is exposed).
    """
    method = getattr(model, "id2name", None)
    if method is not None:
        for args in ((int(index), kind.lower()), (kind.lower(), int(index))):
            try:
                value = method(*args)
            except (AttributeError, IndexError, TypeError, ValueError, KeyError):
                continue
            if value is not None:
                return str(value)
    try:
        import mujoco
        ptr = getattr(model, "ptr", None)
        if ptr is not None:
            return mujoco.mj_id2name(
                ptr, getattr(mujoco.mjtObj, f"mjOBJ_{kind.upper()}"), int(index)) or ""
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    accessor = getattr(model, kind.lower(), None)
    if accessor:
        try: return str(accessor(int(index)).name or "")
        except (AttributeError, IndexError, TypeError, ValueError): pass
    return ""


def resolve(model: Any) -> dict[str, Any]:
    """Resolve each leg from compiled model identities, never force-vector order."""
    body_names = {i: compiled_name(model, "body", i) for i in range(int(model.nbody))}
    geom_names = {i: compiled_name(model, "geom", i) for i in range(int(model.ngeom))}
    ground = tuple(i for i, name in geom_names.items()
                   if namespace_component(name).lower() in GROUND_COMPONENTS)
    bodies, geoms = {}, {}
    for leg in LEGS:
        candidates = [i for i, name in body_names.items()
                      if namespace_component(name) == f"{leg}Tarsus5"]
        bodies[leg] = candidates[0] if len(candidates) == 1 and candidates[0] != 0 else None
        tarsal_bodies = {i for i, name in body_names.items()
                         if namespace_component(name) in
                         {f"{leg}Tarsus{segment}" for segment in range(1, 6)}}
        geoms[leg] = tuple(gid for gid in geom_names
                           if int(model.geom_bodyid[gid]) in tarsal_bodies)
    available = bool(ground) and all(bodies[x] is not None and geoms[x] for x in LEGS)
    return {"available": available,
        "method": "exact terminal component of slash-namespaced compiled MuJoCo identities",
        "ground_geom_ids": ground, "tarsus5_body_ids": bodies, "tarsal_geom_ids": geoms,
        "body_names": body_names, "geom_names": geom_names}


def sample(physics: Any, identity: dict[str, Any]):
    """Return contact flags and Tarsus5 world positions in fixed leg order."""
    import numpy as np
    positions = np.full((6, 3), np.nan, dtype=np.float64)
    contacts = np.zeros(6, dtype=np.bool_)
    for i, leg in enumerate(LEGS):
        bid = identity["tarsus5_body_ids"][leg]
        if bid is not None: positions[i] = np.asarray(physics.data.xpos[int(bid)])
    if identity["available"]:
        ground = set(identity["ground_geom_ids"])
        owners = {gid: i for i, leg in enumerate(LEGS) for gid in identity["tarsal_geom_ids"][leg]}
        for c in physics.data.contact[:physics.data.ncon]:
            g1, g2 = int(c.geom1), int(c.geom2)
            if g1 in ground and g2 in owners: contacts[owners[g2]] = True
            if g2 in ground and g1 in owners: contacts[owners[g1]] = True
    return contacts, positions
