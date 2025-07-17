import sys as _sys
from collections.abc import Mapping as _Mapping

from . import (
    catalog as _catalog,
    index as _index,
    scoping as _scoping,
    stubs as _stubs,
)


def _to_supported_qualified_paths(
    definitions: _Mapping[_catalog.Path, _scoping.Scope],
    references: _Mapping[_catalog.Path, _scoping.ModuleReferences],
    submodules: _Mapping[_catalog.Path, _scoping.ModuleSubmodules],
    superclasses: _Mapping[_catalog.Path, _scoping.ModuleSuperclasses],
    /,
) -> _index.QualifiedPaths:
    result: dict[
        _catalog.Path, dict[_catalog.Path, list[_catalog.QualifiedPath]]
    ] = {}
    for module in _sys.modules.copy().values():
        module_index = _index.from_module(module)
        for module_path, module_qualified_paths in module_index.items():
            supported_module_qualified_paths = result.setdefault(
                module_path, {}
            )
            for (
                object_path,
                object_qualified_paths,
            ) in module_qualified_paths.items():
                if (
                    len(
                        supported_object_qualified_paths := [
                            (located_module_path, located_object_path)
                            for (
                                located_module_path,
                                located_object_path,
                            ) in object_qualified_paths
                            if _scoping.contains_object_path(
                                located_module_path,
                                (),
                                located_object_path,
                                definitions,
                                references,
                                submodules,
                                superclasses,
                            )
                        ]
                    )
                    > 0
                ):
                    supported_module_qualified_paths.setdefault(
                        object_path, []
                    ).extend(supported_object_qualified_paths)
    return result


supported_stdlib_qualified_paths = _to_supported_qualified_paths(
    _stubs.definitions,
    _stubs.references,
    _stubs.submodules,
    _stubs.superclasses,
)
