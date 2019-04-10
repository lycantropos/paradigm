from functools import singledispatch
from typing import (Any,
                    Callable,
                    Tuple)

from hypothesis import (Phase,
                        core,
                        settings)
from hypothesis.errors import (NoSuchExample,
                               Unsatisfiable)
from hypothesis.searchstrategy import SearchStrategy

from paradigm import models
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


@singledispatch
def is_signature_empty(signature: models.Base) -> bool:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@is_signature_empty.register(models.Plain)
def is_plain_signature_empty(signature: models.Plain) -> bool:
    return False


@is_signature_empty.register(models.Overloaded)
def is_overloaded_signature_empty(signature: models.Overloaded) -> bool:
    return not signature.signatures
