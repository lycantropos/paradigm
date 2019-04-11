from typing import (Any,
                    Dict,
                    List,
                    Union)

from typed_ast import ast3

from paradigm import catalog

Node = Union[ast3.AST, catalog.Path]
Scope = Dict[catalog.Path, List[Node]]
Namespace = Dict[str, Any]
