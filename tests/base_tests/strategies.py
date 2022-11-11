from collections import deque
from functools import (partial,
                       reduce)
from importlib import import_module
from types import ModuleType
from typing import (Any,
                    Deque,
                    List,
                    Union)

from hypothesis import strategies

from paradigm._core import catalog
from paradigm._core.discovery import supported_stdlib_modules_paths
from tests.contracts import is_supported


def find_module_callables_recursively(module: ModuleType) -> List[Any]:
    queue: Deque[Union[ModuleType, type]] = deque([module])
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
                               for content in vars(container).values()
                               if callable(content) and is_supported(content)]
        result.extend(contained_callables)
        queue.extendleft(content
                         for content in contained_callables
                         if isinstance(content, type))
    return result


callables = (strategies.sampled_from(sorted(supported_stdlib_modules_paths))
             .map(catalog.path_to_string)
             .map(import_module)
             .map(find_module_callables_recursively)
             .filter(bool)
             .flatmap(strategies.sampled_from))
callables |= callables.map(partial)
overloaded_callables = strategies.sampled_from([int, reduce, super, type])
