from functools import (partial,
                       reduce,
                       singledispatch)
from operator import (attrgetter,
                      le)
from typing import (Any,
                    Callable,
                    Dict,
                    Tuple,
                    TypeVar)

from hypothesis import strategies

from paradigm._core.models import (to_parameters_by_kind,
                                   to_parameters_by_name)
from paradigm.base import (OverloadedSignature,
                           Parameter,
                           PlainSignature)
from tests.strategies import (identifiers,
                              to_homogeneous_tuples)
from tests.utils import (AnySignature,
                         Args,
                         Kwargs,
                         Strategy,
                         negate,
                         pack)

_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')


def to_parameters(*,
                  names: Strategy[str] = identifiers,
                  kinds: Strategy[Parameter.Kind],
                  has_default_flags: Strategy[bool] =
                  strategies.booleans()) -> Strategy[Parameter]:
    def normalize_mapping(mapping: Dict[str, Any]) -> Dict[str, Any]:
        kind = mapping['kind']
        return ({**mapping, 'has_default': False}
                if (kind is Parameter.Kind.VARIADIC_KEYWORD
                    or kind is Parameter.Kind.VARIADIC_POSITIONAL)
                else mapping)

    return (strategies.fixed_dictionaries(dict(name=names,
                                               kind=kinds,
                                               has_default=has_default_flags))
            .map(normalize_mapping)
            .map(lambda mapping: Parameter(**mapping)))


def to_plain_signatures(*,
                        parameters_names: Strategy[str] = identifiers,
                        parameters_kinds: Strategy[Parameter.Kind],
                        parameters_has_default_flags: Strategy[bool] =
                        strategies.booleans(),
                        min_size: int = 0,
                        max_size: int) -> Strategy[PlainSignature]:
    if min_size < 0:
        raise ValueError('Min size '
                         'should not be negative, '
                         f'but found {min_size}.')
    if min_size > max_size:
        raise ValueError('Min size '
                         'should not be greater '
                         'than max size, '
                         f'but found {min_size} > {max_size}.')

    empty = strategies.builds(PlainSignature)
    if max_size == 0:
        return empty

    @strategies.composite
    def extend(
            draw: Callable[[Strategy[_T1]], _T1],
            base: Strategy[Tuple[Parameter, ...]]
    ) -> Strategy[Tuple[Parameter, ...]]:
        precursors = draw(base)
        precursors_names = set(map(attrgetter('name'), precursors))
        precursors_kinds = to_parameters_by_kind(precursors)
        last_precursor = precursors[-1]

        def is_kind_valid(parameter: Parameter) -> bool:
            kind = parameter.kind
            return (not precursors_kinds[kind]
                    if (kind is Parameter.Kind.VARIADIC_KEYWORD
                        or kind is Parameter.Kind.VARIADIC_POSITIONAL)
                    else True)

        def normalize(parameter: Parameter) -> Parameter:
            kind = parameter.kind
            if (kind is Parameter.Kind.POSITIONAL_OR_KEYWORD
                    or kind is Parameter.Kind.POSITIONAL_ONLY):
                if last_precursor.has_default and not parameter.has_default:
                    return Parameter(name=parameter.name,
                                     kind=kind,
                                     has_default=True)
            return parameter

        follower = draw(
                (to_parameters(names=identifiers.filter(negate(precursors_names
                                                               .__contains__)),
                               kinds=(parameters_kinds
                                      .filter(partial(le,
                                                      max(precursors_kinds)))),
                               has_default_flags=parameters_has_default_flags)
                 .filter(is_kind_valid)
                 .map(normalize))
        )
        return precursors + (follower,)

    base_parameters = to_parameters(names=parameters_names,
                                    kinds=parameters_kinds,
                                    has_default_flags=
                                    parameters_has_default_flags)
    non_empty = (strategies.recursive(strategies.tuples(base_parameters),
                                      extend,
                                      max_leaves=max_size)
                 .map(pack(PlainSignature)))
    if min_size == 0:
        return empty | non_empty
    return non_empty


def to_overloaded_signatures(bases: Strategy[AnySignature],
                             *,
                             min_size: int = 2,
                             max_size: int = None) -> Strategy[
    OverloadedSignature]:
    return (strategies.lists(bases,
                             min_size=min_size,
                             max_size=max_size)
            .map(pack(OverloadedSignature)))


def to_signature_with_unexpected_args(
        signature: AnySignature
) -> Strategy[Tuple[AnySignature, Args]]:
    return strategies.tuples(strategies.just(signature),
                             to_unexpected_args(signature))


def to_signature_with_unexpected_kwargs(
        signature: AnySignature
) -> Strategy[Tuple[AnySignature, Kwargs]]:
    return strategies.tuples(strategies.just(signature),
                             to_unexpected_kwargs(signature))


def to_signature_with_expected_args(
        signature: AnySignature
) -> Strategy[Tuple[AnySignature, Args]]:
    return strategies.tuples(strategies.just(signature),
                             to_expected_args(signature))


def to_signature_with_expected_kwargs(
        signature: AnySignature
) -> Strategy[Tuple[AnySignature, Kwargs]]:
    return strategies.tuples(strategies.just(signature),
                             to_expected_kwargs(signature))


def to_expected_args(
        signature: AnySignature,
        *,
        values: Strategy[_T1] = strategies.none()
) -> Strategy[Args]:
    count = signature_to_min_positionals_count(signature)
    return to_homogeneous_tuples(values,
                                 max_size=count)


def to_expected_kwargs(
        signature: AnySignature,
        *,
        values: Strategy[_T1] = strategies.none()
) -> Strategy[Kwargs]:
    keywords = signature_to_keywords_intersection(signature)
    if not keywords:
        return strategies.fixed_dictionaries({})
    return strategies.dictionaries(strategies.sampled_from(list(keywords
                                                                .keys())),
                                   values)


def to_unexpected_args(
        signature: AnySignature,
        *,
        values: Strategy[_T1] = strategies.none()
) -> Strategy[Args]:
    count = signature_to_max_positionals_count(signature) + 1
    return to_homogeneous_tuples(values,
                                 min_size=count)


def to_unexpected_kwargs(
        signature: AnySignature,
        *,
        values: Strategy[_T1] = strategies.none()
) -> Strategy[Kwargs]:
    keywords = signature_to_keywords_union(signature)
    is_unexpected = negate(keywords.__contains__)
    return (strategies.dictionaries(identifiers.filter(is_unexpected), values)
            .filter(bool))


@singledispatch
def signature_to_max_positionals_count(signature: AnySignature) -> int:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@singledispatch
def signature_to_min_positionals_count(signature: AnySignature) -> int:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@signature_to_max_positionals_count.register(PlainSignature)
@signature_to_min_positionals_count.register(PlainSignature)
def _(signature: PlainSignature) -> int:
    parameters_by_kind = to_parameters_by_kind(signature.parameters)
    positionals = (parameters_by_kind[Parameter.Kind.POSITIONAL_ONLY]
                   + parameters_by_kind[Parameter.Kind.POSITIONAL_OR_KEYWORD])
    return len(positionals)


@signature_to_max_positionals_count.register(OverloadedSignature)
def _(signature: OverloadedSignature) -> int:
    return max(map(signature_to_max_positionals_count, signature.signatures),
               default=0)


@signature_to_min_positionals_count.register(OverloadedSignature)
def _(signature: OverloadedSignature) -> int:
    return min(map(signature_to_min_positionals_count, signature.signatures),
               default=0)


@singledispatch
def signature_to_keywords_intersection(
        signature: AnySignature
) -> Dict[str, Parameter]:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@singledispatch
def signature_to_keywords_union(
        signature: AnySignature
) -> Dict[str, Parameter]:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@signature_to_keywords_union.register(PlainSignature)
@signature_to_keywords_intersection.register(PlainSignature)
def _(signature: PlainSignature) -> Dict[str, Parameter]:
    parameters_by_kind = to_parameters_by_kind(signature.parameters)
    keywords = (parameters_by_kind[Parameter.Kind.POSITIONAL_OR_KEYWORD]
                + parameters_by_kind[Parameter.Kind.KEYWORD_ONLY])
    return to_parameters_by_name(keywords)


@signature_to_keywords_intersection.register(OverloadedSignature)
def _(signature: OverloadedSignature) -> Dict[str, Parameter]:
    if not signature.signatures:
        return {}

    def intersect(left_dictionary: Dict[_T1, _T2],
                  right_dictionary: Dict[_T1, _T2]) -> Dict[_T1, _T2]:
        common_keys = left_dictionary.keys() & right_dictionary.keys()
        return {key: right_dictionary[key] for key in common_keys}

    return reduce(intersect,
                  map(signature_to_keywords_intersection,
                      signature.signatures))


@signature_to_keywords_union.register(OverloadedSignature)
def _(signature: OverloadedSignature) -> Dict[str, Parameter]:
    if not signature.signatures:
        return {}

    def unite(left_dictionary: Dict[_T1, _T2],
              right_dictionary: Dict[_T1, _T2]) -> Dict[_T1, _T2]:
        return {**left_dictionary, **right_dictionary}

    return reduce(unite,
                  map(signature_to_keywords_union, signature.signatures))
