from functools import (partial,
                       singledispatch)
from typing import (Any,
                    Dict,
                    Iterable,
                    Tuple)

import pytest

from paradigm import signatures
from tests.utils import implication


def test_basic(non_empty_signature: signatures.Base) -> None:
    result = non_empty_signature.bind()

    assert result == non_empty_signature


def test_expected_args(non_empty_signature: signatures.Base,
                       non_empty_signature_expected_args: Tuple[Any, ...]
                       ) -> None:
    result = non_empty_signature.bind(*non_empty_signature_expected_args)

    assert implication(bool(non_empty_signature_expected_args),
                       result != non_empty_signature)


def test_expected_kwargs(non_empty_signature: signatures.Base,
                         non_empty_signature_expected_kwargs: Dict[str, Any]
                         ) -> None:
    result = non_empty_signature.bind(**non_empty_signature_expected_kwargs)

    assert implication(bool(non_empty_signature_expected_kwargs),
                       signature_parameters_has_defaults(
                               result,
                               names=non_empty_signature_expected_kwargs))


@singledispatch
def signature_parameters_has_defaults(signature: signatures.Base,
                                      *,
                                      names: Iterable[str]) -> bool:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@signature_parameters_has_defaults.register(signatures.Plain)
def plain_signature_parameters_has_defaults(signature: signatures.Plain,
                                            *,
                                            names: Iterable[str]) -> bool:
    parameters = signatures.to_parameters_by_name(signature.parameters)
    return all(parameters[name].has_default for name in names)


@signature_parameters_has_defaults.register(signatures.Overloaded)
def overloaded_signature_parameters_has_defaults(
        signature: signatures.Overloaded,
        *,
        names: Iterable[str]) -> bool:
    return all(map(partial(signature_parameters_has_defaults,
                           names=names),
                   signature.signatures))


def test_unexpected_args(
        non_variadic_signature: signatures.Base,
        non_variadic_signature_unexpected_args: Tuple[Any, ...]) -> None:
    with pytest.raises(TypeError):
        non_variadic_signature.bind(*non_variadic_signature_unexpected_args)


def test_unexpected_kwargs(
        non_variadic_signature: signatures.Base,
        non_variadic_signature_unexpected_kwargs: Dict[str, Any]) -> None:
    with pytest.raises(TypeError):
        non_variadic_signature.bind(**non_variadic_signature_unexpected_kwargs)
