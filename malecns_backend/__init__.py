"""Headless loader for the processed Male CNS v1.0 artifacts."""

from .loader import MaleCNSData, load_malecns
from .neural import MaleCNSBrain, ModelConfig

__all__ = ["MaleCNSData", "load_malecns", "MaleCNSBrain", "ModelConfig"]
