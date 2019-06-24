import typing
from functools import (partial,
                       singledispatch)
from typing import (NamedTuple,
                    Union,
                    overload)

from typed_ast import ast3

from paradigm import catalog
from .data_access import search_nodes
from .hints import (Node,
                    Scope)

TYPING_MODULE_PATH = catalog.from_module(typing)
NAMED_TUPLE_CLASS_PATH = next(iter(catalog.paths_factory(NamedTuple)))
OVERLOAD_FUNCTION_PATH = next(iter(catalog.paths_factory(overload)))


@singledispatch
def evaluate_node(node: ast3.AST,
                  *,
                  scope: Scope,
                  module_path: catalog.Path) -> Node:
    raise TypeError('Unsupported node type: {type}.'
                    .format(type=type(node)))


@evaluate_node.register(ast3.Name)
def evaluate_name(node: ast3.Name,
                  *,
                  scope: Scope,
                  module_path: catalog.Path) -> Node:
    return catalog.from_string(node.id)


@evaluate_node.register(ast3.expr)
def evaluate_ellipsis_or_num(node: Union[ast3.Ellipsis, ast3.Num],
                             *,
                             scope: Scope,
                             module_path: catalog.Path) -> Node:
    return catalog.from_string(str(Ellipsis))


@evaluate_node.register(ast3.NameConstant)
def evaluate_name_constant(node: ast3.NameConstant,
                           *,
                           scope: Scope,
                           module_path: catalog.Path) -> Node:
    return catalog.from_string(str(node.value))


@evaluate_node.register(ast3.Attribute)
def evaluate_attribute(node: ast3.Attribute,
                       *,
                       scope: Scope,
                       module_path: catalog.Path) -> Node:
    value_path = evaluate_node(node.value,
                               scope=scope,
                               module_path=module_path)
    return value_path.join(catalog.from_string(node.attr))


@evaluate_node.register(ast3.Subscript)
def evaluate_subscript(node: ast3.Subscript,
                       *,
                       scope: Scope,
                       module_path: catalog.Path) -> Node:
    return evaluate_node(node.value,
                         scope=scope,
                         module_path=module_path)


@evaluate_node.register(ast3.Call)
def evaluate_call(node: ast3.Call,
                  *,
                  scope: Scope,
                  module_path: catalog.Path) -> Node:
    if not is_named_tuple_definition(node,
                                     scope=scope,
                                     module_path=module_path):
        return node
    class_name_node, fields_node = node.args

    def field_to_parameter(field_node: ast3.expr) -> ast3.arg:
        name_node, annotation_node = field_node.elts
        return ast3.arg(ast3.literal_eval(name_node), annotation_node)

    initializer_node = ast3.FunctionDef(
            '__init__',
            ast3.arguments([ast3.arg('self', None)]
                           + list(map(field_to_parameter,
                                      fields_node.elts)),
                           None, [], [], None, []),
            [ast3.Pass()], [], None)
    function_path = evaluate_node(node.func,
                                  scope=scope,
                                  module_path=module_path)
    class_def = ast3.ClassDef(ast3.literal_eval(class_name_node),
                              [ast3.Name(str(function_path), ast3.Load())],
                              [], [initializer_node], [])
    return ast3.fix_missing_locations(ast3.copy_location(class_def, node))


def is_named_tuple_definition(node: ast3.Call,
                              *,
                              scope: Scope,
                              module_path: catalog.Path) -> bool:
    evaluator = partial(evaluate_node,
                        scope=scope,
                        module_path=module_path)
    function_path = evaluator(node.func)
    return any_path_has_origin(function_path,
                               candidates_module_path=module_path,
                               candidates_scope=scope,
                               origin_module_path=TYPING_MODULE_PATH,
                               origin_object_path=NAMED_TUPLE_CLASS_PATH)


def is_overloaded_function(node: ast3.FunctionDef,
                           *,
                           scope: Scope,
                           module_path: catalog.Path) -> bool:
    evaluator = partial(evaluate_node,
                        scope=scope,
                        module_path=module_path)
    decorators_paths = map(evaluator, node.decorator_list)
    return any_path_has_origin(*decorators_paths,
                               candidates_module_path=module_path,
                               candidates_scope=scope,
                               origin_module_path=TYPING_MODULE_PATH,
                               origin_object_path=OVERLOAD_FUNCTION_PATH)


def any_path_has_origin(*candidates: catalog.Path,
                        candidates_module_path: catalog.Path,
                        candidates_scope: Scope,
                        origin_module_path: catalog.Path,
                        origin_object_path: catalog.Path) -> bool:
    searcher = partial(search_nodes,
                       scope=candidates_scope)
    if candidates_module_path == origin_module_path:
        return any(path == origin_object_path
                   for path in candidates)
    for candidate in candidates:
        try:
            candidate_nodes = searcher(candidate)
        except KeyError:
            if catalog.is_attribute(candidate):
                parent_nodes = searcher(candidate.parent)
                if isinstance(parent_nodes[-1], ast3.Import):
                    if any(to_actual_path(name_alias) == origin_module_path
                           for name_alias in parent_nodes.names):
                        return (catalog.from_string(candidate.parts[-1])
                                == origin_object_path)
        else:
            origin_node = candidate_nodes[-1]
            if isinstance(origin_node, ast3.ImportFrom):
                if (catalog.from_string(origin_node.module)
                        == origin_module_path):
                    try:
                        name_alias = next(
                                name_alias
                                for name_alias in reversed(origin_node.names)
                                if to_alias_path(name_alias) == candidate)
                    except StopIteration:
                        pass
                    else:
                        return (to_actual_path(name_alias)
                                == origin_object_path)
    return False


def to_actual_path(node: ast3.alias) -> catalog.Path:
    return catalog.from_string(node.name)


def to_alias_path(node: ast3.alias) -> catalog.Path:
    return catalog.from_string(to_alias_string(node))


def to_alias_string(node: ast3.alias) -> str:
    return node.asname or node.name
