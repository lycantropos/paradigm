import ast as _ast
import inspect as _inspect
import types as _types
import typing as _t
from functools import (partial as _partial,
                       singledispatch as _singledispatch)
from itertools import zip_longest as _zip_longest
from operator import itemgetter as _itemgetter

from ._core import (arboreal as _arboreal,
                    catalog as _catalog,
                    qualified as _qualified)
from ._core import models
from ._core.names import qualified_names as _qualified_names

Overloaded = models.Overloaded
Parameter = models.Parameter
Plain = models.Plain
_Signature = _t.Union[Overloaded, Plain]


@_singledispatch
def from_callable(object_: _t.Callable[..., _t.Any]) -> _Signature:
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


@from_callable.register(_types.BuiltinFunctionType)
@from_callable.register(_types.BuiltinMethodType)
@from_callable.register(_types.FunctionType)
@from_callable.register(_types.MethodType)
@from_callable.register(_types.MethodDescriptorType)
@from_callable.register(_types.MethodWrapperType)
@from_callable.register(_types.WrapperDescriptorType)
@from_callable.register(type)
def _(value: _t.Callable[..., _t.Any]) -> _Signature:
    try:
        return ((_from_callable(value)
                 if isinstance(value.__self__, type)
                 else (_from_callable(getattr(type(value.__self__),
                                              value.__name__))
                       .bind(value.__self__)))
                if (isinstance(value, _types.BuiltinMethodType)
                    and value.__self__ is not None
                    and not isinstance(value.__self__, _types.ModuleType)
                    or isinstance(value, (_types.MethodType,
                                          _types.MethodWrapperType)))
                else (_from_callable(value).bind(value)
                      if isinstance(value, type)
                      else _from_callable(value)))
    except ValueError:
        return _from_raw_signature(_inspect.signature(value))


@from_callable.register(_partial)
def _(object_: _partial) -> _Signature:
    return from_callable(object_.func).bind(*object_.args, **object_.keywords)


def _from_ast(signature_ast: _ast.arguments) -> _Signature:
    parameters = filter(
            None,
            (*_to_positional_parameters(signature_ast),
             _to_variadic_positional_parameter(signature_ast),
             *_to_keyword_parameters(signature_ast),
             _to_variadic_keyword_parameter(signature_ast))
    )
    return _Plain(*parameters)


def _from_callable(value: _t.Callable[..., _t.Any]) -> _Signature:
    module_name, object_name = _qualified.name_from(value)
    try:
        candidates_names = _qualified_names[module_name][object_name]
    except KeyError:
        if module_name is not None:
            assert object_name, value
            qualified_paths = [(_catalog.path_from_string(module_name),
                                _catalog.path_from_string(object_name))]
        else:
            qualified_paths = []
    else:
        qualified_paths = [(_catalog.path_from_string(module_name),
                            _catalog.path_from_string(object_name))
                           for module_name, object_name in candidates_names]
    _, result = min(
            filter(_itemgetter(1),
                   [_from_path(module_path, object_path)
                    for module_path, object_path in qualified_paths]),
            key=_itemgetter(0)
    )
    return result


def _from_path(module_path: _catalog.Path,
               object_path: _catalog.Path) -> _t.Tuple[
    int, _t.Optional[_Signature]]:
    try:
        depth, nodes = _arboreal.to_functions_defs(module_path, object_path)
    except KeyError:
        return -1, None
    else:
        assert len(nodes) > 0 or depth == -1
        return ((depth,
                 _Overloaded(*[_from_ast(node.args) for node in nodes]))
                if nodes
                else (-1, None))


def _from_raw_signature(object_: _inspect.Signature) -> _Signature:
    return _Plain(*[_Parameter(name=raw.name,
                               kind=Parameter.Kind(raw.kind),
                               has_default=raw.default is not _inspect._empty)
                    for raw in object_.parameters.values()])


def _to_keyword_parameters(
        signature_ast: _ast.arguments
) -> _t.Iterable[Parameter]:
    kind = Parameter.Kind.KEYWORD_ONLY
    return [_to_parameter(parameter_ast, default_ast,
                          kind=kind)
            for parameter_ast, default_ast in zip(signature_ast.kwonlyargs,
                                                  signature_ast.kw_defaults)]


def _to_parameter(parameter_ast: _ast.arg,
                  default_ast: _t.Optional[_ast.expr],
                  *,
                  kind: Parameter.Kind) -> Parameter:
    return _Parameter(name=parameter_ast.arg,
                      kind=kind,
                      has_default=default_ast is not None)


def _to_positional_parameters(
        signature_ast: _ast.arguments
) -> _t.Iterable[Parameter]:
    # double-reversing since parameters with default arguments go last
    parameters_with_defaults_ast: _t.List[_ast.arg] = list(_zip_longest(
            reversed(signature_ast.args), signature_ast.defaults
    ))[::-1]
    kind = Parameter.Kind.POSITIONAL_ONLY
    return [_to_parameter(parameter_ast, default_ast,
                          kind=kind)
            for parameter_ast, default_ast in parameters_with_defaults_ast]


def _to_variadic_keyword_parameter(
        signature_ast: _ast.arguments
) -> _t.Optional[Parameter]:
    parameter_ast = signature_ast.kwarg
    return (None
            if parameter_ast is None
            else _Parameter(name=parameter_ast.arg,
                            kind=Parameter.Kind.VARIADIC_KEYWORD,
                            has_default=False))


def _to_variadic_positional_parameter(
        signature_ast: _ast.arguments
) -> _t.Optional[Parameter]:
    parameter_ast = signature_ast.vararg
    return (None
            if parameter_ast is None
            else _Parameter(name=parameter_ast.arg,
                            kind=Parameter.Kind.VARIADIC_POSITIONAL,
                            has_default=False))
