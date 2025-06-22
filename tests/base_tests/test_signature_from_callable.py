from typing import Any, Callable

from hypothesis import given

from paradigm.base import (
    OverloadedSignature,
    PlainSignature,
    signature_from_callable,
)

from . import strategies


@given(strategies.callables)
def test_basic(callable_: Callable[..., Any]) -> None:
    result = signature_from_callable(callable_)

    assert isinstance(result, (OverloadedSignature, PlainSignature))


@given(strategies.overloaded_callables)
def test_overloaded(callable_: Callable[..., Any]) -> None:
    result = signature_from_callable(callable_)

    assert isinstance(result, OverloadedSignature)
