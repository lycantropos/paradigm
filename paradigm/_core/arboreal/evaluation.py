from __future__ import annotations

import ast
import builtins
import operator
import types
import weakref
from collections import ChainMap
from collections.abc import MutableMapping
from functools import singledispatch
from importlib import import_module
from typing import Any, ForwardRef, TypeGuard, Union

from typing_extensions import Self, TypeVar

from paradigm._core import catalog, namespacing, scoping, sources, stubs
from paradigm._core.utils import MISSING

from . import conversion
from .execution import execute_statement
from .kind import StatementNodeKind
from .utils import is_dependency_name, recursively_iterate_children

AstExpression = ast.expr


def evaluate_expression_node(
    ast_node: AstExpression,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    return _evaluate_expression_node(
        ast_node, module_path, parent_path, parent_namespace
    )


@singledispatch
def _evaluate_expression_node(
    ast_node: AstExpression,
    _module_path: catalog.Path,
    _parent_path: catalog.Path,
    _parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    raise TypeError(type(ast_node))


@singledispatch
def _evaluate_statement_node(
    ast_node: ast.stmt,
    _module_path: catalog.Path,
    _parent_path: catalog.Path,
    _parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    raise TypeError(type(ast_node))


@singledispatch
def _evaluate_operator_node(ast_node: ast.operator | ast.unaryop) -> Any:
    raise TypeError(type(ast_node))


@_evaluate_operator_node.register(ast.USub)
def _(_ast_node: ast.USub, /) -> Any:
    return operator.neg


@_evaluate_operator_node.register(ast.UAdd)
def _(_ast_node: ast.UAdd, /) -> Any:
    return operator.pos


@_evaluate_expression_node.register(ast.UnaryOp)
def _(
    ast_node: ast.UnaryOp,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    return _evaluate_operator_node(ast_node.op)(
        _evaluate_expression_node(
            ast_node.operand, module_path, parent_path, parent_namespace
        )
    )


_T = TypeVar('_T')


def _all_not_none(value: list[_T | None], /) -> TypeGuard[list[_T]]:
    return all(element is not None for element in value)


@_evaluate_expression_node.register(ast.Dict)
def _(
    ast_node: ast.Dict,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert _all_not_none(ast_node.keys), ast_node.keys
    return {
        _evaluate_expression_node(
            key, module_path, parent_path, parent_namespace
        ): _evaluate_expression_node(
            value, module_path, parent_path, parent_namespace
        )
        for key, value in zip(ast_node.keys, ast_node.values, strict=False)
    }


@_evaluate_operator_node.register(ast.BitAnd)
def _(_ast_node: ast.BitAnd, /) -> Any:
    return operator.and_


@_evaluate_operator_node.register(ast.BitOr)
def _(_ast_node: ast.BitOr, /) -> Any:
    return operator.or_


@_evaluate_operator_node.register(ast.BitXor)
def _(_ast_node: ast.BitXor, /) -> Any:
    return operator.xor


@_evaluate_expression_node.register(ast.Call)
def _(
    ast_node: ast.Call,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    args = [
        _evaluate_expression_node(
            arg, module_path, parent_path, parent_namespace
        )
        for arg in ast_node.args
    ]
    kwargs = {
        parameter_name: _evaluate_expression_node(
            keyword.value, module_path, parent_path, parent_namespace
        )
        for keyword in ast_node.keywords
        if (parameter_name := keyword.arg) is not None
    }
    callable_ = _evaluate_expression_node(
        ast_node.func, module_path, parent_path, parent_namespace
    )
    return callable_(*args, **kwargs)


class _LazyEvaluator(ast.NodeTransformer):
    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        if node.returns is not None:
            node.returns = ast.Constant(conversion.to_str(node.returns))
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if node.returns is not None:
            node.returns = ast.Constant(conversion.to_str(node.returns))
        self.generic_visit(node)
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        return ast.arg(
            node.arg,
            (
                None
                if node.annotation is None
                else ast.Constant(conversion.to_str(node.annotation))
            ),
            getattr(node, 'type_comment', None),
        )


_AstNode = TypeVar('_AstNode', bound=ast.stmt)


def _to_lazy_statement(node: _AstNode) -> _AstNode:
    result = _LazyEvaluator().visit(node)
    assert isinstance(result, type(node)), (result, node)
    return result


@_evaluate_statement_node.register(ast.AsyncFunctionDef)
@_evaluate_statement_node.register(ast.FunctionDef)
def _(
    ast_node: ast.AsyncFunctionDef | ast.FunctionDef,
    module_path: catalog.Path,
    _parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    namespace = dict(parent_namespace)
    try:
        source_path = sources.from_module_path(module_path)
    except sources.NotFound:
        source_path = sources.Path(*module_path)
    execute_statement(
        ast.fix_missing_locations(_to_lazy_statement(ast_node)),
        source_path=source_path,
        namespace=namespace,
    )
    name = ast_node.name
    result = parent_namespace[name] = namespace.pop(name)
    return result


@_evaluate_expression_node.register(ast.Constant)
def _(
    ast_node: ast.Constant,
    _module_path: catalog.Path,
    _parent_path: catalog.Path,
    _parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    return ast_node.value


@_evaluate_expression_node.register(ast.Tuple)
def _(
    ast_node: ast.Tuple,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return tuple(
        _evaluate_expression_node(
            element, module_path, parent_path, parent_namespace
        )
        for element in ast_node.elts
    )


@_evaluate_expression_node.register(ast.List)
def _(
    ast_node: ast.List,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return [
        _evaluate_expression_node(
            element, module_path, parent_path, parent_namespace
        )
        for element in ast_node.elts
    ]


@_evaluate_statement_node.register(ast.AnnAssign)
@_evaluate_statement_node.register(ast.Assign)
def _(
    ast_node: ast.Assign,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    if (
        len(
            target_names := conversion.statement_node_to_defined_names(
                ast_node
            )
        )
        == 1
    ):
        # potential cyclic definition
        (target_name,) = target_names
        parent_namespace = ChainMap(
            {target_name: ForwardRef(target_name)}, parent_namespace
        )
    return _evaluate_expression_node(
        ast_node.value, module_path, parent_path, parent_namespace
    )


@_evaluate_expression_node.register(ast.BinOp)
def _(
    ast_node: ast.BinOp,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    left = _evaluate_expression_node(
        ast_node.left, module_path, parent_path, parent_namespace
    )
    right = _evaluate_expression_node(
        ast_node.right, module_path, parent_path, parent_namespace
    )
    try:
        return _evaluate_operator_node(ast_node.op)(left, right)
    except TypeError:
        assert isinstance(ast_node.op, ast.BitOr), ast_node
        return Union[left, right]  # noqa: UP007


@_evaluate_expression_node.register(ast.Name)
def _(
    ast_node: ast.Name,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    object_name = ast_node.id
    module_path, object_path = scoping.resolve_object_path(
        module_path,
        parent_path,
        (object_name,),
        stubs.definitions,
        stubs.references,
        stubs.submodules,
        stubs.superclasses,
    )
    return _evaluate_qualified_path(module_path, object_path, parent_namespace)


@_evaluate_expression_node.register(ast.Attribute)
def _(
    ast_node: ast.Attribute,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    value = _evaluate_expression_node(
        ast_node.value, module_path, parent_path, parent_namespace
    )
    try:
        return getattr(value, ast_node.attr)
    except AttributeError:
        module_path, object_path = scoping.resolve_object_path(
            module_path,
            parent_path,
            conversion.to_path(ast_node),
            stubs.definitions,
            stubs.references,
            stubs.submodules,
            stubs.superclasses,
        )
        return _evaluate_qualified_path(
            module_path, object_path, parent_namespace
        )


def _evaluate_qualified_path(
    module_path: catalog.Path,
    object_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
    *,
    builtins_module_path: catalog.Path = catalog.module_path_from_module(  # noqa: B008
        builtins
    ),
    modules_cache: MutableMapping[
        catalog.Path, types.ModuleType
    ] = weakref.WeakValueDictionary(),  # noqa: B008
    object_overrides: MutableMapping[catalog.QualifiedPath, Any] = {  # noqa: B006
        (('typing',), ('TypeVar',)): TypeVar
    },
    objects_cache: MutableMapping[
        catalog.QualifiedPath, Any
    ] = weakref.WeakValueDictionary(  # noqa: B008
        [((('_typeshed',), ('Self',)), Self)]
    ),
) -> Any:
    if len(object_path) > 0 and (
        (candidate := parent_namespace.get(object_path[-1], MISSING))
        is not MISSING
    ):
        return candidate
    try:
        return object_overrides[module_path, object_path]
    except KeyError:
        pass
    module_name = catalog.path_to_string(module_path)
    try:
        module = import_module(module_name)
    except ImportError:
        if len(object_path) == 0:
            try:
                return modules_cache[module_path]
            except KeyError:
                modules_cache[module_path] = module = types.ModuleType(
                    module_name
                )
                namespace = module.__dict__
                for name in stubs.definitions[module_path]:
                    namespace[name] = parent_namespace[name] = (
                        _evaluate_qualified_path(
                            module_path, (name,), parent_namespace
                        )
                    )
                return module
    else:
        try:
            return (
                namespacing.search(module, object_path)
                if object_path
                else module
            )
        except namespacing.ObjectNotFound:
            pass
    try:
        return objects_cache[module_path, object_path]
    except KeyError:
        pass
    assert len(object_path) > 0
    module_nodes = stubs.statements_nodes[module_path]
    node_kind = stubs.statements_nodes_kinds[module_path][object_path]
    try:
        nodes = module_nodes[object_path]
    except KeyError:
        assert node_kind is StatementNodeKind.CLASS, (module_path, object_path)
    else:
        if node_kind is not StatementNodeKind.CLASS:
            for node in nodes:
                parent_namespace[object_path[-1]] = _evaluate_statement_node(
                    node, module_path, object_path[:-1], parent_namespace
                )
            return parent_namespace[object_path[-1]]
    scope = stubs.definitions[module_path]
    for part in object_path:
        scope = scope[part]
    class_namespace: namespacing.Namespace = {'__module__': __name__}
    module_namespace: namespacing.Namespace = {'__name__': __name__}
    annotations_nodes = {}
    for name in scope:
        nodes = module_nodes[(*object_path, name)]
        definitions_nodes: list[ast.stmt] = []
        for node in nodes:
            if isinstance(node, ast.AnnAssign) and node.value is None:
                annotations_nodes[name] = node.annotation
            else:
                assert isinstance(node, ast.stmt), (module_path, object_path)
                definitions_nodes.append(node)
        for definition_node in definitions_nodes:
            for dependency_name in {
                child.id
                for child in recursively_iterate_children(
                    _to_lazy_statement(definition_node)
                )
                if is_dependency_name(child)
            }:
                dependency_module_path, dependency_object_path = (
                    scoping.resolve_object_path(
                        module_path,
                        object_path,
                        (dependency_name,),
                        stubs.definitions,
                        stubs.references,
                        stubs.submodules,
                        stubs.superclasses,
                    )
                )
                if dependency_module_path != builtins_module_path:
                    module_namespace[dependency_name] = (
                        _evaluate_qualified_path(
                            dependency_module_path,
                            dependency_object_path,
                            module_namespace,
                        )
                    )
            class_namespace[name] = _evaluate_statement_node(
                definition_node,
                module_path,
                object_path,
                ChainMap(class_namespace, module_namespace),
            )
    bases = tuple(
        _evaluate_qualified_path(
            superclass_module_path, superclass_object_path, module_namespace
        )
        for (
            superclass_module_path,
            superclass_object_path,
        ) in stubs.superclasses.get(module_path, {}).get(object_path, [])
    )
    if annotations_nodes:
        class_namespace['__annotations__'] = {}
    result = parent_namespace[object_path[-1]] = objects_cache[
        module_path, object_path
    ] = types.new_class(
        catalog.path_to_string(object_path),
        bases,
        exec_body=lambda namespace: namespace.update(class_namespace),
    )
    if annotations_nodes:
        result.__annotations__.update(
            {
                name: _evaluate_expression_node(
                    annotation_node, module_path, object_path, parent_namespace
                )
                for name, annotation_node in annotations_nodes.items()
            }
        )
    globals()[catalog.path_to_string(object_path)] = result
    return result


@_evaluate_expression_node.register(ast.Subscript)
def _(
    ast_node: ast.Subscript,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    value = _evaluate_expression_node(
        ast_node.value, module_path, parent_path, parent_namespace
    )
    item = _evaluate_expression_node(
        ast_node.slice, module_path, parent_path, parent_namespace
    )
    try:
        return value[item]
    except TypeError:
        return value
