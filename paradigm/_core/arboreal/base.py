from typing import Optional

from paradigm._core import (catalog,
                            sources)
from .leveling import (NameLookupError,
                       Node,
                       import_module_node)


def find_node(module_path: catalog.Path,
              object_path: catalog.Path) -> Optional[Node]:
    try:
        module_node = import_module_node(module_path)
    except sources.NotFound:
        return None
    object_node = module_node
    for part in object_path:
        object_node.resolve()
        try:
            object_node = object_node.get_attribute_by_name(part)
        except NameLookupError:
            return None
    object_node.resolve()
    return object_node
