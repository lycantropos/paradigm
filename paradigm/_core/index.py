import typing as t
import warnings
from importlib import import_module

from paradigm._core import (catalog,
                            namespacing,
                            pretty)

QualifiedPaths = t.Dict[
    catalog.Path, t.Dict[catalog.Path, t.List[catalog.QualifiedPath]]
]


def from_modules(modules_paths: t.Iterable[catalog.Path]) -> QualifiedPaths:
    result: QualifiedPaths = {}
    for module_path in modules_paths:
        _index_module_path(module_path,
                           paths=result)
    return result


def _index_module_or_type(namespace: namespacing.ModuleOrType,
                          *,
                          paths: QualifiedPaths,
                          module_path: catalog.Path,
                          parent_path: catalog.Path,
                          visited_classes: t.Set[type]) -> None:
    for name, value in vars(namespace).items():
        if isinstance(value, type):
            if value not in visited_classes:
                object_path = parent_path + (name,)
                qualified_module_path, qualified_object_path = (
                    catalog.qualified_path_from(value)
                )
                assert (
                        qualified_module_path or qualified_object_path
                ), catalog.path_to_string(module_path + object_path)
                (paths.setdefault(qualified_module_path, {})
                 .setdefault(qualified_object_path, [])
                 .append((module_path, object_path)))
                _index_module_or_type(
                        value,
                        paths=paths,
                        module_path=module_path,
                        parent_path=object_path,
                        visited_classes={*visited_classes, value}
                )
        else:
            qualified_module_path, qualified_object_path = (
                catalog.qualified_path_from(value)
            )
            if qualified_object_path:
                (paths.setdefault(qualified_module_path, {})
                 .setdefault(qualified_object_path, [])
                 .append((module_path, parent_path + (name,))))


def _index_module_path(module_path: catalog.Path,
                       *,
                       paths: QualifiedPaths) -> None:
    module_name = catalog.path_to_string(module_path)
    try:
        module = import_module(module_name)
    except Exception as error:
        warnings.warn(f'Failed importing module "{module_name}". '
                      f'Reason:\n{pretty.format_exception(error)}',
                      ImportWarning)
    else:
        _index_module_or_type(module,
                              paths=paths,
                              module_path=module_path,
                              parent_path=(),
                              visited_classes=set())
