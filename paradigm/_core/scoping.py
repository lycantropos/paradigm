from __future__ import annotations

import builtins
from collections.abc import Collection, Mapping
from typing import Final, TypeAlias

from . import catalog

SPECIALIZATION_SCOPE_NAME: Final[str] = '@specializations'

ModuleReferences: TypeAlias = Mapping[catalog.Path, catalog.QualifiedPath]
ModuleSubmodules: TypeAlias = Collection[catalog.Path]
ModuleSuperclasses: TypeAlias = Mapping[
    catalog.Path, Collection[catalog.QualifiedPath]
]
Scope: TypeAlias = Mapping[str, 'Scope']


class ObjectNotFound(Exception):
    pass


def scope_contains_path(scope: Scope, path: catalog.Path) -> bool:
    for part in path:
        try:
            scope = scope[part]
        except KeyError:
            return False
    return True


def contains_object_path(
    module_path: catalog.Path,
    parent_path: catalog.Path,
    object_path: catalog.Path,
    module_definitions: Mapping[catalog.Path, Scope],
    module_references: Mapping[catalog.Path, ModuleReferences],
    module_submodules: Mapping[catalog.Path, ModuleSubmodules],
    module_superclasses: Mapping[catalog.Path, ModuleSuperclasses],
    /,
) -> bool:
    try:
        resolve_object_path(
            module_path,
            parent_path,
            object_path,
            module_definitions,
            module_references,
            module_submodules,
            module_superclasses,
        )
    except ObjectNotFound:
        return False
    else:
        return True


def resolve_object_path(
    module_path: catalog.Path,
    parent_path: catalog.Path,
    object_path: catalog.Path,
    module_scopes: Mapping[catalog.Path, Scope],
    module_references: Mapping[catalog.Path, ModuleReferences],
    module_submodules: Mapping[catalog.Path, ModuleSubmodules],
    module_superclasses: Mapping[catalog.Path, ModuleSuperclasses],
    /,
    *visited_module_paths: catalog.Path,
    _builtins_module_path: catalog.Path = catalog.module_path_from_module(  # noqa: B008
        builtins
    ),
) -> catalog.QualifiedPath:
    try:
        scope = module_scopes[module_path]
    except KeyError:
        raise ObjectNotFound((module_path, object_path)) from None
    if not object_path:
        return (module_path, object_path)
    assert scope_contains_path(scope, parent_path)
    if parent_path and scope_contains_path(
        scope, (*parent_path, object_path[0])
    ):
        return resolve_object_path(
            module_path,
            (),
            parent_path + object_path,
            module_scopes,
            module_references,
            module_submodules,
            module_superclasses,
            *visited_module_paths,
        )
    if object_path[0] in scope:
        superclasses, object_scope = (
            module_superclasses.get(module_path, {}),
            scope[object_path[0]],
        )
        for index, sub_name in enumerate(object_path[1:], start=1):
            if sub_name in object_scope:
                object_scope = object_scope[sub_name]
            else:
                sub_path = object_path[:index]
                try:
                    sub_path_superclasses = superclasses[sub_path]
                except KeyError:
                    pass
                else:
                    for (
                        superclass_module_path,
                        superclass_object_path,
                    ) in sub_path_superclasses:
                        try:
                            return resolve_object_path(
                                superclass_module_path,
                                (),
                                superclass_object_path + object_path[index:],
                                module_scopes,
                                module_references,
                                module_submodules,
                                module_superclasses,
                                *visited_module_paths,
                                module_path,
                            )
                        except ObjectNotFound:
                            continue
                if object_path[0] != object.__name__:
                    return resolve_object_path(
                        _builtins_module_path,
                        (),
                        (object.__name__, *object_path[index:]),
                        module_scopes,
                        module_references,
                        module_submodules,
                        module_superclasses,
                        *visited_module_paths,
                    )
                raise ObjectNotFound((module_path, object_path))
        return (module_path, object_path)
    for sub_module_path in module_submodules.get(module_path, []):
        if sub_module_path not in visited_module_paths:
            try:
                return resolve_object_path(
                    sub_module_path,
                    (),
                    object_path,
                    module_scopes,
                    module_references,
                    module_submodules,
                    module_superclasses,
                    *visited_module_paths,
                    module_path,
                )
            except ObjectNotFound:
                continue
    references = module_references[module_path]
    for offset in range(len(object_path)):
        sub_object_path = object_path[: len(object_path) - offset]
        try:
            referent_module_path, referent_object_path = references[
                sub_object_path
            ]
        except KeyError:
            continue
        else:
            try:
                referent_module_path, referent_object_path = (
                    resolve_object_path(
                        referent_module_path,
                        (),
                        referent_object_path,
                        module_scopes,
                        module_references,
                        module_submodules,
                        module_superclasses,
                        *visited_module_paths,
                        module_path,
                    )
                )
            except ObjectNotFound:
                referent_module_path += referent_object_path[:1]
                referent_object_path = referent_object_path[1:]
                assert referent_module_path in module_scopes, (
                    module_path,
                    object_path,
                )
            return resolve_object_path(
                referent_module_path,
                (),
                referent_object_path
                + object_path[len(object_path) - offset :],
                module_scopes,
                module_references,
                module_submodules,
                module_superclasses,
                *visited_module_paths,
                module_path,
            )
    if scope_contains_path(module_scopes[_builtins_module_path], object_path):
        return _builtins_module_path, object_path
    raise ObjectNotFound((module_path, object_path))
