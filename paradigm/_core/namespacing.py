import types
from collections.abc import MutableMapping
from functools import reduce
from typing import Any, TypeAlias

from . import catalog

ModuleOrType: TypeAlias = types.ModuleType | type
Namespace: TypeAlias = MutableMapping[str, Any]


class ObjectNotFound(Exception):
    pass


def search(module_or_type: ModuleOrType, object_path: catalog.Path) -> Any:
    try:
        return reduce(getattr, object_path, module_or_type)
    except AttributeError:
        raise ObjectNotFound(object_path) from None
