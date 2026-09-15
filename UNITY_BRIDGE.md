# Python–Unity fly-state bridge

This iteration keeps `fly_embodied.py`, FlyGym/MuJoCo, the PyTorch connectome,
plasticity, sensory processing, and behavior selection authoritative. Unity is
an optional observer. No Unity value is fed back into the simulation.

## What was inspected and where the adapter attaches

* `fly_embodied.py` owns the application loop. The body advances at a `1e-4`
  second timestep; sensors and the brain are serviced every 100 body steps;
  the existing viewer is synchronized separately at about 60 Hz. Its completed
  FlyGym observation contains `obs['fly'][0]` (position in millimetres) and
  `obs['fly_orientation']` (the body's world-space forward/X vector).
* `brain_body_bridge.py` advances the sparse neural engine and its DN rate
  decoder. `BrainBodyBridge.compute_drive()` stores the current `mode`,
  `left_drive`, and `right_drive` before the body step.
* `terrarium_controller.py` owns pause/speed, movable environmental source
  positions, selection, and transient pokes. `interaction_controller.py` maps
  viewer input to those commands on the simulation thread.
* `terrarium_viewer.py` owns GLFW callbacks and rendering but never steps the
  model. `terrarium_visuals.py` adds MJCF presentation geometry; physical walls
  alone participate in wall mechanosensation.
* Visual, somatosensory, gustatory, olfactory, wall, and vocalization systems
  read the current FlyGym observation/environment and write firing rates into
  `BrainEngine`; they remain unchanged.

The safest output seam is immediately after a successful body step: the new
adapter copies the completed observation and already-selected bridge mode. A
bounded, one-item queue passes that snapshot to a network thread. Thus socket
accept/write latency cannot alter simulation timing, and stale snapshots are
dropped instead of accumulating.

## Launch

### Python backend

Use the same environment and options as the existing simulation, adding only
`--unity`:

```bash
cd /workspace/FlyBrainUnity/fly-brain-interactive
python fly_embodied.py --unity
```

This starts the complete neural, sensory, behavioral, and FlyGym/MuJoCo physics
simulation, enables the TCP bridge, and runs until interrupted. Unity is the
normal visual frontend, so no MuJoCo window is opened. To display the original
MuJoCo viewer alongside Unity for debugging, use:

```bash
python fly_embodied.py --unity --mujoco-viewer
```

Optional settings are `--unity-port 8765` and `--unity-rate 30`. A duration can
still be requested explicitly with `--duration`; its default of zero is
unlimited. Without `--unity`, startup and execution follow the original path.
The legacy `--unity-bridge` option remains accepted for existing scripts and
retains its previous behavior, including the MuJoCo viewer by default.

### Unity frontend

1. Open `/workspace/FlyBrainUnity/FlyBrainUnity` with Unity `6000.3.10f1`.
2. Open `Assets/Scenes/SampleScene.unity`.
3. Press **Play**. A runtime bootstrap automatically creates the TCP receiver
   primitive fly proxy, environment mirror, and automatic camera; no scene
   editing is required. Press **F** to toggle Overview/Follow Fly and **L** to
   toggle stable-ID labels over dynamic mirrored objects.
4. Start either side first. Unity retries once per second and its HUD changes
   from **Disconnected** to **Connected** after the Python server is available.

No additional Unity packages are needed; the implementation uses the standard
`System.Net.Sockets` API and Unity's built-in JSON parser and IMGUI.

## Protocol

Python listens only on `127.0.0.1:8765` using TCP. Each update is one compact
UTF-8 JSON object followed by `\n` (newline-delimited JSON). Protocol version 1
is output-only and supports one Unity client. Python also sends an
`environment_definition` on every connection and coalesced `environment_state`
transforms while authoritative objects move.

```json
{"type":"fly_state","protocol_version":1,"time":12.35,"position":[0.2,0.03,-0.4],"orientation":[1,0,0],"rotation":[0,0,0],"behavior":"walking","movement":{"left_drive":0.8,"right_drive":0.8,"speed_mm_s":9.4}}
```

Field semantics:

* `time`: authoritative simulation seconds.
* `position`: FlyGym/MuJoCo `[x,y,z]` in millimetres.
* `orientation`: normalized world-space forward direction (the fly body X axis).
* `rotation`: convenience `[roll,pitch,yaw]` in degrees in the source Z-up
  frame. The proof of concept has only the forward vector, so roll/pitch are 0.
* `behavior`: the authoritative `BrainBodyBridge.mode` string.
* `movement`: current motor drives plus observation-derived linear speed.

Coordinate conversion is explicit in `WorldVisualScale`: source millimetres,
right-handed, Z-up `[x,y,z]` become Unity visual units, left-handed, Y-up
`[x,z,y]`, at **1 mm = 0.1 Unity unit**. Dimensions use the identical mapping;
orientation uses the same axis swap and `Quaternion.LookRotation`. Scientific
wire values remain millimetres and future calibration changes one class.

The exact environment is flag-dependent. Plain `--unity` mirrors FlyGym's real
flat substrate and does not invent objects absent from Python. For the existing
full `LoomingArena` terrarium (physical 64 mm square shell and predator), add
`--visual --terrarium`; add `--gustatory` and/or `--olfactory` to instantiate
and mirror the real sugar, bitter, food, and danger sources.

With `--unity --visual --terrarium --gustatory --olfactory`, the current Python
configuration instantiates and transmits ten objects: the substrate, four
walls, predator, two taste zones, and two odor sources. The HUD displays the
number of successfully mirrored objects beside the definition count (normally
`10/10`) so a rejected protocol object is visible rather than silently replaced.

## Runtime behavior and limitations

* Python targets at most 30 wall-clock updates/second and reports actual sends
  every five seconds while connected. Expensive neural updates can lower it.
* Unity receives asynchronously, retains only recent snapshots, and renders at
  its own rate using exponential position/rotation interpolation.
* Overview continuously fits the received environment renderer bounds plus the
  fly using the camera's real vertical and horizontal field of view. The HUD
  also reports the fly's converted pose, viewport/depth, frustum result, and
  clearance from the mirrored floor surface for runtime coordinate diagnosis.
* The proxy is deliberately a high-contrast primitive marker, not an articulated fly. Only yaw can be
  reconstructed from the currently exposed forward vector; full body roll and
  pitch require exporting the MuJoCo free-joint quaternion in a later change.
* TCP has no authentication or encryption because it binds to loopback only.
* There is no Unity-to-Python event channel yet, no clock synchronization, and
  reconnecting starts from the newest subsequently published state.

## Recommended next milestone

Add a second, explicitly typed sensory-event channel from Unity to Python while
keeping Python authoritative. First mirror only terrarium object transforms and
mouse pokes, validate them on the Python simulation thread, and feed them into
the existing `TerrariumController`/sensory systems. In parallel, export the
thorax quaternion and stable object identifiers so Unity can render full pose
and environmental sources without duplicating experimental logic.
