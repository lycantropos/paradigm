import enum
from abc import (ABC,
                 abstractmethod)
from collections import defaultdict
from itertools import (chain,
                       starmap)
from operator import (attrgetter,
                      methodcaller)
from typing import (Any,
                    Dict,
                    Iterable,
                    List,
                    Tuple)

from . import cached
from .hints import Domain


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
            value = 'argument' + 's' * (positionals_count != 1)
            raise TypeError('Takes {parameters_count} positional {value}, '
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
