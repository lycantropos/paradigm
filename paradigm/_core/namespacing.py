import typing as t
from functools import reduce

from . import catalog

Namespace = t.Dict[str, t.Any]


def search(namespace: Namespace, path: catalog.Path) -> t.Any:
    root_object = namespace[path[0]]
    return (reduce(getattr, path[1:], root_object)
            if len(path) > 1
            else root_object)
