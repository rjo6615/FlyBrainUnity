"""Formatting and lightweight screen-space overlay for terrarium mode."""

import mujoco


class TerrariumHUD:
    """Populate MuJoCo's overlay queue without owning a window or GL context."""

    def __init__(self, viewer, controller, camera):
        self.viewer, self.controller, self.camera = viewer, controller, camera
        self.data = {}

    def update(self, data):
        self.data = data

    @staticmethod
    def _bar(value, width=8):
        value = max(0.0, min(1.0, float(value or 0.0)))
        ticks = int(round(value * width))
        glyph = "|" * ticks if ticks else ("." if value > 0 else "-")
        return f"{value:4.2f} {glyph}"

    def draw(self):
        """Add compact panels when supported by this MuJoCo viewer version."""
        sim = getattr(self.viewer, "_sim", None)
        if not sim:
            return
        target = sim()
        add = getattr(target, "add_overlay", None)
        clear = getattr(target, "clear_overlay", None)
        if not add:
            return
        if clear:
            clear()
        c, d = self.controller, self.data
        if not c.show_hud:
            return
        left = (f"Behavior  {d.get('behavior', 'IDLE')}\n"
                f"Simulation  {'PAUSED' if c.paused else 'RUNNING'}\n"
                f"Speed  {c.speed:g}x\nSelected  {c.selected_name}\n"
                f"Camera  {self.camera.mode_name if self.camera else 'FREE'}")
        add(mujoco.mjtGridPos.mjGRID_TOPLEFT, "TERRARIUM", left)
        groups = (("Network", "network"),
                  ("P9", "p9"), ("DNa01", "dna01"), ("DNa02", "dna02"),
                  ("MDN", "mdn"), ("GF", "gf"), ("aDN1", "adn1"),
                  ("MN9", "mn9"))
        add(mujoco.mjtGridPos.mjGRID_TOPRIGHT, "BRAIN ACTIVITY",
            "\n".join(f"{name:<7} {self._bar(d.get(key, 0))}"
                      for name, key in groups))
        sensory = (("Vision", d.get("vision", 0)),
                   ("Smell", d.get("smell", 0)),
                   ("Taste", d.get("taste", 0)),
                   ("Touch", d.get("touch", 0)),
                   ("Looming", d.get("looming", 0)))
        add(mujoco.mjtGridPos.mjGRID_BOTTOMLEFT, "SENSORY INPUT",
            "\n".join(f"{name:<9} {float(val or 0):.2f}"
                      for name, val in sensory))
        if c.mouse_available:
            controls = ("Left-drag  move on floor\nPredator selected + wheel  height\n"
                        "Right-click  deselect")
        else:
            controls = ("KP 0  select\nKP 4/6/8/2  move\n"
                        "KP 7/9  height  (mouse unavailable)")
        if c.selection_notice_visible:
            controls = f"SELECTED: {c.selected_name}\n\n" + controls
        add(mujoco.mjtGridPos.mjGRID_BOTTOMRIGHT, "OBJECT CONTROL", controls)
        if c.show_help:
            help_text = ("OBJECTS\nLeft-click select   left-drag move   predator+wheel height\n"
                         "Right-click or empty click deselect\n\n"
                         "INTERACTION\nKP 5 poke\n\nCAMERA\nF follow   C cycle   mouse wheel zoom/orbit\n\n"
                         "SIMULATION\nSpace pause   Backspace reset\n\nUI\nH help   L labels   Tab HUD")
            add(mujoco.mjtGridPos.mjGRID_TOPLEFT, "CONTROL REFERENCE", help_text)

def behavior_label(bridge, decoder):
    if bridge.mode != "walking":
        return bridge.mode.upper()
    left, right = bridge.left_drive, bridge.right_drive
    if max(abs(left), abs(right)) < 0.04:
        return "IDLE"
    if left < -0.04 and right < -0.04:
        return "BACKWARD"
    if abs(left - right) > 0.12:
        return "TURNING"
    return "WALKING"


def monitor_fields(controller, bridge, decoder, fly_pos, predator_distance):
    return {
        "behavior": behavior_label(bridge, decoder),
        "terrarium_selected": controller.selected_name,
        "terrarium_speed": controller.speed,
        "terrarium_paused": controller.paused,
        "fly_pos": [float(x) for x in fly_pos],
        "predator_distance": float(predator_distance),
        "p9": decoder.get_group_rate("forward"),
        "dna01": (decoder.get_normalized("DNa01_left") +
                  decoder.get_normalized("DNa01_right")) / 2,
        "dna02": (decoder.get_normalized("DNa02_left") +
                  decoder.get_normalized("DNa02_right")) / 2,
        "mdn": decoder.get_group_rate("backward"),
        "gf": decoder.get_group_rate("escape"),
        "adn1": decoder.get_group_rate("groom"),
        "mn9": decoder.get_group_rate("feed"),
    }
