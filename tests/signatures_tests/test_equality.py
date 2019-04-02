from paradigm import signatures
from tests.utils import implication


def test_reflexivity(signature: signatures.Base) -> None:
    assert signature == signature


def test_symmetry(signature: signatures.Base,
                  other_signature: signatures.Base) -> None:
    assert implication(signature == other_signature,
                       other_signature == signature)


def test_transitivity(signature: signatures.Base,
                      other_signature: signatures.Base,
                      another_signature: signatures.Base) -> None:
    assert implication(signature == other_signature
                       and other_signature == another_signature,
                       signature == another_signature)
