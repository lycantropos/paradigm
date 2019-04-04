import enum
import inspect
import platform
from abc import (ABC,
                 abstractmethod)
from collections import defaultdict
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
                    Dict,
                    Iterable,
                    List,
                    Optional,
                    Tuple)
from weakref import WeakKeyDictionary

from . import cached
from .hints import (Domain,
                    Map,
                    MethodDescriptorType,
                    WrapperDescriptorType)


class Parameter:
    class Kind(enum.IntEnum):
        POSITIONAL_ONLY = 0
        POSITIONAL_OR_KEYWORD = 1
        VARIADIC_POSITIONAL = 2
        KEYWORD_ONLY = 3
        VARIADIC_KEYWORD = 4

        def __repr__(self) -> str:
            return type(self).__qualname__ + '.' + self.name

        def __str__(self) -> str:
            return self.name.lower().replace('_', ' ')

    positionals_kinds = {Kind.POSITIONAL_ONLY, Kind.POSITIONAL_OR_KEYWORD}
    keywords_kinds = {Kind.POSITIONAL_OR_KEYWORD, Kind.KEYWORD_ONLY}
    kinds_prefixes = defaultdict(str,
                                 {Kind.VARIADIC_POSITIONAL: '*',
                                  Kind.VARIADIC_KEYWORD: '**'})

    def __init__(self,
                 *,
                 name: str,
                 kind: Kind,
                 has_default: bool) -> None:
        self.name = name
        self.kind = kind
        self.has_default = has_default

    def __eq__(self, other: 'Parameter') -> bool:
        if not isinstance(other, Parameter):
            return NotImplemented
        return (self.name == other.name
                and self.kind == other.kind
                and self.has_default is other.has_default)

    def __hash__(self) -> int:
        return hash((self.name, self.kind, self.has_default))

    def __repr__(self) -> str:
        return (type(self).__qualname__
                + '('
                + ', '.join(starmap('{}={!r}'.format, vars(self).items()))
                + ')')

    def __str__(self) -> str:
        return ''.join([self.kinds_prefixes[self.kind],
                        self.name,
                        '=...' if self.has_default else ''])


def to_parameters_by_kind(parameters: Iterable[Parameter]
                          ) -> Dict[Parameter.Kind, List[Parameter]]:
    result = defaultdict(list)
    for parameter in parameters:
        result[parameter.kind].append(parameter)
    return result


def to_parameters_by_name(parameters: Iterable[Parameter]
                          ) -> Dict[str, Parameter]:
    return {parameter.name: parameter
            for parameter in parameters}


def all_parameters_has_defaults(parameters: Iterable[Parameter]) -> bool:
    return all(map(attrgetter('has_default'), parameters))


class Base(ABC):
    @abstractmethod
    def __repr__(self) -> str:
        pass

    @abstractmethod
    def __eq__(self, other: 'Base') -> bool:
        pass

    @abstractmethod
    def __hash__(self) -> int:
        pass

    @abstractmethod
    def all_set(self, *args: Domain, **kwargs: Domain) -> bool:
        pass

    @abstractmethod
    def expects(self, *args: Domain, **kwargs: Domain) -> bool:
        pass

    @abstractmethod
    def bind(self, *args: Domain, **kwargs: Domain) -> 'Base':
        pass


class Plain(Base):
    def __init__(self, *parameters: Parameter) -> None:
        self._parameters = parameters

    @property
    def parameters(self) -> Tuple[Parameter, ...]:
        return self._parameters

    def __eq__(self, other: Base) -> bool:
        if not isinstance(other, Base):
            return NotImplemented
        if not isinstance(other, Plain):
            return False
        return self._parameters == other._parameters

    def __hash__(self) -> int:
        return hash(self._parameters)

    def __repr__(self) -> str:
        return (type(self).__qualname__
                + '(' + ', '.join(map(repr, self._parameters)) + ')')

    def __str__(self) -> str:
        return '(' + ', '.join(map(str, self._parameters)) + ')'

    @cached.property_
    def parameters_by_kind(self) -> Dict[Parameter.Kind, List[Parameter]]:
        return to_parameters_by_kind(self._parameters)

    def all_set(self, *args: Domain, **kwargs: Domain) -> bool:
        positionals = (self.parameters_by_kind[Parameter.Kind.POSITIONAL_ONLY]
                       + self.parameters_by_kind[
                           Parameter.Kind.POSITIONAL_OR_KEYWORD])
        unexpected_positional_arguments_found = (
                not self.parameters_by_kind[Parameter.Kind.VARIADIC_POSITIONAL]
                and len(args) > len(positionals))
        if unexpected_positional_arguments_found:
            return False
        rest_positionals = positionals[len(args):]
        rest_positionals_by_kind = to_parameters_by_kind(rest_positionals)
        rest_keywords = (
                rest_positionals_by_kind[Parameter.Kind.POSITIONAL_OR_KEYWORD]
                + self.parameters_by_kind[Parameter.Kind.KEYWORD_ONLY])
        rest_keywords_by_name = to_parameters_by_name(rest_keywords)
        unexpected_keyword_arguments_found = (
                not self.parameters_by_kind[Parameter.Kind.VARIADIC_KEYWORD]
                and kwargs.keys() - rest_keywords_by_name.keys())
        if unexpected_keyword_arguments_found:
            return False
        rest_keywords_by_name = {
            name: parameter
            for name, parameter in rest_keywords_by_name.items()
            if name not in kwargs}
        rest_positionals_only = (
            rest_positionals_by_kind[Parameter.Kind.POSITIONAL_ONLY])
        rest_keywords = rest_keywords_by_name.values()
        return (all_parameters_has_defaults(rest_positionals_only)
                and all_parameters_has_defaults(rest_keywords))

    def expects(self, *args: Domain, **kwargs: Domain) -> bool:
        positionals = (self.parameters_by_kind[Parameter.Kind.POSITIONAL_ONLY]
                       + self.parameters_by_kind[
                           Parameter.Kind.POSITIONAL_OR_KEYWORD])
        unexpected_positional_arguments_found = (
                not self.parameters_by_kind[Parameter.Kind.VARIADIC_POSITIONAL]
                and len(args) > len(positionals))
        if unexpected_positional_arguments_found:
            return False
        rest_positionals = positionals[len(args):]
        rest_positionals_by_kind = to_parameters_by_kind(rest_positionals)
        rest_keywords = (
                rest_positionals_by_kind[Parameter.Kind.POSITIONAL_OR_KEYWORD]
                + self.parameters_by_kind[Parameter.Kind.KEYWORD_ONLY])
        rest_keywords_by_name = to_parameters_by_name(rest_keywords)
        unexpected_keyword_arguments_found = (
                not self.parameters_by_kind[Parameter.Kind.VARIADIC_KEYWORD]
                and kwargs.keys() - rest_keywords_by_name.keys())
        if unexpected_keyword_arguments_found:
            return False
        return True

    def bind(self, *args: Domain, **kwargs: Domain) -> Base:
        parameters = _bind_keywords(_bind_positionals(
                self.parameters,
                args, kwargs,
                has_variadic=bool(self.parameters_by_kind[
                                      Parameter.Kind.VARIADIC_POSITIONAL])),
                kwargs,
                has_variadic=bool(self.parameters_by_kind[
                                      Parameter.Kind.VARIADIC_KEYWORD]))
        return Plain(*parameters)


def _bind_positionals(parameters: Iterable[Parameter],
                      args: Tuple[Domain, ...],
                      kwargs: Dict[str, Domain],
                      *,
                      has_variadic: bool) -> Iterable[Parameter]:
    positionals_count = 0
    parameters = iter(parameters)
    for _ in args:
        for parameter in parameters:
            if parameter.kind in Parameter.positionals_kinds:
                if parameter.name in kwargs:
                    if parameter.kind in Parameter.keywords_kinds:
                        raise TypeError('Got multiple values '
                                        'for parameter "{parameter}".'
                                        .format(parameter=parameter.name))
                    else:
                        raise TypeError('Parameter "{parameter}" is {kind!s}, '
                                        'but was passed as a keyword.'
                                        .format(kind=parameter.kind,
                                                parameter=parameter.name))
                positionals_count += 1
                break
            yield parameter
        else:
            if has_variadic:
                return
            value = 'argument' + 's' * (positionals_count - 1)
            raise TypeError('Takes {parameters_count} positional {value} '
                            'but {arguments_count} were given.'
                            .format(parameters_count=positionals_count,
                                    value=value,
                                    arguments_count=len(args)))
    yield from parameters


def _bind_keywords(parameters: Iterable[Parameter],
                   kwargs: Dict[str, Any],
                   *,
                   has_variadic: bool) -> Iterable[Parameter]:
    kwargs_names = set(kwargs)
    for parameter in parameters:
        if parameter.name in kwargs_names:
            if parameter.kind not in Parameter.keywords_kinds:
                raise TypeError('Parameter "{parameter}" is {kind!s}, '
                                'but was passed as a keyword.'
                                .format(kind=parameter.kind,
                                        parameter=parameter.name))
            yield Parameter(name=parameter.name,
                            kind=parameter.kind,
                            has_default=True)
            kwargs_names.remove(parameter.name)
            continue
        yield parameter
    if kwargs_names and not has_variadic:
        raise TypeError('Got unexpected '
                        'keyword arguments "{arguments_names}".'
                        .format(arguments_names='", "'.join(kwargs_names)))


class Overloaded(Base):
    def __new__(cls, *signatures: Base) -> Base:
        if len(signatures) == 1:
            return signatures[0]
        return super().__new__(cls)

    def __init__(self, *signatures: Base) -> None:
        def flatten(signature: Base) -> Iterable[Base]:
            if isinstance(signature, type(self)):
                yield from signature.signatures
            else:
                yield signature

        self.signatures = tuple(chain.from_iterable(map(flatten, signatures)))

    def __eq__(self, other: Base) -> bool:
        if not isinstance(other, Base):
            return NotImplemented
        if not isinstance(other, Overloaded):
            return False
        return self.signatures == other.signatures

    def __hash__(self) -> int:
        return hash(self.signatures)

    def __repr__(self) -> str:
        return (type(self).__qualname__
                + '(' + ', '.join(map(repr, self.signatures)) + ')')

    def __str__(self) -> str:
        return ' or '.join(map(str, self.signatures))

    def all_set(self, *args: Domain, **kwargs: Domain) -> bool:
        return any(map(methodcaller(Base.all_set.__name__, *args, **kwargs),
                       self.signatures))

    def expects(self, *args: Domain, **kwargs: Domain) -> bool:
        return any(map(methodcaller(Base.expects.__name__, *args, **kwargs),
                       self.signatures))

    def bind(self, *args: Domain, **kwargs: Domain) -> Base:
        signatures = list(filter(methodcaller(Base.expects.__name__,
                                              *args, **kwargs),
                                 self.signatures))
        if not signatures:
            raise TypeError('No corresponding signature found.')
        signatures = map(methodcaller(Base.bind.__name__, *args, **kwargs),
                         signatures)
        return Overloaded(*signatures)


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
            method = None
            for cls, next_cls in zip(object_.__mro__, object_.__mro__[1:]):
                if cls.__new__ is not next_cls.__new__:
                    method = cls.__new__
                    break
                elif cls.__init__ is not next_cls.__init__:
                    method = cls.__init__
                    break
            if method is None:
                raise
            return slice_parameters(factory(method), slice(1, None))
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
                module_path = catalog.factory(catalog
                                              .module_name_factory(object_))
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
            module_path = catalog.factory(catalog.module_name_factory(object_))
            signature_factory = partial(to_signature,
                                        module_path=module_path)
            try:
                method_signature = next(filter(None, map(signature_factory,
                                                         method_paths)))
            except StopIteration:
                raise error
            else:
                return slice_parameters(method_signature, slice(1, None))


    to_method_path = methodcaller(catalog.Path.join.__name__,
                                  catalog.factory('__init__'))


    def to_signature(object_path: catalog.Path,
                     module_path: catalog.Path) -> Optional[Base]:
        try:
            object_nodes = arboretum.to_nodes(object_path, module_path)
        except KeyError:
            return None
        else:
            try:
                return Overloaded(*map(from_ast, map(attrgetter('args'),
                                                     object_nodes)))
            except AttributeError:
                return None


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
