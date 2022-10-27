import ast
from pathlib import Path

from paradigm._core.hints import Namespace
from . import construction


def execute_statement(node: ast.stmt,
                      *,
                      source_path: Path,
                      namespace: Namespace) -> None:
    _execute_tree(construction.from_node(node),
                  source_path=source_path,
                  namespace=namespace)


def _execute_tree(node: ast.Module,
                  *,
                  source_path: Path,
                  namespace: Namespace) -> None:
    code = compile(node, str(source_path), 'exec')
    exec(code, namespace)