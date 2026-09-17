"""Body-independent MaleCNS leg embodiment interfaces (Milestone 3B)."""

from .loop import EmbodimentLoop, TimingConfig
from .mappings import SELECTED_PATHWAY, load_selected_pathway
from .motor import MotorActivityObserver, MotorDecoder, MotorSafety
from .sensory import EncodedSensoryDrive, LegSensoryFrame, SensoryEncoder

__all__ = [
    "EmbodimentLoop", "TimingConfig", "SELECTED_PATHWAY",
    "load_selected_pathway", "MotorActivityObserver", "MotorDecoder",
    "MotorSafety", "EncodedSensoryDrive", "LegSensoryFrame",
    "SensoryEncoder",
]
