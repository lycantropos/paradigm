from functools import singledispatch
from pathlib import Path

from typed_ast import ast3

from paradigm.hints import Namespace
from . import (construction,
               conversion)


@singledispatch
def execute(node: ast3.AST,
            *,
            source_path: Path,
            namespace: Namespace) -> None:
    raise TypeError('Unsupported node type: {type}.'
                    .format(type=type(node)))


@execute.register(ast3.stmt)
def execute_statement(node: ast3.stmt,
                      *,
                      source_path: Path,
                      namespace: Namespace) -> None:
    execute_tree(construction.from_node(node),
                 source_path=source_path,
                 namespace=namespace)


@execute.register(ast3.Module)
def execute_tree(node: ast3.Module,
                 *,
                 source_path: Path,
                 namespace: Namespace) -> None:
    code = compile(conversion.typed_to_plain(node), str(source_path), 'exec')
    exec(code, namespace)
