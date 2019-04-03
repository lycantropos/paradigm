from functools import singledispatch
from typing import (Any,
                    Dict,
                    Tuple)

from paradigm import signatures


def test_basic(signature: signatures.Base) -> None:
    assert signature.expects() or is_signature_empty(signature)


def test_unexpected_positionals(non_variadic_signature: signatures.Base,
                                unexpected_positionals: Tuple[Any, ...]
                                ) -> None:
    assert not non_variadic_signature.expects(*unexpected_positionals)


def test_unexpected_keywords(non_variadic_signature: signatures.Base,
                             unexpected_keywords: Dict[str, Any]) -> None:
    assert not non_variadic_signature.expects(**unexpected_keywords)


@singledispatch
def is_signature_empty(signature: signatures.Base) -> bool:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@is_signature_empty.register(signatures.Plain)
def is_plain_signature_empty(signature: signatures.Plain) -> bool:
    return False


@is_signature_empty.register(signatures.Overloaded)
def is_overloaded_signature_empty(signature: signatures.Overloaded) -> bool:
    return not signature.signatures
