from hypothesis import given

from tests.utils import ArgT, Args, KwArgs, Signature, implication

from . import strategies


@given(strategies.signatures)
def test_relation_with_expects(signature: Signature) -> None:
    assert implication(signature.all_set(), signature.expects())


@given(strategies.non_variadic_signatures_with_unexpected_args)
def test_unexpected_args(
    signature_with_unexpected_args: tuple[Signature, Args[ArgT]],
) -> None:
    signature, unexpected_args = signature_with_unexpected_args

    assert not signature.all_set(*unexpected_args)


@given(strategies.non_variadic_signatures_with_unexpected_kwargs)
def test_unexpected_kwargs(
    signature_with_unexpected_kwargs: tuple[Signature, KwArgs[ArgT]],
) -> None:
    signature, unexpected_kwargs = signature_with_unexpected_kwargs

    assert not signature.all_set(**unexpected_kwargs)
