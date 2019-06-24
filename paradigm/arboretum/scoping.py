import builtins
import copy

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


def populate(module_path: catalog.Path,
             *,
             scope: Scope) -> None:
    root = to_flat_root(module_path)
    examination.conduct(root,
                        module_path=module_path,
                        scope=scope)


builtins_module_path = catalog.from_module(builtins)
builtins_scope = {}
populate(builtins_module_path,
         scope=builtins_scope)


def factory(module_path: catalog.Path) -> Scope:
    result = copy.deepcopy(builtins_scope)
    if module_path != builtins_module_path:
        populate(module_path,
                 scope=result)
    return result
