import sys
import types
from functools import (reduce,
                       singledispatch)
from importlib import (abc,
                       machinery)
from itertools import chain
from operator import methodcaller
from types import ModuleType
from typing import (Any,
                    Iterable)

from paradigm import catalog
from . import importing
from .hints import Namespace


@singledispatch
def factory(object_: Any) -> Namespace:
    return object_


replacing_modules_names = {
    '_importlib_modulespec': [types.__name__,
                              abc.__name__,
                              machinery.__name__]}
if sys.platform == 'win32':
    import nt

    replacing_modules_names['posix'] = [nt.__name__]


def to_replacing_modules_names(path_parts: Iterable[str]) -> Iterable[str]:
    yield from chain.from_iterable(
            filter(None, map(replacing_modules_names.get, path_parts)))


@factory.register(catalog.Path)
def from_module_path(object_: catalog.Path) -> Namespace:
    modules_names = list(to_replacing_modules_names(object_.parts))

    if modules_names:
        return merge(*map(from_module_name, modules_names))
    return from_module_name(str(object_))


@factory.register(ModuleType)
def from_module(object_: ModuleType) -> Namespace:
    return dict(vars(object_))


@factory.register(str)
def from_module_name(object_: str) -> Namespace:
    return from_module(importing.safe(object_))


def merge(*namespaces: Namespace) -> Namespace:
    return dict(chain.from_iterable(map(methodcaller('items'), namespaces)))


def search(namespace: Namespace, path: catalog.Path) -> Any:
    return reduce(getattr, path.parts[1:], namespace[path.parts[0]])


def contains(namespace: Namespace, path: catalog.Path) -> bool:
    try:
        search(namespace, path)
    except (KeyError, AttributeError):
        return False
    else:
        return True
