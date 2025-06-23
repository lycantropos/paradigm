from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, overload

from typing_extensions import Never, TypeVarTuple

from ._core import models as _models, signatures as _signatures

OptionalParameter = _models.OptionalParameter
OverloadedSignature = _models.OverloadedSignature
ParameterKind = _models.ParameterKind
PlainSignature = _models.PlainSignature
RequiredParameter = _models.RequiredParameter


_T1_contra = TypeVar('_T1_contra', contravariant=True)
_T2_contra = TypeVar('_T2_contra', contravariant=True)
_T3_contra = TypeVar('_T3_contra', contravariant=True)
_T4_contra = TypeVar('_T4_contra', contravariant=True)
_T5_contra = TypeVar('_T5_contra', contravariant=True)
_T6_contra = TypeVar('_T6_contra', contravariant=True)
_Ts = TypeVarTuple('_Ts')


@overload
def signature_from_callable(
    callable_: Callable[[], Any], /
) -> OverloadedSignature[Never] | PlainSignature[Never]: ...


@overload
def signature_from_callable(
    callable_: Callable[[_T1_contra], Any], /
) -> OverloadedSignature[_T1_contra] | PlainSignature[_T1_contra]: ...


@overload
def signature_from_callable(
    callable_: Callable[[_T1_contra, _T2_contra], Any], /
) -> (
    OverloadedSignature[_T1_contra | _T2_contra]
    | PlainSignature[_T1_contra | _T2_contra]
): ...


@overload
def signature_from_callable(
    callable_: Callable[[_T1_contra, _T2_contra, _T3_contra], Any], /
) -> (
    OverloadedSignature[_T1_contra | _T2_contra | _T3_contra]
    | PlainSignature[_T1_contra | _T2_contra | _T3_contra]
): ...


@overload
def signature_from_callable(
    callable_: Callable[[_T1_contra, _T2_contra, _T3_contra, _T4_contra], Any],
    /,
) -> (
    OverloadedSignature[_T1_contra | _T2_contra | _T3_contra | _T4_contra]
    | PlainSignature[_T1_contra | _T2_contra | _T3_contra | _T4_contra]
): ...


@overload
def signature_from_callable(
    callable_: Callable[
        [_T1_contra, _T2_contra, _T3_contra, _T4_contra, _T5_contra], Any
    ],
    /,
) -> (
    OverloadedSignature[
        _T1_contra | _T2_contra | _T3_contra | _T4_contra | _T5_contra
    ]
    | PlainSignature[
        _T1_contra | _T2_contra | _T3_contra | _T4_contra | _T5_contra
    ]
): ...


@overload
def signature_from_callable(
    callable_: Callable[
        [
            _T1_contra,
            _T2_contra,
            _T3_contra,
            _T4_contra,
            _T5_contra,
            _T6_contra,
        ],
        Any,
    ],
    /,
) -> (
    OverloadedSignature[
        _T1_contra
        | _T2_contra
        | _T3_contra
        | _T4_contra
        | _T5_contra
        | _T6_contra
    ]
    | PlainSignature[
        _T1_contra
        | _T2_contra
        | _T3_contra
        | _T4_contra
        | _T5_contra
        | _T6_contra
    ]
): ...


@overload
def signature_from_callable(
    callable_: Callable[
        [
            _T1_contra,
            _T2_contra,
            _T3_contra,
            _T4_contra,
            _T5_contra,
            _T6_contra,
            *_Ts,
        ],
        Any,
    ],
    /,
) -> (
    OverloadedSignature[
        _T1_contra
        | _T2_contra
        | _T3_contra
        | _T4_contra
        | _T5_contra
        | _T6_contra
    ]
    | PlainSignature[
        _T1_contra
        | _T2_contra
        | _T3_contra
        | _T4_contra
        | _T5_contra
        | _T6_contra
    ]
): ...


def signature_from_callable(
    callable_: Callable[..., Any], /
) -> OverloadedSignature[Any] | PlainSignature[Any]:
    return _signatures.from_callable(callable_)
