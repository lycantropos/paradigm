from typing import (Any,
                    Callable)

from hypothesis import given

from paradigm import signatures
from . import strategies


@given(strategies.callables)
def test_basic(callable_: Callable[..., Any]) -> None:
    result = signatures.from_callable(callable_)

    assert isinstance(result, (signatures.Overloaded, signatures.Plain))


@given(strategies.overloaded_callables)
def test_overloaded(callable_: Callable[..., Any]) -> None:
    result = signatures.from_callable(callable_)

    assert isinstance(result, signatures.Overloaded)
