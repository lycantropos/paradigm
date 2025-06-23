from __future__ import annotations

import sys
from collections.abc import Callable
from functools import reduce, singledispatch
from operator import getitem
from typing import Any, Literal, Optional, TypeVar, Union

from hypothesis import strategies as st

from paradigm._core import catalog
from paradigm._core.models import (
    Parameter,
    to_parameters_by_kind,
    to_parameters_by_name,
)
from paradigm.base import (
    OptionalParameter,
    OverloadedSignature,
    ParameterKind,
    PlainSignature,
    RequiredParameter,
)
from tests.utils import ArgT, Args, KwArgs, Signature, negate, pack

from .utils import identifiers, to_homogeneous_tuples

_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')


def qualified_path_is_valid(value: type, /) -> bool:
    module_path, object_path = catalog.qualified_path_from(value)
    return (
        len(module_path) > 0
        and len(object_path) > 0
        and (
            getattr(
                sys.modules.get(catalog.path_to_string(module_path)),
                catalog.path_to_string(object_path),
                None,
            )
            is value
        )
    )


plain_hashable_values_strategy = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_infinity=False, allow_nan=False)
    | st.complex_numbers(allow_infinity=False, allow_nan=False)
    | st.binary()
    | st.text()
)
hashable_values_strategy = st.recursive(
    plain_hashable_values_strategy,
    lambda step: st.lists(step).map(tuple) | st.frozensets(step),
    max_leaves=3,
)
values_strategy = st.recursive(
    hashable_values_strategy | st.sets(hashable_values_strategy),
    lambda step: (
        st.lists(step)
        | st.lists(step).map(tuple)
        | st.dictionaries(hashable_values_strategy, step)
    ),
    max_leaves=3,
)
types_with_round_trippable_repr = st.from_type(type).filter(
    qualified_path_is_valid
)


def nest_annotations(base: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
    return (
        st.builds(lambda argument: argument | None, base)
        | st.builds(lambda argument: Optional[argument], base)
        | st.builds(
            lambda elements: Union[elements],
            (st.lists(base, min_size=1, max_size=5).map(tuple)),
        )
        | st.builds(
            tuple.__class_getitem__, st.tuples(base, st.just(Ellipsis))
        )
        | st.builds(
            tuple.__class_getitem__,
            (
                st.lists(
                    base,
                    # due to
                    # https://github.com/python/cpython/issues/94245
                    min_size=sys.version_info < (3, 10),
                    max_size=5,
                ).map(tuple)
            ),
        )
        | st.builds(
            getitem,
            st.just(Callable),
            st.tuples(
                st.just(Ellipsis) | st.lists(base, min_size=0, max_size=5),
                base,
            ),
        )
    )


def is_hashable(value: Any, /) -> bool:
    try:
        hash(value)
    except Exception:
        return False
    else:
        return True


base_hashable_annotations_strategy = (
    st.none()
    | (
        st.lists(plain_hashable_values_strategy, min_size=1)
        .map(tuple)
        .map(lambda variants: Literal[variants])
    )
    | types_with_round_trippable_repr.filter(is_hashable)
)
hashable_annotations_strategy = st.recursive(
    base_hashable_annotations_strategy, nest_annotations, max_leaves=3
)
base_annotations_strategy = (
    st.none()
    | (
        st.lists(plain_hashable_values_strategy, min_size=1)
        .map(tuple)
        .map(lambda variants: Literal[variants])
    )
    | types_with_round_trippable_repr
)
annotations_strategy = st.recursive(
    base_annotations_strategy, nest_annotations, max_leaves=3
)


def to_optional_parameters(
    *,
    annotations: st.SearchStrategy[Any] = annotations_strategy,
    names: st.SearchStrategy[str] = identifiers,
    kinds: st.SearchStrategy[ParameterKind] = st.sampled_from(  # noqa: B008
        list(ParameterKind)
    ),
    defaults: st.SearchStrategy[Any] = values_strategy,
) -> st.SearchStrategy[OptionalParameter]:
    def normalize_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
        kind = mapping['kind']
        if (
            kind is ParameterKind.VARIADIC_KEYWORD
            or kind is ParameterKind.VARIADIC_POSITIONAL
        ):
            mapping.pop('default', None)
        return mapping

    return (
        st.fixed_dictionaries(
            {
                'annotation': annotations,
                'name': names,
                'kind': kinds,
                'default': defaults,
            }
        )
        .map(normalize_mapping)
        .map(lambda mapping: OptionalParameter(**mapping))
    )


def to_required_parameters(
    *,
    annotations: st.SearchStrategy[Any] = annotations_strategy,
    names: st.SearchStrategy[str] = identifiers,
    kinds: st.SearchStrategy[
        Literal[
            ParameterKind.POSITIONAL_ONLY,
            ParameterKind.POSITIONAL_OR_KEYWORD,
            ParameterKind.KEYWORD_ONLY,
        ]
    ] = st.sampled_from(  # noqa: B008
        [
            ParameterKind.POSITIONAL_ONLY,
            ParameterKind.POSITIONAL_OR_KEYWORD,
            ParameterKind.KEYWORD_ONLY,
        ]
    ),
) -> st.SearchStrategy[RequiredParameter]:
    return st.builds(
        RequiredParameter, annotation=annotations, name=names, kind=kinds
    )


def to_plain_signatures(
    *,
    parameters_annotations: st.SearchStrategy[Any] = annotations_strategy,
    parameters_names: st.SearchStrategy[str] = identifiers,
    required_parameters_kinds: st.SearchStrategy[
        Literal[
            ParameterKind.POSITIONAL_ONLY,
            ParameterKind.POSITIONAL_OR_KEYWORD,
            ParameterKind.KEYWORD_ONLY,
        ]
    ] = st.sampled_from(  # noqa: B008
        [
            ParameterKind.POSITIONAL_ONLY,
            ParameterKind.POSITIONAL_OR_KEYWORD,
            ParameterKind.KEYWORD_ONLY,
        ]
    ),
    optional_parameters_kinds: st.SearchStrategy[
        ParameterKind
    ] = st.sampled_from(list(ParameterKind)),  # noqa: B008
    parameters_defaults: st.SearchStrategy[Any] = values_strategy,
    min_size: int = 0,
    max_size: int,
) -> st.SearchStrategy[PlainSignature[Any]]:
    if min_size < 0:
        raise ValueError(
            f'Min size should not be negative, but found {min_size}.'
        )
    if min_size > max_size:
        raise ValueError(
            'Min size '
            'should not be greater '
            'than max size, '
            f'but found {min_size} > {max_size}.'
        )
    base_parameters = to_required_parameters(
        annotations=parameters_annotations,
        names=parameters_names,
        kinds=required_parameters_kinds,
    ) | to_optional_parameters(
        annotations=parameters_annotations,
        names=parameters_names,
        kinds=optional_parameters_kinds,
        defaults=parameters_defaults,
    )

    def normalize_parameters(
        parameters: list[Parameter], /
    ) -> list[Parameter]:
        parameters_by_kind = to_parameters_by_kind(
            to_parameters_by_name(parameters).values()
        )
        for kind, kind_parameters in parameters_by_kind.items():
            if (
                kind is ParameterKind.VARIADIC_POSITIONAL
                or kind is ParameterKind.VARIADIC_KEYWORD
            ):
                kind_parameters[:] = kind_parameters[:1]
            kind_parameters.sort(key=OptionalParameter.__instancecheck__)
        if (
            any(
                isinstance(parameter, OptionalParameter)
                for parameter in parameters_by_kind.get(
                    ParameterKind.POSITIONAL_ONLY, []
                )
            )
            and ParameterKind.POSITIONAL_OR_KEYWORD in parameters_by_kind
        ):
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

    return st.builds(
        pack(PlainSignature),
        (
            st.lists(
                base_parameters, min_size=min_size, max_size=max_size
            ).map(normalize_parameters)
        ),
        st.fixed_dictionaries({'returns': parameters_annotations}),
    )


def to_overloaded_signatures(
    bases: st.SearchStrategy[PlainSignature[ArgT]],
    /,
    *,
    min_size: int = 2,
    max_size: int | None = None,
) -> st.SearchStrategy[OverloadedSignature[ArgT]]:
    return st.lists(bases, min_size=min_size, max_size=max_size).map(
        lambda signatures: OverloadedSignature(*signatures)
    )


AnySignatureT = TypeVar('AnySignatureT', bound=Signature)


def to_signature_with_unexpected_args(
    signature: AnySignatureT, /
) -> st.SearchStrategy[tuple[AnySignatureT, Args[ArgT]]]:
    return st.tuples(st.just(signature), to_unexpected_args(signature))


def to_signature_with_unexpected_kwargs(
    signature: AnySignatureT, /
) -> st.SearchStrategy[tuple[AnySignatureT, KwArgs[ArgT]]]:
    return st.tuples(st.just(signature), to_unexpected_kwargs(signature))


def to_signature_with_expected_args(
    signature: AnySignatureT, /
) -> st.SearchStrategy[tuple[AnySignatureT, Args[ArgT]]]:
    return st.tuples(st.just(signature), to_expected_args(signature))


def to_signature_with_expected_kwargs(
    signature: AnySignatureT, /
) -> st.SearchStrategy[tuple[AnySignatureT, KwArgs[ArgT]]]:
    return st.tuples(st.just(signature), to_expected_kwargs(signature))


def to_expected_args(
    signature: Signature,
    /,
    *,
    values: st.SearchStrategy[Any] = st.none(),  # noqa: B008
) -> st.SearchStrategy[Args[ArgT]]:
    count = signature_to_min_positionals_count(signature)
    return to_homogeneous_tuples(values, max_size=count)


def to_expected_kwargs(
    signature: Signature,
    /,
    *,
    values: st.SearchStrategy[Any] = st.none(),  # noqa: B008
) -> st.SearchStrategy[KwArgs[ArgT]]:
    keywords = signature_to_keywords_intersection(signature)
    if not keywords:
        return st.fixed_dictionaries({})
    return st.dictionaries(st.sampled_from(list(keywords.keys())), values)


def to_unexpected_args(
    signature: Signature,
    /,
    *,
    values: st.SearchStrategy[Any] = st.none(),  # noqa: B008
) -> st.SearchStrategy[Args[ArgT]]:
    count = signature_to_max_positionals_count(signature) + 1
    return to_homogeneous_tuples(values, min_size=count)


def to_unexpected_kwargs(
    signature: Signature,
    /,
    *,
    values: st.SearchStrategy[Any] = st.none(),  # noqa: B008
) -> st.SearchStrategy[KwArgs[ArgT]]:
    keywords = signature_to_keywords_union(signature)
    is_unexpected = negate(keywords.__contains__)
    return st.dictionaries(identifiers.filter(is_unexpected), values).filter(
        bool
    )


@singledispatch
def signature_to_max_positionals_count(signature: Signature, /) -> int:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@singledispatch
def signature_to_min_positionals_count(signature: Signature, /) -> int:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@signature_to_max_positionals_count.register(PlainSignature)
@signature_to_min_positionals_count.register(PlainSignature)
def _(signature: PlainSignature[ArgT], /) -> int:
    parameters_by_kind = to_parameters_by_kind(signature.parameters)
    positionals = (
        parameters_by_kind[ParameterKind.POSITIONAL_ONLY]
        + parameters_by_kind[ParameterKind.POSITIONAL_OR_KEYWORD]
    )
    return len(positionals)


@signature_to_max_positionals_count.register(OverloadedSignature)
def _(signature: OverloadedSignature[ArgT], /) -> int:
    return max(
        map(signature_to_max_positionals_count, signature.signatures),
        default=0,
    )


@signature_to_min_positionals_count.register(OverloadedSignature)
def _(signature: OverloadedSignature[ArgT], /) -> int:
    return min(
        map(signature_to_min_positionals_count, signature.signatures),
        default=0,
    )


@singledispatch
def signature_to_keywords_intersection(
    signature: Signature, /
) -> dict[str, Parameter]:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@singledispatch
def signature_to_keywords_union(
    signature: Signature, /
) -> dict[str, Parameter]:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@signature_to_keywords_union.register(PlainSignature)
@signature_to_keywords_intersection.register(PlainSignature)
def _(signature: PlainSignature[ArgT], /) -> dict[str, Parameter]:
    parameters_by_kind = to_parameters_by_kind(signature.parameters)
    keywords = (
        parameters_by_kind[ParameterKind.POSITIONAL_OR_KEYWORD]
        + parameters_by_kind[ParameterKind.KEYWORD_ONLY]
    )
    return to_parameters_by_name(keywords)


@signature_to_keywords_intersection.register(OverloadedSignature)
def _(signature: OverloadedSignature[ArgT], /) -> dict[str, Parameter]:
    if not signature.signatures:
        return {}

    def intersect(
        left_dictionary: dict[_T1, _T2], right_dictionary: dict[_T1, _T2], /
    ) -> dict[_T1, _T2]:
        common_keys = left_dictionary.keys() & right_dictionary.keys()
        return {key: right_dictionary[key] for key in common_keys}

    return reduce(
        intersect,
        map(signature_to_keywords_intersection, signature.signatures),
    )


@signature_to_keywords_union.register(OverloadedSignature)
def _(signature: OverloadedSignature[ArgT]) -> dict[str, Parameter]:
    if not signature.signatures:
        return {}

    def unite(
        left_dictionary: dict[_T1, _T2], right_dictionary: dict[_T1, _T2], /
    ) -> dict[_T1, _T2]:
        return {**left_dictionary, **right_dictionary}

    return reduce(
        unite, map(signature_to_keywords_union, signature.signatures)
    )
