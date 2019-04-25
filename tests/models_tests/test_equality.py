from hypothesis import given

from paradigm import models
from tests.utils import implication
from . import strategies


@given(strategies.signatures)
def test_reflexivity(signature: models.Base) -> None:
    assert signature == signature


@given(strategies.signatures, strategies.signatures)
def test_symmetry(signature: models.Base,
                  other_signature: models.Base) -> None:
    assert implication(signature == other_signature,
                       other_signature == signature)


@given(strategies.signatures, strategies.signatures, strategies.signatures)
def test_transitivity(signature: models.Base,
                      other_signature: models.Base,
                      another_signature: models.Base) -> None:
    assert implication(signature == other_signature
                       and other_signature == another_signature,
                       signature == another_signature)
