import enum
import typing as t
from abc import (ABC,
                 abstractmethod)
from collections import defaultdict
from itertools import (chain,
                       takewhile)

from typing_extensions import (Literal,
                               TypeGuard,
                               final)

from . import annotated

_MIN_SUB_SIGNATURES_COUNT = 2


@final
class _Default(enum.Enum):
    NONE = enum.auto()


_NONE = _Default.NONE


@final
class ParameterKind(enum.IntEnum):
    POSITIONAL_ONLY = 0
    POSITIONAL_OR_KEYWORD = 1
    VARIADIC_POSITIONAL = 2
    KEYWORD_ONLY = 3
    VARIADIC_KEYWORD = 4

    def __repr__(self) -> str:
        return type(self).__qualname__ + '.' + self.name

    def __str__(self) -> str:
        return self.name.lower().replace('_', ' ')


class BaseParameter(ABC):
    @property
    @abstractmethod
    def annotation(self) -> t.Any:
        """Returns annotation of the parameter."""

    @property
    @abstractmethod
    def kind(self) -> ParameterKind:
        """Returns kind of the parameter."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns name of the parameter."""


@final
class RequiredParameter(BaseParameter):
    @property
    def annotation(self) -> t.Any:
        return self._annotation

    @property
    def kind(self) -> ParameterKind:
        return self._kind

    @property
    def name(self) -> str:
        return self._name

    __slots__ = '_annotation', '_kind', '_name'

    _annotation: t.Any
    _kind: ParameterKind
    _name: str

    def __new__(cls,
                *,
                annotation: t.Any,
                kind: Literal[ParameterKind.POSITIONAL_ONLY,
                              ParameterKind.POSITIONAL_OR_KEYWORD,
                              ParameterKind.KEYWORD_ONLY],
                name: str) -> 'RequiredParameter':
        if (kind is ParameterKind.VARIADIC_POSITIONAL
                or kind is ParameterKind.VARIADIC_KEYWORD):
            raise ValueError('Variadic parameters can\'t be required.')
        self = super().__new__(cls)
        self._annotation, self._kind, self._name = annotation, kind, name
        return self

    @t.overload
    def __eq__(self, other: BaseParameter) -> bool:
        ...

    @t.overload
    def __eq__(self, other: t.Any) -> t.Any:
        ...

    def __eq__(self, other):
        return ((type(self) is type(other)
                 and self.name == other.name
                 and self.kind is other.kind
                 and annotated.are_equal(self.annotation, other.annotation))
                if isinstance(other, BaseParameter)
                else NotImplemented)

    def __getnewargs_ex__(self) -> t.Tuple[t.Tuple[()], t.Dict[str, t.Any]]:
        return (), {'annotation': self._annotation,
                    'kind': self._kind,
                    'name': self._name}

    def __hash__(self) -> int:
        return hash((self._annotation, self._kind, self._name))

    def __repr__(self) -> str:
        return (f'{type(self).__qualname__}('
                f'annotation={annotated.to_repr(self.annotation)}, '
                f'kind={repr(self.kind)}, '
                f'name={repr(self.name)}'
                f')')

    def __str__(self) -> str:
        return f'{self.name}: {annotated.to_repr(self.annotation)}'


@final
class OptionalParameter(BaseParameter):
    @property
    def annotation(self) -> t.Any:
        return self._annotation

    @property
    def default(self) -> t.Any:
        return self._default

    @property
    def has_default(self) -> bool:
        return self._has_default

    @property
    def kind(self) -> ParameterKind:
        return self._kind

    @property
    def name(self) -> str:
        return self._name

    __slots__ = '_annotation', '_default', '_has_default', '_kind', '_name'

    _annotation: t.Any
    _default: t.Union[_Default, t.Any]
    _has_default: bool
    _kind: ParameterKind
    _name: str

    def __new__(cls,
                *,
                annotation: t.Any,
                default: t.Union[_Default, t.Any] = _NONE,
                kind: ParameterKind,
                name: str) -> 'OptionalParameter':
        has_default = default is not _NONE
        if ((kind is ParameterKind.VARIADIC_POSITIONAL
             or kind is ParameterKind.VARIADIC_KEYWORD)
                and has_default):
            raise ValueError('Variadic parameters '
                             'can\'t have default arguments.')
        self = super().__new__(cls)
        (
            self._annotation, self._has_default, self._kind, self._name
        ) = annotation, has_default, kind, name
        if has_default:
            self._default = default
        return self

    @t.overload
    def __eq__(self, other: BaseParameter) -> bool:
        ...

    @t.overload
    def __eq__(self, other: t.Any) -> t.Any:
        ...

    def __eq__(self, other):
        return ((type(self) is type(other)
                 and self.name == other.name
                 and self.kind is other.kind
                 and self.has_default is other.has_default
                 and (not self.has_default
                      or annotated.are_equal(self.default, other.default))
                 and annotated.are_equal(self.annotation, other.annotation))
                if isinstance(other, BaseParameter)
                else NotImplemented)

    def __getnewargs_ex__(self) -> t.Tuple[t.Tuple[()], t.Dict[str, t.Any]]:
        return (), {'annotation': self._annotation,
                    **({'default': self._default}
                       if self._has_default
                       else {}),
                    'kind': self._kind,
                    'name': self._name}

    def __hash__(self) -> int:
        return hash((self._annotation,
                     *((self._default,) if self._has_default else ()),
                     self._kind, self._name))

    def __repr__(self) -> str:
        return (f'{type(self).__qualname__}('
                f'annotation={annotated.to_repr(self.annotation)}, '
                + (f'default={annotated.to_repr(self.default)}, '
                   if self.has_default
                   else '')
                + f'kind={repr(self.kind)}, '
                  f'name={repr(self.name)}'
                  f')')

    def __str__(self) -> str:
        return ''.join([('*'
                         if self.kind is ParameterKind.VARIADIC_POSITIONAL
                         else ('**'
                               if self.kind is ParameterKind.VARIADIC_KEYWORD
                               else '')),
                        self.name,
                        f': {annotated.to_repr(self.annotation)}',
                        (f' = {annotated.to_repr(self.default)}'
                         if self.has_default
                         else '')])


Parameter = t.Union[OptionalParameter, RequiredParameter]


def to_parameters_by_kind(
        parameters: t.Iterable[Parameter]
) -> t.Dict[ParameterKind, t.List[Parameter]]:
    result = defaultdict(list)
    for parameter in parameters:
        result[parameter.kind].append(parameter)
    return result


def to_parameters_by_name(
        parameters: t.Iterable[Parameter]
) -> t.Dict[str, Parameter]:
    return {parameter.name: parameter for parameter in parameters}


def all_parameters_are_optional(
        parameters: t.Iterable[Parameter]
) -> TypeGuard[t.Iterable[OptionalParameter]]:
    return all(isinstance(parameter, OptionalParameter)
               for parameter in parameters)


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
    def bind(self, *args: _Arg, **kwargs: _KwArg) -> 'BaseSignature':
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
                parameters_by_kind[ParameterKind.POSITIONAL_ONLY]
                + parameters_by_kind[ParameterKind.POSITIONAL_OR_KEYWORD]
        )
        unexpected_positional_arguments_found = (
                not parameters_by_kind[ParameterKind.VARIADIC_POSITIONAL]
                and len(args) > len(positionals)
        )
        if unexpected_positional_arguments_found:
            return False
        rest_positionals = positionals[len(args):]
        rest_positionals_by_kind = to_parameters_by_kind(rest_positionals)
        rest_keywords: t.Iterable[Parameter] = (
                rest_positionals_by_kind[ParameterKind.POSITIONAL_OR_KEYWORD]
                + parameters_by_kind[ParameterKind.KEYWORD_ONLY]
        )
        rest_keywords_by_name = to_parameters_by_name(rest_keywords)
        unexpected_keyword_arguments_found = (
                not parameters_by_kind[ParameterKind.VARIADIC_KEYWORD]
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
            ParameterKind.POSITIONAL_ONLY
        ]
        rest_keywords = rest_keywords_by_name.values()
        return (all_parameters_are_optional(rest_positionals_only)
                and all_parameters_are_optional(rest_keywords))

    def expects(self, *args: _Arg, **kwargs: _KwArg) -> bool:
        parameters_by_kind = to_parameters_by_kind(self._parameters)
        positionals = (parameters_by_kind[ParameterKind.POSITIONAL_ONLY]
                       + parameters_by_kind[
                           ParameterKind.POSITIONAL_OR_KEYWORD
                       ])
        unexpected_positional_arguments_found = (
                not parameters_by_kind[ParameterKind.VARIADIC_POSITIONAL]
                and len(args) > len(positionals)
        )
        if unexpected_positional_arguments_found:
            return False
        rest_positionals = positionals[len(args):]
        rest_positionals_by_kind = to_parameters_by_kind(rest_positionals)
        rest_keywords = (
                rest_positionals_by_kind[ParameterKind.POSITIONAL_OR_KEYWORD]
                + parameters_by_kind[ParameterKind.KEYWORD_ONLY]
        )
        rest_keywords_by_name = to_parameters_by_name(rest_keywords)
        unexpected_keyword_arguments_found = (
                not parameters_by_kind[ParameterKind.VARIADIC_KEYWORD]
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
                                            ParameterKind.VARIADIC_POSITIONAL
                                        ]
                                )
                        ),
                        kwargs,
                        has_variadic=bool(parameters_by_kind[
                                              ParameterKind.VARIADIC_KEYWORD
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
                if (kind is ParameterKind.POSITIONAL_OR_KEYWORD
                        or kind is ParameterKind.POSITIONAL_ONLY):
                    if (isinstance(parameter, RequiredParameter)
                            and isinstance(prior, OptionalParameter)):
                        raise ValueError(
                                'Invalid parameters order: '
                                f'required positional parameter "{name}" '
                                'follows '
                                f'optional parameter "{prior.name}".'
                        )
                elif (kind is ParameterKind.VARIADIC_POSITIONAL
                      or kind is ParameterKind.VARIADIC_KEYWORD):
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

    def __repr__(self) -> str:
        return (f'{type(self).__qualname__}('
                + (f'{", ".join(map(repr, self._parameters))}, '
                   if self._parameters
                   else '')
                + f'returns={annotated.to_repr(self._returns)})')

    def __str__(self) -> str:
        parameters_by_kind = to_parameters_by_kind(self._parameters)
        positionals_only = parameters_by_kind[ParameterKind.POSITIONAL_ONLY]
        parts = list(map(str, positionals_only))
        if positionals_only:
            parts.append(self.POSITIONAL_ONLY_SEPARATOR)
        parts.extend(map(str,
                         parameters_by_kind[
                             ParameterKind.POSITIONAL_OR_KEYWORD
                         ]))
        variadic_positionals = parameters_by_kind[
            ParameterKind.VARIADIC_POSITIONAL
        ]
        parts.extend(map(str, variadic_positionals))
        keywords_only = parameters_by_kind[ParameterKind.KEYWORD_ONLY]
        if keywords_only and not variadic_positionals:
            parts.append(self.KEYWORD_ONLY_SEPARATOR)
        parts.extend(map(str, keywords_only))
        parts.extend(map(str,
                         parameters_by_kind[ParameterKind.VARIADIC_KEYWORD]))
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

    def bind(self, *args: _Arg, **kwargs: _KwArg) -> Signature:
        signatures = [signature.bind(*args, **kwargs)
                      for signature in self._signatures
                      if signature.expects(*args, **kwargs)]
        if not signatures:
            raise TypeError('No corresponding signature found.')
        return from_signatures(*signatures)

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

    def __repr__(self) -> str:
        return (f'{type(self).__qualname__}'
                f'({", ".join(map(repr, self._signatures))})')

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
        return (parameter.kind is ParameterKind.POSITIONAL_OR_KEYWORD
                or parameter.kind is ParameterKind.POSITIONAL_ONLY)

    positionals = tuple(takewhile(is_positionable, parameters))
    if len(args) > len(positionals) and not has_variadic:
        value = 'argument' + 's' * (len(positionals) != 1)
        raise TypeError(f'Takes {len(positionals)} positional {value}, '
                        f'but {len(args)} '
                        f'{"was" if len(args) == 1 else "were"} given.')
    for positional in positionals[:len(args)]:
        if positional.name in kwargs:
            kind = positional.kind
            if (kind is ParameterKind.POSITIONAL_OR_KEYWORD
                    or kind is ParameterKind.KEYWORD_ONLY):
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
               if (parameter.kind is ParameterKind.POSITIONAL_OR_KEYWORD
                   or parameter.kind is ParameterKind.KEYWORD_ONLY)}
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
                    (
                        OptionalParameter(
                                annotation=parameter.annotation,
                                name=parameter.name,
                                kind=ParameterKind.KEYWORD_ONLY,
                                **({'default': parameter.default}
                                   if (isinstance(parameter, OptionalParameter)
                                       and parameter.has_default)
                                   else ({'default': kwargs[parameter.name]}
                                         if parameter.name in kwargs_names
                                         else {}))
                        )
                        if (isinstance(parameter, OptionalParameter)
                            or parameter.name in kwargs_names)
                        else RequiredParameter(annotation=parameter.annotation,
                                               name=parameter.name,
                                               kind=ParameterKind.KEYWORD_ONLY)
                    )
                    if (parameter.kind is ParameterKind.POSITIONAL_OR_KEYWORD
                        or parameter.kind is ParameterKind.KEYWORD_ONLY)
                    else parameter
                    for parameter in parameters[first_kwarg_index:]
                    if parameter.kind is not ParameterKind.VARIADIC_POSITIONAL
            ))
