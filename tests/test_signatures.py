import platform
from itertools import chain
from types import (BuiltinFunctionType,
                   FunctionType,
                   MethodType)
from typing import (Any,
                    Callable)

import pytest

from paradigm import signatures
from paradigm.hints import (MethodDescriptorType,
                            WrapperDescriptorType)


def test_factory(built_in_function: BuiltinFunctionType,
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
def test_factory_fail(unsupported_callable: Callable[..., Any]) -> None:
    with pytest.raises(ValueError):
        signatures.factory(unsupported_callable)


def test_has_unset_parameters(callable_: Callable[..., Any]) -> None:
    result = signatures.factory(callable_)

    if isinstance(result, signatures.Plain):
        assert (result.has_unset_parameters()
                or is_plain_signature_all_set(result))
    else:
        assert isinstance(result, signatures.Overloaded)
        assert (result.has_unset_parameters()
                or all(map(is_plain_signature_all_set, result.signatures)))


def is_plain_signature_all_set(signature: signatures.Plain) -> bool:
    variadic_parameters_kinds = {signatures.Parameter.Kind.VARIADIC_POSITIONAL,
                                 signatures.Parameter.Kind.VARIADIC_KEYWORD}
    non_variadic_parameters_kinds = (set(signatures.Parameter.Kind)
                                     - variadic_parameters_kinds)
    non_variadic_parameters = chain.from_iterable(
            signature.parameters_by_kind[kind]
            for kind in non_variadic_parameters_kinds)
    return (all(parameter.has_default
                for parameter in non_variadic_parameters)
            or all(parameter.kind in variadic_parameters_kinds
                   for parameter in signature.parameters))
