import inspect
from pathlib import Path
from types import ModuleType
from typing import (Iterable,
                    Optional,
                    Tuple)

import mypy

from . import (catalog,
               file_system)

_STUB_EXTENSION = '.pyi'


class NotFound(Exception):
    pass


def from_module(module: ModuleType) -> Path:
    try:
        return Path(module.__path__[0])
    except AttributeError:
        try:
            return Path(inspect.getfile(module))
        except Exception as error:
            raise NotFound(module) from error


def from_module_path(module_path: catalog.Path) -> Path:
    try:
        return _stubs_cache[module_path]
    except KeyError as error:
        raise NotFound(module_path) from error


def _generate_stubs_cache_items(
        root: Path
) -> Iterable[Tuple[catalog.Path, Path]]:
    def to_module_path(stub: Path) -> catalog.Path:
        return _relative_file_path_to_module_path(
                stub.relative_to(root).with_suffix('.py')
        )

    return [(to_module_path(file), file)
            for file in file_system.find_files(root)
            if _is_stub(file)]


def _is_stub(path: Path) -> bool:
    return path.suffixes == [_STUB_EXTENSION]


def _relative_file_path_to_module_path(path: Path) -> catalog.Path:
    if path.is_absolute():
        raise ValueError('Path should be relative.')
    *parts, module_file_name = path.parts

    def to_module_name(file_name: str) -> Optional[str]:
        if file_name == '.':
            return None
        result = inspect.getmodulename(file_name)
        if result == file_system.INIT_MODULE_NAME:
            return None
        return result

    module_name = to_module_name(module_file_name)
    return (catalog.Path(*parts)
            if module_name is None
            else catalog.Path(*parts, module_name))


_stubs_cache = dict(_generate_stubs_cache_items(from_module(mypy) / 'typeshed'
                                                / 'stdlib'))
