import importlib
from functools import reduce
from types import ModuleType
from typing import Any

from . import catalog
from .hints import Namespace


def from_module_path(object_: catalog.Path) -> Namespace:
    return from_module(importlib.import_module(str(object_)))


def from_module(object_: ModuleType) -> Namespace:
    return dict(vars(object_))


def contains(namespace: Namespace, path: catalog.Path) -> bool:
    try:
        search(namespace, path)
    except (KeyError, AttributeError):
        return False
    else:
        return True


def search(namespace: Namespace, path: catalog.Path) -> Any:
    return reduce(getattr, path.parts[1:], namespace[path.parts[0]])
