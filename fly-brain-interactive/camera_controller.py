"""Stable terrarium camera modes for the MuJoCo passive viewer."""

import mujoco


class CameraController:
    MODES = ("CLOSE FOLLOW", "WIDE FOLLOW", "TERRARIUM OVERVIEW", "FREE")

    def __init__(self, viewer, body_id):
        self.viewer = viewer
        self.body_id = body_id
        self.mode_index = 2 if body_id >= 0 else 3
        self.reset()
        self.keep_terrarium_visuals_clean()

    @property
    def mode_name(self):
        return self.MODES[self.mode_index]

    def reset(self, follow=None):
        if follow is not None:
            self.mode_index = 0 if follow else 3
        cam = self.viewer.cam
        tracking = self.mode_index in (0, 1)
        cam.type = (mujoco.mjtCamera.mjCAMERA_TRACKING if tracking
                    else mujoco.mjtCamera.mjCAMERA_FREE)
        if self.body_id >= 0:
            cam.trackbodyid = self.body_id
        settings = ((12.5, -125, -24), (32.0, -125, -32),
                    (72.0, -128, -38), (45.0, -125, -28))
        cam.distance, cam.azimuth, cam.elevation = settings[self.mode_index]

    def follow(self):
        self.mode_index = 0
        self.reset()

    def cycle(self):
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.reset()
        self.keep_terrarium_visuals_clean()

    def toggle(self):
        """Backward-compatible alias for cycling the presentation modes."""
        self.cycle()

    def zoom(self, direction):
        self.viewer.cam.distance = max(
            3.0, min(300.0, self.viewer.cam.distance * (0.85 ** direction)))

    def keep_terrarium_visuals_clean(self):
        """Undo MuJoCo's built-in ``C`` contact-force visualization toggle.

        The passive viewer handles its own shortcuts in addition to invoking
        our key callback.  MuJoCo assigns ``C`` to contact-force rendering,
        which can draw a huge yellow force cylinder over this millimetre-scale
        animal.  Terrarium mode assigns ``C`` to the requested camera toggle,
        so contact diagnostics must remain disabled after the native handler
        sees that same event.
        """
        flags = self.viewer.opt.flags
        flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = False
        flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = False
