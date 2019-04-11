from typing import List

from paradigm import catalog
from .hints import (Node,
                    Scope)
from .logical import is_link


def search_nodes(path: catalog.Path,
                 *,
                 scope: Scope) -> List[Node]:
    nodes = scope[path]
    while is_link(nodes[-1]):
        nodes = scope[nodes[-1]]
    return nodes
