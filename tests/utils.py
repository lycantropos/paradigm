from __future__ import annotations

import pickle
import types
from typing import Any, Callable, ParamSpec, TypeVar

from hypothesis.strategies import SearchStrategy

from paradigm.base import (
    OptionalParameter,
    OverloadedSignature,
    PlainSignature,
    RequiredParameter,
)

AnySignature = TypeVar('AnySignature', OverloadedSignature, PlainSignature)
AnyParameter = TypeVar('AnyParameter', OptionalParameter, RequiredParameter)
Strategy = SearchStrategy
_PredicateParamsT = ParamSpec('_PredicateParamsT')
Predicate = Callable[_PredicateParamsT, bool]
_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')
Args = tuple[_T1, ...]
Kwargs = dict[str, _T1]


def equivalence(left_statement: bool, right_statement: bool, /) -> bool:  # noqa: FBT001
    return not left_statement ^ right_statement


def implication(antecedent: bool, consequent: bool, /) -> bool:  # noqa: FBT001
    return not antecedent or consequent


def negate(predicate: Predicate) -> Predicate:
    def negated(
        *args: _PredicateParamsT.args, **kwargs: _PredicateParamsT.kwargs
    ) -> bool:
        return not predicate(*args, **kwargs)

    return negated


def pack(function: Callable[..., _T2]) -> Callable[[tuple[_T1, ...]], _T2]:
    def packed(
        args: tuple[_T1, ...], kwargs: dict[str, Any] | None = None
    ) -> _T2:
        return function(*args, **({} if kwargs is None else kwargs))

    return packed


def round_trip_pickle(object_: Any) -> Any:
    return pickle.loads(pickle.dumps(object_))


def to_contents(object_: types.ModuleType | type) -> list[Any]:
    return list(vars(object_).values())
