from __future__ import annotations

import sys as _sys
from collections.abc import Mapping as _Mapping, Sequence as _Sequence
from pathlib import Path as _Path
from types import ModuleType
from typing import Final as _Final, TypeAlias as _TypeAlias

import mypy as _mypy
from mypy.version import __version__ as _mypy_version

import paradigm
from paradigm import __version__ as _version
from paradigm._core import (
    caching as _caching,
    catalog as _catalog,
    file_system as _file_system,
    namespacing as _namespacing,
    sources as _sources,
)

_CACHE_ROOT_DIRECTORY_NAME_PREFIX: _Final[str] = (
    '_'
    + _mypy.__name__
    + '_'
    + _mypy_version.replace('.', '_')
    + '_'
    + _sys.platform
    + '_'
    + _sys.implementation.name
    + '_'
    + '_'.join(map(str, _sys.version_info))
)
_CACHE_ROOT_DIRECTORY_PATH: _Final[_Path] = (
    _Path.home()
    / '.cache'
    / paradigm.__name__
    / (_CACHE_ROOT_DIRECTORY_NAME_PREFIX + '_' + _Path(__file__).stem)
)
_CACHE_ROOT_DIRECTORY_PATH.mkdir(exist_ok=True, parents=True)


class _FieldName:
    QUALIFIED_PATHS = 'qualified_paths'
    VERSION = 'version'


QualifiedPaths: _TypeAlias = _Mapping[
    _catalog.Path, _Mapping[_catalog.Path, _Sequence[_catalog.QualifiedPath]]
]


def from_module(
    module: ModuleType,
    /,
    *,
    cache_directory_path: _Path = _CACHE_ROOT_DIRECTORY_PATH / 'qualified',
) -> QualifiedPaths:
    module_path = _catalog.module_path_from_module(module)
    try:
        source_path = _sources.from_module_path(module_path)
    except _sources.NotFound:
        return {}
    if source_path.stem != _file_system.INIT_MODULE_NAME:
        package_directory_path = cache_directory_path.joinpath(*module_path)
        package_directory_path.mkdir(exist_ok=True, parents=True)
        cache_file_path = package_directory_path / (
            f'{_file_system.INIT_MODULE_NAME}{_file_system.MODULE_FILE_SUFFIX}'
        )
    else:
        package_directory_path = cache_directory_path.joinpath(
            *module_path[:-1]
        )
        package_directory_path.mkdir(exist_ok=True, parents=True)
        cache_file_path = (
            package_directory_path
            / f'{module_path[-1]}{_file_system.MODULE_FILE_SUFFIX}'
        )
    result: dict[
        _catalog.Path, dict[_catalog.Path, list[_catalog.QualifiedPath]]
    ]
    try:
        (result, cached_version) = _caching.load(
            cache_file_path, _FieldName.QUALIFIED_PATHS, _FieldName.VERSION
        )
    except Exception:
        pass
    else:
        if cached_version == _version:
            return result
    result = {}
    _index_module_or_type(
        module,
        paths=result,
        module_path=module_path,
        parent_path=(),
        visited_classes=set(),
    )
    _caching.save(
        cache_file_path,
        **{_FieldName.QUALIFIED_PATHS: result, _FieldName.VERSION: _version},
    )
    return result


def _index_module_or_type(
    namespace: _namespacing.ModuleOrType,
    /,
    *,
    paths: dict[
        _catalog.Path, dict[_catalog.Path, list[_catalog.QualifiedPath]]
    ],
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    visited_classes: set[type],
) -> None:
    for name, value in vars(namespace).items():
        if isinstance(value, type):
            if value not in visited_classes:
                object_path = (*parent_path, name)
                qualified_module_path, qualified_object_path = (
                    _catalog.qualified_path_from(value)
                )
                assert qualified_module_path or qualified_object_path, (
                    _catalog.path_to_string(module_path + object_path)
                )
                (
                    paths.setdefault(qualified_module_path, {})
                    .setdefault(qualified_object_path, [])
                    .append((module_path, object_path))
                )
                _index_module_or_type(
                    value,
                    paths=paths,
                    module_path=module_path,
                    parent_path=object_path,
                    visited_classes={*visited_classes, value},
                )
        else:
            qualified_module_path, qualified_object_path = (
                _catalog.qualified_path_from(value)
            )
            if qualified_object_path:
                (
                    paths.setdefault(qualified_module_path, {})
                    .setdefault(qualified_object_path, [])
                    .append((module_path, (*parent_path, name)))
                )
