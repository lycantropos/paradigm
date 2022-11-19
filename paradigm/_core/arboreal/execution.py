import ast
import typing as t
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
    exec(code, namespace)


def evaluate_expression(node: ast.expr,
                        *,
                        source_path: Path,
                        namespace: namespacing.Namespace) -> t.Any:
    # to avoid name conflicts
    # we're using name that won't be present
    # because it'll lead to ``SyntaxError`` otherwise
    # and no AST will be generated
    temporary_name = '@tmp'
    assignment = _expression_to_assignment(node,
                                           name=temporary_name)
    execute_statement(assignment,
                      source_path=source_path,
                      namespace=namespace)
    return namespace.pop(temporary_name)


def _expression_to_assignment(node: ast.expr,
                              *,
                              name: str) -> ast.Assign:
    name_node = ast.copy_location(ast.Name(name, ast.Store()), node)
    return ast.copy_location(ast.Assign([name_node], node), node)
