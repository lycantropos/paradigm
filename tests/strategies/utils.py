import ast
import importlib
import keyword
from pathlib import Path
from string import ascii_letters
from typing import (Optional,
                    Tuple)

from hypothesis import strategies

from paradigm.definitions import (is_supported,
                                  stdlib_modules_names,
                                  unsupported)
from paradigm.hints import Domain
from tests.utils import (Strategy,
                         negate,
                         pack)


def to_homogeneous_tuples(elements: Optional[Strategy[Domain]] = None,
                          *,
                          min_size: int = 0,
                          max_size: Optional[int] = None
                          ) -> Strategy[Tuple[Domain, ...]]:
    return (strategies.lists(elements,
                             min_size=min_size,
                             max_size=max_size)
            .map(tuple))


identifiers_characters = strategies.sampled_from(ascii_letters + '_')
identifiers = (strategies.text(identifiers_characters,
                               min_size=1)
               .filter(str.isidentifier)
               .filter(negate(keyword.iskeyword)))

paths = strategies.lists(identifiers).map(pack(Path))


def is_valid_source(string: str) -> bool:
    try:
        ast.parse(string)
    except (ValueError, SyntaxError):
        return False
    else:
        return True


keywords_lists = strategies.lists(strategies.sampled_from(keyword.kwlist))
invalid_source_lines = ((keywords_lists.map(' '.join)
                         | keywords_lists.map(';'.join))
                        .filter(negate(is_valid_source)))
invalid_sources = strategies.lists(invalid_source_lines,
                                   min_size=1).map('\n'.join)
modules_list = list(filter(is_supported,
                           map(importlib.import_module,
                               stdlib_modules_names
                               - unsupported.stdlib_modules_names)))
modules = strategies.sampled_from(modules_list)
