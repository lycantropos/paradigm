from functools import (partial,
                       singledispatch)
from typing import (Iterable,
                    Tuple)

import pytest
from hypothesis import given

from paradigm import models
from tests.utils import (Args,
                         Kwargs,
                         implication)
from . import strategies


@given(strategies.signatures)
def test_basic(signature) -> None:
    result = signature.bind()

    assert result == signature


@given(strategies.non_empty_signatures_with_expected_args)
def test_expected_args(signature_with_expected_args: Tuple[models.Base, Args]
                       ) -> None:
    signature, expected_args = signature_with_expected_args

    result = signature.bind(*expected_args)

    assert implication(bool(expected_args),
                       result != signature)


@given(strategies.non_empty_signatures_with_expected_kwargs)
def test_expected_kwargs(
        signature_with_expected_kwargs: Tuple[models.Base, Kwargs]) -> None:
    signature, expected_kwargs = signature_with_expected_kwargs
    result = signature.bind(**expected_kwargs)

    assert implication(bool(expected_kwargs),
                       signature_parameters_has_defaults(
                               result,
                               names=expected_kwargs))


@singledispatch
def signature_parameters_has_defaults(signature: models.Base,
                                      *,
                                      names: Iterable[str]) -> bool:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@signature_parameters_has_defaults.register(models.Plain)
def plain_signature_parameters_has_defaults(signature: models.Plain,
                                            *,
                                            names: Iterable[str]) -> bool:
    parameters = models.to_parameters_by_name(signature.parameters)
    return all(parameters[name].has_default for name in names)


@signature_parameters_has_defaults.register(models.Overloaded)
def overloaded_signature_parameters_has_defaults(
        signature: models.Overloaded,
        *,
        names: Iterable[str]) -> bool:
    return all(map(partial(signature_parameters_has_defaults,
                           names=names),
                   signature.signatures))


@given(strategies.non_variadic_signatures_with_unexpected_args)
def test_unexpected_args(
        signature_with_unexpected_args: Tuple[models.Base, Args]) -> None:
    signature, unexpected_args = signature_with_unexpected_args

    with pytest.raises(TypeError):
        signature.bind(*unexpected_args)


@given(strategies.non_variadic_signatures_with_unexpected_args)
def test_unexpected_kwargs(
        signature_with_unexpected_kwargs: Tuple[models.Base, Kwargs]) -> None:
    signature, unexpected_kwargs = signature_with_unexpected_kwargs

    with pytest.raises(TypeError):
        signature.bind(**unexpected_kwargs)
