from functools import singledispatch

from typed_ast import ast3

from . import (construction,
               conversion)
from .hints import Namespace


@singledispatch
def execute(node: ast3.AST,
            *,
            namespace: Namespace) -> None:
    raise TypeError('Unsupported node type: {type}.'
                    .format(type=type(node)))


@execute.register(ast3.stmt)
def execute_statement(node: ast3.stmt,
                      *,
                      namespace: Namespace) -> None:
    execute_tree(construction.from_node(node),
                 namespace=namespace)


@execute.register(ast3.Module)
def execute_tree(node: ast3.Module,
                 *,
                 namespace: Namespace) -> None:
    code = compile(conversion.typed_to_plain(node), '<unknown>', 'exec')
    exec(code, namespace)
