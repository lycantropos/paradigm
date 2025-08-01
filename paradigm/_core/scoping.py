import builtins
from collections.abc import Collection, Mapping
from typing import TypeAlias

from . import catalog

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
    modules_definitions: Mapping[catalog.Path, Scope],
    modules_references: Mapping[catalog.Path, ModuleReferences],
    modules_submodules: Mapping[catalog.Path, ModuleSubmodules],
    modules_superclasses: Mapping[catalog.Path, ModuleSuperclasses],
) -> bool:
    try:
        resolve_object_path(
            module_path,
            parent_path,
            object_path,
            modules_definitions,
            modules_references,
            modules_submodules,
            modules_superclasses,
        )
    except ObjectNotFound:
        return False
    else:
        return True


def resolve_object_path(
    module_path: catalog.Path,
    parent_path: catalog.Path,
    object_path: catalog.Path,
    modules_definitions: Mapping[catalog.Path, Scope],
    modules_references: Mapping[catalog.Path, ModuleReferences],
    modules_submodules: Mapping[catalog.Path, ModuleSubmodules],
    modules_superclasses: Mapping[catalog.Path, ModuleSuperclasses],
    /,
    *visited_modules_paths: catalog.Path,
    _builtins_module_path: catalog.Path = catalog.module_path_from_module(  # noqa: B008
        builtins
    ),
) -> catalog.QualifiedPath:
    try:
        module_definitions = modules_definitions[module_path]
    except KeyError:
        raise ObjectNotFound((module_path, object_path)) from None
    if not object_path:
        return (module_path, object_path)
    assert scope_contains_path(module_definitions, parent_path)
    if parent_path and scope_contains_path(
        module_definitions, (*parent_path, object_path[0])
    ):
        return resolve_object_path(
            module_path,
            (),
            parent_path + object_path,
            modules_definitions,
            modules_references,
            modules_submodules,
            modules_superclasses,
            *visited_modules_paths,
        )
    if object_path[0] in module_definitions:
        module_superclasses, scope = (
            modules_superclasses.get(module_path, {}),
            module_definitions[object_path[0]],
        )
        for index, sub_name in enumerate(object_path[1:], start=1):
            if sub_name in scope:
                scope = scope[sub_name]
            else:
                sub_path = object_path[:index]
                try:
                    sub_path_superclasses = module_superclasses[sub_path]
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
                                modules_definitions,
                                modules_references,
                                modules_submodules,
                                modules_superclasses,
                                *visited_modules_paths,
                                module_path,
                            )
                        except ObjectNotFound:
                            continue
                if object_path[0] != object.__name__:
                    return resolve_object_path(
                        _builtins_module_path,
                        (),
                        (object.__name__, *object_path[index:]),
                        modules_definitions,
                        modules_references,
                        modules_submodules,
                        modules_superclasses,
                        *visited_modules_paths,
                    )
                raise ObjectNotFound((module_path, object_path))
        return (module_path, object_path)
    for sub_module_path in modules_submodules.get(module_path, []):
        if sub_module_path not in visited_modules_paths:
            try:
                return resolve_object_path(
                    sub_module_path,
                    (),
                    object_path,
                    modules_definitions,
                    modules_references,
                    modules_submodules,
                    modules_superclasses,
                    *visited_modules_paths,
                    module_path,
                )
            except ObjectNotFound:
                continue
    module_references = modules_references[module_path]
    for offset in range(len(object_path)):
        sub_object_path = object_path[: len(object_path) - offset]
        try:
            referent_module_path, referent_object_path = module_references[
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
                        modules_definitions,
                        modules_references,
                        modules_submodules,
                        modules_superclasses,
                        *visited_modules_paths,
                        module_path,
                    )
                )
            except ObjectNotFound:
                referent_module_path += referent_object_path[:1]
                referent_object_path = referent_object_path[1:]
                assert referent_module_path in modules_definitions, (
                    module_path,
                    object_path,
                )
            return resolve_object_path(
                referent_module_path,
                (),
                referent_object_path
                + object_path[len(object_path) - offset :],
                modules_definitions,
                modules_references,
                modules_submodules,
                modules_superclasses,
                *visited_modules_paths,
                module_path,
            )
    if scope_contains_path(
        modules_definitions[_builtins_module_path], object_path
    ):
        return _builtins_module_path, object_path
    raise ObjectNotFound((module_path, object_path))
