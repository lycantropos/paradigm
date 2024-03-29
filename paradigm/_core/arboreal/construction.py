import ast
import sys
import typing as t
from pathlib import Path

from .conversion import RawAstNode

_AST_NAMESPACE = vars(ast).copy()
del _AST_NAMESPACE[ast.Ellipsis.__qualname__]


def from_node(ast_node: ast.AST) -> ast.Module:
    return ast.Module([ast_node], [])


def from_raw(raw: RawAstNode,
             *,
             namespace: t.Dict[str, t.Any] = _AST_NAMESPACE) -> ast.AST:
    result = eval(raw, namespace)
    assert isinstance(result, ast.AST), result
    return result


def from_source_path(path: Path) -> ast.Module:
    return ast.parse(path.read_text())
