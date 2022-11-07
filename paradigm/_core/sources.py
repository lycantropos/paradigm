import inspect
from pathlib import Path
from typing import Dict

import mypy

from importlib.util import find_spec
from . import (catalog,
               file_system)

_STUB_EXTENSION = '.pyi'


class NotFound(Exception):
    pass


def from_module_path(module_path: catalog.Path) -> Path:
    try:
        return _stubs_cache[module_path]
    except KeyError as error:
        raise NotFound(module_path) from error


def _to_stubs_cache(
        root: Path = Path(mypy.__spec__.origin).parent / 'typeshed' / 'stdlib'
) -> Dict[catalog.Path, Path]:
    assert root.exists(), root

    def to_module_path(stub_path: Path) -> catalog.Path:
        return _relative_file_path_to_module_path(
                stub_path.relative_to(root).with_suffix('.py')
        )

    return {to_module_path(file_path): file_path
            for file_path in file_system.find_files_paths(root)
            if _is_stub(file_path)}


def _is_stub(path: Path) -> bool:
    return path.suffixes == [_STUB_EXTENSION]


def _relative_file_path_to_module_path(path: Path) -> catalog.Path:
    assert not path.is_absolute(), 'Path should be relative.'
    *parent_path_parts, module_file_name = path.parts
    parent_path = tuple(parent_path_parts)
    module_name = inspect.getmodulename(module_file_name)
    return (parent_path
            if (module_name is None
                or module_name == file_system.INIT_MODULE_NAME)
            else parent_path + (module_name,))


_stubs_cache = _to_stubs_cache()


def _is_module_path_discoverable(module_path: catalog.Path) -> bool:
    module_name = catalog.path_to_string(module_path)
    try:
        return find_spec(module_name) is not None
    except ImportError:
        return False
    except ValueError:
        return True


discoverable_stdlib_modules_paths = {
    module_path
    for module_path in _stubs_cache.keys()
    if _is_module_path_discoverable(module_path)
}
stdlib_modules_paths = set(_stubs_cache.keys())
