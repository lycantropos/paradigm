from functools import singledispatch

from paradigm import signatures


def test_basic(signature: signatures.Base) -> None:
    assert signature.expects() or is_signature_empty(signature)


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
