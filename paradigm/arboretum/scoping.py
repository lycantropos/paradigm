import builtins

from paradigm import catalog
from . import examination
from .hints import Scope
from .leveling import to_flat_root


def to_children_scope(path: catalog.Path,
                      *,
                      scope: Scope) -> Scope:
    return {object_path: nodes[:]
            for object_path, nodes in scope.items()
            if object_path.is_child_of(path)
            and object_path != path}


builtins_scope = {}


def factory(module_path: catalog.Path) -> Scope:
    root = to_flat_root(module_path)
    result = dict(builtins_scope)
    examination.conduct(root,
                        module_path=module_path,
                        scope=result)
    return result


builtins_scope.update(factory(catalog.factory(builtins)))
