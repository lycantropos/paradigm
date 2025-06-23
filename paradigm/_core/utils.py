from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from typing_extensions import ParamSpec

_Params = ParamSpec('_Params')
_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')


def decorate_if(
    decorator: Callable[[Callable[_Params, _T1]], Any],
    condition: bool,  # noqa: FBT001
    /,
) -> Callable[[Callable[_Params, _T1]], Any]:
    return decorator if condition else _identity_decorator


singledispatchmethod = functools.singledispatchmethod


def _identity_decorator(
    value: Callable[_Params, _T1],
) -> Callable[_Params, _T1]:
    return value
