import sys
from functools import singledispatch

from hypothesis import strategies

from paradigm.base import (OverloadedSignature,
                           Parameter,
                           PlainSignature)
from tests.utils import (AnySignature,
                         negate)
from .factories import (to_overloaded_signatures,
                        to_parameters,
                        to_plain_signatures,
                        to_signature_with_expected_args,
                        to_signature_with_expected_kwargs,
                        to_signature_with_unexpected_args,
                        to_signature_with_unexpected_kwargs)

MAX_ARGUMENTS_COUNT = sys.maxsize

positionable_kinds = strategies.sampled_from(
        [Parameter.Kind.POSITIONAL_ONLY, Parameter.Kind.POSITIONAL_OR_KEYWORD]
)
keywordable_kinds = strategies.sampled_from(
        [Parameter.Kind.POSITIONAL_OR_KEYWORD, Parameter.Kind.KEYWORD_ONLY]
)
non_variadic_kinds = positionable_kinds | keywordable_kinds
variadic_kinds = strategies.sampled_from([Parameter.Kind.VARIADIC_KEYWORD,
                                          Parameter.Kind.VARIADIC_POSITIONAL])
kinds = non_variadic_kinds | variadic_kinds
parameters = to_parameters(kinds=kinds)
plain_signatures = to_plain_signatures(parameters_kinds=kinds,
                                       max_size=MAX_ARGUMENTS_COUNT)
overloaded_signatures = to_overloaded_signatures(plain_signatures,
                                                 max_size=MAX_ARGUMENTS_COUNT)
signatures = plain_signatures | overloaded_signatures
plain_non_variadic_signatures = to_plain_signatures(
        parameters_kinds=non_variadic_kinds,
        max_size=MAX_ARGUMENTS_COUNT)
non_variadic_signatures = (
        plain_non_variadic_signatures
        | to_overloaded_signatures(plain_non_variadic_signatures,
                                   max_size=MAX_ARGUMENTS_COUNT))
non_variadic_signatures_with_unexpected_args = non_variadic_signatures.flatmap(
        to_signature_with_unexpected_args
)
non_variadic_signatures_with_unexpected_kwargs = (
    non_variadic_signatures.flatmap(to_signature_with_unexpected_kwargs)
)


@singledispatch
def is_signature_empty(signature: AnySignature) -> bool:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@is_signature_empty.register(PlainSignature)
def _(signature: PlainSignature) -> bool:
    return False


@is_signature_empty.register(OverloadedSignature)
def _(signature: OverloadedSignature) -> bool:
    return not signature.signatures


non_empty_signatures = signatures.filter(negate(is_signature_empty))
non_empty_signatures_with_expected_args = non_empty_signatures.flatmap(
        to_signature_with_expected_args
)
non_empty_signatures_with_expected_kwargs = non_empty_signatures.flatmap(
        to_signature_with_expected_kwargs
)
