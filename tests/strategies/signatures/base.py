from hypothesis import strategies

from paradigm.signatures import Parameter
from tests.configs import MAX_ARGUMENTS_COUNT
from .factories import (to_overloaded_signatures,
                        to_parameters,
                        to_plain_signatures)

positionals_kinds = strategies.sampled_from(list(Parameter.positionals_kinds))
keywords_kinds = strategies.sampled_from(list(Parameter.keywords_kinds))
variadic_kinds = strategies.sampled_from(list(set(Parameter.Kind)
                                              - Parameter.positionals_kinds
                                              - Parameter.keywords_kinds))

positionals_parameters = to_parameters(kinds=positionals_kinds)
keywords_parameters = to_parameters(kinds=keywords_kinds)
non_variadic_parameters = positionals_parameters | keywords_parameters
variadic_parameters = to_parameters(kinds=variadic_kinds)
parameters = non_variadic_parameters | variadic_parameters

plain_signatures = to_plain_signatures(parameters,
                                       max_size=MAX_ARGUMENTS_COUNT)
overloaded_signatures = to_overloaded_signatures(plain_signatures,
                                                 max_size=MAX_ARGUMENTS_COUNT)
signatures = plain_signatures | overloaded_signatures
plain_non_variadic_signatures = to_plain_signatures(non_variadic_parameters,
                                                    max_size=MAX_ARGUMENTS_COUNT)
non_variadic_signatures = (
        plain_non_variadic_signatures
        | to_overloaded_signatures(plain_non_variadic_signatures,
                                   max_size=MAX_ARGUMENTS_COUNT))
