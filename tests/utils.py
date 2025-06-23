from __future__ import annotations

import pickle
import types
from collections.abc import Callable
from typing import Any, ParamSpec, TypeAlias, TypeVar

from hypothesis.strategies import SearchStrategy

from paradigm.base import OverloadedSignature, PlainSignature

Strategy = SearchStrategy
ArgT = TypeVar('ArgT')
Args = tuple[ArgT, ...]
KwArgs = dict[str, ArgT]
Signature: TypeAlias = OverloadedSignature[Any] | PlainSignature[Any]


def equivalence(left_statement: bool, right_statement: bool, /) -> bool:  # noqa: FBT001
    return not left_statement ^ right_statement


def implication(antecedent: bool, consequent: bool, /) -> bool:  # noqa: FBT001
    return not antecedent or consequent


_PredicateParamsT = ParamSpec('_PredicateParamsT')
Predicate = Callable[_PredicateParamsT, bool]


def negate(
    predicate: Predicate[_PredicateParamsT],
) -> Predicate[_PredicateParamsT]:
    def negated(
        *args: _PredicateParamsT.args, **kwargs: _PredicateParamsT.kwargs
    ) -> bool:
        return not predicate(*args, **kwargs)

    return negated


_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')


def pack(
    function: Callable[..., _T2],
) -> (
    Callable[[tuple[ArgT, ...]], _T2]
    | Callable[[tuple[ArgT, ...], dict[str, ArgT]], _T2]
):
    def packed(
        args: tuple[ArgT, ...], kwargs: dict[str, ArgT] | None = None
    ) -> _T2:
        return function(*args, **({} if kwargs is None else kwargs))

    return packed


def round_trip_pickle(object_: Any) -> Any:
    return pickle.loads(pickle.dumps(object_))


def to_contents(object_: types.ModuleType | type) -> list[Any]:
    return list(vars(object_).values())
