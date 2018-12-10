import platform
from types import (BuiltinFunctionType,
                   FunctionType,
                   MethodType)
from typing import (Any,
                    Callable)

import pytest

from paradigm import signatures
from paradigm.hints import (MethodDescriptorType,
                            WrapperDescriptorType)


def test_basic(built_in_function: BuiltinFunctionType,
               class_: type,
               function: FunctionType,
               method: MethodType,
               method_descriptor: MethodDescriptorType,
               wrapper_descriptor: WrapperDescriptorType) -> None:
    for callable_ in (built_in_function,
                      class_,
                      function,
                      method,
                      method_descriptor,
                      wrapper_descriptor):
        result = signatures.factory(callable_)

        assert isinstance(result, signatures.Base)


@pytest.mark.skipif(platform.python_implementation() == 'PyPy',
                    reason='requires CPython')
def test_overloaded(overloaded_callable: Callable[..., Any]) -> None:
    result = signatures.factory(overloaded_callable)

    assert isinstance(result, signatures.Overloaded)


@pytest.mark.skipif(platform.python_implementation() == 'PyPy',
                    reason='requires CPython')
def test_fail(unsupported_callable: Callable[..., Any]) -> None:
    with pytest.raises(ValueError):
        signatures.factory(unsupported_callable)
