import keyword
from string import ascii_letters
from typing import (Optional,
                    Tuple,
                    TypeVar)

from hypothesis import strategies

from tests.utils import (Strategy,
                         negate)

_T = TypeVar('_T')


def to_homogeneous_tuples(elements: Optional[Strategy[_T]] = None,
                          *,
                          min_size: int = 0,
                          max_size: Optional[int] = None
                          ) -> Strategy[Tuple[_T, ...]]:
    return (strategies.lists(elements,
                             min_size=min_size,
                             max_size=max_size)
            .map(tuple))


identifiers_characters = strategies.sampled_from(ascii_letters + '_')
identifiers = (strategies.text(identifiers_characters,
                               min_size=1)
               .filter(str.isidentifier)
               .filter(negate(keyword.iskeyword)))
