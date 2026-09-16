"""Headless tools for the processed Male CNS v1.0 artifacts.

Runtime symbols are imported lazily so metadata-only audit commands do not
need to import NumPy or instantiate any part of the neural runtime.
"""

__all__ = ["MaleCNSData", "load_malecns", "MaleCNSBrain", "ModelConfig"]


def __getattr__(name):
    if name in ("MaleCNSData", "load_malecns"):
        from .loader import MaleCNSData, load_malecns
        return {"MaleCNSData": MaleCNSData, "load_malecns": load_malecns}[name]
    if name in ("MaleCNSBrain", "ModelConfig"):
        from .neural import MaleCNSBrain, ModelConfig
        return {"MaleCNSBrain": MaleCNSBrain, "ModelConfig": ModelConfig}[name]
    raise AttributeError(name)
