from __future__ import annotations

import keyword
from string import ascii_letters
from typing import TypeVar

from hypothesis import strategies

from tests.utils import Strategy, negate

_T = TypeVar('_T')


def to_homogeneous_tuples(
    elements: Strategy[_T] | None = None,
    *,
    min_size: int = 0,
    max_size: int | None = None,
) -> Strategy[tuple[_T, ...]]:
    return strategies.lists(
        elements, min_size=min_size, max_size=max_size
    ).map(tuple)


identifiers_characters = strategies.sampled_from(ascii_letters + '_')
identifiers = (
    strategies.text(identifiers_characters, min_size=1)
    .filter(str.isidentifier)
    .filter(negate(keyword.iskeyword))
)
