import os
import sys
import warnings
from operator import methodcaller
from pathlib import Path
from types import ModuleType
from typing import (Any,
                    Callable,
                    Iterable,
                    List,
                    Set,
                    Union)

from paradigm import (catalog,
                      modules,
                      namespaces)


def _add(set_: Set[Any], module_name: str, name: str) -> None:
    module = modules.safe_import(module_name)
    if module is None:
        return
    path = catalog.from_string(name)
    try:
        object_ = _search_by_path(module, path)
    except KeyError:
        warnings.warn(f'Module "{module_name}" has no object '
                      f'with name "{path.parts[0]}".')
    except AttributeError:
        warnings.warn(f'Module "{module_name}" has no object '
                      f'with path "{path}".')
    else:
        set_.add(object_)


def _add_module(set_: Set[Any], module_name: str) -> None:
    module = modules.safe_import(module_name)
    if module is None:
        return
    set_.add(module)


def _search_by_path(module: ModuleType, path: catalog.Path) -> Any:
    return namespaces.search(namespaces.from_module(module), path)


def _to_callables(object_: Union[ModuleType, type]) -> Iterable[Callable]:
    yield from filter(callable, _to_contents(object_))


def _to_contents(object_: Union[ModuleType, type]) -> List[Any]:
    return list(vars(object_).values())


def _update(set_: Set[Any], module_name: str, names: Iterable[str]) -> None:
    for name in names:
        _add(set_, module_name, name)


def _update_modules(set_: Set[Any], modules_names: Iterable[str]) -> None:
    for module_name in modules_names:
        _add_module(set_, module_name)


def find_stdlib_modules_names(
        directory_path: Path = Path(os.__file__).parent,
) -> Iterable[str]:
    yield from sys.builtin_module_names

    def is_stdlib_module_path(path: Path) -> bool:
        base_name = path.stem
        # skips 'LICENSE', '__pycache__', 'site-packages', etc.
        return not (base_name.isupper()
                    or base_name.startswith('__')
                    or '-' in base_name)

    sources_paths = filter(is_stdlib_module_path, directory_path.iterdir())
    sources_relative_paths = map(methodcaller(Path.relative_to.__name__,
                                              directory_path),
                                 sources_paths)
    yield from map(str, map(methodcaller(Path.with_suffix.__name__, ''),
                            sources_relative_paths))


stdlib_modules_names = set(find_stdlib_modules_names())
