from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any, Final, TypeVar

from .conversion import RawNode

_AST_NAMESPACE: Final[dict[str, ast.AST]] = vars(ast).copy()
if sys.version_info < (3, 14):
    _AST_NAMESPACE.pop(ast.Ellipsis.__qualname__, None)


def from_statement_node(ast_node: ast.stmt, /) -> ast.Module:
    return ast.Module([ast_node], [])


_NodeT = TypeVar('_NodeT', ast.expr, ast.stmt)


def from_raw(
    raw: RawNode,
    /,
    *,
    cls: type[_NodeT],
    namespace: dict[str, Any] = _AST_NAMESPACE,
) -> _NodeT:
    result = eval(raw, namespace)
    assert isinstance(result, cls), result
    return result


def from_source_path(path: Path, /) -> ast.Module:
    return ast.parse(path.read_text())
