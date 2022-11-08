from typing import (Any,
                    Callable)

from hypothesis import given

from paradigm._core import catalog
from paradigm._core.sources import stdlib_modules_paths
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
    module_path, _ = catalog.qualified_path_from(callable_)
    assert module_path in stdlib_modules_paths, module_path

    result = signature_from_callable(callable_)

    assert isinstance(result, OverloadedSignature)
