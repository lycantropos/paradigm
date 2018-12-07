from typing import (Any,
                    Callable)

from paradigm import signatures
from tests.utils import implication


def test_reflexivity(callable_: Callable[..., Any]) -> None:
    signature = signatures.factory(callable_)

    assert signature == signature


def test_symmetry(callable_: Callable[..., Any],
                  second_callable) -> None:
    signature = signatures.factory(callable_)
    second_signature = signatures.factory(second_callable)

    assert implication(signature == second_signature,
                       second_signature == signature)


def test_transitivity(callable_: Callable[..., Any],
                      second_callable,
                      third_callable) -> None:
    signature = signatures.factory(callable_)
    second_signature = signatures.factory(second_callable)
    third_signature = signatures.factory(third_callable)

    assert implication(signature == second_signature
                       and second_signature == third_signature,
                       signature == third_signature)
