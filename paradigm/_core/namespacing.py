import types
import typing as t
from functools import reduce

from . import catalog

ModuleOrType = t.Union[types.ModuleType, type]
Namespace = t.MutableMapping[str, t.Any]


class ObjectNotFound(Exception):
    pass


def search(module_or_type: ModuleOrType, object_path: catalog.Path) -> t.Any:
    try:
        return reduce(getattr, object_path, module_or_type)
    except AttributeError:
        raise ObjectNotFound(object_path)
