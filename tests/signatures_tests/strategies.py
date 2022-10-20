import types
from collections import deque
from functools import (partial,
                       reduce)
from typing import (Any,
                    List,
                    Union)

from hypothesis import strategies

from tests import is_supported
from tests.strategies import modules_list
from tests.utils import to_contents


def find_callables_recursively(
        objects: List[Union[types.ModuleType, type]]
) -> List[Any]:
    queue = deque(objects)
    result = []
    visited_types = set()
    while queue:
        container = queue.pop()
        if isinstance(container, type):
            if container in visited_types:
                continue
            else:
                visited_types.add(container)
        contained_callables = [content
                               for content in to_contents(container)
                               if callable(content) and is_supported(content)]
        result.extend(contained_callables)
        queue.extendleft(content
                         for content in contained_callables
                         if isinstance(content, type))
    return result


callables_list = find_callables_recursively(modules_list)
callables = strategies.sampled_from(callables_list)
callables |= callables.map(partial)
overloaded_callables = strategies.sampled_from([int, reduce, super, type])
