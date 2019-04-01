import platform
from itertools import chain
from typing import (Any,
                    Callable)

import pytest

from paradigm import signatures


def test_basic(callable_: Callable[..., Any]) -> None:
    result = signatures.factory(callable_)

    if isinstance(result, signatures.Plain):
        assert result.all_set() or is_plain_signature_unset(result)
    else:
        assert isinstance(result, signatures.Overloaded)
        assert result.all_set() or is_overloaded_signature_unset(result)


@pytest.mark.skipif(platform.python_implementation() == 'PyPy',
                    reason='requires CPython')
def test_overloaded(overloaded_callable: Callable[..., Any]) -> None:
    result = signatures.factory(overloaded_callable)

    assert isinstance(result, signatures.Overloaded)
    assert result.all_set() or is_overloaded_signature_unset(result)


def is_plain_signature_unset(signature: signatures.Plain) -> bool:
    variadic_parameters_kinds = {signatures.Parameter.Kind.VARIADIC_POSITIONAL,
                                 signatures.Parameter.Kind.VARIADIC_KEYWORD}
    non_variadic_parameters_kinds = (set(signatures.Parameter.Kind)
                                     - variadic_parameters_kinds)
    non_variadic_parameters = chain.from_iterable(
            signature.parameters_by_kind[kind]
            for kind in non_variadic_parameters_kinds)
    return not (signatures.all_parameters_has_defaults(non_variadic_parameters)
                or all(parameter.kind in variadic_parameters_kinds
                       for parameter in signature.parameters))


def is_overloaded_signature_unset(signature: signatures.Overloaded) -> bool:
    return all(map(is_plain_signature_unset, signature.signatures))
