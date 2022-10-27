from hypothesis import given

from paradigm import signatures
from tests.utils import AnySignature
from . import strategies


@given(strategies.signatures)
def test_type(signature: AnySignature) -> None:
    result = str(signature)

    assert isinstance(result, str)


@given(strategies.plain_signatures)
def test_plain(signature: signatures.Plain) -> None:
    result = str(signature)

    assert all(str(parameter) in result for parameter in signature.parameters)


@given(strategies.overloaded_signatures)
def test_nesting(signature: signatures.Overloaded) -> None:
    result = str(signature)

    assert all(str(signature) in result for signature in signature.signatures)
