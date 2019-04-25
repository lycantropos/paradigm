from typing import Tuple

from hypothesis import given

from paradigm import models
from tests.utils import (Args,
                         Kwargs,
                         implication)
from . import strategies


@given(strategies.signatures)
def test_relation_with_expects(signature: models.Base) -> None:
    assert implication(signature.all_set(), signature.expects())


@given(strategies.non_variadic_signatures_with_unexpected_args)
def test_unexpected_args(
        signature_with_unexpected_args: Tuple[models.Base, Args]) -> None:
    signature, unexpected_args = signature_with_unexpected_args

    assert not signature.all_set(*unexpected_args)


@given(strategies.non_variadic_signatures_with_unexpected_kwargs)
def test_unexpected_kwargs(
        signature_with_unexpected_kwargs: Tuple[models.Base, Kwargs]) -> None:
    signature, unexpected_kwargs = signature_with_unexpected_kwargs

    assert not signature.all_set(**unexpected_kwargs)
