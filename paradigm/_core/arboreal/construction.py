import ast
import sys
from pathlib import Path


def from_source_path(path: Path) -> ast.Module:
    return ast.parse(path.read_text())


if sys.version_info < (3, 8):
    def from_node(ast_node: ast.AST) -> ast.Module:
        return ast.Module([ast_node])
else:
    def from_node(ast_node: ast.AST) -> ast.Module:
        return ast.Module([ast_node], [])
