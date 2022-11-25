import sys as _sys
import typing as _t
from importlib import import_module as _import_module
from operator import attrgetter as _attrgetter
from pathlib import Path as _Path

import mypy as _mypy
from mypy.version import __version__ as _mypy_version

from paradigm import __version__ as _version
from . import index as _index

_CACHE_PATH = _Path(__file__).with_name(
        '_' + _mypy.__name__ + '_' + _mypy_version.replace('.', '_')
        + '_' + _sys.platform
        + '_' + _sys.implementation.name
        + '_' + '_'.join(map(str, _sys.version_info))
        + '_' + _Path(__file__).name
)
_STDLIB_QUALIFIED_PATHS_FIELD_NAME = 'stdlib_qualified_paths'
_VERSION_FIELD_NAME = 'version'

supported_stdlib_qualified_paths: _index.QualifiedPaths
try:
    supported_stdlib_qualified_paths, _cached_version = _attrgetter(
            _STDLIB_QUALIFIED_PATHS_FIELD_NAME, _VERSION_FIELD_NAME
    )(
            _import_module((''
                            if __name__ in ('__main__', '__mp_main__')
                            else __name__.rsplit('.', maxsplit=1)[0] + '.')
                           + _CACHE_PATH.stem)
    )
except Exception:
    _reload_cache = True
else:
    _reload_cache = _cached_version != _version
if _reload_cache:
    from . import execution as _execution

    if _execution.is_main_process():
        from . import (catalog as _catalog,
                       exporting as _exporting,
                       scoping as _scoping,
                       stubs as _stubs)
        from .discovery import (
            supported_stdlib_modules_paths as _supported_stdlib_modules_paths
        )


        def _to_supported_qualified_paths(
                qualified_paths: _index.QualifiedPaths,
                definitions: _t.Mapping[_catalog.Path, _scoping.Scope],
                references: _t.Mapping[_catalog.Path,
                                       _scoping.ModuleReferences],
                submodules: _t.Mapping[_catalog.Path,
                                       _scoping.ModuleSubmodules],
                superclasses: _t.Mapping[_catalog.Path,
                                         _scoping.ModuleSuperclasses]
        ) -> _index.QualifiedPaths:
            result = {}
            for (
                    module_path, module_qualified_paths
            ) in qualified_paths.items():
                supported_module_qualified_paths = {}
                for (
                        object_path, object_qualified_paths
                ) in module_qualified_paths.items():
                    supported_object_qualified_paths = [
                        (located_module_path, located_object_path)
                        for located_module_path, located_object_path
                        in object_qualified_paths
                        if _scoping.contains_object_path(
                                located_module_path, (), located_object_path,
                                definitions, references, submodules,
                                superclasses
                        )
                    ]
                    if supported_object_qualified_paths:
                        supported_module_qualified_paths[object_path] = (
                            supported_object_qualified_paths
                        )
                if supported_module_qualified_paths:
                    result[module_path] = supported_module_qualified_paths
            return result


        supported_stdlib_qualified_paths = _to_supported_qualified_paths(
                _execution.call_in_process(_index.from_modules,
                                           _supported_stdlib_modules_paths),
                _stubs.definitions, _stubs.references, _stubs.submodules,
                _stubs.superclasses
        )
        _exporting.save(_CACHE_PATH,
                        **{
                            _STDLIB_QUALIFIED_PATHS_FIELD_NAME:
                                supported_stdlib_qualified_paths,
                            _VERSION_FIELD_NAME: _version
                        })
    else:
        supported_stdlib_qualified_paths = {}
