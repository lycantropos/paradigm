from __future__ import annotations

import types
import warnings
from collections import deque
from functools import partial, reduce
from importlib import import_module
from types import ModuleType
from typing import Any

from hypothesis import strategies

from paradigm._core import catalog
from paradigm._core.discovery import supported_stdlib_module_paths
from tests.contracts import is_supported


def find_optional_module_callables_recursively(
    module: ModuleType | None, /
) -> list[Any]:
    if module is None:
        return []
    queue: deque[ModuleType | type] = deque([module])
    result = []
    visited_types = set()
    while queue:
        container = queue.pop()
        if isinstance(container, type):
            if container in visited_types:
                continue
            visited_types.add(container)
        contained_callables = [
            content
            for content in vars(container).values()
            if callable(content) and is_supported(content)
        ]
        result.extend(contained_callables)
        queue.extendleft(
            content
            for content in contained_callables
            if isinstance(content, type)
        )
    return result


def safe_import_module(name: str, /) -> types.ModuleType | None:
    try:
        return import_module(name)
    except Exception:
        warnings.warn(
            f'Failed importing module "{name}".', ImportWarning, stacklevel=2
        )
        return None


callables = (
    strategies.sampled_from(sorted(supported_stdlib_module_paths))
    .map(catalog.path_to_string)
    .map(safe_import_module)
    .map(find_optional_module_callables_recursively)
    .filter(bool)
    .flatmap(strategies.sampled_from)
)
callables |= callables.map(partial)
overloaded_callables = strategies.sampled_from([int, reduce, super, type])
