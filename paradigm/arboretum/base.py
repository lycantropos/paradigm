from functools import partial
from itertools import takewhile
from typing import List

from typed_ast import ast3

from paradigm import catalog
from . import (reduction,
               scoping)
from .data_access import (follow_links,
                          search_nodes)
from .evaluation import is_overloaded_function
from .logical import (are_dicts_similar,
                      are_lists_similar,
                      is_function_def,
                      is_link)


def to_functions_defs(object_path: catalog.Path,
                      module_path: catalog.Path) -> List[ast3.AST]:
    scope = scoping.factory(module_path)
    reduce_node = reduction.factory(module_path=module_path,
                                    scope=scope)
    while True:
        try:
            candidates = search_nodes(object_path,
                                      scope=scope)
        except KeyError:
            parent_path = object_path.parent
            parent_nodes = []
            while parent_path.parts:
                try:
                    parent_nodes = scope[parent_path]
                except KeyError:
                    parent_path = parent_path.parent
                else:
                    break
            if not parent_nodes:
                raise
            last_parent_node = parent_nodes[-1]
            if is_link(last_parent_node):
                object_path = object_path.with_parent(last_parent_node)
                continue
            children_scope_before = scoping.to_children_scope(parent_path,
                                                              scope=scope)
            reduce_node(last_parent_node)
            children_remain_intact = are_dicts_similar(
                    scoping.to_children_scope(parent_path,
                                              scope=scope),
                    children_scope_before)
            if children_remain_intact:
                return []
            continue
        if not is_function_def(candidates[-1]):
            nodes_before = candidates[:]
            reduce_node(candidates[-1])
            nodes_remain_intact = are_lists_similar(search_nodes(object_path,
                                                                 scope=scope),
                                                    nodes_before)
            if nodes_remain_intact:
                return []
            continue
        break
    candidates = follow_links(candidates,
                              scope=scope)
    candidates = takewhile(is_function_def, reversed(candidates))
    try:
        function_def = next(candidates)
    except StopIteration:
        return []
    is_overload = partial(is_overloaded_function,
                          scope=scope,
                          module_path=module_path)
    result = [function_def]
    if is_overload(function_def):
        result += list(takewhile(is_overload, candidates))
    return result
