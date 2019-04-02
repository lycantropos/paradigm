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
def map_(cache: Mapping[Domain, Range]) -> Operator[Map[Domain, Range]]:
    """
    Returns decorator that calls wrapped function
    if nothing was found in cache for its argument.

    Wrapped function arguments should be hashable.
    """

    def wrapper(function: Map[Domain, Range]) -> Map[Domain, Range]:
        @wraps(function)
        def wrapped(argument: Domain) -> Range:
            try:
                return cache[argument]
            except KeyError:
                return function(argument)

        return wrapped

    return wrapper


@map_.register(abc.MutableMapping)
def updatable_map(cache: MutableMapping[Domain, Range]) -> Operator[Map]:
    """
    Returns decorator that calls wrapped function
    if nothing was found in cache for its argument
    and reuses result afterwards.

    Wrapped function arguments should be hashable.
    """

    def wrapper(function: Map[Domain, Range]) -> Map[Domain, Range]:
        @wraps(function)
        def wrapped(argument: Domain) -> Range:
            try:
                return cache[argument]
            except KeyError:
                result = function(argument)
                cache[argument] = result
                return result

        return wrapped

    return wrapper


def property_(getter: Map[Domain, Range]) -> property:
    """
    Returns property that calls given getter on the first access
    and reuses result afterwards.

    Class instances should be hashable and weak referenceable.
    """
    return property(map_(WeakKeyDictionary())(getter))
