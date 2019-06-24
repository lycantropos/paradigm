from functools import partial
from typing import List

from typed_ast import ast3

from paradigm import catalog
from paradigm.hints import Map
from .evaluation import (evaluate_node,
                         to_alias_path)
from .hints import (Node,
                    Scope)
from .logical import is_link


class Registry(ast3.NodeVisitor):
    def __init__(self,
                 *,
                 scope: Scope,
                 module_path: catalog.Path) -> None:
        self.scope = scope
        self.module_path = module_path

    def visit_Import(self, node: ast3.Import):
        for name_alias in node.names:
            self.register(to_alias_path(name_alias), node)

    def visit_ImportFrom(self, node: ast3.ImportFrom):
        for name_alias in node.names:
            self.register(to_alias_path(name_alias), node)

    def visit_FunctionDef(self, node: ast3.FunctionDef):
        self.generic_visit(node)
        path = catalog.from_string(node.name)
        self.register(path, node)

    def visit_ClassDef(self, node: ast3.ClassDef):
        path = catalog.from_string(node.name)
        self.register(path, node)
        children_scope = {}
        visit_child = Registry(scope=children_scope,
                               module_path=self.module_path).visit
        for child in node.body:
            visit_child(child)
        for child_path, child_nodes in children_scope.items():
            self.batch_register(path.join(child_path), child_nodes)

    def visit_Assign(self, node: ast3.Assign):
        value_node = self.evaluator(node.value)
        for path in map(self.evaluator, node.targets):
            self.register(path, value_node)
        if not is_link(value_node):
            self.visit(value_node)

    def visit_AnnAssign(self, node: ast3.AnnAssign):
        self.register(self.evaluator(node.target), node)

    def batch_register(self, path, nodes: List[Node]) -> None:
        self.scope.setdefault(path, []).extend(nodes)

    def register(self, path, node: Node) -> None:
        self.scope.setdefault(path, []).append(node)

    @property
    def evaluator(self) -> Map[ast3.expr, catalog.Path]:
        return partial(evaluate_node,
                       scope=self.scope,
                       module_path=self.module_path)


def conduct(node: ast3.AST,
            *,
            module_path: catalog.Path,
            scope: Scope) -> None:
    Registry(scope=scope,
             module_path=module_path).visit(node)
