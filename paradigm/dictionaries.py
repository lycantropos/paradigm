from itertools import chain
from operator import methodcaller
from typing import Iterable

from paradigm.hints import Namespace


def merge(namespaces: Iterable[Namespace]) -> Namespace:
    return dict(chain.from_iterable(map(methodcaller('items'), namespaces)))
