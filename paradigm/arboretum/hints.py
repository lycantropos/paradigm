from typing import (Any,
                    Dict,
                    List,
                    MutableMapping,
                    Union)

from typed_ast import ast3

from paradigm import catalog

Namespace = Dict[str, Any]
Node = Union[ast3.AST, catalog.Path]
Scope = MutableMapping[catalog.Path, List[Node]]
