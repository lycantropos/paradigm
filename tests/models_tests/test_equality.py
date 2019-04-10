from paradigm import models
from tests.utils import implication


def test_reflexivity(signature: models.Base) -> None:
    assert signature == signature


def test_symmetry(signature: models.Base,
                  other_signature: models.Base) -> None:
    assert implication(signature == other_signature,
                       other_signature == signature)


def test_transitivity(signature: models.Base,
                      other_signature: models.Base,
                      another_signature: models.Base) -> None:
    assert implication(signature == other_signature
                       and other_signature == another_signature,
                       signature == another_signature)
