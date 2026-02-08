import sys
from functools import singledispatch
from typing import Any

from hypothesis import strategies as st

from paradigm.base import OverloadedSignature, ParameterKind, PlainSignature
from tests.utils import ArgT, Args, KwArgs, Signature

from .factories import (
    hashable_annotation_strategy,
    hashable_value_strategy,
    to_optional_parameter_strategy,
    to_overloaded_signature_strategy,
    to_plain_signature_strategy,
    to_required_parameter_strategy,
    to_signature_with_expected_args_strategy,
    to_signature_with_expected_kwargs_strategy,
    to_signature_with_unexpected_args_strategy,
    to_signature_with_unexpected_kwargs_strategy,
)

MAX_ARGUMENT_COUNT = sys.maxsize

positionable_kind_strategy = st.sampled_from(
    [ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD]
)
keywordable_kind_strategy = st.sampled_from(
    [ParameterKind.POSITIONAL_OR_KEYWORD, ParameterKind.KEYWORD_ONLY]
)
non_variadic_kind_strategy = (
    positionable_kind_strategy | keywordable_kind_strategy
)
parameter_strategy = (
    to_required_parameter_strategy() | to_optional_parameter_strategy()
)
plain_signature_strategy = to_plain_signature_strategy(
    max_size=MAX_ARGUMENT_COUNT
)
hashable_plain_signature_strategy = to_plain_signature_strategy(
    parameter_annotations=hashable_annotation_strategy,
    parameter_defaults=hashable_value_strategy,
    max_size=MAX_ARGUMENT_COUNT,
)
overloaded_signature_strategy = to_overloaded_signature_strategy(
    plain_signature_strategy, max_size=MAX_ARGUMENT_COUNT
)
hashable_overloaded_signature_strategy = to_overloaded_signature_strategy(
    hashable_plain_signature_strategy, max_size=MAX_ARGUMENT_COUNT
)
signature_strategy = plain_signature_strategy | overloaded_signature_strategy
hashable_signature_strategy = (
    hashable_plain_signature_strategy | hashable_overloaded_signature_strategy
)
plain_non_variadic_signature_strategy = to_plain_signature_strategy(
    optional_parameter_kinds=non_variadic_kind_strategy,
    max_size=MAX_ARGUMENT_COUNT,
)
non_variadic_signature_strategy = (
    plain_non_variadic_signature_strategy
    | to_overloaded_signature_strategy(
        plain_non_variadic_signature_strategy, max_size=MAX_ARGUMENT_COUNT
    )
)
non_variadic_signature_with_unexpected_args_strategy: st.SearchStrategy[
    tuple[Signature, Args[Any]]
] = non_variadic_signature_strategy.flatmap(
    to_signature_with_unexpected_args_strategy
)
non_variadic_signature_with_unexpected_kwargs_strategy: st.SearchStrategy[
    tuple[Signature, KwArgs[Any]]
] = non_variadic_signature_strategy.flatmap(
    to_signature_with_unexpected_kwargs_strategy
)


@singledispatch
def is_signature_empty(signature: Signature, /) -> bool:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@is_signature_empty.register(PlainSignature)
def _(_signature: PlainSignature[ArgT], /) -> bool:
    return False


@is_signature_empty.register(OverloadedSignature)
def _(signature: OverloadedSignature[ArgT], /) -> bool:
    return not signature.signatures


signature_with_expected_args_strategy: st.SearchStrategy[
    tuple[Signature, Args[Any]]
] = signature_strategy.flatmap(to_signature_with_expected_args_strategy)
signature_with_expected_kwargs_strategy: st.SearchStrategy[
    tuple[Signature, KwArgs[Any]]
] = signature_strategy.flatmap(to_signature_with_expected_kwargs_strategy)
