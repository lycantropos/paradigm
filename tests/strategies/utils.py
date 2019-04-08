from keyword import iskeyword
from string import ascii_letters
from typing import (Optional,
                    Tuple)

from hypothesis import strategies
from hypothesis.searchstrategy import SearchStrategy

from paradigm.hints import Domain
from tests.utils import negate


def to_homogeneous_tuples(elements: Optional[SearchStrategy[Domain]] = None,
                          *,
                          min_size: int = 0,
                          max_size: Optional[int] = None
                          ) -> SearchStrategy[Tuple[Domain, ...]]:
    return (strategies.lists(elements,
                             min_size=min_size,
                             max_size=max_size)
            .map(tuple))


identifiers_characters = strategies.sampled_from(ascii_letters + '_')
identifiers = (strategies.text(identifiers_characters,
                               min_size=1)
               .filter(str.isidentifier)
               .filter(negate(iskeyword)))