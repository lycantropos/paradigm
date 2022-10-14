import builtins
import enum
import importlib
import typing
from collections import deque
from functools import (partial,
                       singledispatch,
                       singledispatchmethod)
from itertools import chain
from pathlib import Path
from reprlib import recursive_repr
from types import MappingProxyType
from typing import (Any,
                    Container,
                    Dict,
                    Iterable,
                    List,
                    Optional,
                    Tuple,
                    Type,
                    Union)

from reprit.base import generate_repr
from typed_ast import ast3

from paradigm import (catalog,
                      namespaces,
                      sources)
from paradigm.hints import (Namespace,
                            Predicate)
from . import construction
from .execution import execute


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


NODE_KINDS_AST_TYPES: Dict[NodeKind, Union[Type[ast3.AST],
                                           Tuple[Type[ast3.AST], ...]]] = {
    NodeKind.ANNOTATED_ASSIGNMENT: ast3.AnnAssign,
    NodeKind.ASSIGNMENT: ast3.Assign,
    NodeKind.CLASS: ast3.ClassDef,
    NodeKind.CONSTANT: ast3.NameConstant,
    NodeKind.FUNCTION: (ast3.AsyncFunctionDef, ast3.FunctionDef),
    NodeKind.IMPORT_FROM: ast3.ImportFrom,
    NodeKind.MODULE: ast3.Module,
    NodeKind.MODULE_IMPORT: (ast3.Import, ast3.ImportFrom),
    NodeKind.SUBSCRIPT: ast3.Subscript,
    NodeKind.UNDEFINED: (),
    NodeKind.UNION: ast3.BinOp,
}
AST_TYPES_NODE_KINDS: Dict[Type[ast3.AST], NodeKind] = {
    ast3.AnnAssign: NodeKind.ANNOTATED_ASSIGNMENT,
    ast3.Assign: NodeKind.ASSIGNMENT,
    ast3.AsyncFunctionDef: NodeKind.FUNCTION,
    ast3.ClassDef: NodeKind.CLASS,
    ast3.FunctionDef: NodeKind.FUNCTION,
    ast3.Import: NodeKind.MODULE_IMPORT,
    ast3.ImportFrom: NodeKind.IMPORT_FROM,
    ast3.Module: NodeKind.MODULE,
    ast3.NameConstant: NodeKind.CONSTANT,
    ast3.BinOp: NodeKind.UNION,
    ast3.Subscript: NodeKind.SUBSCRIPT,
}
assert all(kind in NODE_KINDS_AST_TYPES for kind in NodeKind)


def _named_tuple_to_constructor_ast_node(ast_node, class_name):
    annotations_ast_nodes: List[ast3.AnnAssign] = [
        ast_child_node
        for ast_child_node in ast_node.body
        if isinstance(ast_child_node, ast3.AnnAssign)
    ]
    assert all(isinstance(ast_node.target, ast3.Name)
               for ast_node in annotations_ast_nodes), ast_node
    signature = ast3.arguments(
            [ast3.arg(ast_node.target.id, ast_node.annotation)
             for ast_node in annotations_ast_nodes],
            None, [], [], None,
            [ast_node.value
             for ast_node in annotations_ast_nodes
             if ast_node.value is not None]
    )
    constructor_ast_node = ast3.fix_missing_locations(
            ast3.FunctionDef('__new__', signature,
                             [ast3.Expr(ast3.Ellipsis())], [],
                             ast3.Name(class_name, ast3.Load()))
    )
    return constructor_ast_node


class Node:
    @property
    def ast_nodes(self) -> List[ast3.AST]:
        assert len({AST_TYPES_NODE_KINDS[type(ast_node)]
                    for ast_node in self._ast_nodes}) <= 1, self
        return self._ast_nodes

    @property
    def kind(self) -> NodeKind:
        return self._kind

    @property
    def module_path(self) -> catalog.Path:
        return self._module_path

    @property
    def object_path(self) -> catalog.Path:
        return self._object_path

    @property
    def source_path(self) -> Path:
        return self._source_path

    def get_attribute(self, name: str) -> 'Node':
        try:
            return self._get_name(name)
        except NameLookupError:
            for sub_node in self._sub_nodes:
                try:
                    return sub_node.get_attribute(name)
                except NameLookupError:
                    pass
            raise NameLookupError(name)

    def lookup_name(self, name: str) -> 'Node':
        try:
            return self._get_name(name)
        except NameLookupError:
            if self._kind is NodeKind.CLASS:
                parent = _graph[self._module_path]
                assert parent._kind is NodeKind.MODULE, parent
                return parent.lookup_name(name)
            else:
                if self._kind is NodeKind.MODULE:
                    for sub_node in self._sub_nodes:
                        try:
                            return sub_node.lookup_name(name)
                        except NameLookupError:
                            pass
                return (self._builtins.lookup_name(name)
                        if self is not self._builtins
                        else self._get_constant(name))

    def locate_name(self, name: str) -> Tuple[int, 'Node']:
        try:
            return 0, self._get_name(name)
        except NameLookupError:
            for depth, sub_node in enumerate(self._sub_nodes,
                                             start=1):
                try:
                    sub_depth, node = sub_node.locate_name(name)
                except NameLookupError:
                    pass
                else:
                    return depth, node
            raise NameLookupError(name)

    def resolve(self) -> None:
        module_node = _graph[self._module_path]
        if module_node._kind is NodeKind.MODULE_IMPORT:
            module_node._resolve_module_import()
        if self._kind is NodeKind.IMPORT_FROM:
            assert len(self._object_path.parts) == 1, self
            final_name, = self._object_path.parts
            for submodule_node in reversed(module_node._sub_nodes):
                try:
                    node = submodule_node.get_attribute(final_name)
                except NameLookupError:
                    pass
                else:
                    node.resolve()
                    self._merge_with(node)
                    break
        assert self._kind not in (NodeKind.IMPORT_FROM, NodeKind.MODULE_IMPORT,
                                  NodeKind.UNDEFINED), self

    def _contains(self, name: str) -> bool:
        return name in self._children

    def _get_constant(self, name: str) -> 'Node':
        try:
            return self._constants[name]
        except KeyError as error:
            raise NameLookupError(name) from error

    def _get_name(self, name: str) -> 'Node':
        try:
            return self._children[name]
        except KeyError as error:
            raise NameLookupError(name) from error

    def _get_name_inserting(self, name: str, value: 'Node') -> 'Node':
        try:
            return self._get_name(name)
        except NameLookupError:
            self._set_name(name, value)
            return value

    def _get_name_inserting_default(self, name: str) -> 'Node':
        try:
            return self._get_name(name)
        except NameLookupError:
            result = Node(
                    self._source_path, self._module_path,
                    self._object_path.join(catalog.Path(name)),
                    NodeKind.UNDEFINED, []
            )
            self._set_name(name, result)
            return result

    def _get_path_inserting_default(self, path: catalog.Path) -> 'Node':
        result = self
        for part in path.parts:
            result = result._get_name_inserting_default(part)
        return result

    def _lookup_name_inserting_default(self, name: str) -> 'Node':
        try:
            return self.lookup_name(name)
        except NameLookupError:
            result = Node(
                    self._source_path, self._module_path,
                    self._object_path.join(catalog.Path(name)),
                    NodeKind.UNDEFINED, []
            )
            self._set_name(name, result)
            return result

    def _lookup_path_inserting_default(self, path: catalog.Path) -> 'Node':
        result = self._lookup_name_inserting_default(path.parts[0])
        for part in path.parts[1:]:
            result = result._get_name_inserting_default(part)
        return result

    def _resolve_module_import(self) -> None:
        ast_node = flat_module_ast_node_from_path(self._source_path,
                                                  self._module_path)
        self._set_ast_node(ast_node)
        for child_ast_node in ast_node.body:
            self._visit_names(child_ast_node)
        assert self.kind is NodeKind.MODULE, self

    _builtins: 'Node'
    _constants: Dict[str, 'Node']

    def _append(self, node: 'Node') -> None:
        assert node is not self, self
        assert self._object_path is not None, self
        assert (self._kind is NodeKind.CLASS
                or self._kind is NodeKind.MODULE), self
        self._sub_nodes.append(node)

    def _append_ast_node(self, ast_node: ast3.AST) -> None:
        ast_node_kind = AST_TYPES_NODE_KINDS[type(ast_node)]
        assert not (ast_node_kind is NodeKind.IMPORT_FROM
                    or ast_node_kind is NodeKind.MODULE_IMPORT), self
        if (self._kind is NodeKind.IMPORT_FROM
                or self._kind is NodeKind.MODULE_IMPORT
                or self._kind is NodeKind.UNDEFINED):
            self._kind = ast_node_kind
        else:
            assert self._kind is ast_node_kind, self
        self._ast_nodes.append(ast_node)

    def _set_ast_node(self, ast_node: ast3.AST) -> None:
        assert (self._kind is NodeKind.IMPORT_FROM
                or self._kind is NodeKind.MODULE_IMPORT
                or self._kind is NodeKind.UNDEFINED), self
        node_kind = AST_TYPES_NODE_KINDS[type(ast_node)]
        assert (node_kind is not NodeKind.IMPORT_FROM
                and node_kind is not NodeKind.MODULE_IMPORT
                and node_kind is not NodeKind.UNDEFINED), self
        self._kind = node_kind
        if node_kind is NodeKind.CLASS:
            assert not self._ast_nodes, self
        self._ast_nodes = [ast_node]

    def _set_name(self, name: str, value: 'Node') -> None:
        assert catalog.Path.SEPARATOR not in name, name
        if self._contains(name):
            raise NameAlreadyExists(name)
        self._children[name] = value

    def _set_path(self, path: catalog.Path, value: 'Node') -> None:
        node = (self._get_path_inserting_default(path.parent)
                if len(path.parts) > 1
                else self)
        node._set_name(path.parts[-1], value)

    def _upsert_path(self, path: catalog.Path, value: 'Node') -> None:
        node = (self._lookup_path_inserting_default(path.parent)
                if len(path.parts) > 1
                else self)
        node._upsert_name(path.parts[-1], value)

    def _upsert_name(self, name: str, value: 'Node') -> None:
        assert catalog.Path.SEPARATOR not in name, name
        if self._contains(name):
            candidate = self._children[name]
            if candidate is not value:
                candidate._merge_with(value)
        else:
            self._set_name(name, value)

    def _merge_with(self, other: 'Node') -> None:
        assert self._kind in (NodeKind.IMPORT_FROM, NodeKind.UNDEFINED), self
        assert not self._ast_nodes, self
        assert not self.__sub_nodes, self
        (
            self._ast_nodes, self._children, self._kind, self._module_path,
            self._object_path, self._source_path, self.__sub_nodes
        ) = (
            other._ast_nodes, other._children, other._kind,
            other._module_path, other._object_path, other._source_path,
            other.__sub_nodes
        )

    @singledispatchmethod
    def _resolve_assigning_value(self, ast_node: ast3.AST) -> Optional['Node']:
        raise TypeError(type(ast_node))

    @_resolve_assigning_value.register(ast3.Name)
    def _(self, ast_node: ast3.Name) -> Optional['Node']:
        assert isinstance(ast_node.ctx, ast3.Load), ast_node
        return self._lookup_name_inserting_default(ast_node.id)

    @_resolve_assigning_value.register(ast3.Attribute)
    def _(self, ast_node: ast3.Attribute) -> Optional['Node']:
        assert isinstance(ast_node.ctx, ast3.Load), ast_node
        value_node = self._resolve_assigning_value(ast_node.value)
        return (value_node
                if value_node is None
                else value_node._get_name_inserting_default(ast_node.attr))

    @_resolve_assigning_value.register(ast3.Dict)
    @_resolve_assigning_value.register(ast3.Tuple)
    @_resolve_assigning_value.register(ast3.List)
    @_resolve_assigning_value.register(ast3.Set)
    def _(self, ast_node: ast3.expr) -> Optional['Node']:
        assert isinstance(ast_node.ctx, ast3.Load), ast_node
        return None

    @_resolve_assigning_value.register(ast3.Subscript)
    def _(self, ast_node: ast3.Subscript) -> Optional['Node']:
        assert isinstance(ast_node.ctx, ast3.Load), ast_node
        return Node(self._source_path, self._module_path, None,
                    NodeKind.SUBSCRIPT, [ast_node])

    @_resolve_assigning_value.register(ast3.NameConstant)
    def _(self, ast_node: ast3.NameConstant) -> 'Node':
        assert ast_node.value is None, ast_node.value
        return self.lookup_name(repr(ast_node.value))

    @_resolve_assigning_value.register(ast3.BinOp)
    def _(self, ast_node: ast3.BinOp) -> Optional['Node']:
        if isinstance(ast_node.op, ast3.BitOr):
            left_node = self._resolve_assigning_value(ast_node.left)
            right_node = self._resolve_assigning_value(ast_node.right)
            return (None
                    if left_node is None or right_node is None
                    else Node(self._source_path, self._module_path, None,
                              NodeKind.UNION, [ast_node], left_node,
                              right_node))
        else:
            return None

    @_resolve_assigning_value.register(ast3.Call)
    @_resolve_assigning_value.register(ast3.Ellipsis)
    def _(self, ast_node: ast3.Call) -> Optional['Node']:
        return None

    @singledispatchmethod
    def _resolve_annotation(self, ast_node: ast3.AST) -> 'Node':
        raise TypeError(type(ast_node))

    @_resolve_annotation.register(ast3.Name)
    def _(self, ast_node: ast3.Name) -> 'Node':
        assert isinstance(ast_node.ctx, ast3.Load), ast_node
        return self._lookup_name_inserting_default(ast_node.id)

    @_resolve_annotation.register(ast3.Subscript)
    def _(self, ast_node: ast3.Subscript) -> 'Node':
        assert isinstance(ast_node.ctx, ast3.Load), ast_node
        return Node(self._source_path, self._module_path, None,
                    NodeKind.SUBSCRIPT, [ast_node],
                    self._resolve_annotation(ast_node.value))

    @_resolve_annotation.register(ast3.NameConstant)
    def _(self, ast_node: ast3.NameConstant) -> 'Node':
        assert ast_node.value is None, ast_node.value
        return self.lookup_name(repr(ast_node.value))

    @_resolve_annotation.register(ast3.Attribute)
    def _(self, ast_node: ast3.Attribute) -> 'Node':
        assert isinstance(ast_node.ctx, ast3.Load), ast_node
        value_node = self._resolve_annotation(ast_node.value)
        return value_node._get_name_inserting_default(ast_node.attr)

    @_resolve_annotation.register(ast3.BinOp)
    def _(self, ast_node: ast3.BinOp) -> 'Node':
        assert isinstance(ast_node.op, ast3.BitOr), ast_node
        left_node = self._resolve_annotation(ast_node.left)
        right_node = self._resolve_annotation(ast_node.right)
        return Node(self._source_path, self._module_path, None, NodeKind.UNION,
                    [ast_node], left_node, right_node)

    @singledispatchmethod
    def _visit_names(self, ast_node: ast3.AST) -> None:
        raise TypeError(type(ast_node))

    @_visit_names.register(ast3.Expr)
    def _(self, ast_node: ast3.Expr) -> None:
        assert isinstance(ast_node.value, ast3.Ellipsis), ast_node
        return None

    @_visit_names.register(ast3.AugAssign)
    def _(self, ast_node: ast3.AugAssign) -> None:
        assert (isinstance(ast_node.target, ast3.Name)
                and ast_node.target.id == '__all__')
        assert isinstance(ast_node.op, ast3.Add), self
        return None

    @_visit_names.register(ast3.AnnAssign)
    def _(self, ast_node: ast3.AnnAssign) -> None:
        value_ast_node = ast_node.value
        target_path = _resolve_assignment_target(ast_node.target)
        if value_ast_node is None:
            value_node = self._resolve_annotation(ast_node.annotation)
            self._upsert_path(target_path, value_node)
        else:
            value_node = self._resolve_assigning_value(value_ast_node)
            if value_node is None:
                target_node = self._lookup_path_inserting_default(target_path)
                target_node._set_ast_node(ast_node)
            else:
                self._upsert_path(target_path, value_node)

    @_visit_names.register(ast3.Assign)
    def _(self, ast_node: ast3.Assign) -> None:
        value_node = self._resolve_assigning_value(ast_node.value)
        if value_node is None:
            targets = ast_node.targets
            assert targets, ast_node
            value_node = self._get_path_inserting_default(
                    _resolve_assignment_target(targets[0])
            )
            value_node._set_ast_node(ast_node)
            for target in targets[1:]:
                self._upsert_path(_resolve_assignment_target(target),
                                  value_node)
        else:
            for target in ast_node.targets:
                self._upsert_path(_resolve_assignment_target(target),
                                  value_node)

    @_visit_names.register(ast3.Import)
    def _(self, ast_node: ast3.Import) -> None:
        for alias in ast_node.names:
            module_import_node = _import_module_node(
                    catalog.from_string(alias.name)
            )
            self._upsert_path(to_alias_path(alias), module_import_node)

    @_visit_names.register(ast3.ImportFrom)
    def _(self, ast_node: ast3.ImportFrom) -> None:
        assert self._kind is NodeKind.MODULE, self
        assert not self._object_path.parts, self
        module_path = to_parent_module_path(
                ast_node,
                parent_module_path=self._module_path
        )
        if module_path == self._module_path:
            for alias in ast_node.names:
                submodule_name = alias.name
                assert submodule_name != catalog.WILDCARD_IMPORT_NAME
                submodule_path = self._module_path.join(
                        catalog.Path(submodule_name)
                )
                submodule_node = self._get_name_inserting(
                        submodule_name,
                        Node(sources.from_module_path(submodule_path),
                             submodule_path, catalog.Path(),
                             NodeKind.MODULE_IMPORT, [])
                )
                assert (
                        submodule_node._kind in (NodeKind.MODULE_IMPORT,
                                                 NodeKind.MODULE)
                ), self
                imported_name = to_alias_string(alias)
                if imported_name != submodule_name:
                    assert not self._contains(imported_name), self
                    self._set_name(imported_name, submodule_node)
                else:
                    assert self._contains(imported_name), self
        else:
            module_node = _import_module_node(module_path)
            for alias in ast_node.names:
                actual_name = alias.name
                if actual_name == catalog.WILDCARD_IMPORT_NAME:
                    module_node.resolve()
                    self._append(module_node)
                else:
                    imported_node = module_node._get_name_inserting(
                            actual_name,
                            Node(module_node._source_path,
                                 module_path, catalog.Path(actual_name),
                                 NodeKind.IMPORT_FROM, [])
                    )
                    self._upsert_name(to_alias_string(alias), imported_node)

    @_visit_names.register(ast3.ClassDef)
    def _(
            self,
            ast_node: ast3.ClassDef,
            *,
            _named_tuple_path: catalog.Path
            = catalog.from_type(typing.NamedTuple),
            _typing_path: catalog.Path = catalog.from_module(typing)
    ) -> None:
        class_name = ast_node.name
        class_node = self._get_name_inserting_default(class_name)
        class_node._set_ast_node(ast_node)
        ast_children_nodes: List[ast3.AST] = [*ast_node.body]
        for ast_base_node in ast_node.bases:
            base_path = _resolve_base_class_path(ast_base_node)
            base_node = self._lookup_path_inserting_default(base_path)
            if (base_node.module_path == _typing_path
                    and base_node.object_path == _named_tuple_path):
                ast_children_nodes.append(_named_tuple_to_constructor_ast_node(
                        ast_node, class_name
                ))
            class_node._append(base_node)
        if self is not self._builtins:
            assert class_name != object.__name__, self
            class_node._append(self._builtins.get_attribute(object.__name__))
        elif class_name != object.__name__:
            assert self._module_path == catalog.BUILTINS_MODULE_PATH, self
            class_node._append(self.get_attribute(object.__name__))
        for ast_child_node in ast_children_nodes:
            class_node._visit_names(ast_child_node)

    @_visit_names.register(ast3.AsyncFunctionDef)
    @_visit_names.register(ast3.FunctionDef)
    def _(self,
          ast_node: Union[ast3.AsyncFunctionDef, ast3.FunctionDef]) -> None:
        function_node = self._get_name_inserting(
                ast_node.name,
                Node(self._source_path, self._module_path,
                     catalog.Path(ast_node.name), NodeKind.FUNCTION, [])
        )
        function_node._append_ast_node(ast_node)

    @property
    def _sub_nodes(self) -> List['Node']:
        assert (len(self.__sub_nodes) == 0
                or self._kind is not NodeKind.MODULE_IMPORT), self
        assert self not in self.__sub_nodes, self
        return self.__sub_nodes

    @property
    def _kind(self) -> NodeKind:
        return self.__kind

    @_kind.setter
    def _kind(self, value: NodeKind) -> None:
        assert self.__kind in (NodeKind.IMPORT_FROM, NodeKind.MODULE_IMPORT,
                               NodeKind.UNDEFINED), self
        assert value is not NodeKind.UNDEFINED, self
        self.__kind = value

    def __init__(self,
                 _source_path: Path,
                 _module_path: catalog.Path,
                 _object_path: Optional[catalog.Path],
                 _kind: NodeKind,
                 _ast_nodes: List[ast3.AST],
                 *_sub_nodes: 'Node',
                 **_children: 'Node'):
        (
            self._ast_nodes, self._children, self.__kind, self._module_path,
            self._object_path, self._source_path, self.__sub_nodes
        ) = (
            _ast_nodes, _children, _kind, _module_path, _object_path,
            _source_path, [*_sub_nodes]
        )

    __repr__ = recursive_repr()(generate_repr(__init__))


_graph: Dict[catalog.Path, Node] = {}


def _import_module_node(path: catalog.Path) -> Node:
    return _graph.setdefault(path,
                             Node(sources.from_module_path(path), path,
                                  catalog.Path(), NodeKind.MODULE_IMPORT, []))


@singledispatch
def _resolve_base_class_path(ast_node: ast3.AST) -> catalog.Path:
    raise TypeError(type(ast_node))


@_resolve_base_class_path.register(ast3.Subscript)
def _(ast_node: ast3.Subscript) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast3.Load), ast_node
    return _resolve_base_class_path(ast_node.value)


@_resolve_base_class_path.register(ast3.Name)
def _(ast_node: ast3.Name) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast3.Load), ast_node
    return catalog.Path(ast_node.id)


@_resolve_base_class_path.register(ast3.Attribute)
def _(ast_node: ast3.Attribute) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast3.Load), ast_node
    return _resolve_base_class_path(ast_node.value).join(
            catalog.Path(ast_node.attr)
    )


@singledispatch
def _resolve_assignment_target(ast_node: ast3.AST) -> catalog.Path:
    raise TypeError(type(ast_node))


@_resolve_assignment_target.register(ast3.Name)
def _(ast_node: ast3.Name) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast3.Store), ast_node
    return catalog.Path(ast_node.id)


@_resolve_assignment_target.register(ast3.Attribute)
def _(ast_node: ast3.Attribute) -> catalog.Path:
    assert isinstance(ast_node.ctx, ast3.Store), ast_node
    return _resolve_assignment_target(ast_node.value).join(
            catalog.Path(ast_node.attr)
    )


def to_parent_module_path(object_: ast3.ImportFrom,
                          *,
                          parent_module_path: catalog.Path) -> catalog.Path:
    level = object_.level
    import_is_relative = level > 0
    if not import_is_relative:
        return catalog.from_string(object_.module)
    depth = (len(parent_module_path.parts)
             + catalog.is_package(parent_module_path)
             - level) or None
    module_path_parts = filter(None,
                               chain(parent_module_path.parts[:depth],
                                     (object_.module,)))
    return catalog.Path(*module_path_parts)


class NamespaceUpdater(ast3.NodeVisitor):
    def __init__(self,
                 *,
                 namespace: Namespace,
                 module_path: catalog.Path,
                 parent_path: catalog.Path,
                 is_nested: bool) -> None:
        self.namespace = namespace
        self.module_path = module_path
        self.parent_path = parent_path
        self.is_nested = is_nested

    def visit_Import(self, node: ast3.Import) -> None:
        for name_alias in node.names:
            actual_path = to_actual_path(name_alias)
            parent_module_name = actual_path.parts[0]
            module = importlib.import_module(parent_module_name)
            self.namespace[parent_module_name] = module

    def visit_ImportFrom(self, node: ast3.ImportFrom) -> None:
        parent_module_path = to_parent_module_path(
                node,
                parent_module_path=self.module_path
        )
        for name_alias in node.names:
            alias_path = self.resolve_path(to_alias_path(name_alias))
            actual_path = to_actual_path(name_alias)
            if actual_path == catalog.WILDCARD_IMPORT_PATH:
                self.namespace.update(namespaces
                                      .from_module_path(parent_module_path))
                continue
            namespace = namespaces.from_module_path(parent_module_path)
            try:
                object_ = namespaces.search(namespace, actual_path)
            except KeyError:
                module_path = parent_module_path.join(actual_path)
                object_ = importlib.import_module(str(module_path))
            self.namespace[str(alias_path)] = object_

    def visit_ClassDef(self, node: ast3.ClassDef) -> None:
        path = self.resolve_path(catalog.from_string(node.name))
        (NamespaceUpdater(namespace=self.namespace,
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


def rectify_ifs(module_root: ast3.Module,
                *,
                namespace: Namespace,
                source_path: Path) -> None:
    namespace = namespace
    source_path = source_path
    ast_nodes = [module_root]
    while ast_nodes:
        node = ast_nodes.pop()
        new_body = []
        for child_ast_node in _flatten_ifs(node.body,
                                           namespace=namespace,
                                           source_path=source_path):
            if isinstance(child_ast_node, ast3.ClassDef):
                ast_nodes.append(child_ast_node)
            new_body.append(child_ast_node)
        node.body = new_body


def _flatten_ifs(candidates: Iterable[ast3.AST],
                 *,
                 namespace: Namespace,
                 source_path: Path) -> Iterable[ast3.AST]:
    for candidate in candidates:
        if isinstance(candidate, ast3.If):
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


def expression_to_assignment(node: ast3.expr,
                             *,
                             name: str) -> ast3.Assign:
    name_node = ast3.copy_location(ast3.Name(name, ast3.Store()), node)
    result = ast3.Assign([name_node], node, None)
    return ast3.copy_location(result, node)


builtins_namespace = namespaces.from_module(builtins)


def import_module_node(module_path: catalog.Path) -> Node:
    node = _import_module_node(module_path)
    node.resolve()
    assert node.kind is NodeKind.MODULE
    return node


def flat_module_ast_node_from_path(source_path: Path,
                                   module_path: catalog.Path) -> ast3.Module:
    assert source_path == sources.from_module_path(module_path), module_path
    result = construction.from_source_path(source_path)
    flatten_ifs(result,
                module_path=module_path,
                source_path=source_path)
    return result


def flatten_ifs(module_root: ast3.Module,
                *,
                module_path: catalog.Path,
                source_path: Path) -> None:
    rectify_ifs(module_root,
                namespace=construct_namespace(module_root, module_path),
                source_path=source_path)


def construct_namespace(module_ast_node: ast3.Module,
                        module_path: catalog.Path) -> Namespace:
    result = builtins_namespace.copy()
    update_namespace = NamespaceUpdater(namespace=result,
                                        module_path=module_path,
                                        parent_path=catalog.Path(),
                                        is_nested=False).visit
    for node in left_search_within_children(module_ast_node,
                                            ast3.If.__instancecheck__):
        dependencies_names = {
            child.id
            for child in left_search_within_children(
                    node.test, ast3.Name.__instancecheck__
            )
            if isinstance(child.ctx, ast3.Load)
        }
        while dependencies_names:
            dependency_name = dependencies_names.pop()
            dependency_node = next(
                    right_search_within_children(module_ast_node,
                                                 partial(node_has_name,
                                                         name=dependency_name))
            )
            update_namespace(dependency_node)
    return result


def to_actual_path(node: ast3.alias) -> catalog.Path:
    return catalog.from_string(node.name)


def to_alias_path(node: ast3.alias) -> catalog.Path:
    return catalog.from_string(to_alias_string(node))


def to_alias_string(node: ast3.alias) -> str:
    return node.asname or node.name


def node_has_name(node: ast3.AST, name: str) -> bool:
    return name in node_to_names(node)


@singledispatch
def node_to_names(node: ast3.AST) -> List[str]:
    return []


@node_to_names.register(ast3.ClassDef)
@node_to_names.register(ast3.FunctionDef)
def class_def_or_function_def_to_name(node: ast3.AST) -> List[str]:
    return [node.name]


@node_to_names.register(ast3.Import)
@node_to_names.register(ast3.ImportFrom)
def import_or_import_from_to_name(node: ast3.Import) -> List[str]:
    result = []
    for name_alias in node.names:
        result.append(to_alias_string(name_alias))
    return result


def left_search_within_children(node: ast3.AST,
                                condition: Predicate[ast3.AST]) -> Iterable:
    children = deque(ast3.iter_child_nodes(node))
    while children:
        child = children.popleft()
        if condition(child):
            yield child
        else:
            children.extend(ast3.iter_child_nodes(child))


def right_search_within_children(node, condition):
    children = deque(ast3.iter_child_nodes(node))
    while children:
        child = children.pop()
        if condition(child):
            yield child
        else:
            children.extendleft(ast3.iter_child_nodes(child))


_builtins_node = _import_module_node(catalog.BUILTINS_MODULE_PATH)
Node._builtins = _builtins_node
Node._constants = MappingProxyType({
    name: Node(_builtins_node.source_path, catalog.BUILTINS_MODULE_PATH,
               catalog.Path(name), NodeKind.CONSTANT, [])
    for name in ['None', 'True', 'False']
})
_builtins_node.resolve()
_builtins_names: Container[str] = vars(builtins).keys()
