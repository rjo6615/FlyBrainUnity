import unittest
import queue
from types import SimpleNamespace
import numpy as np

from terrarium_controller import TerrariumController
from interaction_controller import InteractionController
from mouse_interaction import MouseInteraction, Pick
from unittest.mock import patch


class Source:
    def __init__(self, label, position=None, center=None):
        self.label = label
        if position is not None:
            self.position = np.array(position, dtype=float)
        if center is not None:
            self.center = np.array(center, dtype=float)


class Arena:
    def __init__(self):
        self.ball_pos = np.array([10.0, 0.0, 2.0])
        self.synced = 0
        self.reset_count = 0

    def sync_interactive_objects(self):
        self.synced += 1

    def reset_interactive_objects(self):
        self.reset_count += 1

    def set_selected_position(self, position):
        self.selected_position = position


class TerrariumControllerTests(unittest.TestCase):
    def setUp(self):
        self.arena = Arena()
        self.sugar = Source('sugar', center=[1, 2])
        self.food = Source('food', position=[3, 4, 1])
        self.controller = TerrariumController(
            self.arena, [self.sugar], [self.food])

    def test_moves_selected_world_object(self):
        self.controller.select(0)
        self.controller.move_selected(dx=-1, dy=1)
        np.testing.assert_allclose(self.arena.ball_pos, [8, 2, 2])
        self.assertEqual(self.arena.synced, 1)

    def test_selected_sources_share_sensory_position_arrays(self):
        self.assertTrue(self.controller.show_labels)
        self.controller.select(1)
        self.assertIs(self.arena.selected_position, self.sugar.center)
        self.controller.move_selected(dx=1)
        np.testing.assert_allclose(self.sugar.center, [3, 2])

    def test_mouse_style_selection_place_height_and_deselect(self):
        self.controller.select(2)
        self.controller.place_selected(99, -99)
        self.controller.adjust_selected_height(1.5)
        np.testing.assert_allclose(self.food.position, [30.5, -30.5, 2.5])
        self.controller.select(None)
        self.assertEqual(self.controller.selected_name, "NONE")
        self.assertIsNone(self.arena.selected_position)

    def test_picked_geom_names_map_to_shared_sensory_objects(self):
        self.assertEqual(self.controller.index_for_geom(
            "arena/looming_predator_leg_-1_2"), 0)
        self.assertEqual(self.controller.index_for_geom(
            "arena/sugar_crystal_0_2"), 1)
        self.assertEqual(self.controller.index_for_geom(
            "arena/odor_source_0_fruit"), 2)
        self.assertIsNone(self.controller.index_for_geom("arena/decor_pebble_a"))

    def test_floor_proximity_pick_has_large_whole_object_targets(self):
        self.assertEqual(self.controller.index_near(10.5, 1.0), 0)
        self.assertEqual(self.controller.index_near(2.0, 2.0), 1)
        self.assertEqual(self.controller.index_near(7.5, 4.0), 2)
        self.assertIsNone(self.controller.index_near(-20, 20))

    def test_poke_is_lateralized_transient_and_summates(self):
        self.controller.queue_poke('left', 0.4)
        self.assertEqual(self.controller.consume_poke_rates(0.1, 200), (80, 0))
        self.controller.queue_poke('right', 0.6)
        left, right = self.controller.consume_poke_rates(0.1, 200)
        self.assertEqual(left, 0)
        self.assertGreater(right, 120)
        self.controller.consume_poke_rates(0.1, 200)
        self.assertIsNone(self.controller.poke)

    def test_keyboard_object_nudging_remains_as_compatibility_fallback(self):
        resets = []
        interaction = InteractionController(
            self.controller, reset_callback=lambda: resets.append(True))
        # Remains safe for users updating from the window-title implementation,
        # whose on_key method may still invoke this compatibility hook.
        self.assertIsNone(interaction.update_window_title())
        self.assertFalse(interaction.on_key(ord('W')))
        # Top-row neural stimulus keys remain unclaimed so fly_embodied can
        # dispatch them after terrarium commands are processed.
        self.assertFalse(interaction.on_key(ord('2')))
        self.assertFalse(interaction.on_key(ord('0')))
        self.assertTrue(interaction.on_key(interaction.KEY_UP))
        interaction.on_key(interaction.KEY_PAUSE)
        interaction.on_key(interaction.KEY_FASTER)
        self.assertEqual(self.arena.ball_pos[1], 0)
        self.assertTrue(self.controller.paused)
        self.assertEqual(self.controller.speed, 2)
        interaction.on_key(interaction.KEY_BACKSPACE)
        self.assertEqual(resets, [True])
        self.assertEqual(self.arena.reset_count, 1)


class MouseInteractionTests(unittest.TestCase):
    """The owned-window event queue moves only a successfully picked object."""

    def setUp(self):
        self.arena = Arena()
        self.sugar = Source('sugar', center=[1, 2])
        self.food = Source('food', position=[3, 4, 1])
        self.controller = TerrariumController(
            self.arena, [self.sugar], [self.food])

    def make_mouse(self, picked):
        mouse = MouseInteraction.__new__(MouseInteraction)
        mouse.events = queue.SimpleQueue()
        mouse.dragging = False
        mouse.drag_plane_z = 0.0
        mouse.drag_offset = np.zeros(2)
        mouse.cursor = (0, 0)
        mouse.last_pick = None
        mouse.controller = self.controller
        mouse.controller.show_debug = False
        mouse._pick = lambda x, y: picked
        mouse.plane_point = lambda x, y, z: np.array([x, y, z], dtype=float)
        mouse._log = lambda message: None
        mouse._debug_state = lambda *args, **kwargs: None
        mouse.model = object()
        mouse.data = object()
        return mouse

    @patch("mouse_interaction.mujoco.mjv_updateScene")
    @patch("mouse_interaction.mujoco.mjv_select")
    def test_pick_supplies_flex_output_required_by_current_mujoco(
            self, select, _update_scene):
        mouse = self.make_mouse(None)
        mouse._dimensions = lambda: (800, 600, 800, 600)
        mouse.pick_opt = object()
        mouse.pick_scene = object()
        mouse.viewer = SimpleNamespace(pert=object(), cam=object())
        mouse.geom_to_object = {7: 2}
        select.side_effect = lambda *args: (
            args[8].__setitem__(0, 7) or 4)

        picked = MouseInteraction._pick(mouse, 200, 150)

        self.assertEqual(picked.object_index, 2)
        self.assertEqual(picked.geom_id, 7)
        self.assertEqual(picked.body_id, 4)
        args = select.call_args.args
        self.assertEqual(len(args), 11)
        np.testing.assert_array_equal(args[9], np.array([-1], dtype=np.int32))
        np.testing.assert_array_equal(args[10], np.array([-1], dtype=np.int32))

    @patch("mouse_interaction.mujoco.mj_forward")
    def test_object_drag_moves_picked_source_with_click_offset(self, forward):
        mouse = self.make_mouse(Pick(2, 8, 4, np.zeros(3)))
        mouse.events.put(("button", 0, 1, 0, 10, 20))
        mouse.events.put(("move", 12, 24))
        mouse.events.put(("button", 0, 0, 0, 12, 24))
        mouse.poll()
        # Click offset is [3,4]-[10,20], so the source follows without snap.
        np.testing.assert_allclose(self.food.position[:2], [5, 8])
        forward.assert_called_once_with(mouse.model, mouse.data)

    @patch("mouse_interaction.mujoco.mj_forward")
    def test_empty_drag_does_not_move_any_object(self, forward):
        mouse = self.make_mouse(None)
        mouse.events.put(("button", 0, 1, 0, 10, 20))
        mouse.events.put(("move", 12, 24))
        mouse.events.put(("button", 0, 0, 0, 12, 24))
        mouse.poll()
        np.testing.assert_allclose(self.food.position, [3, 4, 1])
        self.assertEqual(self.controller.selected_name, "NONE")
        forward.assert_not_called()


if __name__ == '__main__':
    unittest.main()
