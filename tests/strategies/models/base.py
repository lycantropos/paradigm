from hypothesis import strategies

from paradigm.models import Parameter
from tests.configs import MAX_ARGUMENTS_COUNT
from .factories import (to_overloaded_signatures,
                        to_parameters,
                        to_plain_signatures)

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
