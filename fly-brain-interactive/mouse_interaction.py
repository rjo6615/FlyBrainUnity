"""MuJoCo picking and camera-correct dragging for :mod:`terrarium_viewer`.

GLFW callbacks enqueue plain input records. Model/data mutation happens only
when ``poll`` is called by the simulation thread.
"""

from dataclasses import dataclass
import queue

import glfw
import mujoco
import numpy as np


@dataclass
class Pick:
    object_index: int
    geom_id: int
    body_id: int
    point: np.ndarray


class MouseInteraction:
    HEIGHT_PER_NOTCH = 0.5

    def __init__(self, viewer, controller, model, data, debug=False):
        self.viewer, self.controller = viewer, controller
        self.model, self.data, self.debug = model, data, debug
        self.window = viewer.window
        self.events = queue.SimpleQueue()
        self.dragging = False
        self.drag_plane_z = 0.0
        self.drag_offset = np.zeros(2)
        self.cursor = (0.0, 0.0)
        self.last_pick = None
        self.pick_opt = mujoco.MjvOption()
        self.pick_opt.geomgroup[:] = 0
        self.pick_opt.geomgroup[1] = 1
        self.pick_scene = mujoco.MjvScene(model, maxgeom=10000)
        self.available = True
        self.unavailable_reason = None
        self.geom_to_object = {}
        self.body_to_object = {}
        for geom_id in range(model.ngeom):
            name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
            index = controller.index_for_geom(name or "")
            if index is not None:
                self.geom_to_object[geom_id] = index
                self.body_to_object[int(model.geom_bodyid[geom_id])] = index
        viewer.set_input_callbacks(self._mouse_button, self._cursor_pos,
                                   self._scroll)
        if debug:
            print(f"[Mouse] callback owner=TerrariumViewer GLFW window={self.window}")
            print(f"[Mouse] geom_id -> object: {self._mapping_description()}")

    def _mapping_description(self):
        mapped = {}
        for geom, index in self.geom_to_object.items():
            mapped.setdefault(self.controller.objects[index][0], []).append(geom)
        return ", ".join(f"{name}={ids}" for name, ids in mapped.items())

    def _log(self, message):
        if self.debug or self.controller.show_debug:
            print(message, flush=True)

    def _mouse_button(self, window, button, action, mods):
        x, y = glfw.get_cursor_pos(window)
        self._log("MOUSE BUTTON CALLBACK FIRED")
        self.events.put(("button", button, action, mods, x, y))

    def _cursor_pos(self, _window, x, y):
        self.cursor = (x, y)
        self._log("CURSOR CALLBACK FIRED")
        self.events.put(("move", x, y))

    def _scroll(self, _window, _xoffset, yoffset):
        self._log("SCROLL CALLBACK FIRED")
        self.events.put(("scroll", yoffset))

    def _dimensions(self):
        return (*glfw.get_window_size(self.window),
                *glfw.get_framebuffer_size(self.window))

    def camera_ray(self, x, y):
        """Return the world ray represented by a logical-window cursor."""
        ww, wh, _, _ = self._dimensions()
        if ww <= 0 or wh <= 0:
            return None, None
        cameras = self.viewer.scene.camera
        eye = (np.asarray(cameras[0].pos) + np.asarray(cameras[1].pos)) / 2
        forward = np.asarray(cameras[0].forward, dtype=float)
        up = np.asarray(cameras[0].up, dtype=float)
        right = np.cross(forward, up)
        half_h = np.tan(np.radians(float(self.model.vis.global_.fovy)) / 2)
        direction = (forward + (2*x/ww-1) * (ww/wh) * half_h * right +
                     (2*(1-y/wh)-1) * half_h * up)
        direction /= np.linalg.norm(direction)
        return eye, direction

    def plane_point(self, x, y, plane_z):
        eye, ray = self.camera_ray(x, y)
        if eye is None or abs(ray[2]) < 1e-10:
            return None
        distance = (plane_z - eye[2]) / ray[2]
        return None if distance <= 0 else eye + distance * ray

    def _pick(self, x, y):
        ww, wh, _, _ = self._dimensions()
        # Build a selection scene from the current camera containing only the
        # authored interactive group. Glass and decorative foreground geoms
        # therefore cannot steal the hit, while mjv_select still performs the
        # actual geometry intersection and depth ordering.
        mujoco.mjv_updateScene(
            self.model, self.data, self.pick_opt, self.viewer.pert,
            self.viewer.cam, mujoco.mjtCatBit.mjCAT_ALL, self.pick_scene)
        selected = np.zeros(3, dtype=np.float64)
        geom = np.array([-1], dtype=np.int32)
        # Current MuJoCo bindings require a writable output array for every
        # selectable object type, even though this application only uses the
        # returned geom and body IDs.
        flex = np.array([-1], dtype=np.int32)
        skin = np.array([-1], dtype=np.int32)
        body = mujoco.mjv_select(
            self.model, self.data, self.pick_opt, ww / wh,
            x / ww, 1.0 - y / wh, self.pick_scene, selected, geom, flex, skin)
        geom_id, body_id = int(geom[0]), int(body)
        index = self.geom_to_object.get(geom_id)
        self._log(f"cursor pixel = ({x:.1f}, {y:.1f})")
        self._log(f"relative cursor = ({x/ww:.6f}, {1-y/wh:.6f})")
        self._log(f"selected geom id = {geom_id}")
        self._log(f"selected body id = {body_id}")
        self._log("selected object = " +
                  (self.controller.objects[index][0] if index is not None else "NONE"))
        if index is None:
            self._log("mjv_select returned no interactive geom" if geom_id < 0
                      else "mjv_select hit a non-interactive geom")
            return None
        return Pick(index, geom_id, body_id, selected.copy())

    def _debug_state(self, button="LEFT DRAG", target=None):
        actual = self.controller.selected_position
        self._log("MOUSE:")
        self._log(f"cursor: {self.cursor[0]:.0f}, {self.cursor[1]:.0f}")
        self._log(f"button: {button}")
        self._log(f"picked geom: {self.last_pick.geom_id if self.last_pick else -1}")
        self._log(f"picked body: {self.last_pick.body_id if self.last_pick else -1}")
        self._log(f"object: {self.controller.selected_name}")
        self._log(f"dragging: {'YES' if self.dragging else 'NO'}")
        if target is not None:
            self._log("world target: " + np.array2string(target, precision=3))
        if actual is not None:
            self._log("actual object pos: " +
                      np.array2string(np.asarray(actual), precision=3))
            value = np.array2string(np.asarray(actual), precision=3)
            if self.controller.selected_name in ("FOOD", "DANGER"):
                name = self.controller.selected_name.lower()
                self._log(f"visual/world {name} position: {value}")
                self._log(f"olfactory {name} source position: {value}")
            elif self.controller.selected_name == "PREDATOR":
                self._log(f"visual/world predator position: {value}")
                self._log(f"looming predator source position: {value}")

    def poll(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                return
            if event[0] == "button":
                _, button, action, _mods, x, y = event
                self.cursor = (x, y)
                if button == glfw.MOUSE_BUTTON_RIGHT and action == glfw.PRESS:
                    self.controller.select(None)
                    self.dragging = False
                    self.last_pick = None
                    self._debug_state("RIGHT DOWN")
                elif button == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
                    self.last_pick = self._pick(x, y)
                    self.controller.select(
                        None if self.last_pick is None else self.last_pick.object_index)
                    self.dragging = self.last_pick is not None
                    if self.dragging:
                        pos = np.asarray(self.controller.selected_position)
                        self.drag_plane_z = float(pos[2]) if len(pos) > 2 else 0.0
                        point = self.plane_point(x, y, self.drag_plane_z)
                        self.drag_offset[:] = (pos[:2] - point[:2]
                                               if point is not None else 0.0)
                    self._debug_state("LEFT DOWN")
                elif button == glfw.MOUSE_BUTTON_LEFT and action == glfw.RELEASE:
                    self.dragging = False
                    self._debug_state("LEFT UP")
            elif event[0] == "move" and self.dragging:
                point = self.plane_point(event[1], event[2], self.drag_plane_z)
                if point is not None:
                    target = point.copy()
                    target[:2] += self.drag_offset
                    self.controller.place_selected(target[0], target[1])
                    mujoco.mj_forward(self.model, self.data)
                    self._debug_state(target=target)
            elif (event[0] == "scroll" and
                  self.controller.selected_name == "PREDATOR"):
                self.controller.adjust_selected_height(
                    event[1] * self.HEIGHT_PER_NOTCH)
                mujoco.mj_forward(self.model, self.data)
                self._debug_state("WHEEL")
