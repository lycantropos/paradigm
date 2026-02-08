from hypothesis import given

from tests.utils import ArgT, Args, KwArgs, Signature

from .strategies import (
    non_variadic_signature_with_unexpected_args_strategy,
    non_variadic_signature_with_unexpected_kwargs_strategy,
    signature_strategy,
    signature_with_expected_args_strategy,
    signature_with_expected_kwargs_strategy,
)


@given(signature_strategy)
def test_basic(signature: Signature) -> None:
    assert signature.expects()


@given(signature_with_expected_args_strategy)
def test_expected_args(
    signature_with_expected_args: tuple[Signature, Args[ArgT]],
) -> None:
    signature, expected_args = signature_with_expected_args

    assert signature.expects(*expected_args)


@given(signature_with_expected_kwargs_strategy)
def test_expected_kwargs(
    signature_with_expected_kwargs: tuple[Signature, KwArgs[ArgT]],
) -> None:
    signature, expected_kwargs = signature_with_expected_kwargs

    assert signature.expects(**expected_kwargs)


@given(non_variadic_signature_with_unexpected_args_strategy)
def test_unexpected_args(
    signature_with_unexpected_args: tuple[Signature, Args[ArgT]],
) -> None:
    signature, unexpected_args = signature_with_unexpected_args

    assert not signature.expects(*unexpected_args)


@given(non_variadic_signature_with_unexpected_kwargs_strategy)
def test_unexpected_kwargs(
    signature_with_unexpected_kwargs: tuple[Signature, KwArgs[ArgT]],
) -> None:
    signature, unexpected_kwargs = signature_with_unexpected_kwargs

    assert not signature.expects(**unexpected_kwargs)
