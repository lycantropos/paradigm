import importlib
import warnings
from types import ModuleType
from typing import (Any,
                    Callable,
                    Iterable,
                    List,
                    Optional,
                    Set,
                    Union)

from paradigm import (catalog,
                      namespaces)


def _update(set_: Set[Any], module_name: str, names: Iterable[str]) -> None:
    for name in names:
        _add(set_, module_name, name)


def _add(set_: Set[Any], module_name: str, name: str) -> None:
    module = _safe_import(module_name)
    if module is None:
        return
    path = catalog.from_string(name)
    try:
        object_ = _search_by_path(module, path)
    except KeyError:
        warnings.warn('Module "{module}" has no object with name "{name}".'
                      .format(module=module_name,
                              name=path.parts[0]))
    except AttributeError:
        warnings.warn('Module "{module}" has no object with path "{path}".'
                      .format(module=module_name,
                              path=path))
    else:
        set_.add(object_)


def _safe_import(module_name: str) -> Optional[ModuleType]:
    try:
        return importlib.import_module(module_name)
    except ImportError:
        warnings.warn('Module "{module}" is not found.'
                      .format(module=module_name))
        return None


def _search_by_path(module: ModuleType, path: catalog.Path) -> Any:
    return namespaces.search(namespaces.from_module(module), path)


def _to_callables(object_: Union[ModuleType, type]) -> Iterable[Callable]:
    yield from filter(callable, _to_contents(object_))


def _to_contents(object_: Union[ModuleType, type]) -> List[Any]:
    return list(vars(object_).values())
