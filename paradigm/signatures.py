import ast
import inspect
import types
from functools import (partial,
                       singledispatch)
from itertools import zip_longest
from operator import itemgetter
from typing import (Any,
                    Callable,
                    Iterable,
                    List,
                    Optional,
                    Tuple)

from . import (arboretum,
               catalog,
               qualified)
from .models import (Base,
                     Overloaded,
                     Parameter,
                     Plain)
from .names import qualified_names


@singledispatch
def factory(object_: Callable[..., Any]) -> Base:
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


@factory.register(inspect.Signature)
def from_raw_signature(object_: inspect.Signature) -> Base:
    def normalize_parameter(raw_parameter: inspect.Parameter) -> Parameter:
        has_default = raw_parameter.default is not inspect._empty
        return Parameter(name=raw_parameter.name,
                         kind=Parameter.Kind(raw_parameter.kind),
                         has_default=has_default)

    parameters = map(normalize_parameter, object_.parameters.values())
    return Plain(*parameters)


def _from_callable(value: Callable[..., Any]) -> Base:
    module_name, object_name = qualified.name_from(value)
    try:
        candidates_names = qualified_names[module_name][object_name]
    except KeyError:
        if module_name is not None:
            assert object_name, value
            qualified_paths = [(catalog.path_from_string(module_name),
                                catalog.path_from_string(object_name))]
        else:
            qualified_paths = []
    else:
        qualified_paths = [(catalog.path_from_string(module_name),
                            catalog.path_from_string(object_name))
                           for module_name, object_name in candidates_names]
    _, result = min(
            filter(itemgetter(1),
                   [_from_path(module_path, object_path)
                    for module_path, object_path in qualified_paths]),
            key=itemgetter(0)
    )
    return result


@factory.register(types.BuiltinFunctionType)
@factory.register(types.BuiltinMethodType)
@factory.register(types.FunctionType)
@factory.register(types.MethodType)
@factory.register(types.MethodDescriptorType)
@factory.register(types.MethodWrapperType)
@factory.register(types.WrapperDescriptorType)
@factory.register(type)
def from_callable(value: Callable[..., Any]) -> Base:
    try:
        return ((_from_callable(value)
                 if isinstance(value.__self__, type)
                 else (_from_callable(getattr(type(value.__self__),
                                              value.__name__))
                       .bind(value.__self__)))
                if (isinstance(value, types.BuiltinMethodType)
                    and value.__self__ is not None
                    and not isinstance(value.__self__, types.ModuleType)
                    or isinstance(value, (types.MethodType,
                                          types.MethodWrapperType)))
                else (_from_callable(value).bind(value)
                      if isinstance(value, type)
                      else _from_callable(value)))
    except ValueError:
        return from_raw_signature(inspect.signature(value))


def _from_path(module_path: catalog.Path,
               object_path: catalog.Path) -> Tuple[int, Optional[Base]]:
    try:
        depth, nodes = arboretum.to_functions_defs(module_path, object_path)
    except KeyError:
        return -1, None
    else:
        assert len(nodes) > 0 or depth == -1
        return ((depth, Overloaded(*[_from_ast(node.args) for node in nodes]))
                if nodes
                else (-1, None))


def _from_ast(signature_ast: ast.arguments) -> Base:
    parameters = filter(
            None,
            (*_to_positional_parameters(signature_ast),
             _to_variadic_positional_parameter(signature_ast),
             *_to_keyword_parameters(signature_ast),
             _to_variadic_keyword_parameter(signature_ast))
    )
    return Plain(*parameters)


def _to_positional_parameters(
        signature_ast: ast.arguments
) -> Iterable[Parameter]:
    # double-reversing since parameters with default arguments go last
    parameters_with_defaults_ast: List[ast.arg] = list(zip_longest(
            reversed(signature_ast.args), signature_ast.defaults
    ))[::-1]
    kind = Parameter.Kind.POSITIONAL_ONLY
    return [_to_parameter(parameter_ast, default_ast,
                          kind=kind)
            for parameter_ast, default_ast in parameters_with_defaults_ast]


def _to_keyword_parameters(
        signature_ast: ast.arguments
) -> Iterable[Parameter]:
    kind = Parameter.Kind.KEYWORD_ONLY
    return [_to_parameter(parameter_ast, default_ast,
                          kind=kind)
            for parameter_ast, default_ast in zip(signature_ast.kwonlyargs,
                                                  signature_ast.kw_defaults)]


def _to_variadic_positional_parameter(
        signature_ast: ast.arguments
) -> Optional[Parameter]:
    parameter_ast = signature_ast.vararg
    return (None
            if parameter_ast is None
            else Parameter(name=parameter_ast.arg,
                           kind=Parameter.Kind.VARIADIC_POSITIONAL,
                           has_default=False))


def _to_variadic_keyword_parameter(
        signature_ast: ast.arguments
) -> Optional[Parameter]:
    parameter_ast = signature_ast.kwarg
    return (None
            if parameter_ast is None
            else Parameter(name=parameter_ast.arg,
                           kind=Parameter.Kind.VARIADIC_KEYWORD,
                           has_default=False))


def _to_parameter(parameter_ast: ast.arg,
                  default_ast: Optional[ast.expr],
                  *,
                  kind: Parameter.Kind) -> Parameter:
    return Parameter(name=parameter_ast.arg,
                     kind=kind,
                     has_default=default_ast is not None)


@factory.register(partial)
def from_partial(object_: partial) -> Base:
    return factory(object_.func).bind(*object_.args, **object_.keywords)


@singledispatch
def _slice_parameters(signature: Base,
                      slice_: slice) -> Base:
    raise TypeError(f'Unsupported signature type: {type(signature)!r}.')


@_slice_parameters.register(Plain)
def _(signature: Plain, slice_: slice) -> Base:
    return Plain(*signature.parameters[slice_])


@_slice_parameters.register(Overloaded)
def _(signature: Overloaded, slice_: slice) -> Base:
    return Overloaded(*map(partial(_slice_parameters,
                                   slice_=slice_),
                           signature.signatures))
