import ast
from typing import (Dict,
                    List,
                    Union)

from paradigm._core import catalog

Node = Union[ast.AST, catalog.Path]
Scope = Dict[catalog.Path, List[Node]]
