from typing import Optional

from paradigm._core import (catalog,
                            scoping,
                            sources,
                            stubs)
from .leveling import (NameLookupError,
                       Node,
                       import_module_node)


def find_node(module_path: catalog.Path,
              object_path: catalog.Path) -> Optional[Node]:
    try:
        referent_module_path, referent_object_path = (
            scoping.resolve_object_path(module_path, object_path,
                                        stubs.definitions, stubs.references,
                                        stubs.sub_scopes)
        )
    except scoping.ObjectNotFound:
        return None
    try:
        module_node = import_module_node(referent_module_path)
    except sources.NotFound:
        return None
    try:
        return module_node.get_attribute_by_path(referent_object_path)
    except NameLookupError:
        return None
