import functools
import sys
from typing import (Any,
                    Callable)

from hypothesis import given, note

from paradigm._core import catalog
from paradigm.base import (OverloadedSignature,
                           PlainSignature,
                           signature_from_callable)
from . import strategies


@given(strategies.callables)
def test_basic(callable_: Callable[..., Any]) -> None:
    result = signature_from_callable(callable_)

    assert isinstance(result, (OverloadedSignature, PlainSignature))


@given(strategies.overloaded_callables)
def test_overloaded(callable_: Callable[..., Any]) -> None:
    note(f'{sys.base_prefix}, {sys.exec_prefix}')
    try:
        result = signature_from_callable(callable_)
    except Exception:
        raise ValueError({
            name: catalog.qualified_path_from(value)
            for name, value in vars(functools).items()
            if callable(value)
        })

    assert isinstance(result, OverloadedSignature)
