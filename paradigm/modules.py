import importlib
import warnings
from types import ModuleType
from typing import Optional


def safe_import(name: str) -> Optional[ModuleType]:
    try:
        return importlib.import_module(name)
    except ImportError:
        warnings.warn('Module "{module}" is not found.'
                      .format(module=name))
        return None
