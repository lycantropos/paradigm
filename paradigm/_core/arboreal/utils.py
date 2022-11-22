import ast
import sys
import typing as t
from collections import deque

from paradigm._core import (catalog,
                            sources)
from typing_extensions import TypeGuard


def recursively_iterate_children(node: ast.AST) -> t.Iterable[ast.AST]:
    candidates = deque(ast.iter_child_nodes(node))
    while candidates:
        candidate = candidates.popleft()
        yield candidate
        candidates.extend(ast.iter_child_nodes(candidate))


def to_parent_module_path(
        ast_node: ast.ImportFrom,
        *,
        parent_module_path: catalog.Path
) -> catalog.Path:
    level = ast_node.level
    import_is_relative = level > 0
    if not import_is_relative:
        assert ast_node.module is not None, ast_node
        return catalog.path_from_string(ast_node.module)
    depth = (len(parent_module_path)
             + sources.is_package(parent_module_path)
             - level) or None
    module_path_parts = (list(parent_module_path[:depth])
                         + ([]
                            if ast_node.module is None
                            else ast_node.module.split('.')))
    return tuple(module_path_parts)


if sys.version_info < (3, 9):
    def subscript_to_item(ast_node: ast.Subscript) -> ast.expr:
        assert isinstance(ast_node.slice, ast.Index)
        return ast_node.slice.value
else:
    def subscript_to_item(ast_node: ast.Subscript) -> ast.expr:
        return ast_node.slice


def is_dependency_name(ast_node: ast.AST) -> TypeGuard[ast.Name]:
    return (isinstance(ast_node, ast.Name)
            and isinstance(ast_node.ctx, ast.Load))
