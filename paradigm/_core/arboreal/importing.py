import ast
import builtins
import importlib
import sys
import typing as t
from collections import deque
from functools import singledispatch
from pathlib import Path

from paradigm._core import (catalog,
                            namespacing,
                            sources)
from . import construction
from .execution import execute_statement


def flatten_ifs(module_root: ast.Module,
                *,
                module_path: catalog.Path,
                source_path: Path) -> None:
    namespace = construct_namespace(module_root, module_path)
    ast_nodes = [module_root]
    while ast_nodes:
        node = ast_nodes.pop()
        new_body = []
        for child_ast_node in _flatten_ifs(node.body,
                                           namespace=namespace,
                                           source_path=source_path):
            if isinstance(child_ast_node, ast.ClassDef):
                ast_nodes.append(child_ast_node)
            new_body.append(child_ast_node)
        node.body = new_body


def _flatten_ifs(candidates: t.Iterable[ast.AST],
                 *,
                 namespace: namespacing.Namespace,
                 source_path: Path) -> t.Iterable[ast.AST]:
    for candidate in candidates:
        if isinstance(candidate, ast.If):
            if evaluate_expression(candidate.test,
                                   source_path=source_path,
                                   namespace=namespace):
                children = candidate.body
            else:
                children = candidate.orelse
            yield from _flatten_ifs(children,
                                    namespace=namespace,
                                    source_path=source_path)
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


builtins_namespace = namespacing.from_module(builtins)


def flat_module_ast_node_from_path(module_path: catalog.Path) -> ast.Module:
    source_path = sources.from_module_path(module_path)
    result = construction.from_source_path(source_path)
    flatten_ifs(result,
                module_path=module_path,
                source_path=source_path)
    return result


def construct_namespace(module_ast_node: ast.Module,
                        module_path: catalog.Path) -> namespacing.Namespace:
    result = builtins_namespace.copy()
    update_namespace = NamespaceUpdater(namespace=result,
                                        module_path=module_path,
                                        parent_path=()).visit
    for if_node in left_search_within_children(module_ast_node,
                                               ast.If.__instancecheck__):
        for dependency_name in {
            child.id
            for child in left_search_within_children(
                    if_node.test,
                    lambda node: (isinstance(node, ast.Name)
                                  and isinstance(node.ctx, ast.Load))
            )
        }:
            dependency_node = right_find_within_children(
                    module_ast_node,
                    lambda node: dependency_name in node_to_names(node)
            )
            update_namespace(dependency_node)
    return result


@singledispatch
def node_to_names(node: ast.AST) -> t.List[str]:
    return []


@node_to_names.register(ast.ClassDef)
@node_to_names.register(ast.FunctionDef)
def class_def_or_function_def_to_name(node: ast.AST) -> t.List[str]:
    return [node.name]


@node_to_names.register(ast.Import)
@node_to_names.register(ast.ImportFrom)
def import_or_import_from_to_name(node: ast.Import) -> t.List[str]:
    return [to_alias_string(alias) for alias in node.names]


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


def right_find_within_children(
        node: ast.AST, condition: t.Callable[[ast.AST], bool]
) -> t.Optional[ast.AST]:
    candidates = deque(ast.iter_child_nodes(node))
    while candidates:
        candidate = candidates.pop()
        if condition(candidate):
            return candidate
        else:
            candidates.extendleft(ast.iter_child_nodes(candidate))
    return None


class NamespaceUpdater(ast.NodeVisitor):
    def __init__(self,
                 *,
                 namespace: namespacing.Namespace,
                 module_path: catalog.Path,
                 parent_path: catalog.Path) -> None:
        self.namespace = namespace
        self.module_path = module_path
        self.parent_path = parent_path

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            actual_module_name = alias.name
            module = importlib.import_module(actual_module_name)
            module_name = alias.asname
            if module_name is None:
                module_name, _, tail = actual_module_name.partition(
                        catalog.SEPARATOR
                )
                if tail:
                    module = sys.modules[module_name]
            self.namespace[module_name] = module

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        parent_module_path = to_parent_module_path(
                node,
                parent_module_path=self.module_path
        )
        for name_alias in node.names:
            alias_path = self.resolve_path(to_alias_path(name_alias))
            actual_path = to_actual_path(name_alias)
            if actual_path == catalog.WILDCARD_IMPORT_PATH:
                self.namespace.update(
                        namespacing.from_module_path(parent_module_path)
                )
                continue
            namespace = namespacing.from_module_path(parent_module_path)
            try:
                object_ = namespacing.search(namespace, actual_path)
            except KeyError:
                module_path = parent_module_path + actual_path
                object_ = importlib.import_module(str(module_path))
            self.namespace[str(alias_path)] = object_

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        path = self.resolve_path(catalog.path_from_string(node.name))
        (NamespaceUpdater(namespace=self.namespace,
                          module_path=self.module_path,
                          parent_path=path)
         .generic_visit(node))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def resolve_path(self, path: catalog.Path) -> catalog.Path:
        return self.parent_path + path


def to_actual_path(node: ast.alias) -> catalog.Path:
    return catalog.path_from_string(node.name)


def to_alias_path(node: ast.alias) -> catalog.Path:
    return catalog.path_from_string(to_alias_string(node))


def to_alias_string(node: ast.alias) -> str:
    return node.asname or node.name


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
