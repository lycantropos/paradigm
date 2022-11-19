import typing as t
from functools import reduce

from . import catalog

Namespace = t.Dict[str, t.Any]


class ObjectNotFound(Exception):
    pass


def search(namespace: Namespace, object_path: catalog.Path) -> t.Any:
    try:
        root_object = namespace[object_path[0]]
    except KeyError:
        raise ObjectNotFound(object_path)
    try:
        return (reduce(getattr, object_path[1:], root_object)
                if len(object_path) > 1
                else root_object)
    except AttributeError:
        raise ObjectNotFound(object_path)
