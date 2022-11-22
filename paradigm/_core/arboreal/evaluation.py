import ast
import builtins
import operator
import sys
import types
import typing as t
import weakref
from functools import singledispatch
from importlib import import_module

from paradigm._core import (catalog,
                            namespacing,
                            scoping,
                            sources,
                            stubs)
from . import (construction,
               conversion)
from .execution import execute_statement
from .kind import NodeKind
from .utils import (is_dependency_name,
                    recursively_iterate_children)


@singledispatch
def evaluate_ast_node(ast_node: ast.AST,
                      module_path: catalog.Path,
                      namespace: namespacing.Namespace) -> t.Any:
    raise TypeError(type(ast_node))


@evaluate_ast_node.register(ast.USub)
def _(ast_node: ast.USub,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    return operator.neg


@evaluate_ast_node.register(ast.UAdd)
def _(ast_node: ast.UAdd,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    return operator.pos


@evaluate_ast_node.register(ast.UnaryOp)
def _(ast_node: ast.UnaryOp,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    return evaluate_ast_node(ast_node.op, module_path, namespace)(
            evaluate_ast_node(ast_node.operand, module_path, namespace)
    )


@evaluate_ast_node.register(ast.BitOr)
def _(ast_node: ast.BitOr,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    return operator.or_


@evaluate_ast_node.register(ast.Call)
def _(ast_node: ast.Call,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    args = [evaluate_ast_node(arg, module_path, namespace)
            for arg in ast_node.args]
    kwargs = {
        keyword.arg: evaluate_ast_node(keyword.value, module_path, namespace)
        for keyword in ast_node.keywords
    }
    return evaluate_ast_node(ast_node.func, module_path, namespace)(
            *args, **kwargs
    )


class _LazyEvaluator(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if node.returns is not None:
            node.returns = ast.Str(conversion.to_str(node.returns))
        self.generic_visit(node)
        return node

    if sys.version_info < (3, 8):
        def visit_arg(self, node: ast.arg) -> ast.arg:
            return ast.arg(node.arg,
                           None
                           if node.annotation is None
                           else ast.Str(conversion.to_str(node.annotation)))
    else:
        def visit_arg(self, node: ast.arg) -> ast.arg:
            return ast.arg(node.arg,
                           None
                           if node.annotation is None
                           else ast.Str(conversion.to_str(node.annotation)),
                           node.type_comment)


@evaluate_ast_node.register(ast.FunctionDef)
def _(ast_node: ast.FunctionDef,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    namespace = namespace.copy()
    try:
        source_path = sources.from_module_path(module_path)
    except sources.NotFound:
        source_path = sources.Path(*module_path)
    execute_statement(
            ast.fix_missing_locations(
                    _LazyEvaluator().visit(ast_node)
            ),
            source_path=source_path,
            namespace=namespace
    )
    return namespace.pop(ast_node.name)


@evaluate_ast_node.register(ast.Constant)
def _(ast_node: ast.Constant,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    return ast_node.value


@evaluate_ast_node.register(ast.Tuple)
def _(ast_node: ast.Tuple,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return tuple(evaluate_ast_node(element, module_path, namespace)
                 for element in ast_node.elts)


@evaluate_ast_node.register(ast.List)
def _(ast_node: ast.List,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return [evaluate_ast_node(element, module_path, namespace)
            for element in ast_node.elts]


@evaluate_ast_node.register(ast.Assign)
def _(ast_node: ast.Assign,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    return evaluate_ast_node(ast_node.value, module_path, namespace)


@evaluate_ast_node.register(ast.AnnAssign)
def _(ast_node: ast.AnnAssign,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    assert ast_node.value is not None, ast_node
    return evaluate_ast_node(ast_node.value, module_path, namespace)


@evaluate_ast_node.register(ast.BinOp)
def _(ast_node: ast.BinOp,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    left = evaluate_ast_node(ast_node.left, module_path, namespace)
    right = evaluate_ast_node(ast_node.right, module_path, namespace)
    try:
        return evaluate_ast_node(ast_node.op, module_path, namespace)(
                left, right
        )
    except TypeError:
        assert isinstance(ast_node.op, ast.BitOr), ast_node
        return t.Union[left, right]


@evaluate_ast_node.register(ast.Name)
def _(ast_node: ast.Name,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    object_name = ast_node.id
    try:
        return namespace[object_name]
    except KeyError:
        module_path, object_path = scoping.resolve_object_path(
                module_path, (), (object_name,), stubs.definitions,
                stubs.references, stubs.sub_scopes
        )
        return _evaluate_qualified_path(module_path, object_path, namespace)


@evaluate_ast_node.register(ast.Attribute)
def _(ast_node: ast.Attribute,
      module_path: catalog.Path,
      namespace: namespacing.Namespace) -> t.Any:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    value = evaluate_ast_node(ast_node.value, module_path, namespace)
    try:
        return getattr(value, ast_node.attr)
    except AttributeError:
        module_path, object_path = scoping.resolve_object_path(
                module_path, (), conversion.to_path(ast_node),
                stubs.definitions, stubs.references, stubs.sub_scopes
        )
        return _evaluate_qualified_path(module_path, object_path, namespace)


def _evaluate_qualified_path(
        module_path: catalog.Path,
        object_path: catalog.Path,
        namespace: namespacing.Namespace,
        *,
        builtins_module_path: catalog.Path
        = catalog.module_path_from_module(builtins),
        cache: t.MutableMapping[catalog.QualifiedPath, t.Any]
        = weakref.WeakValueDictionary()
) -> t.Any:
    try:
        module = import_module(catalog.path_to_string(module_path))
    except ImportError:
        if not object_path:
            try:
                return cache[(module_path, object_path)]
            except KeyError:
                module = types.ModuleType(catalog.path_to_string(module_path))
                module_namespace = module.__dict__
                module_namespace.update({
                    name: _evaluate_qualified_path(module_path, (name,),
                                                   module_namespace)
                    for name in stubs.definitions[module_path].keys()
                })
                cache[(module_path, object_path)] = module
                return module
        module_namespace = namespace.copy()
    else:
        if not object_path:
            return module
        module_namespace = {**namespace, **vars(module)}
        try:
            return namespacing.search(module_namespace, object_path)
        except namespacing.ObjectNotFound:
            pass
    module_raw_ast_nodes = stubs.raw_ast_nodes[module_path]
    try:
        raw_ast_nodes = module_raw_ast_nodes[object_path]
    except KeyError:
        try:
            return cache[(module_path, object_path)]
        except KeyError:
            assert (
                    NodeKind(stubs.nodes_kinds[module_path][object_path])
                    is NodeKind.CLASS
            )
            scope = stubs.definitions[module_path]
            for part in object_path:
                scope = scope[part]
            class_namespace = {
                name: field
                for name, field in module_namespace.items()
                if not name.startswith('__') and not name.endswith('__')
            }
            class_namespace['__module__'] = catalog.path_to_string(module_path)
            annotations_nodes = {}
            for name in scope.keys():
                raw_ast_nodes = module_raw_ast_nodes[object_path + (name,)]
                ast_nodes = [construction.from_raw(raw_ast_node)
                             for raw_ast_node in raw_ast_nodes]
                definitions_nodes = []
                for ast_node in ast_nodes:
                    if (isinstance(ast_node, ast.AnnAssign)
                            and ast_node.value is None):
                        annotations_nodes[name] = ast_node.annotation
                    else:
                        definitions_nodes.append(ast_node)
                to_lazy = _LazyEvaluator().visit
                for definition_node in definitions_nodes:
                    for dependency_name in {
                        child.id
                        for child in recursively_iterate_children(
                                to_lazy(definition_node)
                        )
                        if is_dependency_name(child)
                    }:
                        dependency_module_path, dependency_object_path = (
                            scoping.resolve_object_path(
                                    module_path, object_path,
                                    (dependency_name,), stubs.definitions,
                                    stubs.references, stubs.sub_scopes
                            )
                        )
                        if dependency_module_path != builtins_module_path:
                            class_namespace[dependency_name] = (
                                _evaluate_qualified_path(
                                        dependency_module_path,
                                        dependency_object_path, class_namespace
                                )
                            )
                    value = evaluate_ast_node(definition_node, module_path,
                                              class_namespace)
                if definitions_nodes:
                    class_namespace[name] = value
            bases = tuple(
                    _evaluate_qualified_path(sub_module_path, sub_object_path,
                                             class_namespace)
                    for sub_module_path, sub_object_path in stubs.sub_scopes[
                        module_path
                    ].get(object_path, [])
            )
            if annotations_nodes:
                class_namespace['__annotations__'] = {}
            result = namespace[object_path[-1]] = cache[
                (module_path, object_path)
            ] = type(object_path[-1], types.resolve_bases(bases),
                     class_namespace)
            if annotations_nodes:
                result.__annotations__.update({
                    name: evaluate_ast_node(ast_node, module_path, namespace)
                    for name, ast_node in annotations_nodes.items()
                })
            return result
    else:
        assert len(raw_ast_nodes) == 1, (module_path, object_path)
        raw_ast_node, = raw_ast_nodes
        ast_node = construction.from_raw(raw_ast_node)
        return evaluate_ast_node(ast_node, module_path, namespace)


if sys.version_info < (3, 8):
    @evaluate_ast_node.register(ast.Ellipsis)
    def _(ast_node: ast.Ellipsis,
          module_path: catalog.Path,
          namespace: namespacing.Namespace) -> t.Any:
        return Ellipsis


    @evaluate_ast_node.register(ast.NameConstant)
    def _(ast_node: ast.NameConstant,
          module_path: catalog.Path,
          namespace: namespacing.Namespace) -> t.Any:
        return ast_node.value


    @evaluate_ast_node.register(ast.Num)
    def _(ast_node: ast.Num,
          module_path: catalog.Path,
          namespace: namespacing.Namespace) -> t.Any:
        return ast_node.n


    @evaluate_ast_node.register(ast.Str)
    def _(ast_node: ast.Str,
          module_path: catalog.Path,
          namespace: namespacing.Namespace) -> t.Any:
        return ast_node.s

if sys.version_info < (3, 9):
    _GenericAlias: t.Any = type(t.List)
    _types_to_generic_aliases = {value.__origin__: value
                                 for value in vars(t).values()
                                 if isinstance(value, _GenericAlias)}


    @evaluate_ast_node.register(ast.Index)
    def _(ast_node: ast.Index,
          module_path: catalog.Path,
          namespace: namespacing.Namespace) -> t.Any:
        return evaluate_ast_node(ast_node.value, module_path, namespace)


    @evaluate_ast_node.register(ast.Subscript)
    def _(ast_node: ast.Subscript,
          module_path: catalog.Path,
          namespace: namespacing.Namespace) -> t.Any:
        assert isinstance(ast_node.ctx, ast.Load), ast_node
        value = evaluate_ast_node(ast_node.value, module_path, namespace)
        item = evaluate_ast_node(ast_node.slice, module_path, namespace)
        try:
            generic_alias = _types_to_generic_aliases[value]
        except KeyError:
            try:
                return value[item]
            except TypeError:
                return value
        else:
            return generic_alias[item]
else:
    @evaluate_ast_node.register(ast.Subscript)
    def _(ast_node: ast.Subscript,
          module_path: catalog.Path,
          namespace: namespacing.Namespace) -> t.Any:
        assert isinstance(ast_node.ctx, ast.Load), ast_node
        value = evaluate_ast_node(ast_node.value, module_path, namespace)
        item = evaluate_ast_node(ast_node.slice, module_path, namespace)
        try:
            return value[item]
        except TypeError:
            return value
