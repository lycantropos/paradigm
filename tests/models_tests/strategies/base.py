from functools import singledispatch

from hypothesis import strategies

from paradigm import models
from paradigm.models import Parameter
from tests.configs import MAX_ARGUMENTS_COUNT
from tests.utils import negate
from .factories import (to_overloaded_signatures,
                        to_parameters,
                        to_plain_signatures,
                        to_signature_with_expected_args,
                        to_signature_with_expected_kwargs,
                        to_signature_with_unexpected_args,
                        to_signature_with_unexpected_kwargs)

positionals_kinds = strategies.sampled_from(list(Parameter.positionals_kinds))
keywords_kinds = strategies.sampled_from(list(Parameter.keywords_kinds))
non_variadic_kinds = positionals_kinds | keywords_kinds
variadic_kinds = strategies.sampled_from(list(set(Parameter.Kind)
                                              - Parameter.positionals_kinds
                                              - Parameter.keywords_kinds))
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
        to_signature_with_unexpected_args)
non_variadic_signatures_with_unexpected_kwargs = (
    non_variadic_signatures.flatmap(to_signature_with_unexpected_kwargs))


@singledispatch
def is_signature_empty(signature: models.Base) -> bool:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@is_signature_empty.register(models.Plain)
def is_plain_signature_empty(signature: models.Plain) -> bool:
    return False


@is_signature_empty.register(models.Overloaded)
def is_overloaded_signature_empty(signature: models.Overloaded) -> bool:
    return not signature.signatures


non_empty_signatures = signatures.filter(negate(is_signature_empty))
non_empty_signatures_with_expected_args = non_empty_signatures.flatmap(
        to_signature_with_expected_args)
non_empty_signatures_with_expected_kwargs = non_empty_signatures.flatmap(
        to_signature_with_expected_kwargs)
