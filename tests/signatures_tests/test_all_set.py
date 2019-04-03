from functools import singledispatch
from itertools import chain
from typing import (Any,
                    Dict,
                    Tuple)

from paradigm import signatures


def test_basic(signature: signatures.Base) -> None:
    assert signature.all_set() or is_signature_unset(signature)


def test_unexpected_positionals(non_variadic_signature: signatures.Base,
                                unexpected_positionals: Tuple[Any, ...]
                                ) -> None:
    assert not non_variadic_signature.all_set(*unexpected_positionals)


def test_unexpected_keywords(non_variadic_signature: signatures.Base,
                             unexpected_keywords: Dict[str, Any]) -> None:
    assert not non_variadic_signature.all_set(**unexpected_keywords)


@singledispatch
def is_signature_unset(signature: signatures.Base) -> bool:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@is_signature_unset.register(signatures.Plain)
def is_plain_signature_unset(signature: signatures.Plain) -> bool:
    variadic_parameters_kinds = {signatures.Parameter.Kind.VARIADIC_POSITIONAL,
                                 signatures.Parameter.Kind.VARIADIC_KEYWORD}
    non_variadic_parameters_kinds = (set(signatures.Parameter.Kind)
                                     - variadic_parameters_kinds)
    non_variadic_parameters = chain.from_iterable(
            signature.parameters_by_kind[kind]
            for kind in non_variadic_parameters_kinds)
    return not (signatures.all_parameters_has_defaults(non_variadic_parameters)
                or all(parameter.kind in variadic_parameters_kinds
                       for parameter in signature.parameters))


@is_signature_unset.register(signatures.Overloaded)
def is_overloaded_signature_unset(signature: signatures.Overloaded) -> bool:
    return all(map(is_signature_unset, signature.signatures))
