import ast
from pathlib import Path

from paradigm._core import namespacing
from . import construction


def execute_statement(node: ast.stmt,
                      *,
                      source_path: Path,
                      namespace: namespacing.Namespace) -> None:
    _execute_tree(construction.from_node(node),
                  source_path=source_path,
                  namespace=namespace)


def _execute_tree(node: ast.Module,
                  *,
                  source_path: Path,
                  namespace: namespacing.Namespace) -> None:
    code = compile(node, str(source_path), 'exec')
    namespace_dict = dict(namespace)
    exec(code, namespace_dict)
    namespace.update(namespace_dict)
