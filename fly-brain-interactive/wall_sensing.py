"""Transduce physical terrarium-wall contacts into bilateral touch input."""

import numpy as np


class WallMechanosensor:
    """Read actual MuJoCo contacts; never issue a movement or mode command."""

    def __init__(self, model):
        import mujoco

        self.mujoco = mujoco
        self.model = model
        # dm_control may namespace arena elements, so match the stable suffix.
        self.wall_ids = set()
        for geom_id in range(model.ngeom):
            name = mujoco.mj_id2name(
                model, mujoco.mjtObj.mjOBJ_GEOM, geom_id) or ""
            if any(name.endswith(f"terrarium_glass_{i}") for i in range(4)):
                self.wall_ids.add(geom_id)

    def rates(self, data, fly_pos, heading, max_rate, force_floor, force_sat):
        """Return left/right JO rates and peak force from wall contacts."""
        left = right = peak = 0.0
        lateral = np.array([-np.sin(heading), np.cos(heading)])
        force = np.zeros(6)
        for i in range(data.ncon):
            contact = data.contact[i]
            if contact.geom1 not in self.wall_ids and contact.geom2 not in self.wall_ids:
                continue
            self.mujoco.mj_contactForce(self.model, data, i, force)
            magnitude = abs(float(force[0]))
            peak = max(peak, magnitude)
            rate = np.clip((magnitude-force_floor)/(force_sat-force_floor), 0, 1)*max_rate
            side = np.dot(np.asarray(contact.pos[:2])-fly_pos[:2], lateral)
            if side >= 0:
                left = max(left, rate)
            else:
                right = max(right, rate)
        return left, right, peak
