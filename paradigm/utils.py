from collections import abc
from functools import (singledispatch,
                       wraps)
from typing import (Mapping,
                    MutableMapping)
from weakref import WeakKeyDictionary

from paradigm.hints import (Domain,
                            Map,
                            Operator,
                            Range)


@singledispatch
def cached_map(cache: Mapping[Domain, Range]) -> Operator[Map[Domain, Range]]:
    def wrapper(map_: Map[Domain, Range]) -> Map[Domain, Range]:
        @wraps(map_)
        def wrapped(argument: Domain) -> Range:
            try:
                return cache[argument]
            except KeyError:
                return map_(argument)

        return wrapped

    return wrapper


@cached_map.register(abc.MutableMapping)
def updatable_cached_map(cache: MutableMapping[Domain, Range]
                         ) -> Operator[Map[Domain, Range]]:
    def wrapper(map_: Map[Domain, Range]) -> Map[Domain, Range]:
        @wraps(map_)
        def wrapped(argument: Domain) -> Range:
            try:
                return cache[argument]
            except KeyError:
                result = map_(argument)
                cache[argument] = result
                return result

        return wrapped

    return wrapper


def memoized_property(getter: Map[Domain, Range]) -> property:
    """
    Returns property that calls given getter on the first access
    and reuses result afterwards.

    Class instances should be hashable and weak referenceable.
    """
    return property(cached_map(WeakKeyDictionary())(getter))
