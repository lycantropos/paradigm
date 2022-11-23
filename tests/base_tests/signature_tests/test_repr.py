import sys

from hypothesis import given

from paradigm import base
from paradigm.base import (OverloadedSignature,
                           PlainSignature)
from tests.utils import AnySignature
from . import strategies


@given(strategies.signatures)
def test_type(signature: AnySignature) -> None:
    result = repr(signature)

    assert isinstance(result, str)


@given(strategies.plain_signatures)
def test_plain(plain_signature: PlainSignature) -> None:
    result = repr(plain_signature)

    assert all(repr(parameter) in result
               for parameter in plain_signature.parameters)


@given(strategies.overloaded_signatures)
def test_nesting(overloaded_signature: OverloadedSignature) -> None:
    result = repr(overloaded_signature)

    assert all(repr(signature) in result
               for signature in overloaded_signature.signatures)


@given(strategies.signatures)
def test_evaluation(signature: AnySignature) -> None:
    signature_repr = repr(signature)

    result = eval(signature_repr, {**vars(base), **sys.modules})

    assert result == signature
