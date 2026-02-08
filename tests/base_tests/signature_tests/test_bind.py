from __future__ import annotations

from collections.abc import Iterable
from functools import partial, singledispatch

import pytest
from hypothesis import given

from paradigm._core.models import to_parameters_by_name
from paradigm.base import (
    OptionalParameter,
    OverloadedSignature,
    PlainSignature,
)
from tests.utils import ArgT, Args, KwArgs, Signature, implication

from .strategies import (
    non_variadic_signature_with_unexpected_args_strategy,
    signature_strategy,
    signature_with_expected_args_strategy,
    signature_with_expected_kwargs_strategy,
)


@given(signature_strategy)
def test_basic(signature: Signature) -> None:
    result = signature.bind()

    assert result == signature


@given(signature_with_expected_args_strategy)
def test_expected_args(
    signature_with_expected_args: tuple[Signature, Args[ArgT]],
) -> None:
    signature, expected_args = signature_with_expected_args

    result = signature.bind(*expected_args)

    assert implication(bool(expected_args), result != signature)


@given(signature_with_expected_kwargs_strategy)
def test_expected_kwargs(
    signature_with_expected_kwargs: tuple[Signature, KwArgs[ArgT]],
) -> None:
    signature, expected_kwargs = signature_with_expected_kwargs

    result = signature.bind(**expected_kwargs)

    assert implication(
        bool(expected_kwargs),
        signature_parameters_has_defaults(result, names=expected_kwargs),
    )


@singledispatch
def signature_parameters_has_defaults(
    signature: Signature,
    /,
    *,
    names: Iterable[str],  # noqa: ARG001
) -> bool:
    raise TypeError(f'Unsupported signature type: {type(signature)}.')


@signature_parameters_has_defaults.register(PlainSignature)
def _(signature: PlainSignature[ArgT], /, *, names: Iterable[str]) -> bool:
    parameters = to_parameters_by_name(signature.parameters)
    return all(
        (
            isinstance(parameter := parameters[name], OptionalParameter)
            and parameter.has_default
        )
        for name in names
    )


@signature_parameters_has_defaults.register(OverloadedSignature)
def _(
    signature: OverloadedSignature[ArgT], /, *, names: Iterable[str]
) -> bool:
    return all(
        map(
            partial(signature_parameters_has_defaults, names=names),
            signature.signatures,
        )
    )


@given(non_variadic_signature_with_unexpected_args_strategy)
def test_unexpected_args(
    signature_with_unexpected_args: tuple[Signature, Args[ArgT]],
) -> None:
    signature, unexpected_args = signature_with_unexpected_args

    with pytest.raises(TypeError):
        signature.bind(*unexpected_args)


@given(non_variadic_signature_with_unexpected_args_strategy)
def test_unexpected_kwargs(
    signature_with_unexpected_kwargs: tuple[Signature, KwArgs[ArgT]],
) -> None:
    signature, unexpected_kwargs = signature_with_unexpected_kwargs

    with pytest.raises(TypeError):
        signature.bind(**unexpected_kwargs)
