import inspect
import os
import site
import typing as t
from importlib.machinery import all_suffixes
from importlib.util import find_spec
from pathlib import Path

import mypy

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


def is_package(module_path: catalog.Path) -> bool:
    try:
        source_path = from_module_path(module_path)
    except NotFound:
        spec = find_spec(catalog.path_to_string(module_path))
        if spec is None or spec.origin is None:
            return False
        source_path = Path(spec.origin)
    return source_path.stem == file_system.INIT_MODULE_NAME


def _to_stubs_cache(
        root: Path = Path(mypy.__spec__.origin).parent / 'typeshed' / 'stdlib'
) -> t.Dict[catalog.Path, Path]:
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
stubs_stdlib_modules_paths = set(_stubs_cache.keys())


def _is_module_path_discoverable(module_path: catalog.Path) -> bool:
    module_name = catalog.path_to_string(module_path)
    try:
        return find_spec(module_name) is not None
    except ImportError:
        return False
    except ValueError:
        return True


_discoverable_stubs_stdlib_modules_paths = {
    module_path
    for module_path in stubs_stdlib_modules_paths
    if (_is_module_path_discoverable(module_path)
        and module_path[-1] != '__main__')
}


def _to_source_path(module_path: catalog.Path) -> t.Optional[Path]:
    module_name = catalog.path_to_string(module_path)
    try:
        spec = find_spec(module_name)
    except ValueError:
        return None
    else:
        origin = spec.origin
        if origin is None:
            return None
        candidate = Path(origin)
        if not candidate.exists():
            return None
        return (candidate.parent
                if candidate.stem == file_system.INIT_MODULE_NAME
                else candidate)


_sources_directories = {
    source_path.parent
    for source_path in [
        _to_source_path(module_path)
        for module_path in _discoverable_stubs_stdlib_modules_paths
        if len(module_path) == 1
    ]
    if source_path is not None and source_path.exists()
}
_site_packages_directories = tuple(site.getsitepackages())
_sources_directories = {
    path
    for path in _sources_directories
    if all((os.path.commonpath([path, candidate_path_string])
            != candidate_path_string)
           for candidate_path_string in _site_packages_directories)
}


def _to_modules_paths(root: Path) -> t.Iterable[catalog.Path]:
    assert root.exists(), root

    def is_source_path(
            path: Path,
            *,
            _suffixes: t.Container[str] = frozenset(all_suffixes())
    ) -> bool:
        return ''.join(path.suffixes) in _suffixes

    def to_module_path(source_path: Path) -> catalog.Path:
        return _relative_file_path_to_module_path(
                source_path.relative_to(root)
        )

    return {to_module_path(file_path)
            for file_path in file_system.find_files_paths(root)
            if is_source_path(file_path)}


def _is_valid_module_path(module_path: catalog.Path) -> bool:
    return ('test' not in module_path
            and 'tests' not in module_path
            and module_path[-1] != '__main__'
            and all(part.isidentifier() for part in module_path))


stdlib_modules_paths = {module_path
                        for path in _sources_directories
                        for module_path in _to_modules_paths(path)
                        if _is_valid_module_path(module_path)}
