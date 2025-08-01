from hypothesis import given

from tests.utils import Signature, implication

from . import strategies


@given(strategies.signatures)
def test_reflexivity(signature: Signature) -> None:
    assert signature == signature


@given(strategies.signatures, strategies.signatures)
def test_symmetry(signature: Signature, other_signature: Signature) -> None:
    assert implication(
        signature == other_signature, other_signature == signature
    )


@given(strategies.signatures, strategies.signatures, strategies.signatures)
def test_transitivity(
    signature: Signature,
    other_signature: Signature,
    another_signature: Signature,
) -> None:
    assert implication(
        signature == other_signature and other_signature == another_signature,
        signature == another_signature,
    )
