import ast as _ast
import builtins
import inspect as _inspect
import sys as _sys
import types as _types
import typing as _t
from functools import (partial as _partial,
                       singledispatch as _singledispatch)
from itertools import zip_longest as _zip_longest
from operator import itemgetter

from . import (catalog as _catalog,
               scoping as _scoping,
               stubs as _stubs)
from .arboreal.kind import NodeKind
from .models import (Parameter as _Parameter,
                     PlainSignature as _PlainSignature,
                     Signature as _Signature,
                     from_signatures as _from_signatures)
from .modules import supported_stdlib_qualified_paths as _qualified_paths


@_singledispatch
def from_callable(_callable: _t.Callable[..., _t.Any]) -> _Signature:
    raise TypeError(f'Unsupported object type: {type(_callable)}.')


@from_callable.register(_types.BuiltinFunctionType)
@from_callable.register(_types.BuiltinMethodType)
@from_callable.register(_types.FunctionType)
@from_callable.register(_types.MethodType)
@from_callable.register(_types.MethodDescriptorType)
@from_callable.register(_types.MethodWrapperType)
@from_callable.register(_types.WrapperDescriptorType)
@from_callable.register(type)
def _(_callable: _t.Callable[..., _t.Any]) -> _Signature:
    try:
        return ((_from_callable(_callable)
                 if isinstance(_callable.__self__, type)
                 else (_from_callable(getattr(type(_callable.__self__),
                                              _callable.__name__))
                       .bind(_callable.__self__)))
                if (isinstance(_callable, _types.BuiltinMethodType)
                    and _callable.__self__ is not None
                    and not isinstance(_callable.__self__, _types.ModuleType)
                    or isinstance(_callable, (_types.MethodType,
                                              _types.MethodWrapperType)))
                else (_from_callable(_callable).bind(_callable)
                      if isinstance(_callable, type)
                      else _from_callable(_callable)))
    except _SignatureNotFound:
        return _from_raw_signature(_inspect.signature(_callable))


@from_callable.register(_partial)
def _(_callable: _partial) -> _Signature:
    return from_callable(_callable.func).bind(*_callable.args,
                                              **_callable.keywords)


@_singledispatch
def _from_ast(ast_node: _ast.AST, module_path: _catalog.Path) -> _Signature:
    raise TypeError(ast_node)


@_singledispatch
def _ast_node_to_path(ast_node: _ast.expr) -> _catalog.Path:
    raise TypeError(type(ast_node))


@_ast_node_to_path.register(_ast.Name)
def _(ast_node: _ast.Name) -> _catalog.Path:
    return (ast_node.id,)


@_ast_node_to_path.register(_ast.Attribute)
def _(ast_node: _ast.Attribute) -> _catalog.Path:
    return _ast_node_to_path(ast_node.value) + (ast_node.attr,)


@_from_ast.register(_ast.AnnAssign)
def _(ast_node: _ast.AnnAssign, module_path: _catalog.Path) -> _Signature:
    annotation_node = ast_node.annotation
    if ast_node.value is None:
        return _from_ast(annotation_node, module_path)
    else:
        raise ValueError(ast_node)


@_from_ast.register(_ast.Subscript)
def _(ast_node: _ast.Subscript,
      module_path: _catalog.Path,
      *,
      callable_object_path: _catalog.Path = ('Callable',),
      typing_module_path: _catalog.Path
      = _catalog.module_path_from_module(_t)) -> _Signature:
    value_path = _ast_node_to_path(ast_node.value)
    value_module_path, value_object_path = _scoping.resolve_object_path(
            module_path, (), value_path, _stubs.definitions,
            _stubs.references, _stubs.sub_scopes
    )
    if (value_module_path == typing_module_path
            and value_object_path == callable_object_path):
        assert isinstance(ast_node.slice, _ast.Index), ast_node
        assert (
            isinstance(ast_node.slice.value, _ast.Tuple)
        ), ast_node
        arguments_annotations = ast_node.slice.value.elts[0]
        if isinstance(arguments_annotations, _ast.List):
            return _PlainSignature(
                    *[_Parameter(name='_' + str(index),
                                 kind=_Parameter.Kind.POSITIONAL_ONLY,
                                 has_default=False)
                      for index in range(len(arguments_annotations.elts))]
            )
        else:
            assert (
                isinstance(arguments_annotations, _ast.Ellipsis)
            ), ast_node
            return _PlainSignature(
                    _Parameter(name='args',
                               kind=_Parameter.Kind.VARIADIC_POSITIONAL,
                               has_default=False),
                    _Parameter(name='kwargs',
                               kind=_Parameter.Kind.VARIADIC_KEYWORD,
                               has_default=False),
            )
    raise ValueError(ast_node)


@_from_ast.register(_ast.Name)
@_from_ast.register(_ast.Attribute)
def _(ast_node: _ast.Subscript,
      module_path: _catalog.Path,
      *,
      type_var_object_path: _catalog.Path
      = _catalog.path_from_string(_t.TypeVar.__qualname__),
      typing_module_path: _catalog.Path
      = _catalog.module_path_from_module(_t)) -> _Signature:
    object_path = _ast_node_to_path(ast_node)
    module_path, object_path = _scoping.resolve_object_path(
            module_path, (), object_path, _stubs.definitions,
            _stubs.references, _stubs.sub_scopes
    )
    node_kind = NodeKind(_stubs.nodes_kinds[module_path][object_path])
    if node_kind is NodeKind.CLASS:
        call_ast_nodes = [
            _deserialize_raw_annotation(raw)
            for raw in _stubs.raw_ast_nodes[module_path][
                (*object_path, object.__call__.__name__)
            ]
        ]
        call_signatures = [_from_ast(ast_node, module_path)
                           for ast_node in call_ast_nodes]
        return _from_signatures(*[signature.bind('self')
                                  for signature in call_signatures])
    else:
        annotation_nodes = [
            _deserialize_raw_annotation(raw)
            for raw in _stubs.raw_ast_nodes[module_path][object_path]
        ]
        if len(annotation_nodes) == 1:
            ast_node, = annotation_nodes
            return _from_ast(ast_node.value, module_path)
    raise ValueError(ast_node)


@_from_ast.register(_ast.Call)
@_from_ast.register(_ast.Attribute)
def _(ast_node: _ast.Subscript,
      module_path: _catalog.Path,
      *,
      type_var_object_path: _catalog.Path
      = _catalog.path_from_string(_t.TypeVar.__qualname__),
      typing_module_path: _catalog.Path
      = _catalog.module_path_from_module(_t)) -> _Signature:
    assert isinstance(ast_node, _ast.Call), ast_node
    callable_object_path = _ast_node_to_path(ast_node.func)
    callable_module_path, callable_object_path = (
        _scoping.resolve_object_path(
                module_path, (), callable_object_path,
                _stubs.definitions, _stubs.references,
                _stubs.sub_scopes
        )
    )
    if (callable_module_path == typing_module_path
            and callable_object_path == type_var_object_path):
        maybe_bound_type_node = next((keyword.value
                                      for keyword in ast_node.keywords
                                      if keyword.arg == 'bound'),
                                     None)
        if maybe_bound_type_node is None:
            _ = 0
        else:
            return _from_ast(maybe_bound_type_node, module_path)
    raise ValueError(ast_node)


@_from_ast.register(_ast.AsyncFunctionDef)
@_from_ast.register(_ast.FunctionDef)
def _(ast_node: _ast.FunctionDef, module_path: _catalog.Path) -> _Signature:
    signature_ast = ast_node.args
    parameters = filter(
            None,
            (*_to_positional_parameters(signature_ast),
             _to_variadic_positional_parameter(signature_ast),
             *_to_keyword_parameters(signature_ast),
             _to_variadic_keyword_parameter(signature_ast))
    )
    return _PlainSignature(*parameters)


class _SignatureNotFound(Exception):
    pass


def _try_resolve_object_path(
        module_path: _catalog.Path, object_path: _catalog.Path
) -> _catalog.QualifiedPath:
    try:
        return _scoping.resolve_object_path(
                module_path, (), object_path, _stubs.definitions,
                _stubs.references, _stubs.sub_scopes
        )
    except _scoping.ObjectNotFound:
        return (), ()


def _from_callable(value: _t.Callable[..., _t.Any]) -> _Signature:
    module_path, object_path = _catalog.qualified_path_from(value)
    try:
        candidates_paths = _qualified_paths[module_path][object_path]
    except KeyError:
        if module_path:
            assert object_path, value
            qualified_paths = [(module_path, object_path)]
        else:
            qualified_paths = []
    else:
        qualified_paths = [path
                           for path in candidates_paths
                           if _value_has_qualified_path(value, path)]
    resolved_qualified_paths = sorted({
        (module_path, object_path)
        for module_path, object_path in [
            _try_resolve_object_path(module_path, object_path)
            for module_path, object_path in qualified_paths
        ]
        if module_path and object_path
    })
    if not resolved_qualified_paths:
        raise _SignatureNotFound(qualified_paths)
    resolved_module_path, resolved_object_path = resolved_qualified_paths[0]
    if (isinstance(value, type)
            or (_stubs.nodes_kinds[resolved_module_path][resolved_object_path]
                == NodeKind.CLASS)):
        depth, (resolved_module_path, resolved_object_path) = min(
                _locate_class_builder_qualified_path(module_path, object_path)
                for module_path, object_path in qualified_paths
        )
    try:
        raw_ast_nodes = _stubs.raw_ast_nodes[resolved_module_path][
            resolved_object_path
        ]
    except KeyError:
        raise _SignatureNotFound(qualified_paths)
    assert raw_ast_nodes, (module_path, object_path)
    ast_nodes = [_deserialize_raw_annotation(raw_ast_node)
                 for raw_ast_node in raw_ast_nodes]
    return _from_signatures(*[_from_ast(ast_node, resolved_module_path)
                              for ast_node in ast_nodes])


def _deserialize_raw_annotation(
        raw: _stubs.RawAstNode,
        *,
        namespace: _t.Dict[str, _t.Any] = vars(_ast)
) -> _ast.AST:
    return eval(raw, namespace)


def _locate_class_builder_qualified_path(
        module_path: _catalog.Path,
        object_path: _catalog.Path,
        *,
        object_builder_qualified_path: _catalog.QualifiedPath
        = (_catalog.module_path_from_module(builtins),
           _catalog.path_from_string(object.__qualname__)
           + _catalog.path_from_string(object.__new__.__name__)),
        constructor_name: str = object.__new__.__name__,
        initializer_name: str = object.__init__.__name__
) -> _t.Tuple[int, _catalog.QualifiedPath]:
    depth = 0
    for depth, (base_module_path, base_object_path) in enumerate(
            _to_mro(module_path, object_path)
    ):
        base_module_annotations = _stubs.raw_ast_nodes[base_module_path]
        constructor_path = object_path + (constructor_name,)
        initializer_path = object_path + (initializer_name,)
        if constructor_path in base_module_annotations:
            return depth, (base_module_path, constructor_path)
        elif initializer_path in base_module_annotations:
            return depth, (base_module_path, initializer_path)
    return (depth, object_builder_qualified_path)


def _to_mro(module_path: _catalog.Path,
            object_path: _catalog.Path) -> _t.Iterable[_catalog.QualifiedPath]:
    yield (module_path, object_path)
    try:
        bases = _stubs.sub_scopes[module_path][object_path]
    except KeyError:
        return
    for base_module_path, base_object_path in bases:
        yield from _to_mro(base_module_path, base_object_path)


def _value_has_qualified_path(value: _t.Any,
                              path: _catalog.QualifiedPath) -> bool:
    module_path, object_path = path
    module_name = _catalog.path_to_string(module_path)
    if module_name not in _sys.modules:
        # undecidable, let's keep it
        return True
    candidate = _sys.modules[module_name]
    for part in object_path:
        try:
            candidate = getattr(candidate, part)
        except AttributeError:
            return False
    return candidate is value


def _from_raw_signature(object_: _inspect.Signature) -> _Signature:
    return _PlainSignature(*[
        _Parameter(name=raw.name,
                   kind=_Parameter.Kind(raw.kind),
                   has_default=raw.default is not _inspect._empty)
        for raw in object_.parameters.values()
    ])


def _to_keyword_parameters(
        signature_ast: _ast.arguments
) -> _t.Iterable[_Parameter]:
    kind = _Parameter.Kind.KEYWORD_ONLY
    return [_to_parameter(parameter_ast, default_ast,
                          kind=kind)
            for parameter_ast, default_ast in zip(signature_ast.kwonlyargs,
                                                  signature_ast.kw_defaults)]


def _to_parameter(parameter_ast: _ast.arg,
                  default_ast: _t.Optional[_ast.expr],
                  *,
                  kind: _Parameter.Kind) -> _Parameter:
    return _Parameter(name=parameter_ast.arg,
                      kind=kind,
                      has_default=default_ast is not None)


def _to_positional_parameters(
        signature_ast: _ast.arguments
) -> _t.Iterable[_Parameter]:
    # double-reversing since parameters with default arguments go last
    parameters_with_defaults_ast: _t.List[
        _t.Tuple[_ast.arg, _t.Optional[_ast.expr]]
    ] = list(_zip_longest(reversed(signature_ast.args),
                          signature_ast.defaults))[::-1]
    kind = _Parameter.Kind.POSITIONAL_ONLY
    return [_to_parameter(parameter_ast, default_ast,
                          kind=kind)
            for parameter_ast, default_ast in parameters_with_defaults_ast]


def _to_variadic_keyword_parameter(
        signature_ast: _ast.arguments
) -> _t.Optional[_Parameter]:
    parameter_ast = signature_ast.kwarg
    return (None
            if parameter_ast is None
            else _Parameter(name=parameter_ast.arg,
                            kind=_Parameter.Kind.VARIADIC_KEYWORD,
                            has_default=False))


def _to_variadic_positional_parameter(
        signature_ast: _ast.arguments
) -> _t.Optional[_Parameter]:
    parameter_ast = signature_ast.vararg
    return (None
            if parameter_ast is None
            else _Parameter(name=parameter_ast.arg,
                            kind=_Parameter.Kind.VARIADIC_POSITIONAL,
                            has_default=False))
