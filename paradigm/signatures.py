import inspect
import platform
from functools import (partial,
                       singledispatch,
                       wraps)
from itertools import (chain,
                       starmap,
                       zip_longest)
from operator import (attrgetter,
                      methodcaller)
from types import (BuiltinFunctionType,
                   BuiltinMethodType,
                   FunctionType,
                   MethodType)
from typing import (Any,
                    Callable,
                    Iterable,
                    Optional)
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


from_class_cache = WeakKeyDictionary()
if platform.python_implementation() == 'PyPy':
    def from_class(object_: type) -> Base:
        try:
            return from_callable(object_)
        except ValueError:
            method = find_initializer_or_constructor(object_)
            if method is None:
                raise
            return slice_parameters(factory(method), slice(1, None))


    def find_initializer_or_constructor(class_: type) -> Callable:
        for cls, next_cls in zip(class_.__mro__, class_.__mro__[1:]):
            if cls.__init__ is not next_cls.__init__:
                return cls.__init__
            elif cls.__new__ is not next_cls.__new__:
                return cls.__new__
else:
    from typed_ast import ast3

    from . import (arboretum,
                   catalog)


    def with_typeshed(function: Map[Callable[..., Any], Base]
                      ) -> Map[Callable[..., Any], Base]:
        @wraps(function)
        def wrapped(object_: Callable[..., Any]) -> Base:
            try:
                return function(object_)
            except ValueError as error:
                object_paths = catalog.paths_factory(object_)
                module_path = catalog.from_string(
                        catalog.module_name_factory(object_))
                signature_factory = partial(to_signature,
                                            module_path=module_path)
                try:
                    return next(filter(None, map(signature_factory,
                                                 object_paths)))
                except StopIteration:
                    raise error

        return wrapped


    from_callable = with_typeshed(from_callable)

    from_class_cache[int] = Overloaded(
            Plain(Parameter(name='x',
                            kind=Parameter.Kind.POSITIONAL_ONLY,
                            has_default=True)),
            Plain(Parameter(name='x',
                            kind=Parameter.Kind.POSITIONAL_ONLY,
                            has_default=False),
                  Parameter(name='base',
                            kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
                            has_default=False)))


    def from_class(object_: type) -> Base:
        try:
            return from_callable(object_)
        except ValueError as error:
            method_paths = map(to_method_path, catalog.paths_factory(object_))
            module_path = catalog.from_string(
                    catalog.module_name_factory(object_))
            signature_factory = partial(to_signature,
                                        module_path=module_path)
            try:
                method_signature = next(filter(None, map(signature_factory,
                                                         method_paths)))
            except StopIteration:
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


    to_method_path = methodcaller(catalog.Path.join.__name__,
                                  catalog.from_string('__init__'))


    def to_signature(object_path: catalog.Path,
                     module_path: catalog.Path) -> Optional[Base]:
        try:
            nodes = arboretum.to_functions_defs(object_path, module_path)
        except KeyError:
            return None
        else:
            if not nodes:
                return None
            return Overloaded(*map(from_ast, map(attrgetter('args'), nodes)))


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
from_class = factory.register(type)(cached.map_(from_class_cache)(from_class))


@factory.register(partial)
def from_partial(object_: partial) -> Base:
    return factory(object_.func).bind(*object_.args, **object_.keywords)


@singledispatch
def slice_parameters(signature: Base,
                     slice_: slice) -> Base:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@slice_parameters.register(Plain)
def slice_plain_parameters(signature: Plain,
                           slice_: slice) -> Base:
    return Plain(*signature.parameters[slice_])


@slice_parameters.register(Overloaded)
def slice_overloaded_parameters(signature: Overloaded,
                                slice_: slice) -> Base:
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
