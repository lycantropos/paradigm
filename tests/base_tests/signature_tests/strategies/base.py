import sys
from functools import singledispatch
from typing import Any

from hypothesis import strategies as st

from paradigm.base import OverloadedSignature, ParameterKind, PlainSignature
from tests.utils import ArgT, Args, KwArgs, Signature

from .factories import (
    hashable_annotations_strategy,
    hashable_values_strategy,
    to_optional_parameters,
    to_overloaded_signatures,
    to_plain_signatures,
    to_required_parameters,
    to_signature_with_expected_args,
    to_signature_with_expected_kwargs,
    to_signature_with_unexpected_args,
    to_signature_with_unexpected_kwargs,
)

MAX_ARGUMENTS_COUNT = sys.maxsize

positionable_kinds = st.sampled_from(
    [ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD]
)
keywordable_kinds = st.sampled_from(
    [ParameterKind.POSITIONAL_OR_KEYWORD, ParameterKind.KEYWORD_ONLY]
)
non_variadic_kinds = positionable_kinds | keywordable_kinds
variadic_kinds = st.sampled_from(
    [ParameterKind.VARIADIC_KEYWORD, ParameterKind.VARIADIC_POSITIONAL]
)
kinds = non_variadic_kinds | variadic_kinds
parameters = to_required_parameters() | to_optional_parameters()
plain_signatures = to_plain_signatures(max_size=MAX_ARGUMENTS_COUNT)
hashable_plain_signatures = to_plain_signatures(
    parameters_annotations=hashable_annotations_strategy,
    parameters_defaults=hashable_values_strategy,
    max_size=MAX_ARGUMENTS_COUNT,
)
overloaded_signatures = to_overloaded_signatures(
    plain_signatures, max_size=MAX_ARGUMENTS_COUNT
)
hashable_overloaded_signatures = to_overloaded_signatures(
    hashable_plain_signatures, max_size=MAX_ARGUMENTS_COUNT
)
signatures = plain_signatures | overloaded_signatures
hashable_signatures = (
    hashable_plain_signatures | hashable_overloaded_signatures
)
plain_non_variadic_signatures = to_plain_signatures(
    optional_parameters_kinds=non_variadic_kinds, max_size=MAX_ARGUMENTS_COUNT
)
non_variadic_signatures = (
    plain_non_variadic_signatures
    | to_overloaded_signatures(
        plain_non_variadic_signatures, max_size=MAX_ARGUMENTS_COUNT
    )
)
non_variadic_signatures_with_unexpected_args: st.SearchStrategy[
    tuple[Signature, Args[Any]]
] = non_variadic_signatures.flatmap(to_signature_with_unexpected_args)
non_variadic_signatures_with_unexpected_kwargs: st.SearchStrategy[
    tuple[Signature, KwArgs[Any]]
] = non_variadic_signatures.flatmap(to_signature_with_unexpected_kwargs)


@singledispatch
def is_signature_empty(signature: Signature, /) -> bool:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@is_signature_empty.register(PlainSignature)
def _(_signature: PlainSignature[ArgT], /) -> bool:
    return False


@is_signature_empty.register(OverloadedSignature)
def _(signature: OverloadedSignature[ArgT], /) -> bool:
    return not signature.signatures


signatures_with_expected_args: st.SearchStrategy[
    tuple[Signature, Args[Any]]
] = signatures.flatmap(to_signature_with_expected_args)
signatures_with_expected_kwargs: st.SearchStrategy[
    tuple[Signature, KwArgs[Any]]
] = signatures.flatmap(to_signature_with_expected_kwargs)
