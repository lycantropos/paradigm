import builtins
import typing as t

from . import catalog

Scope = t.Dict[str, dict]
ModuleReferences = t.Dict[catalog.Path, catalog.QualifiedPath]
ModuleSubScopes = t.Dict[catalog.Path, t.Set[catalog.QualifiedPath]]


def scope_contains_path(scope: Scope, path: catalog.Path) -> bool:
    for part in path:
        try:
            scope = scope[part]
        except KeyError:
            return False
    return True


def contains_object_path(
        module_path: catalog.Path,
        object_path: catalog.Path,
        modules_definitions: t.Dict[catalog.Path, Scope],
        modules_references: t.Dict[catalog.Path, ModuleReferences],
        modules_sub_scopes: t.Dict[catalog.Path, ModuleSubScopes],
        *visited_modules_paths: catalog.Path,
        _builtins_module_path: catalog.Path
        = catalog.module_path_from_module(builtins)
) -> bool:
    try:
        module_definitions = modules_definitions[module_path]
    except KeyError:
        return False
    module_sub_scopes = modules_sub_scopes[module_path]
    if object_path and object_path[0] in module_definitions:
        scope = module_definitions[object_path[0]]
        for index, sub_name in enumerate(object_path[1:],
                                         start=1):
            if sub_name in scope:
                scope = scope[sub_name]
            else:
                try:
                    sub_path_sub_scopes = module_sub_scopes[
                        object_path[:index]
                    ]
                except KeyError:
                    pass
                else:
                    for (
                            sub_scope_module_path, sub_scope_object_path
                    ) in sub_path_sub_scopes:
                        if contains_object_path(
                                sub_scope_module_path,
                                sub_scope_object_path + object_path[index:],
                                modules_definitions, modules_references,
                                modules_sub_scopes, *visited_modules_paths,
                                module_path
                        ):
                            return True
                return (object_path[0] != object.__name__
                        and contains_object_path(
                                _builtins_module_path,
                                (object.__name__,) + object_path[index:],
                                modules_definitions, modules_references,
                                modules_sub_scopes, *visited_modules_paths
                        ))
        return True
    else:
        if () in module_sub_scopes:
            for sub_module_path, _ in module_sub_scopes[()]:
                if sub_module_path not in visited_modules_paths:
                    if contains_object_path(
                            sub_module_path, object_path, modules_definitions,
                            modules_references, modules_sub_scopes,
                            *visited_modules_paths, module_path
                    ):
                        return True
        module_references = modules_references[module_path]
        for offset in range(len(object_path)):
            sub_object_path = object_path[:len(object_path) - offset]
            try:
                referent_module_name, referent_object_path = module_references[
                    sub_object_path
                ]
            except KeyError:
                continue
            else:
                return contains_object_path(
                        referent_module_name,
                        referent_object_path
                        + object_path[len(object_path) - offset:],
                        modules_definitions, modules_references,
                        modules_sub_scopes, *visited_modules_paths, module_path
                )
        return scope_contains_path(modules_definitions[_builtins_module_path],
                                   object_path)


class ObjectNotFound(Exception):
    pass


def resolve_object_path(
        module_path: catalog.Path,
        object_path: catalog.Path,
        modules_definitions: t.Mapping[catalog.Path, Scope],
        modules_references: t.Mapping[catalog.Path, ModuleReferences],
        modules_sub_scopes: t.Mapping[catalog.Path, ModuleSubScopes],
        *visited_modules_paths: catalog.Path,
        _builtins_module_path: catalog.Path
        = catalog.module_path_from_module(builtins)
) -> catalog.QualifiedPath:
    try:
        module_definitions = modules_definitions[module_path]
    except KeyError:
        raise ObjectNotFound((module_path, object_path))
    if not object_path:
        return (module_path, object_path)
    module_sub_scopes = modules_sub_scopes[module_path]
    if object_path[0] in module_definitions:
        scope = module_definitions[object_path[0]]
        for index, sub_name in enumerate(object_path[1:],
                                         start=1):
            if sub_name in scope:
                scope = scope[sub_name]
            else:
                try:
                    sub_path_sub_scopes = module_sub_scopes[
                        object_path[:index]
                    ]
                except KeyError:
                    pass
                else:
                    for (
                            sub_scope_module_path, sub_scope_object_path
                    ) in sub_path_sub_scopes:
                        try:
                            return resolve_object_path(
                                    sub_scope_module_path,
                                    sub_scope_object_path
                                    + object_path[index:],
                                    modules_definitions, modules_references,
                                    modules_sub_scopes, *visited_modules_paths,
                                    module_path
                            )
                        except ObjectNotFound:
                            continue
                if object_path[0] != object.__name__:
                    return resolve_object_path(
                            _builtins_module_path,
                            (object.__name__,) + object_path[index:],
                            modules_definitions, modules_references,
                            modules_sub_scopes, *visited_modules_paths
                    )
                else:
                    raise ObjectNotFound((module_path, object_path))
        return (module_path, object_path)
    else:
        if () in module_sub_scopes:
            for sub_module_path, _ in module_sub_scopes[()]:
                if sub_module_path not in visited_modules_paths:
                    try:
                        return resolve_object_path(
                                sub_module_path, object_path,
                                modules_definitions, modules_references,
                                modules_sub_scopes, *visited_modules_paths,
                                module_path
                        )
                    except ObjectNotFound:
                        continue
        module_references = modules_references[module_path]
        for offset in range(len(object_path)):
            sub_object_path = object_path[:len(object_path) - offset]
            try:
                referent_module_name, referent_object_path = module_references[
                    sub_object_path
                ]
            except KeyError:
                continue
            else:
                return resolve_object_path(
                        referent_module_name,
                        referent_object_path
                        + object_path[len(object_path) - offset:],
                        modules_definitions, modules_references,
                        modules_sub_scopes, *visited_modules_paths, module_path
                )
        if scope_contains_path(modules_definitions[_builtins_module_path],
                               object_path):
            return _builtins_module_path, object_path
        raise ObjectNotFound((module_path, object_path))
