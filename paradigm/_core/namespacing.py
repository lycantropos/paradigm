import importlib
import typing as t
from functools import reduce
from types import ModuleType

from . import catalog

Namespace = t.Dict[str, t.Any]


def from_module_path(object_: catalog.Path) -> Namespace:
    return from_module(importlib.import_module(str(object_)))


def from_module(object_: ModuleType) -> Namespace:
    return vars(object_)


def contains(namespace: Namespace, path: catalog.Path) -> bool:
    try:
        search(namespace, path)
    except (KeyError, AttributeError):
        return False
    else:
        return True


def search(namespace: Namespace, path: catalog.Path) -> t.Any:
    root_object = namespace[path[0]]
    return (reduce(getattr, path[1:], root_object)
            if len(path) > 1
            else root_object)
