from functools import (partial,
                       singledispatch)
from typing import (Iterable,
                    Tuple)

import pytest
from hypothesis import given

from paradigm.base import (OverloadedSignature,
                           PlainSignature)
from paradigm._core.models import to_parameters_by_name
from tests.utils import (AnySignature,
                         Args,
                         Kwargs,
                         implication)
from . import strategies


@given(strategies.signatures)
def test_basic(signature: AnySignature) -> None:
    result = signature.bind()

    assert result == signature


@given(strategies.non_empty_signatures_with_expected_args)
def test_expected_args(
        signature_with_expected_args: Tuple[AnySignature, Args]
) -> None:
    signature, expected_args = signature_with_expected_args

    result = signature.bind(*expected_args)

    assert implication(bool(expected_args), result != signature)


@given(strategies.non_empty_signatures_with_expected_kwargs)
def test_expected_kwargs(
        signature_with_expected_kwargs: Tuple[AnySignature, Kwargs]
) -> None:
    signature, expected_kwargs = signature_with_expected_kwargs

    result = signature.bind(**expected_kwargs)

    assert implication(
            bool(expected_kwargs),
            signature_parameters_has_defaults(result,
                                              names=expected_kwargs)
    )


@singledispatch
def signature_parameters_has_defaults(signature: AnySignature,
                                      *,
                                      names: Iterable[str]) -> bool:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@signature_parameters_has_defaults.register(PlainSignature)
def _(signature: PlainSignature,
      *,
      names: Iterable[str]) -> bool:
    parameters = to_parameters_by_name(signature.parameters)
    return all(parameters[name].has_default for name in names)


@signature_parameters_has_defaults.register(OverloadedSignature)
def _(signature: OverloadedSignature,
      *,
      names: Iterable[str]) -> bool:
    return all(map(partial(signature_parameters_has_defaults,
                           names=names),
                   signature.signatures))


@given(strategies.non_variadic_signatures_with_unexpected_args)
def test_unexpected_args(
        signature_with_unexpected_args: Tuple[AnySignature, Args]
) -> None:
    signature, unexpected_args = signature_with_unexpected_args

    with pytest.raises(TypeError):
        signature.bind(*unexpected_args)


@given(strategies.non_variadic_signatures_with_unexpected_args)
def test_unexpected_kwargs(
        signature_with_unexpected_kwargs: Tuple[AnySignature, Kwargs]
) -> None:
    signature, unexpected_kwargs = signature_with_unexpected_kwargs

    with pytest.raises(TypeError):
        signature.bind(**unexpected_kwargs)
