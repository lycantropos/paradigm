from __future__ import annotations

import functools
import typing as t

import typing_extensions as te

_Params = te.ParamSpec('_Params')
_T1 = t.TypeVar('_T1')
_T2 = t.TypeVar('_T2')


def decorate_if(
        decorator: t.Callable[[t.Callable[_Params, _T1]], t.Any],
        condition: bool
) -> t.Callable[[t.Callable[_Params, _T1]], t.Any]:
    return decorator if condition else _identity_decorator


singledispatchmethod = functools.singledispatchmethod


def _identity_decorator(
        value: t.Callable[_Params, _T1]
) -> t.Callable[_Params, _T1]:
    return value
