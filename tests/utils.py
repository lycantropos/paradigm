from typing import Any

from hypothesis import core
from hypothesis.searchstrategy import SearchStrategy


def find(strategy: SearchStrategy) -> Any:
    return core.find(strategy,
                     lambda _: True)


def implication(antecedent: bool, consequent: bool) -> bool:
    return not antecedent or consequent
