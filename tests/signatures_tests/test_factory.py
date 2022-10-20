from typing import (Any,
                    Callable)

from hypothesis import given

from paradigm import (models,
                      signatures)
from . import strategies


@given(strategies.callables)
def test_basic(callable_: Callable[..., Any]) -> None:
    result = signatures.factory(callable_)

    assert isinstance(result, models.Base)


@given(strategies.overloaded_callables)
def test_overloaded(callable_: Callable[..., Any]) -> None:
    result = signatures.factory(callable_)

    assert isinstance(result, models.Overloaded)
