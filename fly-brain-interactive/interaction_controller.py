"""Non-positional key-command adapter for terrarium interaction."""


class InteractionController:
    """Translate viewer events into world manipulation and sensory pokes.

    Commands are dispatched on the simulation thread after MuJoCo's supported
    ``launch_passive`` callback places their keycodes in a thread-safe queue.
    This class must never be called directly from the native viewer thread.
    """

    HELP = ("Left-drag objects | drag+wheel height | right-click deselect | "
            "H or KP / help | L labels | Tab HUD | F or KP 1 follow | "
            "C or KP 3 camera | Space or KP Enter pause | KP 0 select | "
            "KP 4/6/8/2 move fallback | KP 7/9 height | KP 5 poke | "
            "KP +/- speed | Backspace or KP . reset")

    # Keep remaining terrarium key actions on the numeric keypad. Unlike
    # Alt-letter and function-key chords, these do not collide with Windows
    # shortcuts or MuJoCo's normal letter, camera, and visualization bindings.
    KEY_SELECT = 320       # GLFW_KEY_KP_0
    KEY_FOLLOW = 321       # GLFW_KEY_KP_1
    KEY_DOWN = 322         # GLFW_KEY_KP_2
    KEY_CAMERA = 323       # GLFW_KEY_KP_3
    KEY_LEFT = 324         # GLFW_KEY_KP_4
    KEY_POKE = 325         # GLFW_KEY_KP_5
    KEY_RIGHT = 326        # GLFW_KEY_KP_6
    KEY_LOWER = 327        # GLFW_KEY_KP_7
    KEY_UP = 328           # GLFW_KEY_KP_8
    KEY_RAISE = 329        # GLFW_KEY_KP_9
    KEY_RESET = 330        # GLFW_KEY_KP_DECIMAL
    KEY_HELP = 331         # GLFW_KEY_KP_DIVIDE
    KEY_DEBUG = 332        # GLFW_KEY_KP_MULTIPLY
    KEY_SLOWER = 333       # GLFW_KEY_KP_SUBTRACT
    KEY_FASTER = 334       # GLFW_KEY_KP_ADD
    KEY_PAUSE = 335        # GLFW_KEY_KP_ENTER
    KEY_SPACE = 32
    KEY_TAB = 258
    KEY_BACKSPACE = 259
    KEY_H = ord('H')
    KEY_L = ord('L')
    KEY_F = ord('F')
    KEY_C = ord('C')

    def __init__(self, terrarium, camera=None, reset_callback=None):
        self.terrarium = terrarium
        self.camera = camera
        self.reset_callback = reset_callback

    def update_window_title(self):
        """Compatibility no-op for checkouts containing the old call site.

        Earlier terrarium revisions called this method after every command and
        changed the GLFW window title.  The title mutation was removed, but a
        partially updated checkout could retain the call while losing the
        method, producing the AttributeError reported when KP 0 was pressed.
        The controls now live in the 3-D scene, so there is nothing to update.
        """
        return None

    def on_key(self, keycode, fast=False):
        if keycode == self.KEY_SELECT:
            self.terrarium.select_next()
        elif keycode in (self.KEY_PAUSE, self.KEY_SPACE):
            self.terrarium.paused = not self.terrarium.paused
        elif keycode in (self.KEY_HELP, self.KEY_H):
            self.terrarium.show_help = not self.terrarium.show_help
        elif keycode == self.KEY_L:
            self.terrarium.show_labels = not self.terrarium.show_labels
            if self.camera:
                self.camera.viewer.opt.sitegroup[3] = self.terrarium.show_labels
        elif keycode == self.KEY_TAB:
            self.terrarium.show_hud = not self.terrarium.show_hud
        elif keycode == self.KEY_DEBUG:
            self.terrarium.show_debug = not self.terrarium.show_debug
        elif keycode == self.KEY_POKE:
            self.terrarium.queue_poke()
        elif keycode == self.KEY_SLOWER:
            self.terrarium.slower()
        elif keycode == self.KEY_FASTER:
            self.terrarium.faster()
        elif keycode in (self.KEY_RESET, self.KEY_BACKSPACE):
            # The native viewer also resets mjData on Backspace. Re-run the
            # simulation wrapper reset so FlyGym's pose/controller state does
            # not disagree with MuJoCo and leave the fly inverted.
            if self.reset_callback:
                self.reset_callback()
            self.terrarium.reset()
            if self.camera:
                self.camera.reset()
        elif keycode in (self.KEY_FOLLOW, self.KEY_F) and self.camera:
            self.camera.follow()
        elif keycode in (self.KEY_CAMERA, self.KEY_C) and self.camera:
            self.camera.cycle()
        else:
            return False
        self.update_window_title()
        return True
