from typing import List

from paradigm import catalog
from .hints import (Node,
                    Scope)
from .logical import is_link


def search_nodes(path: catalog.Path,
                 *,
                 scope: Scope) -> List[Node]:
    return follow_links(scope[path],
                        scope=scope)


def follow_links(nodes: List[Node],
                 *,
                 scope: Scope) -> List[Node]:
    while is_link(nodes[-1]):
        nodes = scope[nodes[-1]]
    return nodes
