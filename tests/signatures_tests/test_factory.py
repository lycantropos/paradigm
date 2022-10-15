import platform
from functools import partial
from types import (BuiltinFunctionType,
                   FunctionType,
                   MethodDescriptorType,
                   MethodType,
                   WrapperDescriptorType)
from typing import (Any,
                    Callable)

import pytest
from hypothesis import given

from paradigm import (models,
                      signatures)
from tests.utils import slow_data_generation
from . import strategies


@given(strategies.built_in_functions,
       strategies.classes,
       strategies.functions,
       strategies.methods,
       strategies.methods_descriptors,
       strategies.wrappers_descriptors,
       strategies.partial_callables,
       strategies.top_coverage_callables)
@slow_data_generation
def test_basic(built_in_function: BuiltinFunctionType,
               class_: type,
               function: FunctionType,
               method: MethodType,
               method_descriptor: MethodDescriptorType,
               wrapper_descriptor: WrapperDescriptorType,
               partial_callable: partial,
               top_coverage_callable: Callable[..., Any]) -> None:
    for callable_ in (built_in_function,
                      class_,
                      function,
                      method,
                      method_descriptor,
                      wrapper_descriptor,
                      partial_callable,
                      top_coverage_callable):
        result = signatures.factory(callable_)

        assert isinstance(result, models.Base)


@pytest.mark.skipif(platform.python_implementation() == 'PyPy',
                    reason='requires CPython')
@given(strategies.overloaded_callables)
def test_overloaded(callable_: Callable[..., Any]) -> None:
    result = signatures.factory(callable_)

    assert isinstance(result, models.Overloaded)


@pytest.mark.skipif(platform.python_implementation() == 'PyPy',
                    reason='requires CPython')
@given(strategies.unsupported_callables)
@slow_data_generation
def test_fail(callable_: Callable[..., Any]) -> None:
    # e.g. `AttributeError` is raised
    # by `curses.window.border` method on Python3.8
    with pytest.raises((AttributeError, ValueError)):
        signatures.factory(callable_)
