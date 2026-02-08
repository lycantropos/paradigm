from __future__ import annotations

import keyword
from string import ascii_letters
from typing import TypeVar

from hypothesis import strategies

from tests.utils import Strategy, negate

_T = TypeVar('_T')


def to_homogeneous_tuple_strategy(
    elements: Strategy[_T], *, min_size: int = 0, max_size: int | None = None
) -> Strategy[tuple[_T, ...]]:
    return strategies.lists(
        elements, min_size=min_size, max_size=max_size
    ).map(tuple)


identifier_character_strategy = strategies.sampled_from(ascii_letters + '_')
identifier_strategy = (
    strategies.text(identifier_character_strategy, min_size=1)
    .filter(str.isidentifier)
    .filter(negate(keyword.iskeyword))
)
