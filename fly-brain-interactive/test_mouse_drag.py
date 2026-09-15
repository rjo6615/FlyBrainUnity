#!/usr/bin/env python3
"""Manual red-cube reproduction for the terrarium interaction architecture.

Success is intentionally visual: click the cube, drag it, and release. Press
Escape or close the window to exit. Use ``--debug-mouse`` for event evidence.
"""

import argparse
import numpy as np
import mujoco

from mouse_interaction import MouseInteraction
from terrarium_viewer import TerrariumViewer


XML = """
<mujoco model="mouse drag reproduction">
  <worldbody>
    <light pos="0 0 8"/>
    <geom name="floor" type="plane" size="5 5 .1" rgba=".25 .3 .25 1"/>
    <body name="red_cube" mocap="true" pos="0 0 .5">
      <geom name="interactive_cube" type="box" size=".5 .5 .5"
            rgba="1 .05 .05 1" group="1"/>
    </body>
  </worldbody>
</mujoco>
"""


class CubeArena:
    def __init__(self, model, data, position):
        self.model, self.data, self.position = model, data, position
        self.mocap_id = int(model.body_mocapid[
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "red_cube")])

    def set_selected_position(self, _position):
        pass

    def sync_interactive_objects(self):
        self.data.mocap_pos[self.mocap_id] = self.position


class CubeController:
    show_debug = False

    def __init__(self, arena):
        self.arena = arena
        self.objects = [("CUBE", arena.position)]
        self.selected = None

    def index_for_geom(self, name):
        return 0 if name == "interactive_cube" else None

    @property
    def selected_name(self):
        return "CUBE" if self.selected == 0 else "NONE"

    @property
    def selected_position(self):
        return self.objects[self.selected][1] if self.selected is not None else None

    def select(self, index):
        self.selected = index

    def place_selected(self, x, y, z=None):
        self.selected_position[:2] = np.clip((x, y), -4.5, 4.5)
        self.arena.sync_interactive_objects()

    def adjust_selected_height(self, delta):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug-mouse", action="store_true")
    args = parser.parse_args()
    model = mujoco.MjModel.from_xml_string(XML)
    data = mujoco.MjData(model)
    position = np.array([0.0, 0.0, 0.5])
    arena = CubeArena(model, data, position)
    controller = CubeController(arena)
    viewer = TerrariumViewer(model, data, title="MuJoCo mouse drag test")
    viewer.cam.lookat[:] = (0, 0, 0)
    viewer.cam.distance = 7
    viewer.cam.azimuth = 135
    viewer.cam.elevation = -35
    mouse = MouseInteraction(viewer, controller, model, data, args.debug_mouse)
    print("Click and drag the red cube; close the window to exit.")
    try:
        while viewer.is_running():
            mouse.poll()
            viewer.sync()
    finally:
        viewer.close()


if __name__ == "__main__":
    main()
