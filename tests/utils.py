import pickle
from typing import (Any,
                    Callable,
                    Dict,
                    Tuple)

from hypothesis import settings
from hypothesis.searchstrategy import SearchStrategy

from paradigm.hints import (Domain,
                            Map,
                            Range)

Strategy = SearchStrategy
Predicate = Callable[..., bool]
Args = Tuple[Domain, ...]
Kwargs = Dict[str, Domain]


def equivalence(left_statement: bool, right_statement: bool) -> bool:
    return not left_statement ^ right_statement


def implication(antecedent: bool, consequent: bool) -> bool:
    return not antecedent or consequent


def negate(predicate: Predicate) -> Predicate:
    def negated(*args, **kwargs) -> bool:
        return not predicate(*args, **kwargs)

    return negated


def pack(function: Callable[..., Range]) -> Map[Tuple[Domain, ...], Range]:
    def packed(args: Tuple[Domain, ...]) -> Range:
        return function(*args)

    return packed


def round_trip_pickle(object_: Any) -> Any:
    return pickle.loads(pickle.dumps(object_))


slow_data_generation = settings(max_examples=30)
