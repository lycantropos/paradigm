from hypothesis import given

from tests.utils import ArgT, Args, KwArgs, Signature

from . import strategies


@given(strategies.signatures)
def test_basic(signature: Signature) -> None:
    assert signature.expects()


@given(strategies.signatures_with_expected_args)
def test_expected_args(
    signature_with_expected_args: tuple[Signature, Args[ArgT]],
) -> None:
    signature, expected_args = signature_with_expected_args

    assert signature.expects(*expected_args)


@given(strategies.signatures_with_expected_kwargs)
def test_expected_kwargs(
    signature_with_expected_kwargs: tuple[Signature, KwArgs[ArgT]],
) -> None:
    signature, expected_kwargs = signature_with_expected_kwargs

    assert signature.expects(**expected_kwargs)


@given(strategies.non_variadic_signatures_with_unexpected_args)
def test_unexpected_args(
    signature_with_unexpected_args: tuple[Signature, Args[ArgT]],
) -> None:
    signature, unexpected_args = signature_with_unexpected_args

    assert not signature.expects(*unexpected_args)


@given(strategies.non_variadic_signatures_with_unexpected_kwargs)
def test_unexpected_kwargs(
    signature_with_unexpected_kwargs: tuple[Signature, KwArgs[ArgT]],
) -> None:
    signature, unexpected_kwargs = signature_with_unexpected_kwargs

    assert not signature.expects(**unexpected_kwargs)
