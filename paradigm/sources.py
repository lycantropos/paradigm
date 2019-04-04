import inspect
import sys
from collections import namedtuple
from functools import singledispatch
from itertools import chain
from pathlib import Path
from types import ModuleType
from typing import (Any,
                    Iterable,
                    Tuple)

from . import catalog
from .file_system import find_files
from .hints import Map

STUB_EXTENSION = '.pyi'


@singledispatch
def factory(object_: Any) -> Path:
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


@factory.register(ModuleType)
def from_module(object_: ModuleType) -> Path:
    try:
        return Path(object_.__path__[0])
    except AttributeError:
        return Path(inspect.getfile(object_))


@factory.register(catalog.Path)
def from_module_path(object_: catalog.Path) -> Path:
    try:
        return cache[object_]
    except KeyError as original_error:
        module_name_path = catalog.factory(object_.parts[-1].lstrip('_'))
        module_path = object_.parent.join(module_name_path)
        try:
            return cache[module_path]
        except KeyError:
            raise original_error


def generate_stubs_cache_items(root: Path
                               ) -> Iterable[Tuple[catalog.Path, Path]]:
    Version = namedtuple('Version', ['major', 'minor'])

    def is_supported_version_directory(directory: Path) -> bool:
        system_version = get_system_version()
        return any(version.major == system_version.major
                   and version.minor <= system_version.minor
                   for version in to_versions(directory))

    def to_versions(directory: Path,
                    *,
                    major_versions_separator: str = 'and'
                    ) -> Iterable[Version]:
        raw_versions = directory.name.split(major_versions_separator)

        def to_version(raw_version: str,
                       *,
                       version_parts_separator: str = '.') -> Version:
            raw_version_parts = raw_version.split(version_parts_separator)
            version_parts = list(map(int, raw_version_parts))
            try:
                major, minor = version_parts
            except ValueError:
                major, = version_parts
                minor = 0
            return Version(major, minor)

        yield from map(to_version, raw_versions)

    def get_system_version() -> Version:
        major, minor, *_ = sys.version_info
        return Version(major, minor)

    def module_full_name_factory(directory: Path) -> Map[Path, catalog.Path]:
        def to_module_path(stub: Path) -> catalog.Path:
            relative_stub_path = stub.relative_to(directory)
            return catalog.factory(relative_stub_path.with_suffix('.py'))

        return to_module_path

    def to_directory_items(directory: Path
                           ) -> Iterable[Tuple[catalog.Path, Path]]:
        to_module_full_name = module_full_name_factory(directory)
        stubs = filter(is_stub, find_files(directory))

        def to_directory_item(stub: Path) -> Tuple[catalog.Path, Path]:
            return to_module_full_name(stub), stub

        yield from map(to_directory_item, stubs)

    def to_directories_items(paths: Iterable[Path]
                             ) -> Iterable[Tuple[catalog.Path, Path]]:
        directories = filter(Path.is_dir, paths)
        directories = filter(is_supported_version_directory, directories)
        yield from chain.from_iterable(map(to_directory_items, directories))

    yield from to_directories_items(root.iterdir())


def is_stub(path: Path) -> bool:
    return path.suffixes == [STUB_EXTENSION]


try:
    import mypy
except ImportError:
    cache = {}
else:
    cache = dict(generate_stubs_cache_items(factory(mypy)
                                            / 'typeshed' / 'stdlib'))
