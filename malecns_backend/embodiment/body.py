"""Optional headless FlyGym adapter; importing this module does not require FlyGym."""
from dataclasses import dataclass
import importlib

import numpy as np

from .sensory import LegSensoryFrame


class FlyGymUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class BodySnapshot:
    frame: LegSensoryFrame
    body_position_m: tuple[float, float, float]
    body_orientation: tuple[float, ...]
    contact_force_n: float
    joint_velocity_rad_s: float = 0.0
    actuator_position_rad: float | None = None


class FlyGymBody:
    """NeuroMechFly/FlyGym position-control adapter for one LM tibia joint.

    The adapter deliberately imports no locomotion example, CPG, steps, or old
    behavior controller. A full 42-position action is required by FlyGym; all
    nonselected entries are held at their latest measured positions.
    """
    behavior_controller_invoked = False

    def __init__(self, timestep_s=0.0001, selected_joint_index=12):
        try:
            flygym = importlib.import_module("flygym")
        except ImportError as exc:
            raise FlyGymUnavailable(
                "FlyGym is not installed. Install a Python-version-compatible "
                "FlyGym/NeuroMechFly release to run the real closed-loop experiment."
            ) from exc
        Fly = getattr(flygym, "Fly")
        Simulation = getattr(flygym, "SingleFlySimulation", None)
        if Simulation is None:
            try:
                Simulation = importlib.import_module("flygym.simulation").SingleFlySimulation
            except (ImportError, AttributeError) as exc:
                raise FlyGymUnavailable("installed FlyGym has no SingleFlySimulation API") from exc
        self.timestep_s = float(timestep_s)
        self.selected_joint_index = int(selected_joint_index)
        self.fly = Fly(enable_adhesion=False, control="position")
        self.sim = Simulation(fly=self.fly, cameras=[], timestep=self.timestep_s)
        self.observation, self.info = self.sim.reset()
        self.physics_steps = 0

    @staticmethod
    def _joint_positions(observation):
        value = np.asarray(observation["joints"], dtype=np.float64)
        # FlyGym observations use row 0 for positions and row 1 for velocities.
        return value[0] if value.ndim == 2 else value

    def observe(self):
        obs = self.observation
        joints = self._joint_positions(obs)
        joint_observation = np.asarray(obs["joints"], dtype=np.float64)
        velocity = (float(joint_observation[1, self.selected_joint_index])
                    if joint_observation.ndim == 2 and joint_observation.shape[0] > 1 else 0.0)
        pos = np.asarray(obs.get("fly", np.zeros((1, 3))), dtype=np.float64).reshape(-1, 3)[0]
        orientation = tuple(np.asarray(obs.get("fly_orientation", ()), dtype=np.float64).ravel().tolist())
        contact = np.asarray(obs.get("contact_forces", ()), dtype=np.float64)
        load = float(np.linalg.norm(contact)) if contact.size else 0.0
        return BodySnapshot(
            LegSensoryFrame(self.physics_steps * self.timestep_s, float(joints[self.selected_joint_index])),
            tuple(float(x) for x in pos), orientation, load,
            velocity, float(joints[self.selected_joint_index]),
        )

    def step(self, command, count=1):
        joints = self._joint_positions(self.observation).copy()
        joints[self.selected_joint_index] = command.target_position_rad
        action = {"joints": joints, "adhesion": np.zeros(6, dtype=np.float64)}
        for _ in range(count):
            result = self.sim.step(action)
            self.observation = result[0]
            self.info = result[-1]
            self.physics_steps += 1
        return self.observe()

    def close(self):
        close = getattr(self.sim, "close", None)
        if close is not None:
            close()


@dataclass(frozen=True)
class SixTibiaBodySnapshot:
    """PHYSICS_MEASURED state used by the simultaneous tibia experiment."""
    time_s: float
    angles_rad: dict[str, float]
    velocities_rad_s: dict[str, float]
    body_position_m: tuple[float, ...] = ()
    body_orientation: tuple[float, ...] = ()
    body_linear_velocity_m_s: tuple[float, ...] = ()
    body_angular_velocity_rad_s: tuple[float, ...] = ()
    contact_force_n: float = 0.0


class SixTibiaFlyGymBody(FlyGymBody):
    """One FlyGym body exposing six tibiae; every other joint is held measured."""
    def __init__(self, interfaces, timestep_s=0.0001):
        self.interfaces = dict(interfaces)
        # Optional read-only observer used by the M4C-2A forensic command.
        # Keeping the default at None leaves the scientific execution path
        # byte-for-byte equivalent at the MuJoCo call boundary.
        self.physics_diagnostic = None
        super().__init__(timestep_s=timestep_s,
                         selected_joint_index=next(iter(interfaces.values())).action_index)

    def observe(self):
        obs = self.observation
        raw = np.asarray(obs["joints"], dtype=np.float64)
        positions = raw[0] if raw.ndim == 2 else raw
        velocities = raw[1] if raw.ndim == 2 and raw.shape[0] > 1 else np.zeros_like(positions)
        pos = tuple(float(x) for x in np.asarray(
            obs.get("fly", ()), dtype=np.float64).reshape(-1).tolist()[:3])
        orientation = tuple(float(x) for x in np.asarray(
            obs.get("fly_orientation", ()), dtype=np.float64).ravel())
        contact = np.asarray(obs.get("contact_forces", ()), dtype=np.float64)
        return SixTibiaBodySnapshot(
            self.physics_steps * self.timestep_s,
            {leg: float(positions[p.action_index]) for leg, p in self.interfaces.items()},
            {leg: float(velocities[p.action_index]) for leg, p in self.interfaces.items()},
            pos, orientation, contact_force_n=float(np.linalg.norm(contact)) if contact.size else 0.0)

    def step(self, commands, count=1):
        joints = self._joint_positions(self.observation).copy()
        for leg, command in commands.items():
            expected = self.interfaces[leg]
            if command.actuator != expected.actuator_name:
                raise ValueError(f"wrong actuator for {leg}: {command.actuator}")
            joints[expected.action_index] = command.target_position_rad
        action = {"joints": joints, "adhesion": np.zeros(6, dtype=np.float64)}
        for _ in range(count):
            observer = self.physics_diagnostic
            token = observer.before_physics_step(self, action) if observer is not None else None
            try:
                result = self.sim.step(action)
            except Exception:
                if observer is not None:
                    observer.failed_physics_step(token)
                raise
            self.observation, self.info = result[0], result[-1]
            self.physics_steps += 1
            if observer is not None:
                observer.successful_physics_step(self, action, token)
        return self.observe()
