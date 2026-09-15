#!/usr/bin/env python3
"""
Embodied Drosophila: Brain-body closed loop with interactive 3D viewer.

Connects the fly-brain connectome simulation (LIF neurons on GPU)
to a NeuroMechFly v2 biomechanical body (flygym + MuJoCo). Behaviors emerge
from spike propagation through the real connectome — no hand-coded rules.

Usage:
    python fly_embodied.py                  # Auto-demo: cycles through stimuli
    python fly_embodied.py --stimulus p9    # Start with P9 forward walking
    python fly_embodied.py --no-auto        # Manual only (keyboard)
    python fly_embodied.py --visual         # REAL VISION: compound eye → connectome

Keys (in MuJoCo viewer window):
    1 = Sugar GRNs      -> forward walking (via downstream P9/MN9)
    2 = P9 direct       -> forward walking
    3 = LC4 looming     -> escape response (via Giant Fiber)
    4 = JO touch        -> grooming (via aDN1)
    5 = Bitter GRNs     -> aversion
    6 = Or56a olfactory  -> repulsion
    0 = No stimulus     -> spontaneous basal activity
    SPACE = Toggle auto-demo on/off
"""

import sys
import argparse
import importlib.metadata
import queue
import numpy as np
import mujoco
import mujoco.viewer

from flygym import Fly
from flygym.simulation import SingleFlySimulation
from flygym.examples.locomotion import PreprogrammedSteps
from flygym.examples.locomotion.turning_controller import HybridTurningController

from brain_body_bridge import (
    BrainEngine, DNRateDecoder, BrainBodyBridge, STIMULI, DN_GROUPS,
)
from visual_system import VisualSystem
from looming_arena import LoomingArena
from brain_monitor import BrainMonitorProcess
from somatosensory import SomatosensorySystem, VibrationSource
from gustatory import GustatorySystem, TasteZone
from olfactory import OlfactorySystem, OdorSource
from vocalization import WingSongSystem
from flight import FlightSystem, FlightState
from terrarium_controller import TerrariumController
from interaction_controller import InteractionController
from camera_controller import CameraController
from terrarium_hud import TerrariumHUD, monitor_fields
from mouse_interaction import MouseInteraction
from terrarium_viewer import TerrariumViewer
from wall_sensing import WallMechanosensor

try:
    from consciousness import ConsciousnessDetector
except ImportError:
    ConsciousnessDetector = None


# ============================================================================
# Auto-demo sequence: cycles through stimuli so the fly is always active
# ============================================================================

AUTO_DEMO_SEQUENCE = [
    # (stimulus_name, duration_seconds, description)
    ('p9',    4.0, 'Forward walking (P9 neurons)'),
    ('lc4',   2.0, 'ESCAPE! (LC4 looming -> Giant Fiber)'),
    (None,    2.0, 'Recovery (no stimulus)'),
    ('sugar', 4.0, 'Sugar detected (feeding approach)'),
    (None,    1.5, 'Pause'),
    ('jo',    4.0, 'Antennal touch (JO -> grooming)'),
    (None,    2.0, 'Recovery'),
    ('p9',    3.0, 'Walking again (P9)'),
    ('lc4',   1.5, 'ESCAPE! (looming threat)'),
    ('p9',    3.0, 'Resume walking (P9)'),
    ('bitter', 3.0, 'Bitter taste (aversion)'),
    (None,    2.0, 'Pause'),
    ('or56a', 3.0, 'Bad smell (Or56a olfactory)'),
    (None,    1.5, 'Recovery'),
]


# ============================================================================
# Grooming Controller
# ============================================================================

class GroomingController:
    """Generates front-leg oscillation for antennal grooming behavior."""

    def __init__(self, preprogrammed_steps=None, freq_hz=4.0):
        self.steps = preprogrammed_steps or PreprogrammedSteps()
        self.freq = freq_hz
        self.neutral = np.zeros(42)
        for i, leg in enumerate(self.steps.legs):
            self.neutral[i * 7:(i + 1) * 7] = self.steps.get_joint_angles(
                leg, np.pi, 0.0
            )

    def get_action(self, time_s):
        """Return joints+adhesion action dict for grooming at given time."""
        joints = self.neutral.copy()
        phase = 2 * np.pi * self.freq * time_s
        femur_offset = 0.3 * np.sin(phase)
        tibia_offset = 0.4 * np.sin(phase + np.pi / 2)
        for base in (0, 21):  # LF and RF
            joints[base + 3] += femur_offset
            joints[base + 5] += tibia_offset
        adhesion = np.array([0, 1, 1, 0, 1, 1])
        return {"joints": joints, "adhesion": adhesion}


# ============================================================================
# Main Simulation
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Embodied Drosophila')
    parser.add_argument('--no-viewer', action='store_true',
                        help='Run headless (no MuJoCo viewer)')
    parser.add_argument('--no-brain', action='store_true',
                        help='Run body only with manual drive (no neural sim)')
    parser.add_argument('--no-auto', action='store_true',
                        help='Disable auto-demo (manual keyboard only)')
    parser.add_argument('--stimulus', type=str, default=None,
                        choices=list(STIMULI.keys()),
                        help='Initial stimulus to activate')
    parser.add_argument('--duration', type=float, default=0.0,
                        help='Max sim duration in seconds (0 = unlimited)')
    parser.add_argument('--visual', action='store_true',
                        help='Enable real vision: compound eye -> connectome '
                             'photoreceptors (uses LoomingArena)')
    parser.add_argument('--approach-angle', type=float, default=0.0,
                        help='Ball approach angle in degrees '
                             '(0=front, +45=right, -45=left)')
    parser.add_argument('--monitor', action='store_true',
                        help='Open brain monitor window (dorsal view)')
    parser.add_argument('--somatosensory', action='store_true',
                        help='Enable touch (contact forces) and sound '
                             '(vibration sources) via JO neurons')
    parser.add_argument('--gustatory', action='store_true',
                        help='Enable taste zones (sugar/bitter) on arena '
                             'floor via GRN neurons')
    parser.add_argument('--olfactory', action='store_true',
                        help='Enable olfactory system: attractive (Or42b) '
                             'and repulsive (Or56a) odor sources')
    parser.add_argument('--vocalize', action='store_true',
                        help='Enable wing song production (courtship/alarm) '
                             'driven by DN activity')
    parser.add_argument('--flight', action='store_true',
                        help='Enable virtual flight via external forces '
                             '(GF triggers takeoff, xfrc_applied on Thorax)')
    parser.add_argument('--consciousness', action='store_true',
                        help='Enable consciousness proxy measurement '
                        '(Phi/IIT, GWT, Self-Model, Perturbation)')
    parser.add_argument('--terrarium', action='store_true',
                        help='Enable interactive world, camera, pause and HUD controls')
    parser.add_argument('--terrarium-input-debug', action='store_true',
                        help='Log GLFW, native picking, and world drag events')
    parser.add_argument('--debug-mouse', action='store_true',
                        help='Log every mouse callback, pick, and drag update')
    args = parser.parse_args()
    args.terrarium_input_debug |= args.debug_mouse
    print(f"[Versions] mujoco={mujoco.__version__} "
          f"flygym={importlib.metadata.version('flygym')}")

    # -- State --
    # Preserve the original simulation's tonic P9 walking drive.  Terrarium
    # sensory inputs are layered onto this baseline and can still select
    # escape, feeding, grooming, or flight through the connectome.  Starting
    # terrarium mode with no stimulus leaves P9 silent and therefore makes a
    # healthy simulation correctly display IDLE forever.
    active_stimulus = [args.stimulus if args.stimulus is not None else 'p9']
    stim_changed = [True]
    auto_demo_enabled = [not args.no_auto and args.stimulus is None
                          and not args.visual]

    # Auto-demo state
    demo_idx = [0]
    demo_time_remaining = [AUTO_DEMO_SEQUENCE[0][1]]

    # -- Keyboard mapping (GLFW keycodes) --
    KEY_MAP = {
        ord('1'): 'sugar',
        ord('2'): 'p9',
        ord('3'): 'lc4',
        ord('4'): 'jo',
        ord('5'): 'bitter',
        ord('6'): 'or56a',
        ord('0'): None,
    }
    GLFW_KEY_SPACE = 32
    terrarium_ref = [None]
    interaction_ref = [None]
    mouse_ref = [None]
    # MuJoCo invokes key_callback from its viewer thread. Never mutate the
    # controller, arena, camera, model, or data there; doing so races the main
    # simulation thread and can terminate the native viewer (notably on KP 0).
    terrarium_keys = queue.SimpleQueue()

    def handle_stimulus_key(keycode):
        """Apply the legacy stimulus keys; return whether one was handled."""
        if keycode not in KEY_MAP:
            return False
        auto_demo_enabled[0] = False  # Manual key disables auto-demo
        active_stimulus[0] = KEY_MAP[keycode]
        stim_changed[0] = True
        name = active_stimulus[0]
        if name and name in STIMULI:
            print(f"\n[Manual] {STIMULI[name]['description']}")
        else:
            print("\n[Manual] OFF -- spontaneous activity")
        return True

    def key_callback(keycode):
        if args.terrarium and interaction_ref[0] is not None:
            terrarium_keys.put(keycode)
            return
        if keycode == GLFW_KEY_SPACE:
            auto_demo_enabled[0] = not auto_demo_enabled[0]
            state = "ON" if auto_demo_enabled[0] else "OFF"
            print(f"\n[Auto-demo] {state}")
            if auto_demo_enabled[0]:
                demo_idx[0] = 0
                demo_time_remaining[0] = AUTO_DEMO_SEQUENCE[0][1]
            return

        handle_stimulus_key(keycode)

    # ── Initialize brain ──
    brain = None
    if not args.no_brain:
        print("Initializing brain (138,639 neurons on GPU)...")
        # A 1 ms neural clock preserves the model's synaptic/membrane time
        # constants while keeping the 15M-synapse closed loop interactive.
        # The benchmark path retains its original 0.1 ms integration step.
        brain = BrainEngine(device='cuda', dt_ms=1.0)

    # ── Initialize visual system (if --visual) ──
    visual = None
    if args.visual and brain is not None:
        print("Initializing visual system (photoreceptor mapping)...")
        visual = VisualSystem(brain.flyid2i, brain.i2flyid)

    # ── Initialize somatosensory system (if --somatosensory) ──
    somato = None
    vibration_sources = []
    if args.somatosensory and brain is not None:
        print("Initializing somatosensory system (JO touch + sound)...")
        somato = SomatosensorySystem(brain.flyid2i)
        # Default vibration sources
        vibration_sources = [
            VibrationSource(
                position=[30.0, 20.0, 1.0],
                frequency=200.0, amplitude=0.8,
                label='courtship'),
            VibrationSource(
                position=[-20.0, -15.0, 1.0],
                frequency=400.0, amplitude=0.6,
                label='alarm'),
        ]
        for vs in vibration_sources:
            print(f"  Vibration: '{vs.label}' at "
                  f"[{vs.position[0]:.0f},{vs.position[1]:.0f}]mm "
                  f"f={vs.frequency:.0f}Hz amp={vs.amplitude:.1f}")

    # ── Initialize gustatory system (if --gustatory) ──
    taste_zones = []
    gusto = None
    if args.gustatory and brain is not None:
        print("Initializing gustatory system (sugar/bitter GRN zones)...")
        taste_zones = [
            TasteZone(center=[15.0, 5.0], radius=8.0,
                      taste='sugar', label='sugar_patch'),
            TasteZone(center=[20.0, -10.0], radius=6.0,
                      taste='bitter', label='bitter_patch'),
        ]
        gusto = GustatorySystem(brain.flyid2i, taste_zones)

    # ── Initialize olfactory system (if --olfactory) ──
    olfact = None
    odor_sources = []
    if args.olfactory and brain is not None:
        print("Initializing olfactory system (Or42b attractive + Or56a repulsive)...")
        odor_sources = [
            OdorSource(
                position=[25.0, 10.0, 1.0],
                odor_type='attractive', amplitude=0.9, spread=25.0,
                label='food'),
            OdorSource(
                position=[-15.0, -12.0, 1.0],
                odor_type='repulsive', amplitude=0.8, spread=20.0,
                label='geosmin'),
        ]
        olfact = OlfactorySystem(brain.flyid2i)
        for src in odor_sources:
            print(f"  Odor: '{src.label}' ({src.odor_type}) at "
                  f"[{src.position[0]:.0f},{src.position[1]:.0f}]mm "
                  f"amp={src.amplitude:.1f} spread={src.spread:.0f}mm")

    # ── Initialize wing song system (if --vocalize) ──
    wing_song = None
    if args.vocalize and brain is not None:
        print("Initializing wing song system (courtship/alarm via DN)...")
        wing_song = WingSongSystem(self_hearing_gain=0.2)
        print(f"  Pulse=200Hz, Sine=160Hz, Alarm=400Hz (self-hearing=20%)")

    # ── Initialize consciousness detection (if --consciousness) ──
    consciousness = None
    if args.consciousness and brain is not None:
        if ConsciousnessDetector is not None:
            consciousness = ConsciousnessDetector(brain)
        else:
            print("[WARN] consciousness.py not found, --consciousness ignored")

    # ── Initialize flight system placeholder (if --flight) ──
    flight_sys = None
    thorax_body_id = -1
    qpos_adr = -1
    dof_adr = -1
    proboscis_jnt_id = -1

    # ── Initialize body ──
    print("Initializing body (NeuroMechFly v2 + MuJoCo)...")
    contact_sensors = [
        f"{leg}{seg}"
        for leg in ["LF", "LM", "LH", "RF", "RM", "RH"]
        for seg in ["Tibia", "Tarsus1", "Tarsus2",
                     "Tarsus3", "Tarsus4", "Tarsus5"]
    ]

    fly = Fly(
        enable_adhesion=True,
        draw_adhesion=False,
        contact_sensor_placements=contact_sensors,
        enable_vision=args.visual,
    )

    # ── Add proboscis joint (Rostrum has no joint in stock NeuroMechFly) ──
    rostrum_body = fly.model.find("body", "Rostrum")
    if rostrum_body is not None:
        rostrum_body.add(
            "joint",
            name="joint_Proboscis",
            type="hinge",
            axis=[0, 1, 0],       # pitch axis: rotates proboscis down
            range=[-0.1, 1.2],    # retracted to fully extended (radians)
            stiffness=50.0,       # spring pulls it back (retracted at rest)
            damping=5.0,
        )
        print("[Proboscis] Added hinge joint to Rostrum body")
    else:
        print("[Proboscis] WARNING: Rostrum body not found in fly model")

    # Use LoomingArena when visual mode is enabled
    arena_kwargs = {}
    if args.visual:
        arena_ground = 500 if args.flight else 100
        arena_start = 120.0 if args.flight else 80.0
        arena_kwargs['arena'] = LoomingArena(
            ball_radius=6.0,
            approach_speed=15.0,
            start_distance=arena_start,
            ball_height=1.5,
            approach_angle=args.approach_angle,
            taste_zones=taste_zones,
            odor_sources=odor_sources,
            ground_size=arena_ground,
        )
        angle_str = f" angle={args.approach_angle}°" if args.approach_angle != 0 else ""
        print(f"[Visual] LoomingArena: r=6mm sphere from {arena_start:.0f}mm at 15mm/s{angle_str}")
        if args.terrarium:
            arena_kwargs['arena'].enable_interactive()

    sim = HybridTurningController(
        fly=fly,
        timestep=1e-4,
        seed=0,
        **arena_kwargs,
    )

    # ── Disable flygym's internal vision rendering BEFORE reset ──
    # Cameras and retina are already initialized from Fly.__init__().
    # We must prevent flygym from calling dm_control's physics.render()
    # during reset/step — it creates an offscreen GL context that
    # conflicts with the MuJoCo passive viewer on Windows.
    if args.visual:
        fly.enable_vision = False

    # ── Initialize bridge ──
    decoder = DNRateDecoder(
        window_ms=50.0, dt_ms=brain.dt if brain is not None else 1.0,
        max_rate=200.0)
    bridge = BrainBodyBridge(decoder, escape_threshold=0.3,
                             groom_threshold=0.02)
    groom_ctrl = GroomingController()

    # ── Register lateralized populations for directional escape ──
    if visual is not None and brain is not None:
        lplc2_idx = visual.get_lplc2_indices(brain.flyid2i)
        lc4_idx = visual.get_lc4_indices(brain.flyid2i)
        for name, indices in {**lplc2_idx, **lc4_idx}.items():
            brain.register_population(name, indices)
            decoder.register_population(name)

    # ── Register JO populations for monitoring ──
    if somato is not None and brain is not None:
        if len(somato.touch_idx_left) > 0:
            brain.register_population('JO_touch_L', somato.touch_idx_left)
            decoder.register_population('JO_touch_L')
        if len(somato.touch_idx_right) > 0:
            brain.register_population('JO_touch_R', somato.touch_idx_right)
            decoder.register_population('JO_touch_R')
        if len(somato.sound_idx_left) > 0:
            brain.register_population('JO_sound_L', somato.sound_idx_left)
            decoder.register_population('JO_sound_L')
        if len(somato.sound_idx_right) > 0:
            brain.register_population('JO_sound_R', somato.sound_idx_right)
            decoder.register_population('JO_sound_R')

    # ── Reset simulation ──
    obs, info = sim.reset(seed=0)
    print(f"Fly spawned at {obs['fly'][0]} mm")

    # ── Post-reset: initialize flight system with model data ──
    if args.flight and brain is not None:
        model_ptr = sim.physics.model.ptr
        fly_name = fly.name

        # Find Thorax body id
        thorax_name = f"{fly_name}/Thorax"
        thorax_body_id = mujoco.mj_name2id(
            model_ptr, mujoco.mjtObj.mjOBJ_BODY, thorax_name)
        if thorax_body_id < 0:
            thorax_body_id = mujoco.mj_name2id(
                model_ptr, mujoco.mjtObj.mjOBJ_BODY, "Thorax")

        # Total mass: sum ONLY fly bodies (prefix = fly_name/)
        fly_mass = 0.0
        for bid in range(model_ptr.nbody):
            bname = mujoco.mj_id2name(
                model_ptr, mujoco.mjtObj.mjOBJ_BODY, bid)
            if bname and bname.startswith(f"{fly_name}/"):
                fly_mass += float(model_ptr.body_mass[bid])

        # Gravity: flygym already uses mm units, so opt.gravity is in mm/s²
        gravity_mm = float(abs(model_ptr.opt.gravity[2]))

        flight_sys = FlightSystem(
            total_mass=fly_mass,
            gravity=gravity_mm,
        )
        # Find free joint for orientation override during flight
        freejoint_id = -1
        for jid in range(model_ptr.njnt):
            if model_ptr.jnt_type[jid] == mujoco.mjtJoint.mjJNT_FREE:
                jbody = model_ptr.jnt_bodyid[jid]
                jname = mujoco.mj_id2name(
                    model_ptr, mujoco.mjtObj.mjOBJ_BODY, jbody)
                if jname and jname.startswith(f"{fly_name}/"):
                    freejoint_id = jid
                    break
        if freejoint_id >= 0:
            qpos_adr = int(model_ptr.jnt_qposadr[freejoint_id])
            dof_adr = int(model_ptr.jnt_dofadr[freejoint_id])
        else:
            qpos_adr = dof_adr = -1

        print(f"[Flight] mass={fly_mass*1e6:.1f}mg gravity={gravity_mm:.0f}mm/s² "
              f"mg={flight_sys.mg:.6f}mN thorax_id={thorax_body_id} "
              f"freejoint={freejoint_id}")

    # ── Find proboscis joint (added dynamically to Rostrum) ──
    model_ptr = sim.physics.model.ptr
    fly_name = fly.name
    if thorax_body_id < 0:
        for thorax_name in (f"{fly_name}/Thorax", "Thorax"):
            thorax_body_id = mujoco.mj_name2id(
                model_ptr, mujoco.mjtObj.mjOBJ_BODY, thorax_name)
            if thorax_body_id >= 0:
                break
    for jname_candidate in [f"{fly_name}/joint_Proboscis", "joint_Proboscis"]:
        proboscis_jnt_id = mujoco.mj_name2id(
            model_ptr, mujoco.mjtObj.mjOBJ_JOINT, jname_candidate)
        if proboscis_jnt_id >= 0:
            break
    if proboscis_jnt_id >= 0:
        proboscis_qadr = int(model_ptr.jnt_qposadr[proboscis_jnt_id])
        print(f"[Proboscis] joint_id={proboscis_jnt_id} qpos_adr={proboscis_qadr}")
    else:
        proboscis_qadr = -1
        print("[Proboscis] WARNING: joint not found after compilation")

    # ── Set up manual vision rendering ──
    eye_renderer = None
    retina = None
    geom_hide_ids = []
    eye_cam_ids = {}

    if visual is not None:
        retina = fly.retina
        fly_name = fly.name

        model_ptr = sim.physics.model.ptr

        # Create MuJoCo-native renderer (coexists with passive viewer)
        eye_renderer = mujoco.Renderer(model_ptr, height=512, width=450)

        # Locate eye cameras
        for side in ["L", "R"]:
            cam_name = f"{fly_name}/{side}Eye_cam"
            cid = mujoco.mj_name2id(
                model_ptr, mujoco.mjtObj.mjOBJ_CAMERA, cam_name)
            eye_cam_ids[side] = cid
            print(f"[Vision] Camera '{cam_name}' -> id={cid}")

        # Locate geoms to hide during eye rendering (avoid self-occlusion)
        for geom_name in getattr(fly, '_geoms_to_hide', []):
            full_name = f"{fly_name}/{geom_name}"
            gid = mujoco.mj_name2id(
                model_ptr, mujoco.mjtObj.mjOBJ_GEOM, full_name)
            if gid >= 0:
                geom_hide_ids.append(gid)
        print(f"[Vision] {len(geom_hide_ids)} geoms hidden during eye render")

    # Terrarium mode owns GLFW so mouse delivery is a public, testable part of
    # our architecture. Non-terrarium runs retain MuJoCo's passive viewer.
    viewer = None
    camera = None
    terrarium_hud = None
    if not args.no_viewer:
        print("Launching MuJoCo viewer...")
        if args.terrarium:
            print("[Viewer] architecture=TerrariumViewer (application-owned GLFW)")
            viewer = TerrariumViewer(
                sim.physics.model.ptr, sim.physics.data.ptr,
                key_callback=key_callback)
        else:
            print("[Viewer] architecture=mujoco.viewer.launch_passive")
            viewer = mujoco.viewer.launch_passive(
                sim.physics.model.ptr, sim.physics.data.ptr,
                key_callback=key_callback,
                show_left_ui=False,
                show_right_ui=False,
            )
        # Configure viewer options and camera
        if viewer is not None:
            viewer.opt.label = mujoco.mjtLabel.mjLABEL_SITE
            # Hide fly sites and show the arena's plain-language object labels.
            for g in range(3):
                viewer.opt.sitegroup[g] = 0
            viewer.opt.sitegroup[3] = 1
            viewer.opt.sitegroup[4] = 1
        if viewer is not None and thorax_body_id >= 0 and args.terrarium:
            camera = CameraController(viewer, thorax_body_id)
        elif viewer is not None and thorax_body_id >= 0:
            viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
            viewer.cam.trackbodyid = thorax_body_id
            viewer.cam.distance = 40.0
            viewer.cam.azimuth = -120.0
            viewer.cam.elevation = -25.0

    # Terrarium controls are available only with the visual arena. Keeping the
    # feature opt-in preserves the original viewer and all headless paths.
    if args.terrarium:
        if not args.visual:
            parser.error('--terrarium requires --visual')

        def reset_simulation():
            """Repair both MuJoCo and FlyGym state after viewer Backspace."""
            nonlocal obs, info, body_step
            obs, info = sim.reset(seed=0)
            body_step = 0

        terrarium_ref[0] = TerrariumController(
            arena_kwargs['arena'], taste_zones, odor_sources)
        interaction_ref[0] = InteractionController(
            terrarium_ref[0], camera, reset_callback=reset_simulation)
        if viewer is not None:
            terrarium_hud = TerrariumHUD(viewer, terrarium_ref[0], camera)
            mouse_ref[0] = MouseInteraction(
                viewer, terrarium_ref[0], model=sim.physics.model.ptr,
                data=sim.physics.data.ptr, debug=args.terrarium_input_debug)
            terrarium_ref[0].mouse_available = mouse_ref[0].available
            if not mouse_ref[0].available:
                print("[Terrarium] Mouse drag unavailable: "
                      f"{mouse_ref[0].unavailable_reason}. "
                      "Using numpad movement fallback.")

    wall_sensor = None
    if args.terrarium and somato is not None:
        wall_sensor = WallMechanosensor(sim.physics.model.ptr)

    # ── Set initial stimulus ──
    if brain is not None:
        brain.set_stimulus(active_stimulus[0])
        stim_changed[0] = False
        stim_desc = STIMULI.get(active_stimulus[0], {}).get(
            'description', active_stimulus[0] or 'none')
        print(f"Initial stimulus: {stim_desc}")

    # ── Launch brain monitor (separate process) ──
    monitor = None
    if args.monitor or args.terrarium:
        print("Launching brain monitor" +
              (" (terrarium controls are shown here)..."
               if args.terrarium else "..."))
        monitor = BrainMonitorProcess()
        monitor.start()

    # ── Timing constants ──
    MONITOR_INTERVAL = 500   # send data every 500 body steps (~50ms sim)
    BRAIN_RATIO = 100        # poll sensors every 100 body steps (10 ms)
    # Advance enough neural ticks to cover the complete interval.  The
    # interactive brain uses a stable 1 ms integration step, so this is ten
    # sparse connectome updates per 10 ms sensor/body interval rather than the
    # prohibitively slow hundred updates required at benchmark resolution.
    BRAIN_SUBSTEPS = (brain.steps_for_elapsed(BRAIN_RATIO * sim.timestep)
                      if brain is not None else 1)
    VISION_RATIO = 1000     # process vision every 1000 body steps (= 100ms, 10Hz)
    STEPS_PER_FRAME = 167    # body steps per viewer frame (~60fps at 1e-4 timestep)
    STATUS_INTERVAL = 10000  # status print every 1.0s sim time

    body_step = 0
    prev_mode = 'walking'
    cached_visual = (None, None)  # cached ALL visual layer (indices, rates)
    last_vision_obs = None        # last vision obs for diagnostics
    physics_errors = 0            # consecutive physics error counter

    import time as _time
    _frame_target = 1.0 / 60.0       # 16.7ms per frame
    _next_viewer_sync = _time.perf_counter()
    _fps_counter = 0
    _fps_timer = _time.perf_counter()
    _measured_fps = 0.0

    print()
    print("=" * 70)
    print("  EMBODIED DROSOPHILA -- Interactive Brain-Body Simulation")
    if visual is not None:
        print("  *** REAL VISION ACTIVE: compound eye -> connectome ***")
    if somato is not None:
        print("  *** SOMATOSENSORY ACTIVE: touch + sound -> JO neurons ***")
    if gusto is not None:
        print("  *** GUSTATORY ACTIVE: sugar/bitter zones -> GRN neurons ***")
    if olfact is not None:
        print("  *** OLFACTORY ACTIVE: food/danger odors -> ORN neurons ***")
    if wing_song is not None:
        print("  *** VOCALIZATION ACTIVE: wing song -> JO self-hearing ***")
    if flight_sys is not None:
        print(f"  *** FLIGHT ACTIVE: GF > {flight_sys.takeoff_thresh} triggers virtual takeoff ***")
    if args.terrarium:
        print("  *** TERRARIUM ACTIVE: manipulate the world; the brain controls the fly ***")
    print("=" * 70)
    if auto_demo_enabled[0]:
        print("  MODE: Auto-demo (cycles through stimuli automatically)")
        print("  Press SPACE to toggle auto-demo on/off")
    else:
        print("  MODE: Manual (use keyboard to change stimulus)")
    if visual is not None:
        print("  VISION: Photoreceptors receive real visual input from flygym")
        print("  A dark sphere approaches — escape should emerge naturally!")
    print("  Keys: 1=sugar 2=P9 3=looming 4=grooming 5=bitter 6=olfactory")
    print("  0=off  SPACE=toggle auto  |  Close viewer to exit")
    if args.terrarium:
        print("  " + InteractionController.HELP.replace("\n", "\n  "))
    print("=" * 70)
    print()

    # ── Main loop ──
    try:
        while True:
            # The owned GLFW window must receive OS events even when a neural
            # step is slow. Passive viewer builds poll on their own thread.
            if isinstance(viewer, TerrariumViewer):
                viewer.poll_events()
            # Apply viewer input on the simulation thread. SimpleQueue keeps
            # the cross-thread callback itself limited to an atomic enqueue.
            if interaction_ref[0] is not None:
                while True:
                    try:
                        keycode = terrarium_keys.get_nowait()
                    except queue.Empty:
                        break
                    if not interaction_ref[0].on_key(keycode):
                        handle_stimulus_key(keycode)
            if mouse_ref[0] is not None:
                mouse_ref[0].poll()

            # Check exit conditions
            if viewer is not None:
                if not viewer.is_running():
                    break
            elif args.duration > 0:
                if body_step * sim.timestep >= args.duration:
                    break

            # Pausing stops simulation time and neural/physics updates, but the
            # passive viewer remains responsive.
            if (terrarium_ref[0] is not None and terrarium_ref[0].paused):
                if viewer is not None:
                    if camera is not None:
                        camera.keep_terrarium_visuals_clean()
                    viewer.sync()
                    _time.sleep(0.02)
                continue

            # ── Auto-demo: advance sequence ──
            if auto_demo_enabled[0] and brain is not None:
                demo_time_remaining[0] -= sim.timestep
                if demo_time_remaining[0] <= 0:
                    demo_idx[0] = (demo_idx[0] + 1) % len(AUTO_DEMO_SEQUENCE)
                    stim_name, duration, desc = AUTO_DEMO_SEQUENCE[demo_idx[0]]
                    demo_time_remaining[0] = duration
                    active_stimulus[0] = stim_name
                    stim_changed[0] = True
                    print(f"\n  >>> [{desc}] "
                          f"({stim_name or 'none'}, {duration:.1f}s)")

            # ── Update stimulus ──
            if stim_changed[0] and brain is not None:
                brain.set_stimulus(active_stimulus[0])
                stim_changed[0] = False
                # Re-apply cached visual rates (set_stimulus zeroes all rates)
                if cached_visual[0] is not None:
                    brain.set_visual_rates(*cached_visual)
                # Re-apply somatosensory rates
                if somato is not None:
                    jo_idx, jo_rates = somato.get_rates()
                    brain.set_sensory_rates(jo_idx, jo_rates)
                # Re-apply gustatory rates
                if gusto is not None:
                    grn_idx, grn_rates = gusto.get_rates()
                    brain.set_sensory_rates(grn_idx, grn_rates)
                # Re-apply olfactory rates
                if olfact is not None:
                    or_idx, or_rates = olfact.get_rates()
                    brain.set_sensory_rates(or_idx, or_rates)

            # ── Visual processing (every VISION_RATIO body steps) ──
            #     Uses mujoco.Renderer (not dm_control physics.render)
            #     to avoid GL context conflict with the passive viewer.
            if visual is not None and body_step % VISION_RATIO == 0:
                model_ptr = sim.physics.model.ptr
                data_ptr = sim.physics.data.ptr

                # Hide self-geoms (eyes, antennae, coxae) to avoid occlusion
                saved_alpha = []
                for gid in geom_hide_ids:
                    saved_alpha.append(model_ptr.geom_rgba[gid, 3].copy())
                    model_ptr.geom_rgba[gid, 3] = 0.0

                # Render both eyes with MuJoCo native renderer
                readouts = []
                for side in ["L", "R"]:
                    cid = eye_cam_ids.get(side, -1)
                    if cid < 0:
                        readouts.append(np.zeros((721, 2), dtype=np.float32))
                        continue
                    eye_renderer.update_scene(data_ptr, camera=cid)
                    raw_img = eye_renderer.render()
                    fish_img = retina.correct_fisheye(raw_img)
                    hex_pxls = retina.raw_image_to_hex_pxls(fish_img)
                    readouts.append(hex_pxls)

                # Restore self-geoms
                for i, gid in enumerate(geom_hide_ids):
                    model_ptr.geom_rgba[gid, 3] = saved_alpha[i]

                vision_obs = np.array(readouts, dtype=np.float32)
                last_vision_obs = vision_obs

                # Inject ALL visual layers: R1-R8, L1, L2, Mi1, Tm1, Tm2, T2
                # T2 -> LC4 -> GF propagates through pure connectome
                vis_idx, vis_rates = visual.process_visual_layers(vision_obs)
                cached_visual = (vis_idx, vis_rates)
                brain.set_visual_rates(vis_idx, vis_rates)

            # ── Somatosensory processing (every brain step) ──
            if somato is not None and body_step % BRAIN_RATIO == 0:
                # Touch: read contact forces from MuJoCo
                contact_forces = obs.get('contact_forces', np.zeros((36, 3)))
                somato.process_contact(contact_forces)

                # Physical glass contacts on any fly body geom become
                # lateralized JO input.  This updates the connectome; it does
                # not reverse, turn, or otherwise command the animal.
                if wall_sensor is not None:
                    fly_pos_wall = obs['fly'][0]
                    fly_orient_wall = obs.get('fly_orientation', np.zeros(3))
                    heading_wall = float(np.arctan2(
                        fly_orient_wall[1], fly_orient_wall[0]))
                    wall_l, wall_r, wall_force = wall_sensor.rates(
                        sim.physics.data.ptr, fly_pos_wall, heading_wall,
                        somato.TOUCH_MAX_RATE, somato.FORCE_FLOOR,
                        somato.FORCE_SAT)
                    somato.touch_rate_left = max(somato.touch_rate_left, wall_l)
                    somato.touch_rate_right = max(somato.touch_rate_right, wall_r)
                    somato.max_contact_force = max(
                        somato.max_contact_force, wall_force)

                # Mouse/P pokes enter the same JO mechanosensory populations.
                # No behavioral mode or motor action is selected here.
                if terrarium_ref[0] is not None:
                    poke_l, poke_r = terrarium_ref[0].consume_poke_rates(
                        BRAIN_RATIO * sim.timestep, somato.TOUCH_MAX_RATE)
                    somato.touch_rate_left = max(somato.touch_rate_left, poke_l)
                    somato.touch_rate_right = max(somato.touch_rate_right, poke_r)
                    somato.max_contact_force = max(
                        somato.max_contact_force,
                        somato.FORCE_FLOOR + max(poke_l, poke_r) /
                        somato.TOUCH_MAX_RATE *
                        (somato.FORCE_SAT - somato.FORCE_FLOOR))

                # Sound: compute vibration from fly position and heading
                fly_pos = obs['fly'][0]  # position in mm
                fly_orient = obs.get('fly_orientation', np.zeros(3))
                # fly_orientation is body X-axis (forward) in world frame
                fly_heading = float(np.arctan2(fly_orient[1], fly_orient[0]))
                somato.process_vibration(fly_pos, fly_heading, vibration_sources)

                # Inject JO rates into brain
                jo_idx, jo_rates = somato.get_rates()
                if args.terrarium:
                    all_jo_idx = np.concatenate([
                        somato.touch_idx_left, somato.touch_idx_right,
                        somato.sound_idx_left, somato.sound_idx_right])
                    brain.clear_sensory_rates(all_jo_idx)
                brain.set_sensory_rates(jo_idx, jo_rates)

                # Update bridge with somatosensory state
                bridge.tactile_force = somato.max_contact_force
                bridge.sound_orientation_bias = (
                    0.0 if args.terrarium else somato.orientation_bias)

            # ── Gustatory processing (every brain step) ──
            if gusto is not None and body_step % BRAIN_RATIO == 0:
                end_effectors = obs.get('end_effectors', np.zeros((6, 3)))
                gusto.process(end_effectors)

                # Inject GRN rates into brain
                grn_idx, grn_rates = gusto.get_rates()
                if args.terrarium:
                    brain.clear_sensory_rates(np.concatenate([
                        gusto.sugar_indices, gusto.bitter_indices]))
                brain.set_sensory_rates(grn_idx, grn_rates)

                # Update bridge with gustatory state
                # Terrarium mode relies on GRN -> connectome -> DN activity;
                # legacy mode retains its bridge-level aversion fallback.
                bridge.bitter_contact = gusto.bitter_active
                bridge.bitter_active = (gusto.bitter_active and
                                        not args.terrarium)

            # ── Olfactory processing (every brain step) ──
            if olfact is not None and body_step % BRAIN_RATIO == 0:
                fly_pos = obs['fly'][0]
                fly_orient = obs.get('fly_orientation', np.zeros(3))
                fly_heading = float(np.arctan2(fly_orient[1], fly_orient[0]))
                olfact.process(fly_pos, fly_heading, odor_sources)

                # Inject ORN rates into brain
                or_idx, or_rates = olfact.get_rates()
                if args.terrarium:
                    brain.clear_sensory_rates(np.concatenate([
                        olfact.att_idx_left, olfact.att_idx_right,
                        olfact.rep_idx_left, olfact.rep_idx_right]))
                brain.set_sensory_rates(or_idx, or_rates)

                # Update bridge with olfactory state
                if args.terrarium:
                    bridge.olfactory_attraction_bias = 0.0
                    bridge.olfactory_repulsive = False
                    bridge.olfactory_repulsion_bias = 0.0
                else:
                    bridge.olfactory_attraction_bias = olfact.attraction_bias
                    bridge.olfactory_repulsive = olfact.is_repulsive_escape
                    bridge.olfactory_repulsion_bias = olfact.repulsion_bias

            # ── Wing song processing (every brain step, silent during flight) ──
            if wing_song is not None and body_step % BRAIN_RATIO == 0:
                if bridge.mode != 'flight':
                    fly_pos_ws = obs['fly'][0]
                    wing_song.process(decoder, fly_pos_ws, BRAIN_RATIO * sim.timestep)
                elif wing_song.is_singing:
                    # Flying fly doesn't sing — wings are for flight
                    wing_song.active_song = None
                    wing_song.wing_freq = 0.0
                    wing_song.wing_amp = 0.0

                # Add wing song vibration to somatosensory input
                if somato is not None and wing_song.is_singing:
                    wing_sources = wing_song.get_vibration_sources()
                    all_vib = vibration_sources + wing_sources
                    fly_orient_ws = obs.get('fly_orientation', np.zeros(3))
                    heading_ws = float(np.arctan2(fly_orient_ws[1], fly_orient_ws[0]))
                    somato.process_vibration(fly_pos_ws, heading_ws, all_vib)
                    # Re-inject updated JO rates
                    jo_idx, jo_rates = somato.get_rates()
                    brain.set_sensory_rates(jo_idx, jo_rates)

            # ── Flight processing (every brain step) ──
            if flight_sys is not None and body_step % BRAIN_RATIO == 0:
                fly_pos_fl = obs['fly'][0]
                # fly_orientation IS the forward direction vector (body X-axis in world)
                fly_fwd = obs.get('fly_orientation', np.array([1.0, 0.0, 0.0]))
                flight_sys.update(
                    decoder, fly_pos_fl, fly_fwd,
                    BRAIN_RATIO * sim.timestep)
                bridge.flight_active = flight_sys.is_airborne

            # ── Brain batch (preserve the model's 0.1 ms neural timestep) ──
            if brain is not None and body_step % BRAIN_RATIO == 0:
                on_neural_step = None
                if consciousness is not None:
                    def on_neural_step():
                        consciousness.update(body_step, bridge.mode)
                brain.advance(decoder, BRAIN_SUBSTEPS, on_neural_step)

            # ── Per-eye T2 fallback for directional escape ──
            if visual is not None and cached_visual[0] is not None:
                vis_eye = visual._T2_eye
                vis_rates_arr = cached_visual[1]
                if vis_rates_arr is not None and len(vis_rates_arr) > 0:
                    mask_L = vis_eye == 0
                    mask_R = vis_eye == 1
                    t2_left = float(vis_rates_arr[mask_L].mean()) if mask_L.any() else 0.0
                    t2_right = float(vis_rates_arr[mask_R].mean()) if mask_R.any() else 0.0
                    bridge.visual_threat_bias = (
                        (t2_right - t2_left) / (t2_left + t2_right + 1e-6))

            # ── Compute drive from DN rates ──
            drive = bridge.compute_drive(dt=BRAIN_RATIO * sim.timestep)

            # ── Mode transitions (throttle prints to avoid I/O spam) ──
            if bridge.mode != prev_mode:
                if (bridge.mode == 'flight' or prev_mode == 'flight'
                        or body_step % 100 == 0):
                    print(f"  >> Behavior: {prev_mode} -> {bridge.mode}")
                    if bridge.mode == 'flight' and flight_sys is not None:
                        h = flight_sys._escape_heading
                        y = flight_sys._escape_yaw
                        print(f"     [Flight] escape heading=[{h[0]:.2f},{h[1]:.2f}] "
                              f"yaw={np.degrees(y):.1f}°")
                prev_mode = bridge.mode

            # ── Apply flight forces (before physics step) ──
            if flight_sys is not None:
                data_ptr = sim.physics.data.ptr
                if flight_sys.is_airborne:
                    data_ptr.xfrc_applied[thorax_body_id] = flight_sys.force_torque
                else:
                    # Clear residual forces when grounded
                    data_ptr.xfrc_applied[thorax_body_id] = 0.0

            # ── Body step ──
            try:
                if bridge.mode == 'flight':
                    # Flight: legs frozen in neutral pose, adhesion OFF
                    flight_action = {
                        "joints": groom_ctrl.neutral.copy(),
                        "adhesion": np.zeros(6),
                    }
                    obs, reward, terminated, truncated, info = \
                        SingleFlySimulation.step(sim, flight_action)
                elif bridge.mode == 'grooming':
                    groom_action = groom_ctrl.get_action(
                        body_step * sim.timestep)
                    obs, reward, terminated, truncated, info = \
                        SingleFlySimulation.step(sim, groom_action)
                else:
                    obs, reward, terminated, truncated, info = sim.step(drive)
                physics_errors = 0  # reset on success

                # ── Proboscis extension during feeding ──
                if proboscis_qadr >= 0 and bridge.mode == 'feeding':
                    sim.physics.data.ptr.qpos[proboscis_qadr] = 1.0

                # ── Orientation override during flight (post-step) ──
                # Directly set the free joint quaternion to prevent spinning.
                # Torques can't reliably control orientation on an articulated
                # body with 100+ joints. This guarantees rigid heading lock.
                if (flight_sys is not None and flight_sys.is_airborne
                        and qpos_adr >= 0):
                    data_ptr = sim.physics.data.ptr
                    desired_quat = flight_sys.get_desired_quat()
                    data_ptr.qpos[qpos_adr + 3:qpos_adr + 7] = desired_quat
                    data_ptr.qvel[dof_adr + 3:dof_adr + 6] = 0.0
                    # During landing: damp upward velocity to help descent
                    if flight_sys.state == FlightState.LANDING:
                        vz = data_ptr.qvel[dof_adr + 2]
                        if vz > 0:  # going up — damp it
                            data_ptr.qvel[dof_adr + 2] = vz * 0.95
                        # Also damp horizontal for clean landing
                        data_ptr.qvel[dof_adr + 0] *= 0.98
                        data_ptr.qvel[dof_adr + 1] *= 0.98

            except Exception as e:
                physics_errors += 1
                if physics_errors >= 50:
                    print(f"  Physics unstable ({physics_errors} errors): {e}")
                    break
                continue  # skip this step, try to recover

            body_step += 1

            # ── Sync viewer at wall-clock 60fps ──
            if viewer is not None and body_step % STEPS_PER_FRAME == 0:
                _now = _time.perf_counter()
                # Pace simulation to real-time
                _sleep = _next_viewer_sync - _now
                if _sleep > 0.001:
                    _time.sleep(_sleep)
                if camera is not None:
                    # The native MuJoCo viewer also binds C to contact-force
                    # visualization.  Keep that diagnostic off because C is
                    # the terrarium free/follow camera binding.
                    camera.keep_terrarium_visuals_clean()
                if terrarium_hud is not None:
                    terrarium_hud.draw()
                viewer.sync()
                # Prevent accumulated time debt when falling behind
                speed = terrarium_ref[0].speed if terrarium_ref[0] else 1.0
                _next_viewer_sync = max(
                    _next_viewer_sync, _now) + _frame_target / speed
                # FPS measurement
                _fps_counter += 1
                if _now - _fps_timer >= 1.0:
                    _measured_fps = _fps_counter / (_now - _fps_timer)
                    _fps_counter = 0
                    _fps_timer = _now

            # ── Status print ──
            if body_step % STATUS_INTERVAL == 0:
                t_sim = body_step * sim.timestep
                pos = obs['fly'][0]
                stim_label = active_stimulus[0] or 'none'
                auto_tag = " [auto]" if auto_demo_enabled[0] else ""
                pos_z = pos[2] if len(pos) > 2 else 0.0
                flight_tag = ""
                if flight_sys is not None and flight_sys.is_airborne:
                    flight_tag = f"  | {flight_sys.get_status_str()}"
                fps_tag = f" {_measured_fps:.0f}fps" if _measured_fps > 0 else ""
                status_line = (
                    f"  t={t_sim:.1f}s{fps_tag}  stim={stim_label:>6s}{auto_tag}  "
                    f"pos=[{pos[0]:.1f}, {pos[1]:.1f}, {pos_z:.1f}] mm  "
                    f"{bridge.get_status_str()}{flight_tag}"
                )
                # Add visual circuit monitoring when vision is active
                if visual is not None:
                    d = decoder
                    gf_rate = np.mean([
                        d.get_normalized('GF_1'),
                        d.get_normalized('GF_2')])
                    ball_x = getattr(
                        arena_kwargs.get('arena'), 'ball_pos',
                        np.array([0]))[0]
                    # LC4 spike monitoring (downstream from lamina)
                    lc4_info = ""
                    if brain is not None:
                        lc4_idx = brain.stim_indices.get('lc4', [])
                        if lc4_idx:
                            spk = brain.state[2]
                            lc4_spikes = spk[0, lc4_idx].sum().item()
                            lc4_info = f" LC4spk={lc4_spikes:.0f}"
                    # Vision diagnostics (retina values are [0,1])
                    vis_info = ""
                    if last_vision_obs is not None:
                        bL = np.mean(last_vision_obs[0])
                        bR = np.mean(last_vision_obs[1])
                        n_dark_L = np.sum(
                            np.mean(last_vision_obs[0], axis=1) < 0.25)
                        n_dark_R = np.sum(
                            np.mean(last_vision_obs[1], axis=1) < 0.25)
                        vis_info = (
                            f" bright=[{bL:.2f},{bR:.2f}]"
                            f" dark_omm=[{n_dark_L},{n_dark_R}]")
                    # Lamina neuron counts
                    lamina_info = f" L1={visual._n_L1} L2={visual._n_L2} T2={visual._n_T2}"
                    # LPLC2/LC4 laterality
                    lplc2_info = ""
                    lplc2_L = decoder.get_pop_rate('LPLC2_left')
                    lplc2_R = decoder.get_pop_rate('LPLC2_right')
                    if lplc2_L > 0 or lplc2_R > 0:
                        lplc2_info = f" LPLC2=[{lplc2_L:.1f},{lplc2_R:.1f}]"
                    status_line += (
                        f"  | ball_x={ball_x:.0f}"
                        f" GF={gf_rate:.3f}{lc4_info}"
                        f"{lamina_info}{lplc2_info}{vis_info}")
                # Add somatosensory monitoring
                if somato is not None:
                    somato_str = somato.get_status_str()
                    if somato_str != "JO=silent":
                        status_line += f"  | {somato_str}"
                # Add gustatory monitoring
                if gusto is not None:
                    gusto_str = gusto.get_status_str()
                    if gusto_str:
                        status_line += f"  | {gusto_str}"
                # Add olfactory monitoring
                if olfact is not None:
                    olf_str = olfact.get_status_str()
                    if olf_str:
                        status_line += f"  | {olf_str}"
                # Add wing song monitoring
                if wing_song is not None:
                    ws_str = wing_song.get_status_str()
                    if ws_str:
                        status_line += f"  | {ws_str}"
                # Add consciousness monitoring
                if consciousness is not None:
                    status_line += f"  | {consciousness.get_status_str()}"
                print(status_line)

            # ── Send data to brain monitor ──
            if monitor is not None and body_step % MONITOR_INTERVAL == 0:
                d = decoder
                mon_data = {
                    't_sim': body_step * sim.timestep,
                    'mode': bridge.mode,
                    'drive': [bridge.left_drive, bridge.right_drive],
                    'stimulus': active_stimulus[0] or 'none',
                    'dn_forward': d.get_group_rate('forward'),
                    'dn_escape': d.get_group_rate('escape'),
                    'dn_groom': d.get_group_rate('groom'),
                    'dn_backward': d.get_group_rate('backward'),
                    'dn_feed': d.get_group_rate('feed'),
                    'dn_turn_L': d.get_group_rate('turn_L'),
                    'dn_turn_R': d.get_group_rate('turn_R'),
                    'threat_asym': bridge.threat_asym,
                    'network': brain.last_activity if brain is not None else 0.0,
                }
                if terrarium_ref[0] is not None:
                    fly_pos_hud = obs['fly'][0]
                    predator_distance = np.linalg.norm(
                        arena_kwargs['arena'].ball_pos - fly_pos_hud)
                    mon_data.update(monitor_fields(
                        terrarium_ref[0], bridge, decoder, fly_pos_hud,
                        predator_distance))
                # Somatosensory data (when available)
                if somato is not None:
                    mon_data['jo_contact'] = somato.touch_level
                    mon_data['jo_sound'] = somato.sound_level
                    mon_data['jo_touch_L'] = (
                        somato.touch_rate_left / somato.TOUCH_MAX_RATE)
                    mon_data['jo_touch_R'] = (
                        somato.touch_rate_right / somato.TOUCH_MAX_RATE)
                    mon_data['jo_sound_L'] = (
                        somato.sound_rate_left / somato.SOUND_MAX_RATE)
                    mon_data['jo_sound_R'] = (
                        somato.sound_rate_right / somato.SOUND_MAX_RATE)
                    mon_data['contact_force'] = somato.max_contact_force
                    mon_data['sound_bias'] = somato.orientation_bias
                # Gustatory data (when available)
                if gusto is not None:
                    mon_data['sugar_level'] = gusto.sugar_level
                    mon_data['bitter_level'] = gusto.bitter_level
                # Wing song data (when available)
                if wing_song is not None:
                    mon_data['wing_freq'] = wing_song.wing_freq
                    mon_data['wing_amp'] = wing_song.wing_amp
                    mon_data['wing_song'] = wing_song.active_song or 'silent'
                    mon_data['wing_level'] = wing_song.song_level
                # Olfactory data (when available)
                if olfact is not None:
                    mon_data['or_att_L'] = (
                        olfact.attractive_rate_left / olfact.ATTRACTIVE_MAX_RATE)
                    mon_data['or_att_R'] = (
                        olfact.attractive_rate_right / olfact.ATTRACTIVE_MAX_RATE)
                    mon_data['or_rep_L'] = (
                        olfact.repulsive_rate_left / olfact.REPULSIVE_MAX_RATE)
                    mon_data['or_rep_R'] = (
                        olfact.repulsive_rate_right / olfact.REPULSIVE_MAX_RATE)
                    mon_data['or_attractive'] = olfact.attractive_level
                    mon_data['or_repulsive'] = olfact.repulsive_level
                # Flight data (when available)
                if flight_sys is not None:
                    mon_data['flight_level'] = flight_sys.flight_level
                    mon_data['flight_state'] = flight_sys.state.name.lower()
                    mon_data['flight_alt'] = flight_sys.altitude
                    mon_data['flight_wing_freq'] = flight_sys.wing_freq
                # Visual data (when available)
                if visual is not None:
                    mon_data['lplc2_left'] = d.get_pop_rate('LPLC2_left')
                    mon_data['lplc2_right'] = d.get_pop_rate('LPLC2_right')
                    mon_data['lc4_left'] = d.get_pop_rate('LC4_left')
                    mon_data['lc4_right'] = d.get_pop_rate('LC4_right')
                    if last_vision_obs is not None:
                        mon_data['bright_left'] = float(
                            np.mean(last_vision_obs[0]))
                        mon_data['bright_right'] = float(
                            np.mean(last_vision_obs[1]))
                        mon_data['dark_omm_left'] = int(np.sum(
                            np.mean(last_vision_obs[0], axis=1) < 0.25))
                        mon_data['dark_omm_right'] = int(np.sum(
                            np.mean(last_vision_obs[1], axis=1) < 0.25))
                    if cached_visual[1] is not None and hasattr(visual, '_T2_eye'):
                        vis_eye = visual._T2_eye
                        vis_r = cached_visual[1]
                        mask_L = vis_eye == 0
                        mask_R = vis_eye == 1
                        mon_data['t2_left'] = float(
                            vis_r[mask_L].mean() / 120.0) if mask_L.any() else 0.0
                        mon_data['t2_right'] = float(
                            vis_r[mask_R].mean() / 120.0) if mask_R.any() else 0.0
                    ball_pos = getattr(
                        arena_kwargs.get('arena'), 'ball_pos', None)
                    if ball_pos is not None:
                        mon_data['ball_x'] = float(ball_pos[0])
                if consciousness is not None:
                    mon_data.update(consciousness.get_monitor_data())
                if terrarium_hud is not None:
                    # Values are direct readings already computed by each
                    # sensory subsystem; absent systems remain explicitly 0.
                    mon_data['vision'] = max(
                        mon_data.get('lplc2_left', 0.0),
                        mon_data.get('lplc2_right', 0.0))
                    mon_data['smell'] = max(
                        mon_data.get('or_attractive', 0.0),
                        mon_data.get('or_repulsive', 0.0))
                    mon_data['taste'] = max(
                        mon_data.get('sugar_level', 0.0),
                        mon_data.get('bitter_level', 0.0))
                    mon_data['touch'] = mon_data.get('jo_contact', 0.0)
                    mon_data['looming'] = mon_data.get('gf', 0.0)
                    terrarium_hud.update(mon_data)
                monitor.send(mon_data)

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        if consciousness is not None:
            consciousness.save_session()
        if brain is not None:
            brain.save_plastic_weights()
        if monitor is not None:
            monitor.stop()
        if viewer is not None:
            viewer.close()
        print(f"\nSimulation ended after {body_step} steps "
              f"({body_step * sim.timestep:.2f}s sim time).")
        if body_step > 0:
            pos = obs['fly'][0]
            print(f"Final position: [{pos[0]:.1f}, {pos[1]:.1f}, "
                  f"{pos[2]:.1f}] mm")


if __name__ == '__main__':
    main()
