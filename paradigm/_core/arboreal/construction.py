from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .conversion import RawAstNode

_AST_NAMESPACE = vars(ast).copy()
del _AST_NAMESPACE[ast.Ellipsis.__qualname__]


def from_node(ast_node: ast.stmt) -> ast.Module:
    return ast.Module([ast_node], [])


def from_raw(
    raw: RawAstNode, *, namespace: dict[str, Any] = _AST_NAMESPACE
) -> ast.AST:
    result = eval(raw, namespace)
    assert isinstance(result, ast.AST), result
    return result


def from_source_path(path: Path) -> ast.Module:
    return ast.parse(path.read_text())
