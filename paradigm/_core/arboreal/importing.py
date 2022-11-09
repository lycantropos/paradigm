import ast
import typing as t
from collections import deque
from importlib import import_module
from pathlib import Path

from paradigm._core import (catalog,
                            namespacing,
                            scoping,
                            sources)
from . import construction
from .execution import execute_statement


def flatten_ifs(
        module_root: ast.Module,
        *,
        module_path: catalog.Path,
        source_path: Path,
        modules_definitions: t.Mapping[catalog.Path, scoping.Scope],
        modules_references: t.Mapping[catalog.Path, scoping.ModuleReferences],
        modules_sub_scopes: t.Mapping[catalog.Path, scoping.ModuleSubScopes]
) -> None:
    ast_nodes = [module_root]
    while ast_nodes:
        node = ast_nodes.pop()
        new_body = []
        for child_ast_node in _flatten_ifs(
                node.body,
                module_path=module_path,
                source_path=source_path,
                modules_definitions=modules_definitions,
                modules_references=modules_references,
                modules_sub_scopes=modules_sub_scopes
        ):
            if isinstance(child_ast_node, ast.ClassDef):
                ast_nodes.append(child_ast_node)
            new_body.append(child_ast_node)
        node.body = new_body


def _flatten_ifs(
        candidates: t.Iterable[ast.AST],
        *,
        module_path: catalog.Path,
        source_path: Path,
        modules_definitions: t.Mapping[catalog.Path, scoping.Scope],
        modules_references: t.Mapping[catalog.Path, scoping.ModuleReferences],
        modules_sub_scopes: t.Mapping[catalog.Path, scoping.ModuleSubScopes]
) -> t.Iterable[ast.AST]:
    for candidate in candidates:
        if isinstance(candidate, ast.If):
            if evaluate_test(candidate.test,
                             module_path=module_path,
                             source_path=source_path,
                             modules_definitions=modules_definitions,
                             modules_references=modules_references,
                             modules_sub_scopes=modules_sub_scopes):
                children = candidate.body
            else:
                children = candidate.orelse
            yield from _flatten_ifs(children,
                                    module_path=module_path,
                                    source_path=source_path,
                                    modules_definitions=modules_definitions,
                                    modules_references=modules_references,
                                    modules_sub_scopes=modules_sub_scopes)
        else:
            yield candidate


def evaluate_expression(node: ast.expr,
                        *,
                        source_path: Path,
                        namespace: namespacing.Namespace) -> t.Any:
    # to avoid name conflicts
    # we're using name that won't be present
    # because it'll lead to ``SyntaxError`` otherwise
    # and no AST will be generated
    temporary_name = '@tmp'
    assignment = expression_to_assignment(node,
                                          name=temporary_name)
    execute_statement(assignment,
                      source_path=source_path,
                      namespace=namespace)
    return namespace.pop(temporary_name)


def expression_to_assignment(node: ast.expr,
                             *,
                             name: str) -> ast.Assign:
    name_node = ast.copy_location(ast.Name(name, ast.Store()), node)
    return ast.copy_location(ast.Assign([name_node], node), node)


def flat_module_ast_node_from_path(
        module_path: catalog.Path,
        modules_definitions: t.Mapping[catalog.Path, scoping.Scope],
        modules_references: t.Mapping[catalog.Path, scoping.ModuleReferences],
        modules_sub_scopes: t.Mapping[catalog.Path, scoping.ModuleSubScopes]
) -> ast.Module:
    source_path = sources.from_module_path(module_path)
    result = construction.from_source_path(source_path)
    flatten_ifs(result,
                module_path=module_path,
                source_path=source_path,
                modules_definitions=modules_definitions,
                modules_references=modules_references,
                modules_sub_scopes=modules_sub_scopes)
    return result


def left_search_within_children(
        node: ast.AST, condition: t.Callable[[ast.AST], bool]
) -> t.Iterable[ast.AST]:
    candidates = deque(ast.iter_child_nodes(node))
    while candidates:
        candidate = candidates.popleft()
        if condition(candidate):
            yield candidate
        else:
            candidates.extend(ast.iter_child_nodes(candidate))


def evaluate_test(
        node: ast.AST,
        module_path: catalog.Path,
        source_path: Path,
        modules_definitions: t.Mapping[catalog.Path, scoping.Scope],
        modules_references: t.Mapping[catalog.Path, scoping.ModuleReferences],
        modules_sub_scopes: t.Mapping[catalog.Path, scoping.ModuleSubScopes]
) -> bool:
    namespace = {}
    for dependency_name in {
        child.id
        for child in left_search_within_children(
                node,
                lambda child: (isinstance(child, ast.Name)
                               and isinstance(child.ctx, ast.Load))
        )
    }:
        dependency_module_path, dependency_object_path = (
            scoping.resolve_object_path(module_path, (dependency_name,),
                                        modules_definitions,
                                        modules_references, modules_sub_scopes)
        )
        module = import_module(catalog.path_to_string(dependency_module_path))
        namespace[dependency_name] = (
            namespacing.search(vars(module), dependency_object_path)
            if dependency_object_path
            else module
        )
    return evaluate_expression(node,
                               namespace=namespace,
                               source_path=source_path)


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
