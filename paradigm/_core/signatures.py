import ast as _ast
import inspect as _inspect
import sys as _sys
import types as _types
import typing as _t
from functools import (partial as _partial,
                       singledispatch as _singledispatch)
from itertools import zip_longest as _zip_longest
from operator import itemgetter as _itemgetter

from . import (arboreal as _arboreal,
               catalog as _catalog)
from .models import (OverloadedSignature as _OverloadedSignature,
                     Parameter as _Parameter,
                     PlainSignature as _PlainSignature)
from .modules import supported_stdlib_qualified_paths as _qualified_paths

_Signature = _t.Union[_OverloadedSignature, _PlainSignature]


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
    except _NodeNotFound:
        return _from_raw_signature(_inspect.signature(_callable))


@from_callable.register(_partial)
def _(_callable: _partial) -> _Signature:
    return from_callable(_callable.func).bind(*_callable.args,
                                              **_callable.keywords)


def _from_ast(signature_ast: _ast.arguments) -> _Signature:
    parameters = filter(
            None,
            (*_to_positional_parameters(signature_ast),
             _to_variadic_positional_parameter(signature_ast),
             *_to_keyword_parameters(signature_ast),
             _to_variadic_keyword_parameter(signature_ast))
    )
    return _PlainSignature(*parameters)


class _NodeNotFound(Exception):
    pass


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
    candidates = [
        (depth, node)
        for depth, node in [
            _from_node(node)
            for node in [_arboreal.find_node(module_path, object_path)
                         for module_path, object_path in qualified_paths]
            if node is not None
        ]
        if node is not None
    ]
    try:
        _, node = min(candidates,
                      key=_itemgetter(0))
    except ValueError:
        raise _NodeNotFound(qualified_paths,
                            _qualified_paths.get(module_path, {}))
    assert node.kind is _arboreal.NodeKind.FUNCTION, (module_path, object_path)
    return _OverloadedSignature(*[_from_ast(ast_node.args)
                                  for ast_node in node.ast_nodes])


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


def _from_node(object_node: _arboreal.Node,
               *,
               constructor_name: str = object.__new__.__name__,
               initializer_name: str = object.__init__.__name__):
    if object_node.kind is _arboreal.NodeKind.CLASS:
        initializer_depth, initializer_node = object_node.locate_name(
                initializer_name
        )
        constructor_depth, constructor_node = object_node.locate_name(
                constructor_name
        )
        return ((constructor_depth, constructor_node)
                if constructor_depth < initializer_depth
                else (initializer_depth, initializer_node))
    elif object_node.kind is _arboreal.NodeKind.FUNCTION:
        return 0, object_node
    else:
        assert (
                object_node.kind is not _arboreal.NodeKind.UNDEFINED
        ), object_node
        return -1, None


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
