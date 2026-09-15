"""GLFW viewer owned by the application for reliable terrarium input.

Unlike ``mujoco.viewer.launch_passive``, this class owns the window and every
callback.  It renders the caller's MjModel/MjData; it never creates or steps a
second simulation.
"""

from contextlib import nullcontext

import glfw
import mujoco


class TerrariumViewer:
    """Small public-API MuJoCo viewer with explicit callback ownership."""

    def __init__(self, model, data, key_callback=None, width=1280, height=720,
                 title="Fly brain terrarium"):
        glfw.set_error_callback(self._glfw_error)
        if not glfw.init():
            raise RuntimeError("GLFW initialization failed")
        self.window = glfw.create_window(width, height, title, None, None)
        if self.window is None:
            glfw.terminate()
            raise RuntimeError("GLFW window creation failed")
        glfw.make_context_current(self.window)
        glfw.swap_interval(1)
        self.model, self.data = model, data
        self.cam = mujoco.MjvCamera()
        self.opt = mujoco.MjvOption()
        self.pert = mujoco.MjvPerturb()
        self.scene = mujoco.MjvScene(model, maxgeom=10000)
        self.context = mujoco.MjrContext(model, mujoco.mjtFontScale.mjFONTSCALE_150)
        mujoco.mjv_defaultFreeCamera(model, self.cam)
        self._key_callback = key_callback
        self._mouse_button_callback = None
        self._cursor_callback = None
        self._scroll_callback = None
        self._overlays = []
        # Kept for the existing HUD's feature test; this is our object, not a
        # private native-viewer implementation.
        self._sim = lambda: self
        glfw.set_key_callback(self.window, self._on_key)
        glfw.set_mouse_button_callback(self.window, self._on_button)
        glfw.set_cursor_pos_callback(self.window, self._on_cursor)
        glfw.set_scroll_callback(self.window, self._on_scroll)
        # Do not wait for hundreds of expensive neural/physics steps before
        # the OS receives its first paint/event cycle. Present one complete
        # MuJoCo frame synchronously while startup is still on this thread.
        self.sync()
        glfw.show_window(self.window)
        glfw.focus_window(self.window)
        glfw.post_empty_event()
        x, y = glfw.get_window_pos(self.window)
        fw, fh = glfw.get_framebuffer_size(self.window)
        print(f"[Viewer] GLFW window opened pos=({x},{y}) framebuffer={fw}x{fh}",
              flush=True)

    @staticmethod
    def _glfw_error(code, description):
        if isinstance(description, bytes):
            description = description.decode("utf-8", errors="replace")
        print(f"[Viewer] GLFW error {code}: {description}", flush=True)

    def set_input_callbacks(self, mouse_button, cursor_pos, scroll):
        self._mouse_button_callback = mouse_button
        self._cursor_callback = cursor_pos
        self._scroll_callback = scroll

    def _on_key(self, _window, key, _scancode, action, _mods):
        if action == glfw.PRESS:
            if key == glfw.KEY_ESCAPE:
                glfw.set_window_should_close(self.window, True)
            elif self._key_callback is not None:
                self._key_callback(key)

    def _on_button(self, window, button, action, mods):
        if self._mouse_button_callback is not None:
            self._mouse_button_callback(window, button, action, mods)

    def _on_cursor(self, window, x, y):
        if self._cursor_callback is not None:
            self._cursor_callback(window, x, y)

    def _on_scroll(self, window, xoffset, yoffset):
        if self._scroll_callback is not None:
            self._scroll_callback(window, xoffset, yoffset)

    def add_overlay(self, gridpos, title, content):
        self._overlays.append((gridpos, title, content))

    def clear_overlay(self):
        self._overlays.clear()

    def sync(self):
        """Synchronize data into the scene, render, and deliver GLFW events."""
        glfw.make_context_current(self.window)
        width, height = glfw.get_framebuffer_size(self.window)
        viewport = mujoco.MjrRect(0, 0, width, height)
        mujoco.mjv_updateScene(
            self.model, self.data, self.opt, self.pert, self.cam,
            mujoco.mjtCatBit.mjCAT_ALL, self.scene)
        mujoco.mjr_render(viewport, self.scene, self.context)
        for gridpos, title, content in self._overlays:
            mujoco.mjr_overlay(mujoco.mjtFontScale.mjFONTSCALE_150, gridpos,
                               viewport, title, content, self.context)
        glfw.swap_buffers(self.window)
        glfw.poll_events()

    def poll_events(self):
        """Deliver input independently of the simulation's render cadence."""
        glfw.poll_events()

    def is_running(self):
        return not glfw.window_should_close(self.window)

    def lock(self):
        # Rendering, event polling and simulation all happen on the caller's
        # main thread. This compatibility method documents that ownership.
        return nullcontext()

    def close(self):
        if self.window is not None:
            glfw.destroy_window(self.window)
            self.window = None
        glfw.terminate()
