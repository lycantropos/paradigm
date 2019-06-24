from functools import partial
from typing import List

from typed_ast import ast3

from paradigm import (catalog,
                      sources)
from paradigm.hints import Map
from . import (examination,
               scoping)
from .data_access import search_nodes
from .evaluation import (evaluate_node,
                         to_actual_path,
                         to_alias_path)
from .hints import (Node,
                    Scope)
from .logical import is_link


def factory(*,
            module_path: catalog.Path,
            scope: Scope) -> Map[ast3.AST, None]:
    return Reducer(scope=scope,
                   module_path=module_path).visit


def complete_new_style_class_bases(bases: List[ast3.expr]) -> List[ast3.Expr]:
    return [*bases, ast3.Name('object', ast3.Load())]


class Reducer(ast3.NodeVisitor):
    def __init__(self,
                 *,
                 scope: Scope,
                 module_path: catalog.Path) -> None:
        self.scope = scope
        self.module_path = module_path

    def visit_Import(self, node: ast3.Import) -> None:
        for name_alias in node.names:
            alias_path = to_alias_path(name_alias)
            actual_path = to_actual_path(name_alias)
            for path, nodes in scoping.factory(actual_path).items():
                self.batch_register(alias_path.join(path), nodes)

    def visit_ImportFrom(self, node: ast3.ImportFrom) -> None:
        parent_module_path = catalog.from_string(node.module)
        for name_alias in node.names:
            alias_path = to_alias_path(name_alias)
            actual_path = to_actual_path(name_alias)
            if actual_path == catalog.WILDCARD_IMPORT:
                for path, nodes in scoping.factory(parent_module_path).items():
                    self.batch_register_if_not_found(path, nodes)
                continue
            object_path = parent_module_path.join(actual_path)
            if is_module_path(object_path):
                for path, nodes in scoping.factory(object_path).items():
                    self.batch_register(alias_path.join(path), nodes)
            else:
                scope = scoping.factory(parent_module_path)
                target_nodes = scope[actual_path]
                while isinstance(target_nodes[-1],
                                 (ast3.Import, ast3.ImportFrom)):
                    visit_target = (Reducer(scope=scope,
                                            module_path=parent_module_path)
                                    .visit)
                    for target_node in target_nodes:
                        visit_target(target_node)
                    target_nodes = scope[actual_path]
                self.scope.update(scope)
                self.scope[alias_path] = target_nodes

    def visit_ClassDef(self, node: ast3.ClassDef) -> None:
        path = catalog.from_string(node.name)
        bases = node.bases
        for base_index, base_node in enumerate(map(self.evaluator, bases)):
            if not is_link(base_node):
                base_scope = {}
                examination.conduct(base_node,
                                    scope=base_scope,
                                    module_path=self.module_path)
                for base_object_path, base_object_nodes in base_scope.items():
                    self.batch_register(base_object_path, base_object_nodes)
                base_class_path, = [
                    base_object_path
                    for base_object_path in base_scope
                    if not catalog.is_attribute(base_object_path)]
                bases[base_index] = ast3.Name(str(base_class_path),
                                              ast3.Load())
            else:
                try:
                    base_nodes = search_nodes(base_node,
                                              scope=self.scope)
                except KeyError:
                    while catalog.is_attribute(base_node):
                        base_node = base_node.parent
                        try:
                            base_nodes = search_nodes(base_node,
                                                      scope=self.scope)
                        except KeyError:
                            continue
                        else:
                            break
                    else:
                        raise
                self.visit(base_nodes[-1])
        bases = complete_new_style_class_bases(bases)
        for base_node in map(self.evaluator, bases):
            base_scope = scoping.to_children_scope(base_node,
                                                   scope=self.scope)
            for base_object_path, base_object_nodes in base_scope.items():
                self.batch_register_if_not_found(base_object_path
                                                 .with_parent(path),
                                                 base_object_nodes)
        children_scope = {}
        visit_child = Reducer(scope=children_scope,
                              module_path=path).visit
        for child in node.body:
            visit_child(child)
        for child_path, child_nodes in children_scope.items():
            self.batch_register(path.join(child_path), child_nodes)

    def batch_register(self, path, nodes: List[Node]) -> None:
        self.scope.setdefault(path, []).extend(nodes)

    def batch_register_if_not_found(self, path, nodes: List[Node]) -> None:
        self.scope.setdefault(path, nodes)

    @property
    def evaluator(self) -> Map[ast3.expr, catalog.Path]:
        return partial(evaluate_node,
                       scope=self.scope,
                       module_path=self.module_path)


def is_module_path(object_path: catalog.Path) -> bool:
    try:
        sources.factory(object_path)
    except KeyError:
        return False
    else:
        return True
