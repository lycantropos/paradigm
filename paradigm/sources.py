import inspect
from functools import singledispatch
from pathlib import Path
from types import ModuleType
from typing import (Any,
                    Iterable,
                    Tuple)

from . import catalog
from .file_system import find_files
from .hints import Map

STUB_EXTENSION = '.pyi'


class NotFound(Exception):
    pass


@singledispatch
def factory(object_: Any) -> Path:
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


@factory.register(ModuleType)
def from_module(object_: ModuleType) -> Path:
    try:
        return Path(object_.__path__[0])
    except AttributeError:
        try:
            return Path(inspect.getfile(object_))
        except Exception as error:
            raise NotFound(object_) from error


@factory.register(catalog.Path)
def from_module_path(object_: catalog.Path) -> Path:
    try:
        return cache[object_]
    except KeyError as error:
        raise NotFound(object_) from error


def generate_stubs_cache_items(root: Path
                               ) -> Iterable[Tuple[catalog.Path, Path]]:
    def module_full_name_factory(directory: Path) -> Map[Path, catalog.Path]:
        def to_module_path(stub: Path) -> catalog.Path:
            relative_stub_path = stub.relative_to(directory)
            return catalog.from_relative_file_path(relative_stub_path
                                                   .with_suffix('.py'))

        return to_module_path

    def to_directory_items(
            directory: Path
    ) -> Iterable[Tuple[catalog.Path, Path]]:
        to_module_full_name = module_full_name_factory(directory)
        stubs = filter(is_stub, find_files(directory))

        def to_directory_item(stub: Path) -> Tuple[catalog.Path, Path]:
            return to_module_full_name(stub), stub

        yield from map(to_directory_item, stubs)

    return to_directory_items(root)


def is_stub(path: Path) -> bool:
    return path.suffixes == [STUB_EXTENSION]


try:
    import mypy
except ImportError:
    cache = {}
else:
    cache = dict(generate_stubs_cache_items(factory(mypy)
                                            / 'typeshed' / 'stdlib'))
