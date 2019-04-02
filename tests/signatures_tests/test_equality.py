from paradigm import signatures
from tests.utils import implication


def test_reflexivity(signature: signatures.Base) -> None:
    assert signature == signature


def test_symmetry(signature: signatures.Base,
                  second_signature: signatures.Base) -> None:
    assert implication(signature == second_signature,
                       second_signature == signature)


def test_transitivity(signature: signatures.Base,
                      second_signature: signatures.Base,
                      third_signature: signatures.Base) -> None:
    assert implication(signature == second_signature
                       and second_signature == third_signature,
                       signature == third_signature)
