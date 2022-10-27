from typing import Tuple

from hypothesis import given

from tests.utils import (AnySignature,
                         Args,
                         Kwargs)
from . import strategies


@given(strategies.signatures)
def test_basic(signature: AnySignature) -> None:
    assert signature.expects()


@given(strategies.non_empty_signatures_with_expected_args)
def test_expected_args(
        signature_with_expected_args: Tuple[AnySignature, Args]
) -> None:
    signature, expected_args = signature_with_expected_args

    assert signature.expects(*expected_args)


@given(strategies.non_empty_signatures_with_expected_kwargs)
def test_expected_args(
        signature_with_expected_kwargs: Tuple[AnySignature, Kwargs]
) -> None:
    signature, expected_kwargs = signature_with_expected_kwargs

    assert signature.expects(**expected_kwargs)


@given(strategies.non_variadic_signatures_with_unexpected_args)
def test_unexpected_args(
        signature_with_unexpected_args: Tuple[AnySignature, Args]
) -> None:
    signature, unexpected_args = signature_with_unexpected_args

    assert not signature.expects(*unexpected_args)


@given(strategies.non_variadic_signatures_with_unexpected_kwargs)
def test_unexpected_kwargs(
        signature_with_unexpected_kwargs: Tuple[AnySignature, Kwargs]
) -> None:
    signature, unexpected_kwargs = signature_with_unexpected_kwargs

    assert not signature.expects(**unexpected_kwargs)
