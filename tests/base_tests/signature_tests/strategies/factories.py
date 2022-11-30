import sys
from functools import (reduce,
                       singledispatch)
from typing import (Any,
                    Dict,
                    List,
                    Optional,
                    Tuple,
                    TypeVar)

from hypothesis import strategies
from typing_extensions import Literal

from paradigm._core import catalog
from paradigm._core.models import (to_parameters_by_kind,
                                   to_parameters_by_name)
from paradigm.base import (OptionalParameter,
                           OverloadedSignature,
                           ParameterKind,
                           PlainSignature,
                           RequiredParameter)
from tests.utils import (AnyParameter,
                         AnySignature,
                         Args,
                         Kwargs,
                         Strategy,
                         negate,
                         pack)
from .utils import (identifiers,
                    to_homogeneous_tuples)

_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')


def qualified_path_is_valid(value: type) -> bool:
    module_path, object_path = catalog.qualified_path_from(value)
    return (module_path
            and object_path
            and getattr(sys.modules.get(catalog.path_to_string(module_path)),
                        catalog.path_to_string(object_path), None) is value)


base_hashable_values_strategy = (
        strategies.none()
        | strategies.booleans()
        | strategies.integers()
        | strategies.floats(allow_infinity=False,
                            allow_nan=False)
        | strategies.complex_numbers(allow_infinity=False,
                                     allow_nan=False)
        | strategies.binary()
        | strategies.text()
)
hashable_values_strategy = strategies.recursive(
        base_hashable_values_strategy,
        lambda step: (strategies.lists(step).map(tuple)
                      | strategies.frozensets(step))
)
values_strategy = strategies.recursive(
        hashable_values_strategy | strategies.sets(hashable_values_strategy),
        lambda step: (strategies.lists(step)
                      | strategies.lists(step).map(tuple)
                      | strategies.dictionaries(hashable_values_strategy,
                                                step))
)
types_with_round_trippable_repr = strategies.from_type(type).filter(
        qualified_path_is_valid
)


def is_hashable(value: Any) -> bool:
    try:
        hash(value)
    except Exception:
        return False
    else:
        return True


hashable_annotations_strategy = (
        strategies.none()
        | (strategies.lists(hashable_values_strategy,
                            min_size=1)
           .map(tuple)
           .map(Literal.__getitem__))
        | types_with_round_trippable_repr.filter(is_hashable)
)
annotations_strategy = (
        strategies.none()
        | (strategies.lists(values_strategy,
                            min_size=1)
           .map(tuple)
           .map(Literal.__getitem__))
        | types_with_round_trippable_repr
)


def to_optional_parameters(
        *,
        annotations: Strategy[Any] = annotations_strategy,
        names: Strategy[str] = identifiers,
        kinds: Strategy[ParameterKind]
        = strategies.sampled_from(list(ParameterKind)),
        defaults: Strategy[bool] = values_strategy
) -> Strategy[OptionalParameter]:
    def normalize_mapping(mapping: Dict[str, Any]) -> Dict[str, Any]:
        kind = mapping['kind']
        if (kind is ParameterKind.VARIADIC_KEYWORD
                or kind is ParameterKind.VARIADIC_POSITIONAL):
            mapping.pop('default', None)
        return mapping

    return (strategies.fixed_dictionaries({'annotation': annotations,
                                           'name': names,
                                           'kind': kinds,
                                           'default': defaults})
            .map(normalize_mapping)
            .map(lambda mapping: OptionalParameter(**mapping)))


def to_required_parameters(
        *,
        annotations: Strategy[Any] = annotations_strategy,
        names: Strategy[str] = identifiers,
        kinds: Strategy[Literal[ParameterKind.POSITIONAL_ONLY,
                                ParameterKind.POSITIONAL_OR_KEYWORD,
                                ParameterKind.KEYWORD_ONLY]]
        = strategies.sampled_from([ParameterKind.POSITIONAL_ONLY,
                                   ParameterKind.POSITIONAL_OR_KEYWORD,
                                   ParameterKind.KEYWORD_ONLY])
) -> Strategy[RequiredParameter]:
    return strategies.builds(RequiredParameter,
                             annotation=annotations,
                             name=names,
                             kind=kinds)


def to_plain_signatures(
        *,
        parameters_annotations: Strategy[Any] = annotations_strategy,
        parameters_names: Strategy[str] = identifiers,
        required_parameters_kinds: Strategy[
            Literal[ParameterKind.POSITIONAL_ONLY,
                    ParameterKind.POSITIONAL_OR_KEYWORD,
                    ParameterKind.KEYWORD_ONLY]
        ] = strategies.sampled_from([ParameterKind.POSITIONAL_ONLY,
                                     ParameterKind.POSITIONAL_OR_KEYWORD,
                                     ParameterKind.KEYWORD_ONLY]),
        optional_parameters_kinds: Strategy[ParameterKind]
        = strategies.sampled_from(list(ParameterKind)),
        parameters_defaults: Strategy[bool] = values_strategy,
        min_size: int = 0,
        max_size: int
) -> Strategy[PlainSignature]:
    if min_size < 0:
        raise ValueError('Min size '
                         'should not be negative, '
                         f'but found {min_size}.')
    if min_size > max_size:
        raise ValueError('Min size '
                         'should not be greater '
                         'than max size, '
                         f'but found {min_size} > {max_size}.')
    base_parameters = (
            to_required_parameters(annotations=parameters_annotations,
                                   names=parameters_names,
                                   kinds=required_parameters_kinds)
            | to_optional_parameters(annotations=parameters_annotations,
                                     names=parameters_names,
                                     kinds=optional_parameters_kinds,
                                     defaults=parameters_defaults)
    )

    def normalize_parameters(
            parameters: List[AnyParameter]
    ) -> List[AnyParameter]:
        parameters_by_kind = to_parameters_by_kind(
                to_parameters_by_name(parameters).values()
        )
        for kind, kind_parameters in parameters_by_kind.items():
            if (kind is ParameterKind.VARIADIC_POSITIONAL
                    or kind is ParameterKind.VARIADIC_KEYWORD):
                kind_parameters[:] = kind_parameters[:1]
            kind_parameters.sort(key=OptionalParameter.__instancecheck__)
        if any(
                isinstance(parameter, OptionalParameter)
                for parameter in parameters_by_kind.get(
                        ParameterKind.POSITIONAL_ONLY, []
                )
        ) and ParameterKind.POSITIONAL_OR_KEYWORD in parameters_by_kind:
            parameters_by_kind[ParameterKind.POSITIONAL_OR_KEYWORD][:] = [
                parameter
                for parameter in parameters_by_kind[
                    ParameterKind.POSITIONAL_OR_KEYWORD
                ]
                if isinstance(parameter, OptionalParameter)
            ]
        result = []
        for kind in sorted(parameters_by_kind.keys()):
            result += parameters_by_kind[kind]
        return result

    return strategies.builds(
            pack(PlainSignature),
            (strategies.lists(base_parameters,
                              min_size=min_size,
                              max_size=max_size)
             .map(normalize_parameters)),
            strategies.fixed_dictionaries({'returns': parameters_annotations})
    )


def to_overloaded_signatures(
        bases: Strategy[AnySignature],
        *,
        min_size: int = 2,
        max_size: Optional[int] = None
) -> Strategy[OverloadedSignature]:
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
    positionals = (parameters_by_kind[ParameterKind.POSITIONAL_ONLY]
                   + parameters_by_kind[ParameterKind.POSITIONAL_OR_KEYWORD])
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
) -> Dict[str, AnyParameter]:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@singledispatch
def signature_to_keywords_union(
        signature: AnySignature
) -> Dict[str, AnyParameter]:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@signature_to_keywords_union.register(PlainSignature)
@signature_to_keywords_intersection.register(PlainSignature)
def _(signature: PlainSignature) -> Dict[str, AnyParameter]:
    parameters_by_kind = to_parameters_by_kind(signature.parameters)
    keywords = (parameters_by_kind[ParameterKind.POSITIONAL_OR_KEYWORD]
                + parameters_by_kind[ParameterKind.KEYWORD_ONLY])
    return to_parameters_by_name(keywords)


@signature_to_keywords_intersection.register(OverloadedSignature)
def _(signature: OverloadedSignature) -> Dict[str, AnyParameter]:
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
def _(signature: OverloadedSignature) -> Dict[str, AnyParameter]:
    if not signature.signatures:
        return {}

    def unite(left_dictionary: Dict[_T1, _T2],
              right_dictionary: Dict[_T1, _T2]) -> Dict[_T1, _T2]:
        return {**left_dictionary, **right_dictionary}

    return reduce(unite,
                  map(signature_to_keywords_union, signature.signatures))
