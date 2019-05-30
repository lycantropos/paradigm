import enum
from abc import (ABC,
                 abstractmethod)
from collections import defaultdict
from itertools import (chain,
                       takewhile)
from operator import (attrgetter,
                      methodcaller)
from typing import (Any,
                    Dict,
                    Iterable,
                    List,
                    Tuple)

from memoir import cached
from reprit.base import generate_repr

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
        # performing validation inside of `__init__` instead of `__new__`,
        # because `pickle` does not support keyword only arguments in `__new__`
        if (kind not in (self.positionals_kinds | self.keywords_kinds)
                and has_default):
            raise ValueError('Variadic parameters '
                             'can\'t have default arguments.')
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

    __repr__ = generate_repr(__init__)

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
    POSITIONAL_ONLY_SEPARATOR = '/'
    KEYWORD_ONLY_SEPARATOR = '*'

    def __new__(cls, *parameters: Parameter) -> 'Plain':
        try:
            prior, *rest = parameters
        except ValueError:
            pass
        else:
            visited_names = {prior.name}
            visited_kinds = {prior.kind}
            for parameter in rest:
                name = parameter.name

                if name in visited_names:
                    raise ValueError('Parameters should have unique names, '
                                     'but found duplicate '
                                     'for parameter "{name}".'
                                     .format(name=name))

                kind = parameter.kind

                if kind < prior.kind:
                    raise ValueError('Invalid parameters order: '
                                     'parameter "{prior_name}" '
                                     'with kind "{prior_kind!s}" '
                                     'precedes parameter "{parameter}" '
                                     'with kind "{kind!s}".'
                                     .format(prior_name=prior.name,
                                             prior_kind=prior.kind,
                                             kind=kind,
                                             parameter=name))

                if kind in Parameter.positionals_kinds:
                    if not parameter.has_default:
                        if prior.has_default:
                            raise ValueError('Invalid parameters order: '
                                             'parameter "{name}" '
                                             'without default argument '
                                             'follows '
                                             'parameter "{prior_name}" '
                                             'with default argument.'
                                             .format(name=name,
                                                     prior_name=prior.name))
                elif kind not in Parameter.keywords_kinds:
                    if kind in visited_kinds:
                        raise ValueError('Variadic parameters '
                                         'should have unique kinds, '
                                         'but found duplicate '
                                         'for kind "{kind!s}".'
                                         .format(kind=kind))

                prior = parameter
                visited_names.add(name)
                visited_kinds.add(kind)
        return super().__new__(cls)

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

    __repr__ = generate_repr(__init__)

    def __str__(self) -> str:
        positionals_only = self.parameters_by_kind[
            Parameter.Kind.POSITIONAL_ONLY]
        parts = list(map(str, positionals_only))
        if positionals_only:
            parts.append(self.POSITIONAL_ONLY_SEPARATOR)
        parts.extend(map(str, self.parameters_by_kind[
            Parameter.Kind.POSITIONAL_OR_KEYWORD]))
        variadic_positionals = self.parameters_by_kind[
            Parameter.Kind.VARIADIC_POSITIONAL]
        parts.extend(map(str, variadic_positionals))
        keywords_only = self.parameters_by_kind[
            Parameter.Kind.KEYWORD_ONLY]
        if keywords_only and not variadic_positionals:
            parts.append(self.KEYWORD_ONLY_SEPARATOR)
        parts.extend(map(str, keywords_only))
        parts.extend(map(str, self.parameters_by_kind[
            Parameter.Kind.VARIADIC_KEYWORD]))
        return '(' + ', '.join(parts) + ')'

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
        return Plain(*_bind_keywords(_bind_positionals(
                self.parameters, args, kwargs,
                has_variadic=bool(self.parameters_by_kind[
                                      Parameter.Kind.VARIADIC_POSITIONAL])),
                kwargs,
                has_variadic=bool(self.parameters_by_kind[
                                      Parameter.Kind.VARIADIC_KEYWORD])))


def _bind_positionals(parameters: Tuple[Parameter, ...],
                      args: Tuple[Domain, ...],
                      kwargs: Dict[str, Domain],
                      *,
                      has_variadic: bool) -> Tuple[Parameter, ...]:
    def is_positional(parameter: Parameter) -> bool:
        return parameter.kind in Parameter.positionals_kinds

    positionals = tuple(takewhile(is_positional, parameters))
    if len(args) > len(positionals) and not has_variadic:
        value = 'argument' + 's' * (len(positionals) != 1)
        raise TypeError('Takes {parameters_count} positional {value}, '
                        'but {arguments_count} {verb} given.'
                        .format(parameters_count=len(positionals),
                                value=value,
                                arguments_count=len(args),
                                verb='was' if len(args) == 1 else 'were'))
    for positional in positionals[:len(args)]:
        if positional.name in kwargs:
            if positional.kind in Parameter.keywords_kinds:
                raise TypeError('Got multiple values '
                                'for parameter "{name}".'
                                .format(name=positional.name))
            else:
                raise TypeError('Parameter "{name}" is {kind!s}, '
                                'but was passed as a keyword.'
                                .format(name=positional.name,
                                        kind=positional.kind))
    return positionals[len(args):] + parameters[len(positionals):]


def _bind_keywords(parameters: Tuple[Parameter, ...],
                   kwargs: Dict[str, Any],
                   *,
                   has_variadic: bool) -> Tuple[Parameter, ...]:
    kwargs_names = set(kwargs)
    extra_kwargs_names = (kwargs_names -
                          {parameter.name
                           for parameter in parameters
                           if parameter.kind in Parameter.keywords_kinds})
    if extra_kwargs_names and not has_variadic:
        value = 'argument' + 's' * (len(extra_kwargs_names) != 1)
        raise TypeError('Got unexpected keyword {value} "{names}".'
                        .format(value=value,
                                names='", "'.join(extra_kwargs_names)))
    kwargs_names -= extra_kwargs_names
    if not kwargs_names:
        return parameters
    first_kwarg_index = next(index
                             for index, parameter in enumerate(parameters)
                             if parameter.name in kwargs_names)
    return (parameters[:first_kwarg_index]
            + tuple(Parameter(name=parameter.name,
                              kind=Parameter.Kind.KEYWORD_ONLY,
                              has_default=(parameter.has_default
                                           or parameter.name in kwargs_names))
                    if parameter.kind in Parameter.keywords_kinds
                    else parameter
                    for parameter in parameters[first_kwarg_index:]
                    if parameter.kind != Parameter.Kind.VARIADIC_POSITIONAL))


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

    __repr__ = generate_repr(__init__)

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
