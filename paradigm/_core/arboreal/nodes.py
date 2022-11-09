import ast
import builtins
import enum
import sys
import typing as t
from functools import (reduce,
                       singledispatch)
from pathlib import Path
from types import MappingProxyType

from reprit.base import generate_repr

from paradigm._core import (catalog,
                            sources,
                            stubs)
from .importing import (flat_module_ast_node_from_path,
                        to_parent_module_path)
from .utils import singledispatchmethod


class NameLookupError(Exception):
    pass


class NameAlreadyExists(Exception):
    pass


class NodeHasDifferentKind(Exception):
    pass


class NodeKind(enum.IntEnum):
    ANNOTATED_ASSIGNMENT = enum.auto()
    ASSIGNMENT = enum.auto()
    CLASS = enum.auto()
    CONSTANT = enum.auto()
    FUNCTION = enum.auto()
    IMPORT_FROM = enum.auto()
    MODULE = enum.auto()
    MODULE_IMPORT = enum.auto()
    SUBSCRIPT = enum.auto()
    UNION = enum.auto()
    UNDEFINED = enum.auto()

    def __repr__(self) -> str:
        return f'{type(self).__qualname__}.{self.name}'


NODE_KINDS_AST_TYPES: t.Dict[
    NodeKind, t.Union[t.Type[ast.AST], t.Tuple[t.Type[ast.AST], ...]]
] = {
    NodeKind.ANNOTATED_ASSIGNMENT: ast.AnnAssign,
    NodeKind.ASSIGNMENT: ast.Assign,
    NodeKind.CLASS: ast.ClassDef,
    NodeKind.CONSTANT: ast.NameConstant,
    NodeKind.FUNCTION: (ast.AsyncFunctionDef, ast.FunctionDef),
    NodeKind.IMPORT_FROM: ast.ImportFrom,
    NodeKind.MODULE: ast.Module,
    NodeKind.MODULE_IMPORT: (ast.Import, ast.ImportFrom),
    NodeKind.SUBSCRIPT: ast.Subscript,
    NodeKind.UNDEFINED: (),
    NodeKind.UNION: ast.BinOp,
}
AST_TYPES_NODE_KINDS: t.Dict[t.Type[ast.AST], NodeKind] = {
    ast.AnnAssign: NodeKind.ANNOTATED_ASSIGNMENT,
    ast.Assign: NodeKind.ASSIGNMENT,
    ast.AsyncFunctionDef: NodeKind.FUNCTION,
    ast.ClassDef: NodeKind.CLASS,
    ast.FunctionDef: NodeKind.FUNCTION,
    ast.Import: NodeKind.MODULE_IMPORT,
    ast.ImportFrom: NodeKind.IMPORT_FROM,
    ast.Module: NodeKind.MODULE,
    ast.NameConstant: NodeKind.CONSTANT,
    ast.BinOp: NodeKind.UNION,
    ast.Subscript: NodeKind.SUBSCRIPT,
}
assert all(kind in NODE_KINDS_AST_TYPES for kind in NodeKind)


def _named_tuple_to_constructor_ast_node(ast_node: ast.ClassDef,
                                         class_name: str) -> ast.FunctionDef:
    annotations_ast_nodes: t.List[ast.AnnAssign] = [
        ast_child_node
        for ast_child_node in ast_node.body
        if isinstance(ast_child_node, ast.AnnAssign)
    ]
    assert all(isinstance(ast_node.target, ast.Name)
               for ast_node in annotations_ast_nodes), ast_node
    constructor_ast_node = ast.fix_missing_locations(
            ast.FunctionDef('__new__',
                            _annotations_to_signature(annotations_ast_nodes),
                            [ast.Expr(ast.Ellipsis())], [],
                            ast.Name(class_name, ast.Load()))
    )
    return constructor_ast_node


if sys.version_info < (3, 8):
    def _annotations_to_signature(
            ast_nodes: t.List[ast.AnnAssign]
    ) -> ast.arguments:
        return ast.arguments([ast.arg(ast_node.target.id, ast_node.annotation)
                              for ast_node in ast_nodes],
                             None, [], [], None,
                             [ast_node.value
                              for ast_node in ast_nodes
                              if ast_node.value is not None])
else:
    def _annotations_to_signature(
            ast_nodes: t.List[ast.AnnAssign]
    ) -> ast.arguments:
        return ast.arguments([],
                             [ast.arg(ast_node.target.id, ast_node.annotation)
                              for ast_node in ast_nodes],
                             None, [], [], None,
                             [ast_node.value
                              for ast_node in ast_nodes
                              if ast_node.value is not None])


class Node:
    @property
    def ast_nodes(self) -> t.List[ast.AST]:
        return self._resolve_ast_nodes()

    @property
    def kind(self) -> NodeKind:
        return self._resolve_kind()

    @property
    def module_path(self) -> catalog.Path:
        return self._resolve_module_path()

    @property
    def object_path(self) -> catalog.Path:
        return self._resolve_object_path()

    @property
    def stub_path(self) -> Path:
        return self._resolve_stub_path()

    def get_attribute_by_name(self, name: str) -> 'Node':
        try:
            return self._local_lookup_name(name)
        except NameLookupError:
            for sub_node in self._sub_nodes:
                try:
                    return sub_node.get_attribute_by_name(name)
                except NameLookupError:
                    pass
            raise NameLookupError(name)

    def get_attribute_by_path(self, path: catalog.Path) -> 'Node':
        return reduce(type(self).get_attribute_by_name, path, self)

    def global_lookup_name(self, name: str) -> 'Node':
        try:
            return self._local_lookup_name(name)
        except NameLookupError:
            if self._resolve_kind() is NodeKind.CLASS:
                parent = _graph[self._resolve_module_path()]
                assert parent._resolve_kind() is NodeKind.MODULE, parent
                return parent.global_lookup_name(name)
            else:
                if self._resolve_kind() is NodeKind.MODULE:
                    for sub_node in self._resolve_sub_nodes():
                        try:
                            return sub_node.global_lookup_name(name)
                        except NameLookupError:
                            pass
                return (self._builtins.global_lookup_name(name)
                        if self is not self._builtins
                        else self._lookup_constant(name))

    def locate_name(self, name: str) -> t.Tuple[int, 'Node']:
        try:
            return 0, self._local_lookup_name(name)
        except NameLookupError:
            for depth, sub_node in enumerate(self._resolve_sub_nodes(),
                                             start=1):
                try:
                    sub_depth, node = sub_node.locate_name(name)
                except NameLookupError:
                    pass
                else:
                    return depth, node
            raise NameLookupError(name)

    def resolve(self) -> None:
        module_node = _graph[self._resolve_module_path()]
        while module_node._resolve_kind() is NodeKind.MODULE_IMPORT:
            module_node._resolve_module_import()
            module_node = _graph[self._resolve_module_path()]
        assert _graph[self._resolve_module_path()] is module_node, self
        if self._resolve_kind() is NodeKind.IMPORT_FROM:
            assert len(self._resolve_object_path()) == 1, self
            final_name, = self._resolve_object_path()
            for submodule_node in reversed(module_node._resolve_sub_nodes()):
                try:
                    node = submodule_node.get_attribute_by_name(final_name)
                except NameLookupError:
                    pass
                else:
                    node.resolve()
                    self._set_redirect(node)
                    break
        for sub_node in self._resolve_sub_nodes():
            sub_node.resolve()
        if self._resolve_kind() is NodeKind.UNDEFINED:
            parent = module_node._local_lookup_path(
                    catalog.path_to_parent(self._resolve_object_path())
            )
            if parent._resolve_kind() is NodeKind.CLASS:
                final_name = self._resolve_object_path()[-1]
                try:
                    node = parent._local_lookup_name(final_name)
                    if node is self:
                        raise NameLookupError(final_name)
                except NameLookupError:
                    for parent_sub_node in parent._resolve_sub_nodes():
                        parent_sub_node.resolve()
                        try:
                            node = parent_sub_node.get_attribute_by_name(
                                    final_name
                            )
                        except NameLookupError:
                            pass
                        else:
                            break
                    else:
                        raise
                assert node is not self, self
                node.resolve()
                self._set_redirect(node)
        assert (self._resolve_kind() is not NodeKind.MODULE
                or not self._resolve_object_path()), self
        assert self._resolve_kind() not in (NodeKind.IMPORT_FROM,
                                            NodeKind.MODULE_IMPORT,
                                            NodeKind.UNDEFINED), self

    def _locals_contain(self, name: str) -> bool:
        return name in self._resolve_locals()

    def _lookup_constant(self, name: str) -> 'Node':
        try:
            return self._constants[name]
        except KeyError as error:
            raise NameLookupError(name) from error

    def _global_lookup_name_inserting_default(self, name: str) -> 'Node':
        try:
            return self.global_lookup_name(name)
        except NameLookupError:
            result = Node(self._resolve_stub_path(),
                          self._resolve_module_path(), (name,),
                          NodeKind.UNDEFINED, [])
            _import_module_node(self._resolve_module_path())._set_name(name,
                                                                       result)
            return result

    def _global_lookup_path_inserting_default(self,
                                              path: catalog.Path) -> 'Node':
        result = self._global_lookup_name_inserting_default(path[0])
        for part in path[1:]:
            result = result._local_lookup_name_inserting_default(part)
        return result

    def _local_lookup_name(self, name: str) -> 'Node':
        try:
            return self._resolve_locals()[name]
        except KeyError as error:
            raise NameLookupError(name) from error

    def _local_lookup_name_inserting(self, name: str, value: 'Node') -> 'Node':
        try:
            return self._local_lookup_name(name)
        except NameLookupError:
            self._set_name(name, value)
            return value

    def _local_lookup_name_inserting_default(self, name: str) -> 'Node':
        try:
            return self._local_lookup_name(name)
        except NameLookupError:
            result = Node(
                    self._resolve_stub_path(), self._resolve_module_path(),
                    self._resolve_object_path() + (name,),
                    NodeKind.UNDEFINED, []
            )
            self._set_name(name, result)
            return result

    def _local_lookup_path_inserting_default(self,
                                             path: catalog.Path) -> 'Node':
        result = self
        for part in path:
            result = result._local_lookup_name_inserting_default(part)
        return result

    def _local_lookup_path(self, path: catalog.Path) -> 'Node':
        result = self
        for part in path:
            result = result._local_lookup_name(part)
        return result

    def _resolve_module_import(self) -> None:
        ast_node = flat_module_ast_node_from_path(
                self._resolve_module_path(),
                modules_definitions=stubs.definitions,
                modules_references=stubs.references,
                modules_sub_scopes=stubs.sub_scopes
        )
        self._set_ast_node(ast_node)
        for child_ast_node in ast_node.body:
            self._visit_names(child_ast_node)
        assert self.kind is NodeKind.MODULE, self

    _builtins: 'Node'
    _constants: t.Dict[str, 'Node']

    def _append(self, node: 'Node') -> None:
        assert node is not self, self
        assert self._object_path is not None, self
        assert (self._kind is NodeKind.CLASS
                or self._kind is NodeKind.MODULE), self
        self._sub_nodes.append(node)

    def _set_ast_node(self, ast_node: ast.AST) -> None:
        assert (self._resolve_kind() is NodeKind.IMPORT_FROM
                or self._resolve_kind() is NodeKind.MODULE_IMPORT
                or self._resolve_kind() is NodeKind.UNDEFINED), self
        node_kind = AST_TYPES_NODE_KINDS[type(ast_node)]
        assert (node_kind is not NodeKind.IMPORT_FROM
                and node_kind is not NodeKind.MODULE_IMPORT
                and node_kind is not NodeKind.UNDEFINED), self
        self._kind = node_kind
        assert not self._ast_nodes, self
        self._ast_nodes = [ast_node]

    def _set_name(self, name: str, value: 'Node') -> None:
        assert catalog.SEPARATOR not in name, name
        if self._locals_contain(name):
            raise NameAlreadyExists(name)
        self._locals[name] = value

    def _set_path(self, path: catalog.Path, value: 'Node') -> None:
        node = (self._local_lookup_path_inserting_default(
                catalog.path_to_parent(path))
                if len(path) > 1
                else self)
        node._set_name(path[-1], value)

    def _upsert_path(self, path: catalog.Path, value: 'Node') -> None:
        node = (self._global_lookup_path_inserting_default(
                catalog.path_to_parent(path))
                if len(path) > 1
                else self)
        node._upsert_name(path[-1], value)

    def _upsert_name(self, name: str, value: 'Node') -> None:
        assert catalog.SEPARATOR not in name, name
        if self._locals_contain(name):
            candidate = self._locals[name]
            if candidate is not value:
                candidate._set_redirect(value)
        else:
            self._set_name(name, value)

    def _set_redirect(self, other: 'Node') -> None:
        assert (
                self._resolve_kind() in (NodeKind.IMPORT_FROM,
                                         NodeKind.UNDEFINED)
        ), self
        assert not self._ast_nodes, self
        assert not self._sub_nodes, self
        cursor = self._redirect
        while cursor is not None:
            cursor, cursor._redirect = cursor._redirect, other
        self._redirect = other

    @singledispatchmethod
    def _resolve_assigning_value(self,
                                 ast_node: ast.AST) -> t.Optional['Node']:
        raise TypeError(type(ast_node))

    @_resolve_assigning_value.register(ast.Name)
    def _(self, ast_node: ast.Name) -> t.Optional['Node']:
        assert isinstance(ast_node.ctx, ast.Load), ast_node
        return self._global_lookup_name_inserting_default(ast_node.id)

    @_resolve_assigning_value.register(ast.Attribute)
    def _(self, ast_node: ast.Attribute) -> t.Optional['Node']:
        assert isinstance(ast_node.ctx, ast.Load), ast_node
        value_node = self._resolve_assigning_value(ast_node.value)
        return (
            value_node
            if value_node is None
            else value_node._local_lookup_name_inserting_default(ast_node.attr)
        )

    @_resolve_assigning_value.register(ast.Dict)
    @_resolve_assigning_value.register(ast.Tuple)
    @_resolve_assigning_value.register(ast.List)
    @_resolve_assigning_value.register(ast.Set)
    def _(self, ast_node: ast.expr) -> t.Optional['Node']:
        assert isinstance(ast_node.ctx, ast.Load), ast_node
        return None

    @_resolve_assigning_value.register(ast.Subscript)
    def _(self, ast_node: ast.Subscript) -> t.Optional['Node']:
        assert isinstance(ast_node.ctx, ast.Load), ast_node
        return Node(self._resolve_stub_path(), self._resolve_module_path(),
                    None,
                    NodeKind.SUBSCRIPT, [ast_node])

    @_resolve_assigning_value.register(ast.Constant)
    @_resolve_assigning_value.register(ast.NameConstant)
    def _(
            self, ast_node: t.Union[ast.Constant, ast.NameConstant]
    ) -> t.Optional['Node']:
        try:
            return self._lookup_constant(repr(ast_node.value))
        except NameLookupError:
            return None

    @_resolve_assigning_value.register(ast.BinOp)
    def _(self, ast_node: ast.BinOp) -> t.Optional['Node']:
        if isinstance(ast_node.op, ast.BitOr):
            left_node = self._resolve_assigning_value(ast_node.left)
            right_node = self._resolve_assigning_value(ast_node.right)
            return (None
                    if left_node is None or right_node is None
                    else Node(self._resolve_stub_path(),
                              self._resolve_module_path(), None,
                              NodeKind.UNION, [ast_node], left_node,
                              right_node))
        else:
            return None

    @_resolve_assigning_value.register(ast.Call)
    @_resolve_assigning_value.register(ast.Ellipsis)
    def _(self, ast_node: ast.Call) -> t.Optional['Node']:
        return None

    @singledispatchmethod
    def _resolve_annotation(self, ast_node: ast.AST) -> 'Node':
        raise TypeError(type(ast_node))

    @_resolve_annotation.register(ast.Name)
    def _(self, ast_node: ast.Name) -> 'Node':
        assert isinstance(ast_node.ctx, ast.Load), ast_node
        return self._global_lookup_name_inserting_default(ast_node.id)

    @_resolve_annotation.register(ast.Subscript)
    def _(self, ast_node: ast.Subscript) -> 'Node':
        assert isinstance(ast_node.ctx, ast.Load), ast_node
        return Node(self._resolve_stub_path(), self._resolve_module_path(),
                    None, NodeKind.SUBSCRIPT, [ast_node],
                    self._resolve_annotation(ast_node.value))

    @_resolve_annotation.register(ast.NameConstant)
    @_resolve_annotation.register(ast.Constant)
    def _(self, ast_node: t.Union[ast.Constant, ast.NameConstant]) -> 'Node':
        return self._lookup_constant(repr(ast_node.value))

    @_resolve_annotation.register(ast.Attribute)
    def _(self, ast_node: ast.Attribute) -> 'Node':
        assert isinstance(ast_node.ctx, ast.Load), ast_node
        value_node = self._resolve_annotation(ast_node.value)
        return value_node._local_lookup_name_inserting_default(ast_node.attr)

    @_resolve_annotation.register(ast.BinOp)
    def _(self, ast_node: ast.BinOp) -> 'Node':
        assert isinstance(ast_node.op, ast.BitOr), ast_node
        left_node = self._resolve_annotation(ast_node.left)
        right_node = self._resolve_annotation(ast_node.right)
        return Node(self._resolve_stub_path(), self._resolve_module_path(),
                    None, NodeKind.UNION, [ast_node], left_node, right_node)

    @singledispatchmethod
    def _visit_names(self, ast_node: ast.AST) -> None:
        raise TypeError(type(ast_node))

    @_visit_names.register(ast.Expr)
    def _(self, ast_node: ast.Expr) -> None:
        assert isinstance(ast_node.value, ast.Ellipsis), ast_node
        return None

    @_visit_names.register(ast.AugAssign)
    def _(self, ast_node: ast.AugAssign) -> None:
        assert (isinstance(ast_node.target, ast.Name)
                and ast_node.target.id == '__all__')
        assert isinstance(ast_node.op, ast.Add), self
        return None

    @_visit_names.register(ast.AnnAssign)
    def _(self, ast_node: ast.AnnAssign) -> None:
        value_ast_node = ast_node.value
        target_path = _resolve_assignment_target(ast_node.target)
        if value_ast_node is None:
            value_node = self._resolve_annotation(ast_node.annotation)
            self._upsert_path(target_path, value_node)
        else:
            value_node = self._resolve_assigning_value(value_ast_node)
            if value_node is None:
                value_node = self._resolve_annotation(ast_node.annotation)
            if value_node._resolve_object_path() is None:
                value_node._object_path = target_path
            self._upsert_path(target_path, value_node)

    @_visit_names.register(ast.Assign)
    def _(self, ast_node: ast.Assign) -> None:
        value_node = self._resolve_assigning_value(ast_node.value)
        if value_node is None:
            targets = ast_node.targets
            assert targets, ast_node
            target_path = _resolve_assignment_target(targets[0])
            value_node = self._local_lookup_path_inserting_default(target_path)
            assert value_node._resolve_object_path() is not None
            value_node._set_ast_node(ast_node)
            for target in targets[1:]:
                self._upsert_path(_resolve_assignment_target(target),
                                  value_node)
        else:
            for target in ast_node.targets:
                self._upsert_path(_resolve_assignment_target(target),
                                  value_node)

    @_visit_names.register(ast.Import)
    def _(self, ast_node: ast.Import) -> None:
        for alias in ast_node.names:
            module_path = catalog.path_from_string(alias.name)
            module_import_node = _import_module_node(module_path)
            if alias.asname is None:
                self._upsert_path(module_path, module_import_node)
            else:
                assert isinstance(alias.asname, str), self
                self._upsert_name(alias.asname, module_import_node)

    @_visit_names.register(ast.ImportFrom)
    def _(self, ast_node: ast.ImportFrom) -> None:
        assert self._resolve_kind() is NodeKind.MODULE, self
        assert not self._resolve_object_path(), self
        module_path = to_parent_module_path(
                ast_node,
                parent_module_path=self._resolve_module_path()
        )
        if module_path == self._resolve_module_path():
            for alias in ast_node.names:
                submodule_name = alias.name
                assert submodule_name != catalog.WILDCARD_IMPORT_NAME
                submodule_path = (self._resolve_module_path()
                                  + (submodule_name,))
                submodule_node = _import_module_node(submodule_path)
                assert (
                        submodule_node._resolve_kind()
                        in (NodeKind.MODULE_IMPORT, NodeKind.MODULE)
                ), self
                self._upsert_name(_to_alias_string(alias), submodule_node)
        else:
            module_node = _import_module_node(module_path)
            for alias in ast_node.names:
                actual_name = alias.name
                if actual_name == catalog.WILDCARD_IMPORT_NAME:
                    module_node.resolve()
                    self._append(module_node)
                else:
                    candidate_module_path = module_path + (actual_name,)
                    if _is_module_path(candidate_module_path):
                        imported_node = _import_module_node(
                                candidate_module_path
                        )
                    else:
                        imported_node = (
                            module_node._local_lookup_name_inserting(
                                    actual_name,
                                    Node(module_node._resolve_stub_path(),
                                         module_path, (actual_name,),
                                         NodeKind.IMPORT_FROM, [])
                            )
                        )
                    self._upsert_name(_to_alias_string(alias), imported_node)

    @_visit_names.register(ast.ClassDef)
    def _(
            self,
            ast_node: ast.ClassDef,
            *,
            _named_tuple_path: catalog.Path
            = catalog.object_path_from_callable(t.NamedTuple),
            _typing_path: catalog.Path = catalog.module_path_from_module(
                    t)
    ) -> None:
        class_name = ast_node.name
        class_node = self._local_lookup_name_inserting_default(class_name)
        class_node._set_ast_node(ast_node)
        assert class_node._resolve_kind() is NodeKind.CLASS
        ast_children_nodes: t.List[ast.AST] = [*ast_node.body]
        for ast_base_node in ast_node.bases:
            base_path = _resolve_base_class_path(ast_base_node)
            base_node = self._global_lookup_path_inserting_default(base_path)
            if (base_node.module_path == _typing_path
                    and base_node.object_path == _named_tuple_path):
                ast_children_nodes.append(_named_tuple_to_constructor_ast_node(
                        ast_node, class_name
                ))
            class_node._append(base_node)
        if self is not self._builtins:
            assert class_name != object.__name__, self
            class_node._append(
                    self._builtins.get_attribute_by_name(object.__name__)
            )
        elif class_name != object.__name__:
            assert (
                    self._resolve_module_path() == catalog.BUILTINS_MODULE_PATH
            ), self
            class_node._append(self.get_attribute_by_name(object.__name__))
        for ast_child_node in ast_children_nodes:
            class_node._visit_names(ast_child_node)

    @_visit_names.register(ast.AsyncFunctionDef)
    @_visit_names.register(ast.FunctionDef)
    def _(self,
          ast_node: t.Union[ast.AsyncFunctionDef, ast.FunctionDef]) -> None:
        try:
            namesake_node = self._local_lookup_name(ast_node.name)
        except NameLookupError:
            node = Node(self._resolve_stub_path(), self._resolve_module_path(),
                        self._resolve_object_path() + (ast_node.name,),
                        NodeKind.FUNCTION, [ast_node])
            self._set_name(ast_node.name, node)
        else:
            if namesake_node._resolve_kind() is NodeKind.FUNCTION:
                assert any(
                        (isinstance(decorator.value, ast.Name)
                         and decorator.value.id == ast_node.name
                         and (decorator.attr == 'setter'
                              or decorator.attr == 'deleter'))
                        if isinstance(decorator, ast.Attribute)
                        else
                        (isinstance(decorator, ast.Name)
                         and decorator.id == t.overload.__name__
                         and ((self.global_lookup_name(t.overload.__name__)
                               .module_path)
                              == catalog.module_path_from_module(t)))
                        for decorator in ast_node.decorator_list
                ), self
                namesake_node._ast_nodes.append(ast_node)
            else:
                node = Node(
                        self._resolve_stub_path(), self._resolve_module_path(),
                        self._resolve_object_path() + (ast_node.name,),
                        NodeKind.FUNCTION, [ast_node]
                )
                self._upsert_name(ast_node.name, node)

    def _resolve_ast_nodes(self) -> t.List[ast.AST]:
        return self._follow_redirects()._ast_nodes

    def _resolve_kind(self) -> NodeKind:
        return self._follow_redirects()._kind

    def _resolve_locals(self) -> t.Dict[str, 'Node']:
        return self._follow_redirects()._locals

    def _resolve_module_path(self) -> catalog.Path:
        return self._follow_redirects()._module_path

    def _resolve_object_path(self) -> catalog.Path:
        return self._follow_redirects()._object_path

    def _resolve_stub_path(self) -> sources.Path:
        return self._stub_path

    def _resolve_sub_nodes(self) -> t.List['Node']:
        return self._follow_redirects()._sub_nodes

    def _follow_redirects(self) -> 'Node':
        cursor = self
        while cursor._redirect is not None:
            cursor = cursor._redirect
            assert cursor is not self, self
        return cursor

    def __init__(self,
                 _stub_path: Path,
                 _module_path: catalog.Path,
                 _object_path: t.Optional[catalog.Path],
                 _kind: NodeKind,
                 _ast_nodes: t.List[ast.AST],
                 *_sub_nodes: 'Node') -> None:
        (
            self._ast_nodes, self._kind, self._module_path,
            self._object_path, self._stub_path, self._sub_nodes
        ) = (
            _ast_nodes, _kind, _module_path, _object_path, _stub_path,
            [*_sub_nodes]
        )
        self._locals: t.Dict[str, Node] = {}
        self._redirect = None

    __repr__ = generate_repr(__init__)


def import_module_node(module_path: catalog.Path) -> Node:
    node = _import_module_node(module_path)
    node.resolve()
    assert node.kind is NodeKind.MODULE
    return node


_graph: t.Dict[catalog.Path, Node] = {}


def _is_module_path(path: catalog.Path) -> bool:
    if path in _graph or catalog.path_to_string(path) in sys.modules:
        return True
    try:
        sources.from_module_path(path)
    except sources.NotFound:
        return False
    else:
        return True


def _import_module_node(path: catalog.Path) -> Node:
    assert len(path) > 0, path
    sub_path = ()
    for part in path:
        sub_path = sub_path + (part,)
        try:
            result = _graph[sub_path]
        except KeyError:
            result = _graph[sub_path] = Node(
                    sources.from_module_path(sub_path), sub_path, (),
                    NodeKind.MODULE_IMPORT, []
            )
    return result


@singledispatch
def _resolve_base_class_path(ast_node: ast.AST) -> catalog.Path:
    raise TypeError(type(ast_node))


@_resolve_base_class_path.register(ast.Subscript)
def _(ast_node: ast.Subscript) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return _resolve_base_class_path(ast_node.value)


@_resolve_base_class_path.register(ast.Name)
def _(ast_node: ast.Name) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return (ast_node.id,)


@_resolve_base_class_path.register(ast.Attribute)
def _(ast_node: ast.Attribute) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return _resolve_base_class_path(ast_node.value) + (ast_node.attr,)


@singledispatch
def _resolve_assignment_target(ast_node: ast.AST) -> catalog.Path:
    raise TypeError(type(ast_node))


@_resolve_assignment_target.register(ast.Name)
def _(ast_node: ast.Name) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast.Store), ast_node
    return (ast_node.id,)


@_resolve_assignment_target.register(ast.Attribute)
def _(ast_node: ast.Attribute) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast.Store), ast_node
    return _resolve_assignment_target(ast_node.value) + (ast_node.attr,)


def _to_alias_string(node: ast.alias) -> str:
    return node.asname or node.name


_builtins_node = _import_module_node(catalog.BUILTINS_MODULE_PATH)
Node._builtins = _builtins_node
Node._constants = MappingProxyType({
    name: Node(_builtins_node.stub_path, catalog.BUILTINS_MODULE_PATH,
               (name,), NodeKind.CONSTANT, [])
    for name in map(repr, [None, True, False])
})
_builtins_node.resolve()
_builtins_names: t.Container[str] = vars(builtins).keys()
