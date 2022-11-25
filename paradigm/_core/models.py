import enum
import typing as t
from abc import (ABC,
                 abstractmethod)
from collections import defaultdict
from itertools import (chain,
                       takewhile)

from reprit.base import generate_repr
from typing_extensions import final

from . import annotated

_MIN_SUB_SIGNATURES_COUNT = 2


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

    @property
    def annotation(self) -> t.Any:
        return self._annotation

    @property
    def has_default(self) -> bool:
        return self._has_default

    @property
    def kind(self) -> Kind:
        return self._kind

    @property
    def name(self) -> str:
        return self._name

    __slots__ = '_annotation', '_has_default', '_kind', '_name'

    _annotation: t.Any
    _has_default: bool
    _kind: Kind
    _name: str

    def __new__(cls,
                *,
                annotation: t.Any,
                has_default: bool,
                kind: Kind,
                name: str) -> 'Parameter':
        # performing validation inside of `__init__` instead of `__new__`,
        # because `pickle` does not support keyword only arguments in `__new__`
        if ((kind is cls.Kind.VARIADIC_POSITIONAL
             or kind is cls.Kind.VARIADIC_KEYWORD)
                and has_default):
            raise ValueError('Variadic parameters '
                             'can\'t have default arguments.')
        self = super().__new__(cls)
        self._annotation, self._has_default, self._kind, self._name = (
            annotation, has_default, kind, name
        )
        return self

    @t.overload
    def __eq__(self, other: 'Parameter') -> bool:
        ...

    @t.overload
    def __eq__(self, other: t.Any) -> t.Any:
        ...

    def __eq__(self, other):
        return ((self.name == other.name
                 and self.kind is other.kind
                 and self.has_default is other.has_default
                 and annotated.are_equal(self.annotation, other.annotation))
                if isinstance(other, Parameter)
                else NotImplemented)

    def __getnewargs_ex__(self) -> t.Tuple[t.Tuple[()], t.Dict[str, t.Any]]:
        return (), {'annotation': self._annotation,
                    'has_default': self._has_default,
                    'kind': self._kind,
                    'name': self._name}

    def __hash__(self) -> int:
        return hash((self._annotation, self._has_default, self._kind,
                     self._name))

    __repr__ = generate_repr(__new__,
                             argument_serializer=annotated.to_repr)

    def __str__(self) -> str:
        return ''.join(['*'
                        if self.kind is self.Kind.VARIADIC_POSITIONAL
                        else ('**'
                              if self.kind is self.Kind.VARIADIC_KEYWORD
                              else ''),
                        self.name,
                        f': {annotated.to_repr(self.annotation)}',
                        ' = ...' if self.has_default else ''])


def to_parameters_by_kind(
        parameters: t.Iterable[Parameter]
) -> t.Dict[Parameter.Kind, t.List[Parameter]]:
    result = defaultdict(list)
    for parameter in parameters:
        result[parameter.kind].append(parameter)
    return result


def to_parameters_by_name(
        parameters: t.Iterable[Parameter]
) -> t.Dict[str, Parameter]:
    return {parameter.name: parameter for parameter in parameters}


def all_parameters_has_defaults(
        parameters: t.Iterable[Parameter]
) -> bool:
    return all(parameter.has_default for parameter in parameters)


_Self = t.TypeVar('_Self')
_Arg = t.TypeVar('_Arg')
_KwArg = t.TypeVar('_KwArg')


class BaseSignature(ABC):
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


@final
class PlainSignature(BaseSignature):
    POSITIONAL_ONLY_SEPARATOR = '/'
    KEYWORD_ONLY_SEPARATOR = '*'

    @property
    def parameters(self) -> t.Sequence[Parameter]:
        return self._parameters

    @property
    def returns(self) -> t.Any:
        return self._returns

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
        rest_keywords: t.Iterable[Parameter] = (
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
        return PlainSignature(
                *_bind_keywords(
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
                ),
                returns=self._returns
        )

    _parameters: t.Tuple[Parameter, ...]
    _returns: t.Any

    __slots__ = '_parameters', '_returns'

    def __new__(cls,
                *parameters: Parameter,
                returns: t.Any) -> 'PlainSignature':
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
                    raise ValueError('Parameters should have unique paths, '
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
        self = super().__new__(cls)
        self._parameters, self._returns = parameters, returns
        return self

    @t.overload
    def __eq__(self, other: BaseSignature) -> bool:
        ...

    @t.overload
    def __eq__(self, other: t.Any) -> t.Any:
        ...

    def __eq__(self, other):
        return ((isinstance(other, PlainSignature)
                 and self._parameters == other._parameters
                 and annotated.are_equal(self._returns, other._returns))
                if isinstance(other, BaseSignature)
                else NotImplemented)

    def __getnewargs_ex__(self) -> t.Tuple[t.Tuple[Parameter, ...],
                                           t.Dict[str, t.Any]]:
        return self._parameters, {'returns': self._returns}

    def __hash__(self) -> int:
        return hash((self._parameters, self.returns))

    __repr__ = generate_repr(__new__,
                             argument_serializer=annotated.to_repr)

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
        return ('(' + ', '.join(parts) + ') -> '
                + annotated.to_repr(self.returns))


Signature = t.Union['OverloadedSignature', PlainSignature]


@final
class OverloadedSignature(BaseSignature):
    @property
    def signatures(self) -> t.Sequence[Signature]:
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

    _signatures: t.Tuple[Signature, ...]

    def __new__(cls, *signatures: Signature) -> 'OverloadedSignature':
        if len(signatures) < _MIN_SUB_SIGNATURES_COUNT:
            raise ValueError('Overloaded signature can be constructed '
                             f'only from at least {_MIN_SUB_SIGNATURES_COUNT} '
                             f'signatures.')

        def flatten(signature: Signature) -> t.Sequence[Signature]:
            return (signature._signatures
                    if isinstance(signature, OverloadedSignature)
                    else [signature])

        self = super().__new__(cls)
        self._signatures = tuple(chain.from_iterable(map(flatten, signatures)))
        return self

    def __eq__(self, other: t.Any) -> t.Any:
        return ((isinstance(other, OverloadedSignature)
                 and self._signatures == other._signatures)
                if isinstance(other, BaseSignature)
                else NotImplemented)

    def __getnewargs__(self) -> t.Tuple[Signature, ...]:
        return self._signatures

    def __hash__(self) -> int:
        return hash(self._signatures)

    __repr__ = generate_repr(__new__)

    def __str__(self) -> str:
        return ' | '.join(map(str, self._signatures))


def from_signatures(*signatures: Signature) -> Signature:
    return (signatures[0]
            if len(signatures) == 1
            else OverloadedSignature(*signatures))


def _bind_positionals(parameters: t.Tuple[Parameter, ...],
                      args: t.Tuple[_Arg, ...],
                      kwargs: t.Dict[str, _KwArg],
                      *,
                      has_variadic: bool) -> t.Tuple[Parameter, ...]:
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


def _bind_keywords(parameters: t.Tuple[Parameter, ...],
                   kwargs: t.Dict[str, t.Any],
                   *,
                   has_variadic: bool) -> t.Tuple[Parameter, ...]:
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
                            annotation=parameter.annotation,
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
