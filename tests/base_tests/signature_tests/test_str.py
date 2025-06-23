from hypothesis import given

from paradigm.base import OverloadedSignature, PlainSignature
from tests.utils import ArgT, Signature

from . import strategies


@given(strategies.signatures)
def test_type(signature: Signature) -> None:
    result = str(signature)

    assert isinstance(result, str)


@given(strategies.plain_signatures)
def test_plain(signature: PlainSignature[ArgT]) -> None:
    result = str(signature)

    assert all(str(parameter) in result for parameter in signature.parameters)


@given(strategies.overloaded_signatures)
def test_nesting(signature: OverloadedSignature[ArgT]) -> None:
    result = str(signature)

    assert all(str(signature) in result for signature in signature.signatures)
