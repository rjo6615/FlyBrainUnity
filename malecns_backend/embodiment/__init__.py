"""Body-independent MaleCNS leg embodiment interfaces (Milestone 3B).

Runtime symbols are lazy so read-only metadata audits do not require NumPy.
"""

__all__ = [
    "EmbodimentLoop", "TimingConfig", "SELECTED_PATHWAY",
    "load_selected_pathway", "MotorActivityObserver", "MotorDecoder",
    "MotorSafety", "EncodedSensoryDrive", "LegSensoryFrame",
    "SensoryEncoder",
]


def __getattr__(name):
    if name in ("EmbodimentLoop", "TimingConfig"):
        from .loop import EmbodimentLoop, TimingConfig
        return {"EmbodimentLoop": EmbodimentLoop, "TimingConfig": TimingConfig}[name]
    if name in ("SELECTED_PATHWAY", "load_selected_pathway"):
        from .mappings import SELECTED_PATHWAY, load_selected_pathway
        return {"SELECTED_PATHWAY": SELECTED_PATHWAY, "load_selected_pathway": load_selected_pathway}[name]
    if name in ("MotorActivityObserver", "MotorDecoder", "MotorSafety"):
        from .motor import MotorActivityObserver, MotorDecoder, MotorSafety
        return {"MotorActivityObserver": MotorActivityObserver, "MotorDecoder": MotorDecoder, "MotorSafety": MotorSafety}[name]
    if name in ("EncodedSensoryDrive", "LegSensoryFrame", "SensoryEncoder"):
        from .sensory import EncodedSensoryDrive, LegSensoryFrame, SensoryEncoder
        return {"EncodedSensoryDrive": EncodedSensoryDrive, "LegSensoryFrame": LegSensoryFrame, "SensoryEncoder": SensoryEncoder}[name]
    raise AttributeError(name)
