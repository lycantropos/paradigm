import builtins
from itertools import chain
from pathlib import Path
from typing import (Any,
                    Iterable)

from typed_ast import ast3

from paradigm import (catalog,
                      importing,
                      namespaces,
                      sources)
from paradigm.hints import Namespace
from . import construction
from .evaluation import (to_actual_path,
                         to_alias_path)
from .execution import execute


def to_parent_module_path(object_: ast3.ImportFrom,
                          *,
                          parent_module_path: catalog.Path) -> catalog.Path:
    level = object_.level
    import_is_relative = level > 0
    if not import_is_relative:
        return catalog.factory(object_.module)
    depth = (len(parent_module_path.parts)
             + catalog.is_package(parent_module_path)
             - level) or None
    module_path_parts = filter(None,
                               chain(parent_module_path.parts[:depth],
                                     (object_.module,)))
    return catalog.Path(*module_path_parts)


def expression_to_assignment(node: ast3.expr,
                             *,
                             name: str) -> ast3.Assign:
    name_node = ast3.copy_location(ast3.Name(name, ast3.Store()), node)
    result = ast3.Assign([name_node], node, None)
    return ast3.copy_location(result, node)


class ImportsFlattener(ast3.NodeTransformer):
    def __init__(self, module_path: catalog.Path) -> None:
        self.module_path = module_path

    def visit_Import(self, node: ast3.Import) -> Iterable[ast3.Import]:
        for name_alias in node.names:
            yield ast3.Import([name_alias])

    def visit_ImportFrom(self, node: ast3.ImportFrom
                         ) -> Iterable[ast3.ImportFrom]:
        parent_module_path = to_parent_module_path(
                node,
                parent_module_path=self.module_path)
        for name_alias in node.names:
            actual_path = to_actual_path(name_alias)
            if actual_path == catalog.WILDCARD_IMPORT:
                yield from to_flat_root(parent_module_path).body
            else:
                yield ast3.ImportFrom(str(parent_module_path), [name_alias], 0)

    def visit_FunctionDef(self, node: ast3.FunctionDef) -> ast3.FunctionDef:
        return node


class NamespaceCollector(ast3.NodeVisitor):
    def __init__(self,
                 *,
                 namespace: Namespace,
                 module_path: catalog.Path,
                 parent_path: catalog.Path,
                 is_nested: bool = False) -> None:
        self.namespace = namespace
        self.module_path = module_path
        self.parent_path = parent_path
        self.is_nested = is_nested

    def visit_Import(self, node: ast3.Import) -> None:
        for name_alias in node.names:
            alias_path = self.resolve_path(to_alias_path(name_alias))
            actual_path = to_actual_path(name_alias)
            if not namespaces.contains(self.namespace, alias_path):
                parent_module_name = actual_path.parts[0]
                module = importing.safe(parent_module_name)
                self.namespace[parent_module_name] = module

    def visit_ImportFrom(self, node: ast3.ImportFrom) -> None:
        parent_module_path = to_parent_module_path(
                node,
                parent_module_path=self.module_path)
        for name_alias in node.names:
            alias_path = self.resolve_path(to_alias_path(name_alias))
            actual_path = to_actual_path(name_alias)
            if actual_path == catalog.WILDCARD_IMPORT:
                self.namespace.update(namespaces.factory(parent_module_path))
                yield from to_flat_root(parent_module_path).body
                continue
            elif not namespaces.contains(self.namespace, alias_path):
                namespace = namespaces.factory(parent_module_path)
                try:
                    object_ = namespaces.search(namespace, actual_path)
                except KeyError:
                    module_path = parent_module_path.join(actual_path)
                    object_ = importing.safe(str(module_path))
                self.namespace[str(alias_path)] = object_

    def visit_ClassDef(self, node: ast3.ClassDef) -> None:
        path = self.resolve_path(catalog.factory(node.name))
        (NamespaceCollector(namespace=self.namespace,
                            parent_path=path,
                            module_path=self.module_path,
                            is_nested=True)
         .generic_visit(node))

    def visit_FunctionDef(self, node: ast3.FunctionDef) -> None:
        return

    def resolve_path(self, path: catalog.Path) -> catalog.Path:
        if self.is_nested:
            return self.parent_path.join(path)
        return path


class IfsFlattener(ast3.NodeTransformer):
    def __init__(self,
                 *,
                 namespace: Namespace,
                 source_path: Path) -> None:
        self.namespace = namespace
        self.source_path = source_path

    def visit_FunctionDef(self, node: ast3.FunctionDef) -> ast3.FunctionDef:
        return node

    def visit_If(self, node: ast3.If) -> Iterable[ast3.AST]:
        if evaluate_expression(node.test,
                               source_path=self.source_path,
                               namespace=self.namespace):
            children = node.body
        else:
            children = node.orelse
        for child in children:
            self.generic_visit(child)
        yield from children


def evaluate_expression(node: ast3.expr,
                        *,
                        source_path: Path,
                        namespace: Namespace) -> Any:
    # to avoid name conflicts
    # we're using name that won't be present
    # because it'll lead to ``SyntaxError`` otherwise
    # and no AST will be generated
    temporary_name = '@tmp'
    assignment = expression_to_assignment(node,
                                          name=temporary_name)
    execute(assignment,
            source_path=source_path,
            namespace=namespace)
    return namespace.pop(temporary_name)


built_ins_namespace = namespaces.factory(builtins)


def to_flat_root(module_path: catalog.Path) -> ast3.Module:
    source_path = sources.factory(module_path)
    result = construction.from_source_path(source_path)
    namespace = namespaces.merge(built_ins_namespace,
                                 namespaces.from_module_path(module_path))
    ImportsFlattener(module_path).visit(result)
    NamespaceCollector(namespace=namespace,
                       module_path=module_path,
                       parent_path=catalog.Path()).visit(result)
    IfsFlattener(namespace=namespace,
                 source_path=source_path).visit(result)
    return result
