import ast
import importlib
import keyword
import os
from pathlib import Path
from string import ascii_letters
from typing import (List,
                    Optional,
                    Tuple,
                    TypeVar)

from hypothesis import strategies

from paradigm._core import catalog
from paradigm._core.discovery import supported_stdlib_modules_paths
from tests.contracts import is_supported
from tests.utils import (Strategy,
                         negate,
                         pack)

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


def to_valid_length(parts: List[str],
                    *,
                    limit: int = 255) -> List[str]:
    result = []
    parts = iter(parts)
    while limit > 0:
        try:
            part = next(parts)
        except StopIteration:
            break
        part = part[:limit]
        result.append(part)
        limit -= len(part) + len(os.sep)
    return result


paths = strategies.lists(identifiers).map(to_valid_length).map(pack(Path))


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
                               map(catalog.path_to_string,
                                   supported_stdlib_modules_paths))))
modules = strategies.sampled_from(modules_list)
