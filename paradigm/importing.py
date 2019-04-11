import importlib

from types import ModuleType


def safe(module_name: str) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return ModuleType(module_name)
