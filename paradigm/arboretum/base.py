import ast
from typing import (List,
                    Tuple)

from paradigm import (catalog,
                      sources)
from .leveling import (NameLookupError,
                       NodeKind,
                       import_module_node)


def to_functions_defs(
        module_path: catalog.Path,
        object_path: catalog.Path,
        *,
        constructor_name: str = object.__new__.__name__,
        initializer_name: str = object.__init__.__name__
) -> Tuple[int, List[ast.AST]]:
    try:
        module_node = import_module_node(module_path)
    except sources.NotFound:
        return -1, []
    object_node = module_node
    for part in object_path.parts:
        object_node.resolve()
        try:
            object_node = object_node.get_attribute_by_name(part)
        except NameLookupError:
            return -1, []
    object_node.resolve()
    if object_node.kind is NodeKind.CLASS:
        initializer_depth, initializer_node = object_node.locate_name(
                initializer_name
        )
        constructor_depth, constructor_node = object_node.locate_name(
                constructor_name
        )
        if constructor_depth < initializer_depth:
            return constructor_depth, constructor_node.ast_nodes
        else:
            return initializer_depth, initializer_node.ast_nodes
    elif object_node.kind is NodeKind.FUNCTION:
        return 0, object_node.ast_nodes
    else:
        assert (
                object_node.kind is not NodeKind.UNDEFINED
        ), module_path.join(object_path)
        return -1, []
