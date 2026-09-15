"""Input-independent state and commands for the interactive terrarium.

This module deliberately manipulates arena objects, never the fly's actuators.
Keyboard and mouse adapters can therefore remain thin and testable.
"""

from dataclasses import dataclass
import time
import numpy as np


@dataclass
class Poke:
    """A short, lateralized mechanosensory pulse."""

    side: str = "both"
    strength: float = 0.65
    remaining: float = 0.18


class TerrariumController:
    """Own interactive selection, time controls, and transient pokes."""

    MOVE_STEP = 2.0
    POSITION_LIMIT = 30.5
    PICK_RADII = {"PREDATOR": 8.0, "SUGAR": 5.0, "POISON": 5.0,
                  "FOOD": 6.5, "DANGER": 5.0}

    def __init__(self, arena, taste_zones, odor_sources):
        self.arena = arena
        self._taste_count = len(taste_zones)
        self.objects = [("PREDATOR", arena.ball_pos)]
        taste_names = {"sugar": "SUGAR", "bitter": "POISON"}
        odor_names = {"attractive": "FOOD", "repulsive": "DANGER"}
        self.objects += [
            (taste_names.get(getattr(z, "taste", ""), z.label.upper()), z.center)
            for z in taste_zones]
        self.objects += [
            (odor_names.get(getattr(s, "odor_type", ""), s.label.upper()),
             s.position) for s in odor_sources]
        self.selected = None
        self.paused = False
        self.speed = 1.0
        self.show_help = False
        self.show_hud = True
        # Object names are essential orientation cues, not debug clutter.
        # They can still be hidden with L for an unobstructed scene.
        self.show_labels = True
        self.show_debug = False
        self.mouse_available = True
        self.poke = None
        self.selection_changed_at = time.monotonic()
        if hasattr(arena, "set_selected_position"):
            arena.set_selected_position(None)

    def index_for_geom(self, geom_name):
        """Map a depth-picked MJCF geom to its interactive sensory object."""
        leaf = geom_name.rsplit("/", 1)[-1]
        if leaf.startswith("looming_predator_"):
            return 0
        if leaf.startswith(("taste_zone_", "sugar_crystal_", "poison_")):
            try:
                source_index = int(leaf.split("_")[2])
            except (IndexError, ValueError):
                return None
            return 1 + source_index
        if leaf.startswith(("odor_source_", "fruit_", "danger_", "odor_halo_")):
            parts = leaf.split("_")
            try:
                source_index = next(int(part) for part in parts if part.isdigit())
            except StopIteration:
                return None
            return 1 + self._taste_count + source_index
        return None

    def index_near(self, x, y):
        """Pick a nearby object on the floor as a renderer-independent fallback."""
        point = np.asarray((x, y), dtype=float)
        candidates = []
        for index, (name, position) in enumerate(self.objects):
            distance = float(np.linalg.norm(np.asarray(position)[:2] - point))
            if distance <= self.PICK_RADII.get(name, 5.0):
                candidates.append((distance, index))
        return min(candidates)[1] if candidates else None

    @property
    def selected_name(self):
        return self.objects[self.selected][0] if self.selected is not None else "NONE"

    @property
    def selected_position(self):
        return None if self.selected is None else self.objects[self.selected][1]

    def select(self, index):
        """Select an object by index, or deselect with ``None``."""
        if index is not None and not 0 <= index < len(self.objects):
            raise IndexError(index)
        self.selected = index
        self.selection_changed_at = time.monotonic()
        if hasattr(self.arena, "set_selected_position"):
            self.arena.set_selected_position(self.selected_position)

    def select_next(self):
        self.select(0 if self.selected is None else
                    (self.selected + 1) % len(self.objects))

    @property
    def selection_notice_visible(self):
        return time.monotonic() - self.selection_changed_at < 1.6

    def move_selected(self, dx=0.0, dy=0.0, dz=0.0, fast=False):
        if self.selected is None:
            return
        amount = self.MOVE_STEP * (4.0 if fast else 1.0)
        pos = self.objects[self.selected][1]
        pos[:2] += np.array([dx, dy]) * amount
        if len(pos) > 2:
            pos[2] = max(0.1, pos[2] + dz * amount)
        self.arena.sync_interactive_objects()

    def place_selected(self, x, y, z=None):
        """Move the shared visual/sensory position, never the fly."""
        if self.selected is None:
            return
        pos = self.selected_position
        pos[:2] = np.clip((x, y), -self.POSITION_LIMIT, self.POSITION_LIMIT)
        if z is not None and len(pos) > 2:
            pos[2] = max(0.1, z)
        self.arena.sync_interactive_objects()

    def adjust_selected_height(self, delta):
        if self.selected is not None and len(self.selected_position) > 2:
            self.selected_position[2] = max(
                0.1, self.selected_position[2] + float(delta))
            self.arena.sync_interactive_objects()

    def queue_poke(self, side="both", strength=0.65):
        # Repeated clicks summate, but remain a sensory rate rather than a
        # behavior command.
        if self.poke is not None:
            strength = min(1.0, strength + self.poke.strength * 0.5)
        self.poke = Poke(side, strength)

    def consume_poke_rates(self, dt, max_rate):
        left = right = 0.0
        if self.poke is not None:
            rate = self.poke.strength * max_rate
            left = rate if self.poke.side in ("left", "both") else 0.0
            right = rate if self.poke.side in ("right", "both") else 0.0
            self.poke.remaining -= dt
            if self.poke.remaining <= 0:
                self.poke = None
        return left, right

    def slower(self):
        self.speed = max(0.125, self.speed / 2.0)

    def faster(self):
        self.speed = min(8.0, self.speed * 2.0)

    def reset(self):
        self.arena.reset_interactive_objects()
        self.paused = False
        self.speed = 1.0
        self.poke = None
        self.selection_changed_at = time.monotonic()
        if hasattr(self.arena, "set_selected_position"):
            self.arena.set_selected_position(self.selected_position)
