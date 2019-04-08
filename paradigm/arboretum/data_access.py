from typing import List

from paradigm import catalog
from paradigm.arboretum.hints import Node, Scope
from paradigm.arboretum.logical import is_link


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