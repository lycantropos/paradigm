import inspect
import platform
import types
from functools import (partial,
                       singledispatch,
                       wraps)
from itertools import (chain,
                       starmap,
                       zip_longest)
from operator import itemgetter
from types import (BuiltinFunctionType,
                   BuiltinMethodType,
                   FunctionType,
                   MethodType)
from typing import (Any,
                    Callable,
                    Iterable,
                    Optional,
                    Tuple)
from weakref import WeakKeyDictionary

from memoir import cached

from .hints import (Map,
                    MethodDescriptorType,
                    WrapperDescriptorType)
from .models import (Base,
                     Overloaded,
                     Parameter,
                     Plain)


@singledispatch
def factory(object_: Callable[..., Any]) -> Base:
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


def from_callable(object_: Callable[..., Any]) -> Base:
    return from_raw_signature(inspect.signature(object_))


@factory.register(inspect.Signature)
def from_raw_signature(object_: inspect.Signature) -> Base:
    def normalize_parameter(raw_parameter: inspect.Parameter) -> Parameter:
        has_default = raw_parameter.default is not inspect._empty
        return Parameter(name=raw_parameter.name,
                         kind=Parameter.Kind(raw_parameter.kind),
                         has_default=has_default)

    parameters = map(normalize_parameter, object_.parameters.values())
    return Plain(*parameters)


if platform.python_implementation() == 'PyPy':
    def from_class(object_: type) -> Base:
        try:
            return from_callable(object_)
        except ValueError:
            method = find_initializer_or_constructor(object_)
            if method is None:
                raise
            return slice_parameters(factory(method), slice(1, None))


    def find_initializer_or_constructor(class_: type) -> Optional[Callable]:
        for cls, next_cls in zip(class_.__mro__, class_.__mro__[1:]):
            if cls.__new__ is not next_cls.__new__:
                return cls.__new__
            elif cls.__init__ is not next_cls.__init__:
                return cls.__init__
        return None
else:
    from typed_ast import ast3

    from . import (arboretum,
                   catalog)


    def with_typeshed(
            function: Map[Callable[..., Any], Base]
    ) -> Map[Callable[..., Any], Base]:
        @wraps(function)
        def wrapped(object_: Callable[..., Any]) -> Base:
            base_module_path = catalog.from_string(
                    catalog.module_name_factory(object_)
            )
            module_paths = [base_module_path]
            root_module_name = base_module_path.parts[0]
            if root_module_name.startswith('_'):
                module_paths.append(
                        base_module_path.with_parent(
                                catalog.Path(root_module_name.lstrip('_'))
                        )
                )
            object_path = catalog.from_callable(object_)
            try:
                _, result = min(filter(itemgetter(1),
                                       [to_signature(module_path, object_path)
                                        for module_path in module_paths]),
                                key=itemgetter(0))
            except ValueError:
                return function(object_)
            else:
                assert (not hasattr(object_, '__self__')
                        or isinstance(object_, (types.MethodType,
                                                types.MethodWrapperType,
                                                types.BuiltinMethodType))
                        or object_ is super)
                return (result.bind(object_.__self__)
                        if (isinstance(object_, (types.MethodType,
                                                 types.MethodWrapperType,
                                                 types.BuiltinMethodType))
                            and not isinstance(object_.__self__,
                                               types.ModuleType))
                        else result)

        return wrapped


    from_callable = with_typeshed(from_callable)


    def from_class(object_: type) -> Base:
        try:
            return from_callable(object_)
        except ValueError as error:
            module_path = catalog.from_string(
                    catalog.module_name_factory(object_)
            )
            class_path = catalog.from_type(object_)
            _, method_signature = to_signature(module_path, class_path)
            if method_signature is None:
                try:
                    base, = object_.__bases__
                except ValueError:
                    pass
                else:
                    if (object_.__init__ is base.__init__
                            and object_.__new__ is base.__new__):
                        result = from_class(base)
                        is_metaclass = base is type and object_ is not type
                        if is_metaclass:
                            if isinstance(result, Overloaded):
                                # metaclasses do not inherit
                                # single-argument constructor of `type`
                                result = max(result.signatures,
                                             key=to_max_parameters_count)
                        return result
                raise error
            else:
                return slice_parameters(method_signature, slice(1, None))


    def to_signature(module_path: catalog.Path,
                     object_path: catalog.Path) -> Tuple[int, Optional[Base]]:
        try:
            depth, nodes = arboretum.to_functions_defs(module_path,
                                                       object_path)
        except KeyError:
            return -1, None
        else:
            assert len(nodes) > 0 or depth == -1
            return ((depth,
                     Overloaded(*[from_ast(node.args) for node in nodes]))
                    if nodes
                    else (-1, None))


    def from_ast(signature_ast: ast3.arguments) -> Base:
        parameters = filter(
                None,
                chain(to_positional_parameters(signature_ast),
                      (to_variadic_positional_parameter(signature_ast),),
                      to_keyword_parameters(signature_ast),
                      (to_variadic_keyword_parameter(signature_ast),)))
        return Plain(*parameters)


    def to_positional_parameters(signature_ast: ast3.arguments
                                 ) -> Iterable[Parameter]:
        # double-reversing since parameters with default arguments go last
        parameters_with_defaults_ast = zip_longest(
                reversed(signature_ast.args),
                signature_ast.defaults)
        parameters_with_defaults_ast = reversed(
                list(parameters_with_defaults_ast))
        parameter_factory = partial(to_parameter,
                                    kind=Parameter.Kind.POSITIONAL_ONLY)
        yield from starmap(parameter_factory, parameters_with_defaults_ast)


    def to_keyword_parameters(signature_ast: ast3.arguments
                              ) -> Iterable[Parameter]:
        parameters_with_defaults_ast = zip(signature_ast.kwonlyargs,
                                           signature_ast.kw_defaults)
        parameter_factory = partial(to_parameter,
                                    kind=Parameter.Kind.KEYWORD_ONLY)
        yield from starmap(parameter_factory, parameters_with_defaults_ast)


    def to_variadic_positional_parameter(signature_ast: ast3.arguments
                                         ) -> Optional[Parameter]:
        parameter_ast = signature_ast.vararg
        if parameter_ast is None:
            return None
        return Parameter(name=parameter_ast.arg,
                         kind=Parameter.Kind.VARIADIC_POSITIONAL,
                         has_default=False)


    def to_variadic_keyword_parameter(signature_ast: ast3.arguments
                                      ) -> Optional[Parameter]:
        parameter_ast = signature_ast.kwarg
        if parameter_ast is None:
            return None
        return Parameter(name=parameter_ast.arg,
                         kind=Parameter.Kind.VARIADIC_KEYWORD,
                         has_default=False)


    def to_parameter(parameter_ast: ast3.arg,
                     default_ast: Optional[ast3.expr],
                     *,
                     kind: Parameter.Kind) -> Parameter:
        return Parameter(name=parameter_ast.arg,
                         kind=kind,
                         has_default=default_ast is not None)

from_callable = [factory.register(cls, from_callable)
                 for cls in (BuiltinFunctionType,
                             BuiltinMethodType,
                             FunctionType,
                             MethodType,
                             MethodDescriptorType,
                             WrapperDescriptorType)][-1]
from_class = factory.register(type)(cached.map_(WeakKeyDictionary())
                                    (from_class))


@factory.register(partial)
def from_partial(object_: partial) -> Base:
    return factory(object_.func).bind(*object_.args, **object_.keywords)


@singledispatch
def slice_parameters(signature: Base,
                     slice_: slice) -> Base:
    raise TypeError(f'Unsupported signature type: {type(signature)!r}.')


@slice_parameters.register(Plain)
def _(signature: Plain, slice_: slice) -> Base:
    return Plain(*signature.parameters[slice_])


@slice_parameters.register(Overloaded)
def _(signature: Overloaded, slice_: slice) -> Base:
    return Overloaded(*map(partial(slice_parameters,
                                   slice_=slice_),
                           signature.signatures))


@singledispatch
def to_max_parameters_count(signature: Base) -> int:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@to_max_parameters_count.register(Plain)
def to_max_plain_parameters_count(signature: Plain) -> int:
    return len(signature.parameters)


@to_max_parameters_count.register(Overloaded)
def to_max_overloaded_parameters_count(signature: Overloaded) -> int:
    return max(map(to_max_parameters_count, signature.signatures))
