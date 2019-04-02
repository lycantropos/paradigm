from typing import (Any,
                    Callable,
                    Tuple)

from hypothesis import (Phase,
                        core,
                        settings)
from hypothesis.errors import (NoSuchExample,
                               Unsatisfiable)
from hypothesis.searchstrategy import SearchStrategy

from paradigm.hints import (Domain,
                            Map,
                            Range)

Predicate = Callable[..., bool]


def find(strategy: SearchStrategy[Domain]) -> Domain:
    first_object_list = []

    def condition(object_: Any) -> bool:
        if first_object_list:
            return True
        else:
            first_object_list.append(object_)
            return False

    try:
        return core.find(strategy,
                         condition,
                         settings=settings(database=None,
                                           phases=tuple(set(Phase)
                                                        - {Phase.shrink})))
    except (NoSuchExample, Unsatisfiable) as search_error:
        try:
            result, = first_object_list
        except ValueError as unpacking_error:
            raise unpacking_error from search_error
        else:
            return result


def implication(antecedent: bool, consequent: bool) -> bool:
    return not antecedent or consequent


def negate(predicate: Predicate) -> Predicate:
    def negated(*args: Domain, **kwargs: Domain) -> bool:
        return not predicate(*args, **kwargs)

    return negated


def pack(function: Callable[..., Range]) -> Map[Tuple[Domain, ...], Range]:
    def packed(args: Tuple[Domain, ...]) -> Range:
        return function(*args)

    return packed
