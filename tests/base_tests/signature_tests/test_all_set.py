from hypothesis import given

from tests.utils import ArgT, Args, KwArgs, Signature, implication

from .strategies import (
    non_variadic_signature_with_unexpected_args_strategy,
    non_variadic_signature_with_unexpected_kwargs_strategy,
    signature_strategy,
)


@given(signature_strategy)
def test_relation_with_expects(signature: Signature) -> None:
    assert implication(signature.all_set(), signature.expects())


@given(non_variadic_signature_with_unexpected_args_strategy)
def test_unexpected_args(
    signature_with_unexpected_args: tuple[Signature, Args[ArgT]],
) -> None:
    signature, unexpected_args = signature_with_unexpected_args

    assert not signature.all_set(*unexpected_args)


@given(non_variadic_signature_with_unexpected_kwargs_strategy)
def test_unexpected_kwargs(
    signature_with_unexpected_kwargs: tuple[Signature, KwArgs[ArgT]],
) -> None:
    signature, unexpected_kwargs = signature_with_unexpected_kwargs

    assert not signature.all_set(**unexpected_kwargs)
