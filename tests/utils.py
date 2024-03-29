import pickle
import types
from typing import (Any,
                    Callable,
                    Dict,
                    List,
                    Optional,
                    Tuple,
                    TypeVar,
                    Union)

from hypothesis.strategies import SearchStrategy

from paradigm.base import (OptionalParameter,
                           OverloadedSignature,
                           PlainSignature,
                           RequiredParameter)

AnySignature = TypeVar('AnySignature', OverloadedSignature, PlainSignature)
AnyParameter = TypeVar('AnyParameter', OptionalParameter, RequiredParameter)
Strategy = SearchStrategy
Predicate = Callable[..., bool]
_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')
Args = Tuple[_T1, ...]
Kwargs = Dict[str, _T1]


def equivalence(left_statement: bool, right_statement: bool) -> bool:
    return not left_statement ^ right_statement


def implication(antecedent: bool, consequent: bool) -> bool:
    return not antecedent or consequent


def negate(predicate: Predicate) -> Predicate:
    def negated(*args, **kwargs) -> bool:
        return not predicate(*args, **kwargs)

    return negated


def pack(function: Callable[..., _T2]) -> Callable[[Tuple[_T1, ...]], _T2]:
    def packed(args: Tuple[_T1, ...],
               kwargs: Optional[Dict[str, Any]] = None) -> _T2:
        return function(*args, **({} if kwargs is None else kwargs))

    return packed


def round_trip_pickle(object_: Any) -> Any:
    return pickle.loads(pickle.dumps(object_))


def to_contents(object_: Union[types.ModuleType, type]) -> List[Any]:
    return list(vars(object_).values())
