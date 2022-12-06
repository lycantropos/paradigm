import inspect
import sys
import sysconfig
import typing as t
from importlib.machinery import (EXTENSION_SUFFIXES,
                                 SOURCE_SUFFIXES)
from importlib.util import find_spec
from itertools import chain
from pathlib import Path

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


def _find_source_path(module_name: str) -> Path:
    maybe_spec = find_spec(module_name)
    assert maybe_spec is not None
    maybe_path_string = maybe_spec.origin
    assert maybe_path_string is not None
    return Path(maybe_path_string)


def _to_stubs_cache(
        root: Path = _find_source_path('mypy').parent / 'typeshed' / 'stdlib'
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
_sources_directories = {
    Path(sysconfig.get_path('platstdlib')),
    Path(sysconfig.get_path('stdlib')),
}


def _to_modules_paths(root: Path) -> t.Iterable[catalog.Path]:
    assert root.exists(), root

    def is_source_path(
            path: Path,
            *,
            _suffixes: t.Container[str] = frozenset(SOURCE_SUFFIXES
                                                    + EXTENSION_SUFFIXES)
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
    return (bool(module_path)
            and 'test' not in module_path
            and 'tests' not in module_path
            and module_path[-1] != '__main__'
            and all((part.isidentifier()
                     and not part.startswith(('_test', 'test_'))
                     and not part.endswith('_test'))
                    for part in module_path))


stdlib_modules_paths = dict.fromkeys(
        chain([catalog.path_from_string(module_name)
               for module_name in sys.builtin_module_names],
              [module_path
               for path in _sources_directories
               for module_path in _to_modules_paths(path)
               if _is_valid_module_path(module_path)])
).keys()
