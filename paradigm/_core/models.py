import enum
from abc import (ABC,
                 abstractmethod)
from collections import defaultdict
from itertools import (chain,
                       takewhile)
from typing import (Any,
                    Dict,
                    Iterable,
                    List,
                    Sequence,
                    Tuple,
                    TypeVar)

from reprit.base import generate_repr


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

    def __init__(self,
                 *,
                 name: str,
                 kind: Kind,
                 has_default: bool) -> None:
        # performing validation inside of `__init__` instead of `__new__`,
        # because `pickle` does not support keyword only arguments in `__new__`
        if ((kind is self.Kind.VARIADIC_POSITIONAL
             or kind is self.Kind.VARIADIC_KEYWORD)
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
                and self.kind is other.kind
                and self.has_default is other.has_default)

    def __hash__(self) -> int:
        return hash((self.name, self.kind, self.has_default))

    __repr__ = generate_repr(__init__)

    def __str__(self) -> str:
        return ''.join(['*'
                        if self.kind is self.Kind.VARIADIC_POSITIONAL
                        else ('**'
                              if self.kind is self.Kind.VARIADIC_KEYWORD
                              else ''),
                        self.name,
                        '=...' if self.has_default else ''])


def to_parameters_by_kind(
        parameters: Iterable[Parameter]
) -> Dict[Parameter.Kind, List[Parameter]]:
    result = defaultdict(list)
    for parameter in parameters:
        result[parameter.kind].append(parameter)
    return result


def to_parameters_by_name(
        parameters: Iterable[Parameter]
) -> Dict[str, Parameter]:
    return {parameter.name: parameter for parameter in parameters}


def all_parameters_has_defaults(
        parameters: Iterable[Parameter]
) -> bool:
    return all(parameter.has_default for parameter in parameters)


_Self = TypeVar('_Self')
_Arg = TypeVar('_Arg')
_KwArg = TypeVar('_KwArg')


class _Signature(ABC):
    __slots__ = ()

    @abstractmethod
    def all_set(self, *args: _Arg, **kwargs: _KwArg) -> bool:
        """
        Checks if the signature has no unspecified parameters left
        with given arguments.
        """

    @abstractmethod
    def expects(self, *args: _Arg, **kwargs: _KwArg) -> bool:
        """Checks if the signature accepts given arguments."""

    @abstractmethod
    def bind(self: _Self, *args: _Arg, **kwargs: _KwArg) -> _Self:
        """Binds given arguments to the signature."""


class PlainSignature(_Signature):
    POSITIONAL_ONLY_SEPARATOR = '/'
    KEYWORD_ONLY_SEPARATOR = '*'

    @property
    def parameters(self) -> Sequence[Parameter]:
        return self._parameters

    def all_set(self, *args: _Arg, **kwargs: _KwArg) -> bool:
        parameters_by_kind = to_parameters_by_kind(self._parameters)
        positionals = (
                parameters_by_kind[Parameter.Kind.POSITIONAL_ONLY]
                + parameters_by_kind[Parameter.Kind.POSITIONAL_OR_KEYWORD]
        )
        unexpected_positional_arguments_found = (
                not parameters_by_kind[Parameter.Kind.VARIADIC_POSITIONAL]
                and len(args) > len(positionals)
        )
        if unexpected_positional_arguments_found:
            return False
        rest_positionals = positionals[len(args):]
        rest_positionals_by_kind = to_parameters_by_kind(rest_positionals)
        rest_keywords = (
                rest_positionals_by_kind[Parameter.Kind.POSITIONAL_OR_KEYWORD]
                + parameters_by_kind[Parameter.Kind.KEYWORD_ONLY]
        )
        rest_keywords_by_name = to_parameters_by_name(rest_keywords)
        unexpected_keyword_arguments_found = (
                not parameters_by_kind[Parameter.Kind.VARIADIC_KEYWORD]
                and kwargs.keys() - rest_keywords_by_name.keys()
        )
        if unexpected_keyword_arguments_found:
            return False
        rest_keywords_by_name = {
            name: parameter
            for name, parameter in rest_keywords_by_name.items()
            if name not in kwargs
        }
        rest_positionals_only = rest_positionals_by_kind[
            Parameter.Kind.POSITIONAL_ONLY
        ]
        rest_keywords = rest_keywords_by_name.values()
        return (all_parameters_has_defaults(rest_positionals_only)
                and all_parameters_has_defaults(rest_keywords))

    def expects(self, *args: _Arg, **kwargs: _KwArg) -> bool:
        parameters_by_kind = to_parameters_by_kind(self._parameters)
        positionals = (parameters_by_kind[Parameter.Kind.POSITIONAL_ONLY]
                       + parameters_by_kind[
                           Parameter.Kind.POSITIONAL_OR_KEYWORD
                       ])
        unexpected_positional_arguments_found = (
                not parameters_by_kind[Parameter.Kind.VARIADIC_POSITIONAL]
                and len(args) > len(positionals)
        )
        if unexpected_positional_arguments_found:
            return False
        rest_positionals = positionals[len(args):]
        rest_positionals_by_kind = to_parameters_by_kind(rest_positionals)
        rest_keywords = (
                rest_positionals_by_kind[Parameter.Kind.POSITIONAL_OR_KEYWORD]
                + parameters_by_kind[Parameter.Kind.KEYWORD_ONLY]
        )
        rest_keywords_by_name = to_parameters_by_name(rest_keywords)
        unexpected_keyword_arguments_found = (
                not parameters_by_kind[Parameter.Kind.VARIADIC_KEYWORD]
                and kwargs.keys() - rest_keywords_by_name.keys()
        )
        return not unexpected_keyword_arguments_found

    def bind(self, *args: _Arg, **kwargs: _KwArg) -> 'PlainSignature':
        parameters_by_kind = to_parameters_by_kind(self._parameters)
        return PlainSignature(*_bind_keywords(
                _bind_positionals(
                        self._parameters, args, kwargs,
                        has_variadic=bool(
                                parameters_by_kind[
                                    Parameter.Kind.VARIADIC_POSITIONAL
                                ]
                        )
                ),
                kwargs,
                has_variadic=bool(parameters_by_kind[
                                      Parameter.Kind.VARIADIC_KEYWORD
                                  ])
        ))

    __slots__ = '_parameters',

    def __new__(cls, *parameters: Parameter) -> 'PlainSignature':
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
                                     f'for parameter "{name}".')
                kind = parameter.kind
                if kind < prior.kind:
                    raise ValueError('Invalid parameters order: '
                                     f'parameter "{prior.name}" '
                                     f'with kind "{prior.kind!s}" '
                                     f'precedes parameter "{name}" '
                                     f'with kind "{kind!s}".')
                if (kind is Parameter.Kind.POSITIONAL_OR_KEYWORD
                        or kind is Parameter.Kind.POSITIONAL_ONLY):
                    if not parameter.has_default:
                        if prior.has_default:
                            raise ValueError('Invalid parameters order: '
                                             f'parameter "{name}" '
                                             'without default argument '
                                             'follows '
                                             f'parameter "{prior.name}" '
                                             'with default argument.')
                elif (kind is not Parameter.Kind.POSITIONAL_OR_KEYWORD
                      and kind is not Parameter.Kind.KEYWORD_ONLY):
                    if kind in visited_kinds:
                        raise ValueError('Variadic parameters '
                                         'should have unique kinds, '
                                         'but found duplicate '
                                         f'for kind "{kind!s}".')
                prior = parameter
                visited_names.add(name)
                visited_kinds.add(kind)
        return super().__new__(cls)

    def __init__(self, *parameters: Parameter) -> None:
        self._parameters = parameters

    def __eq__(self, other: _Signature) -> bool:
        return (isinstance(other, PlainSignature)
                and self._parameters == other._parameters
                if isinstance(other, _Signature)
                else NotImplemented)

    def __hash__(self) -> int:
        return hash(self._parameters)

    __repr__ = generate_repr(__init__)

    def __str__(self) -> str:
        parameters_by_kind = to_parameters_by_kind(self._parameters)
        positionals_only = parameters_by_kind[Parameter.Kind.POSITIONAL_ONLY]
        parts = list(map(str, positionals_only))
        if positionals_only:
            parts.append(self.POSITIONAL_ONLY_SEPARATOR)
        parts.extend(map(str,
                         parameters_by_kind[
                             Parameter.Kind.POSITIONAL_OR_KEYWORD
                         ]))
        variadic_positionals = parameters_by_kind[
            Parameter.Kind.VARIADIC_POSITIONAL
        ]
        parts.extend(map(str, variadic_positionals))
        keywords_only = parameters_by_kind[Parameter.Kind.KEYWORD_ONLY]
        if keywords_only and not variadic_positionals:
            parts.append(self.KEYWORD_ONLY_SEPARATOR)
        parts.extend(map(str, keywords_only))
        parts.extend(map(str,
                         parameters_by_kind[Parameter.Kind.VARIADIC_KEYWORD]))
        return '(' + ', '.join(parts) + ')'


class OverloadedSignature(_Signature):
    @property
    def signatures(self) -> Sequence[_Signature]:
        return self._signatures

    def all_set(self, *args: _Arg, **kwargs: _KwArg) -> bool:
        return any(signature.all_set(*args, **kwargs)
                   for signature in self._signatures)

    def expects(self, *args: _Arg, **kwargs: _KwArg) -> bool:
        return any(signature.expects(*args, **kwargs)
                   for signature in self._signatures)

    def bind(self, *args: _Arg, **kwargs: _KwArg) -> 'OverloadedSignature':
        signatures = [signature
                      for signature in self._signatures
                      if signature.expects(*args, **kwargs)]
        if not signatures:
            raise TypeError('No corresponding signature found.')
        return OverloadedSignature(*[signature.bind(*args, **kwargs)
                                     for signature in signatures])

    __slots__ = '_signatures',

    def __new__(cls, *signatures: _Signature) -> _Signature:
        return (signatures[0]
                if len(signatures) == 1
                else super().__new__(cls))

    def __init__(self, *signatures: _Signature) -> None:
        def flatten(signature: _Signature) -> Sequence[_Signature]:
            return (signature._signatures
                    if isinstance(signature, OverloadedSignature)
                    else [signature])

        self._signatures = tuple(chain.from_iterable(map(flatten, signatures)))

    def __eq__(self, other: Any) -> Any:
        return ((isinstance(other, OverloadedSignature)
                 and self._signatures == other._signatures)
                if isinstance(other, _Signature)
                else NotImplemented)

    def __hash__(self) -> int:
        return hash(self._signatures)

    __repr__ = generate_repr(__init__)

    def __str__(self) -> str:
        return ' or '.join(map(str, self._signatures))


def _bind_positionals(parameters: Tuple[Parameter, ...],
                      args: Tuple[_Arg, ...],
                      kwargs: Dict[str, _KwArg],
                      *,
                      has_variadic: bool) -> Tuple[Parameter, ...]:
    def is_positionable(parameter: Parameter) -> bool:
        return (parameter.kind is Parameter.Kind.POSITIONAL_OR_KEYWORD
                or parameter.kind is Parameter.Kind.POSITIONAL_ONLY)

    positionals = tuple(takewhile(is_positionable, parameters))
    if len(args) > len(positionals) and not has_variadic:
        value = 'argument' + 's' * (len(positionals) != 1)
        raise TypeError(f'Takes {len(positionals)} positional {value}, '
                        f'but {len(args)} '
                        f'{"was" if len(args) == 1 else "were"} given.')
    for positional in positionals[:len(args)]:
        if positional.name in kwargs:
            kind = positional.kind
            if (kind is Parameter.Kind.POSITIONAL_OR_KEYWORD
                    or kind is Parameter.Kind.KEYWORD_ONLY):
                raise TypeError('Got multiple values '
                                f'for parameter "{positional.name}".')
            else:
                raise TypeError(f'Parameter "{positional.name}" is {kind!s}, '
                                'but was passed as a keyword.')
    return positionals[len(args):] + parameters[len(positionals):]


def _bind_keywords(parameters: Tuple[Parameter, ...],
                   kwargs: Dict[str, Any],
                   *,
                   has_variadic: bool) -> Tuple[Parameter, ...]:
    kwargs_names = set(kwargs)
    extra_kwargs_names = (
            kwargs_names
            - {parameter.name
               for parameter in parameters
               if (parameter.kind is Parameter.Kind.POSITIONAL_OR_KEYWORD
                   or parameter.kind is Parameter.Kind.KEYWORD_ONLY)}
    )
    if extra_kwargs_names and not has_variadic:
        value = 'argument' + 's' * (len(extra_kwargs_names) != 1)
        names = '", "'.join(extra_kwargs_names)
        raise TypeError(f'Got unexpected keyword {value}: "{names}".')
    kwargs_names -= extra_kwargs_names
    if not kwargs_names:
        return parameters
    first_kwarg_index = next(index
                             for index, parameter in enumerate(parameters)
                             if parameter.name in kwargs_names)
    return (parameters[:first_kwarg_index]
            + tuple(
                    Parameter(
                            name=parameter.name,
                            kind=Parameter.Kind.KEYWORD_ONLY,
                            has_default=(parameter.has_default
                                         or parameter.name in kwargs_names)
                    )
                    if (parameter.kind is Parameter.Kind.POSITIONAL_OR_KEYWORD
                        or parameter.kind is Parameter.Kind.KEYWORD_ONLY)
                    else parameter
                    for parameter in parameters[first_kwarg_index:]
                    if (parameter.kind
                        is not Parameter.Kind.VARIADIC_POSITIONAL)
            ))
