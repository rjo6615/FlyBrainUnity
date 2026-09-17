"""Deterministic, non-intervening comparison of six-tibia executions."""
from __future__ import annotations

import numpy as np

from .six_tibia import LEG_ORDER


def _difference(a, b):
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        aa, bb = np.asarray(a), np.asarray(b)
        if aa.shape != bb.shape:
            return "shape", aa.shape, bb.shape
        unequal = np.flatnonzero(aa != bb)
        if unequal.size:
            i = int(unequal[0]); return i, aa.flat[i].item(), bb.flat[i].item()
        return None
    return None if a == b else (None, a, b)


def first_divergence(canonical, instrumented):
    """Locate the earliest exact difference, ordered by runtime stage."""
    if len(canonical) != len(instrumented):
        return {"first_divergence_time_ms": 0, "first_divergence_stage": "schedule",
                "first_divergence_leg": None, "first_divergence_quantity": "row_count",
                "canonical_value": len(canonical), "instrumented_value": len(instrumented)}
    for left, right in zip(canonical, instrumented):
        t=left["time_ms"]
        checks=[]
        checks.append(("rng",None,"before_sensory",left.get("rng_before_sensory"),right.get("rng_before_sensory")))
        for leg in LEG_ORDER:
            checks.extend((("physical",leg,"angle",left["before"].angles_rad[leg],right["before"].angles_rad[leg]),
                           ("physical",leg,"velocity",left["before"].velocities_rad_s[leg],right["before"].velocities_rad_s[leg]),
                           ("sensory",leg,"encoded_rate",left["encoded"][leg].rates_hz,right["encoded"][leg].rates_hz),
                           ("sensory",leg,"spike_increment",left["sensory_increments"][leg],right["sensory_increments"][leg])))
        checks.extend((("cns",None,"spiking_neuron_indices",left.get("spiking_neuron_indices"),right.get("spiking_neuron_indices")),
                       ("cns",None,"spike_increment",left["cns_spike_increment"],right["cns_spike_increment"])))
        for leg in LEG_ORDER:
            checks.extend((("motor",leg,"increments",left["motor"][leg]["increments"],right["motor"][leg]["increments"]),
                           ("motor",leg,"filtered_hz",left["motor"][leg]["filtered_hz"],right["motor"][leg]["filtered_hz"]),
                           ("motor",leg,"decoded_offset",left["actuation"][leg]["decoded_offset_rad"],right["actuation"][leg]["decoded_offset_rad"]),
                           ("motor",leg,"actuator_target",left["actuation"][leg]["final_target_rad"],right["actuation"][leg]["final_target_rad"])))
        checks.append(("rng",None,"after_stochastic_drive",left.get("rng_after_stochastic_drive"),right.get("rng_after_stochastic_drive")))
        for stage,leg,quantity,a,b in checks:
            diff=_difference(a,b)
            if diff is not None:
                index,av,bv=diff
                if index is not None: quantity=f"{quantity}[{index}]"
                return {"first_divergence_time_ms":t,"first_divergence_stage":stage,
                        "first_divergence_leg":leg,"first_divergence_quantity":quantity,
                        "canonical_value":av,"instrumented_value":bv}
    return None
