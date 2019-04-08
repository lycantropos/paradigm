from functools import singledispatch
from itertools import (chain,
                       starmap)
from typing import (Any,
                    Dict,
                    Hashable,
                    List)

from typed_ast import ast3

from paradigm import catalog
from .hints import Node

is_link = catalog.Path.__instancecheck__
is_function_def = ast3.FunctionDef.__instancecheck__


@singledispatch
def are_similar(left_object: Any, right_object: Any) -> bool:
    return left_object == right_object


@are_similar.register(list)
def are_lists_similar(left_object: List[Any], right_object: List[Any]) -> bool:
    if type(left_object) is not type(right_object):
        return False
    if len(left_object) != len(right_object):
        return False
    return all(starmap(are_similar, zip(left_object, right_object)))


@are_similar.register(dict)
def are_dicts_similar(left_object: Dict[Hashable, Any],
                      right_object: Dict[Hashable, Any]) -> bool:
    if type(left_object) is not type(right_object):
        return False
    if left_object.keys() != right_object.keys():
        return False
    for key, left_value in left_object.items():
        if not are_similar(left_value, right_object[key]):
            return False
    return True


@are_similar.register(ast3.AST)
def are_nodes_similar(left_object: ast3.AST, right_object: Node) -> bool:
    if type(left_object) is not type(right_object):
        return False
    for property_name in chain(left_object._attributes, left_object._fields):
        try:
            left_property = getattr(left_object, property_name)
        except AttributeError:
            continue
        try:
            right_property = getattr(right_object, property_name)
        except AttributeError:
            return False
        if not are_similar(left_property, right_property):
            return False
    return True
