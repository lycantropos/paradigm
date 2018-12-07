from itertools import chain
from typing import (Any,
                    Callable)

from paradigm import signatures


def test_has_unset_parameters(callable_: Callable[..., Any]) -> None:
    result = signatures.factory(callable_)

    if isinstance(result, signatures.Plain):
        assert (result.has_unset_parameters()
                or is_plain_signature_all_set(result))
    else:
        assert isinstance(result, signatures.Overloaded)
        assert (result.has_unset_parameters()
                or all(map(is_plain_signature_all_set, result.signatures)))


def is_plain_signature_all_set(signature: signatures.Plain) -> bool:
    variadic_parameters_kinds = {signatures.Parameter.Kind.VARIADIC_POSITIONAL,
                                 signatures.Parameter.Kind.VARIADIC_KEYWORD}
    non_variadic_parameters_kinds = (set(signatures.Parameter.Kind)
                                     - variadic_parameters_kinds)
    non_variadic_parameters = chain.from_iterable(
            signature.parameters_by_kind[kind]
            for kind in non_variadic_parameters_kinds)
    return (all(parameter.has_default
                for parameter in non_variadic_parameters)
            or all(parameter.kind in variadic_parameters_kinds
                   for parameter in signature.parameters))
