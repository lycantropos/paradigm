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
from typing import Any, ForwardRef, TypeGuard, TypeVar

from typing_extensions import Self

from paradigm._core import catalog, namespacing, scoping, sources, stubs

from . import construction, conversion
from .execution import execute_statement
from .kind import NodeKind
from .utils import is_dependency_name, recursively_iterate_children

AstExpression = ast.expr


@singledispatch
def evaluate_expression_node(
    ast_node: AstExpression,
    _module_path: catalog.Path,
    _parent_path: catalog.Path,
    _parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    raise TypeError(type(ast_node))


@singledispatch
def evaluate_statement_node(
    ast_node: ast.stmt,
    _module_path: catalog.Path,
    _parent_path: catalog.Path,
    _parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    raise TypeError(type(ast_node))


@singledispatch
def evaluate_operator_node(ast_node: ast.operator | ast.unaryop) -> Any:
    raise TypeError(type(ast_node))


@evaluate_operator_node.register(ast.USub)
def _(_ast_node: ast.USub, /) -> Any:
    return operator.neg


@evaluate_operator_node.register(ast.UAdd)
def _(_ast_node: ast.UAdd, /) -> Any:
    return operator.pos


@evaluate_expression_node.register(ast.UnaryOp)
def _(
    ast_node: ast.UnaryOp,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    return evaluate_operator_node(ast_node.op)(
        evaluate_expression_node(
            ast_node.operand, module_path, parent_path, parent_namespace
        )
    )


_T = TypeVar('_T')


def _all_not_none(value: list[_T | None], /) -> TypeGuard[list[_T]]:
    return all(element is not None for element in value)


@evaluate_expression_node.register(ast.Dict)
def _(
    ast_node: ast.Dict,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert _all_not_none(ast_node.keys), ast_node.keys
    return {
        evaluate_expression_node(
            key, module_path, parent_path, parent_namespace
        ): evaluate_expression_node(
            value, module_path, parent_path, parent_namespace
        )
        for key, value in zip(ast_node.keys, ast_node.values, strict=False)
    }


@evaluate_operator_node.register(ast.BitAnd)
def _(_ast_node: ast.BitAnd, /) -> Any:
    return operator.and_


@evaluate_operator_node.register(ast.BitOr)
def _(_ast_node: ast.BitOr, /) -> Any:
    return operator.or_


@evaluate_operator_node.register(ast.BitXor)
def _(_ast_node: ast.BitXor, /) -> Any:
    return operator.xor


@evaluate_expression_node.register(ast.Call)
def _(
    ast_node: ast.Call,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
) -> Any:
    args = [
        evaluate_expression_node(
            arg, module_path, parent_path, parent_namespace
        )
        for arg in ast_node.args
    ]
    kwargs = {
        parameter_name: evaluate_expression_node(
            keyword.value, module_path, parent_path, parent_namespace
        )
        for keyword in ast_node.keywords
        if (parameter_name := keyword.arg) is not None
    }
    return evaluate_expression_node(
        ast_node.func, module_path, parent_path, parent_namespace
    )(*args, **kwargs)


class _LazyEvaluator(ast.NodeTransformer):
    def visit_AsyncFunctionDef(  # noqa: N802
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        if node.returns is not None:
            node.returns = ast.Constant(conversion.to_str(node.returns))
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:  # noqa: N802
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


@evaluate_statement_node.register(ast.AsyncFunctionDef)
@evaluate_statement_node.register(ast.FunctionDef)
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


@evaluate_expression_node.register(ast.Constant)
def _(
    ast_node: ast.Constant,
    _module_path: catalog.Path,
    _parent_path: catalog.Path,
    _parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    return ast_node.value


@evaluate_expression_node.register(ast.Tuple)
def _(
    ast_node: ast.Tuple,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return tuple(
        evaluate_expression_node(
            element, module_path, parent_path, parent_namespace
        )
        for element in ast_node.elts
    )


@evaluate_expression_node.register(ast.List)
def _(
    ast_node: ast.List,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return [
        evaluate_expression_node(
            element, module_path, parent_path, parent_namespace
        )
        for element in ast_node.elts
    ]


@evaluate_statement_node.register(ast.AnnAssign)
@evaluate_statement_node.register(ast.Assign)
def _(
    ast_node: ast.Assign,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
    *,
    cache: dict[catalog.QualifiedPath, Any] | None = None,
) -> Any:
    if cache is None:
        cache = {}
    targets_paths = [
        scoping.resolve_object_path(
            module_path,
            parent_path,
            (name,),
            stubs.definitions,
            stubs.references,
            stubs.submodules,
            stubs.superclasses,
        )
        for name in conversion.to_names(ast_node)
    ]
    for target_path in targets_paths:
        try:
            result = cache[target_path]
        except KeyError:
            _, target_object_path = target_path
            cache[target_path] = ForwardRef(
                catalog.path_to_string(target_object_path)
            )
            continue
        else:
            break
    else:
        result = evaluate_expression_node(
            ast_node.value, module_path, parent_path, parent_namespace
        )
    for target_path in targets_paths:
        cache[target_path] = result
    return result


@evaluate_expression_node.register(ast.BinOp)
def _(
    ast_node: ast.BinOp,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    left = evaluate_expression_node(
        ast_node.left, module_path, parent_path, parent_namespace
    )
    right = evaluate_expression_node(
        ast_node.right, module_path, parent_path, parent_namespace
    )
    try:
        return evaluate_operator_node(ast_node.op)(left, right)
    except TypeError:
        assert isinstance(ast_node.op, ast.BitOr), ast_node
        return left | right


@evaluate_expression_node.register(ast.Name)
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
    return evaluate_qualified_path(module_path, object_path, parent_namespace)


@evaluate_expression_node.register(ast.Attribute)
def _(
    ast_node: ast.Attribute,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
    /,
) -> Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    value = evaluate_expression_node(
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
        return evaluate_qualified_path(
            module_path, object_path, parent_namespace
        )


def evaluate_qualified_path(
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
    objects_cache: MutableMapping[
        catalog.QualifiedPath, Any
    ] = weakref.WeakValueDictionary([((('_typeshed',), ('Self',)), Self)]),  # noqa: B008
) -> Any:
    module_name = catalog.path_to_string(module_path)
    try:
        module = import_module(module_name)
    except ImportError:
        if not object_path:
            try:
                return modules_cache[module_path]
            except KeyError:
                modules_cache[module_path] = module = types.ModuleType(
                    module_name
                )
                namespace = module.__dict__
                for name in stubs.definitions[module_path]:
                    namespace[name] = parent_namespace[name] = (
                        evaluate_qualified_path(
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
        module_raw_ast_nodes = stubs.raw_ast_nodes[module_path]
        node_kind = stubs.nodes_kinds[module_path][object_path]
        try:
            raw_ast_nodes = module_raw_ast_nodes[object_path]
        except KeyError:
            assert node_kind is NodeKind.CLASS, (module_path, object_path)
        else:
            if node_kind is not NodeKind.CLASS:
                for raw_ast_node in raw_ast_nodes:
                    ast_node = construction.from_raw(raw_ast_node)
                    assert isinstance(ast_node, ast.stmt), (
                        module_path,
                        object_path,
                    )
                    parent_namespace[object_path[-1]] = (
                        evaluate_statement_node(
                            ast_node,
                            module_path,
                            object_path[:-1],
                            parent_namespace,
                        )
                    )
                return parent_namespace[object_path[-1]]
        scope = stubs.definitions[module_path]
        for part in object_path:
            scope = scope[part]
        class_namespace: namespacing.Namespace = {'__module__': __name__}
        module_namespace: namespacing.Namespace = {'__name__': __name__}
        annotations_nodes = {}
        for name in scope:
            raw_ast_nodes = module_raw_ast_nodes[(*object_path, name)]
            ast_nodes = [
                construction.from_raw(raw_ast_node)
                for raw_ast_node in raw_ast_nodes
            ]
            definitions_nodes: list[ast.stmt] = []
            for ast_node in ast_nodes:
                if (
                    isinstance(ast_node, ast.AnnAssign)
                    and ast_node.value is None
                ):
                    annotations_nodes[name] = ast_node.annotation
                else:
                    assert isinstance(ast_node, ast.stmt), (
                        module_path,
                        object_path,
                    )
                    definitions_nodes.append(ast_node)
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
                            evaluate_qualified_path(
                                dependency_module_path,
                                dependency_object_path,
                                module_namespace,
                            )
                        )
                class_namespace[name] = evaluate_statement_node(
                    definition_node,
                    module_path,
                    object_path,
                    ChainMap(class_namespace, module_namespace),
                )
        bases = tuple(
            evaluate_qualified_path(
                superclass_module_path,
                superclass_object_path,
                module_namespace,
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
                    name: evaluate_expression_node(
                        annotation_node,
                        module_path,
                        object_path,
                        parent_namespace,
                    )
                    for name, annotation_node in annotations_nodes.items()
                }
            )
        globals()[catalog.path_to_string(object_path)] = result
        return result


@evaluate_expression_node.register(ast.Subscript)
def _(
    ast_node: ast.Subscript,
    module_path: catalog.Path,
    parent_path: catalog.Path,
    parent_namespace: namespacing.Namespace,
) -> Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    value = evaluate_expression_node(
        ast_node.value, module_path, parent_path, parent_namespace
    )
    item = evaluate_expression_node(
        ast_node.slice, module_path, parent_path, parent_namespace
    )
    try:
        return value[item]
    except TypeError:
        return value
