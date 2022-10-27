from hypothesis import given

from tests.utils import (AnySignature,
                         implication)
from . import strategies


@given(strategies.signatures)
def test_reflexivity(signature: AnySignature) -> None:
    assert signature == signature


@given(strategies.signatures, strategies.signatures)
def test_symmetry(signature: AnySignature,
                  other_signature: AnySignature) -> None:
    assert implication(signature == other_signature,
                       other_signature == signature)


@given(strategies.signatures, strategies.signatures, strategies.signatures)
def test_transitivity(signature: AnySignature,
                      other_signature: AnySignature,
                      another_signature: AnySignature) -> None:
    assert implication(signature == other_signature
                       and other_signature == another_signature,
                       signature == another_signature)
