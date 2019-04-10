from typing import (Any,
                    Dict,
                    Tuple)

from paradigm import models
from tests.utils import implication


def test_relation_with_expects(signature: models.Base) -> None:
    assert implication(signature.all_set(), signature.expects())


def test_unexpected_args(
        non_variadic_signature: models.Base,
        non_variadic_signature_unexpected_args: Tuple[Any, ...]) -> None:
    assert not non_variadic_signature.all_set(
            *non_variadic_signature_unexpected_args)


def test_unexpected_kwargs(
        non_variadic_signature: models.Base,
        non_variadic_signature_unexpected_kwargs: Dict[str, Any]) -> None:
    assert not non_variadic_signature.all_set(
            **non_variadic_signature_unexpected_kwargs)
