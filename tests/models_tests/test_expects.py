from typing import (Any,
                    Dict,
                    Tuple)

from paradigm import models


def test_basic(non_empty_signature: models.Base) -> None:
    assert non_empty_signature.expects()


def test_expected_args(non_empty_signature: models.Base,
                       non_empty_signature_expected_args: Tuple[Any, ...]
                       ) -> None:
    assert non_empty_signature.expects(*non_empty_signature_expected_args)


def test_expected_kwargs(non_empty_signature: models.Base,
                         non_empty_signature_expected_kwargs: Dict[str, Any]
                         ) -> None:
    assert non_empty_signature.expects(**non_empty_signature_expected_kwargs)


def test_unexpected_args(
        non_variadic_signature: models.Base,
        non_variadic_signature_unexpected_args: Tuple[Any, ...]) -> None:
    assert not non_variadic_signature.expects(
            *non_variadic_signature_unexpected_args)


def test_unexpected_kwargs(
        non_variadic_signature: models.Base,
        non_variadic_signature_unexpected_kwargs: Dict[str, Any]) -> None:
    assert not non_variadic_signature.expects(
            **non_variadic_signature_unexpected_kwargs)
