import inspect as _inspect
import sys as _sys
import typing as _t
from importlib import import_module as _import_module
from pathlib import Path as _Path

import mypy as _mypy
from mypy.version import __version__ as _mypy_version

from . import (catalog as _catalog,
               scoping as _scoping)

_QualifiedPaths = _t.Dict[
    _catalog.Path, _t.Dict[_catalog.Path, _t.List[_catalog.QualifiedPath]]
]

_CACHE_PATH = _Path(__file__).with_name(
        '_' + _mypy.__name__ + '_' + _mypy_version.replace('.', '_')
        + '_' + _sys.platform
        + '_' + _sys.implementation.name
        + '_' + '_'.join(map(str, _sys.version_info))
        + '_' + _Path(__file__).name
)
_STDLIB_QUALIFIED_PATHS_FIELD_NAME = 'stdlib_qualified_paths'
supported_stdlib_qualified_paths: _QualifiedPaths

try:
    supported_stdlib_qualified_paths = getattr(
            _import_module((''
                            if __name__ in ('__main__', '__mp_main__')
                            else __name__.rsplit('.', maxsplit=1)[0] + '.')
                           + _inspect.getmodulename(str(_CACHE_PATH))),
            _STDLIB_QUALIFIED_PATHS_FIELD_NAME
    )
except Exception:
    import traceback as _traceback
    import types as _types
    import warnings as _warnings

    from . import (execution as _execution,
                   exporting as _exporting,
                   namespacing as _namespacing,
                   pretty as _pretty,
                   stubs as _stubs)
    from .discovery import (
        supported_stdlib_modules_paths as _supported_stdlib_modules_paths
    )


    def _index_namespace(namespace: _namespacing.Namespace,
                         *,
                         paths: _QualifiedPaths,
                         module_path: _catalog.Path,
                         parent_path: _catalog.Path,
                         visited_classes: _t.Set[type]) -> None:
        for name, value in namespace.items():
            if isinstance(value, type):
                if value not in visited_classes:
                    object_path = parent_path + (name,)
                    qualified_module_path, qualified_object_path = (
                        _catalog.qualified_path_from(value)
                    )
                    assert (
                            qualified_module_path or qualified_object_path
                    ), _catalog.path_to_string(module_path + object_path)
                    (paths.setdefault(qualified_module_path, {})
                     .setdefault(qualified_object_path, [])
                     .append((module_path, object_path)))
                    _index_namespace(vars(value),
                                     paths=paths,
                                     module_path=module_path,
                                     parent_path=object_path,
                                     visited_classes={*visited_classes, value})
            else:
                qualified_module_path, qualified_object_path = (
                    _catalog.qualified_path_from(value)
                )
                if qualified_object_path:
                    (paths.setdefault(qualified_module_path, {})
                     .setdefault(qualified_object_path, [])
                     .append((module_path, parent_path + (name,))))


    def _index_module_path(module_path: _catalog.Path,
                           *,
                           paths: _QualifiedPaths) -> None:
        module_name = _catalog.path_to_string(module_path)
        try:
            module = _import_module(module_name)
        except Exception as error:
            _warnings.warn(f'Failed importing module "{module_name}". '
                           f'Reason:\n{_pretty.format_exception(error)}',
                           ImportWarning)
        else:
            _index_namespace(vars(module),
                             paths=paths,
                             module_path=module_path,
                             parent_path=(),
                             visited_classes=set())


    def _index_modules(
            modules_paths: _t.Iterable[_catalog.Path]
    ) -> _QualifiedPaths:
        result: _QualifiedPaths = {}
        for module_path in modules_paths:
            _index_module_path(module_path,
                               paths=result)
        return result


    if _execution.is_main_process():
        _stdlib_qualified_paths = _execution.call_in_process(
                _index_modules, _supported_stdlib_modules_paths
        )
    else:
        _stdlib_qualified_paths = _index_modules(
                _supported_stdlib_modules_paths
        )


    def _to_supported_qualified_paths(
            qualified_paths: _QualifiedPaths,
            definitions: _t.Dict[_catalog.Path, _scoping.Scope],
            references: _t.Dict[_catalog.Path, _scoping.ModuleReferences],
            sub_scopes: _t.Dict[_catalog.Path, _scoping.ModuleSubScopes]
    ) -> _QualifiedPaths:
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
                            located_module_path, located_object_path,
                            definitions, references, sub_scopes
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
            _stdlib_qualified_paths,
            _stubs.definitions, _stubs.references, _stubs.sub_scopes
    )
    _exporting.save(
            _CACHE_PATH,
            **{
                'all_stdlib_qualified_paths': _stdlib_qualified_paths,
                _STDLIB_QUALIFIED_PATHS_FIELD_NAME:
                    supported_stdlib_qualified_paths
            }
    )
