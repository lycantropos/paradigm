import ast
from typing import (Dict,
                    List,
                    Union)

from paradigm import catalog

Node = Union[ast.AST, catalog.Path]
Scope = Dict[catalog.Path, List[Node]]
