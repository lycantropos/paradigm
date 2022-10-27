import ast
import sys
from pathlib import Path


def from_source_path(object_: Path) -> ast.Module:
    return ast.parse(object_.read_text())


if sys.version_info < (3, 8):
    def from_node(object_: ast.AST) -> ast.Module:
        return ast.Module([object_])
else:
    def from_node(object_: ast.AST) -> ast.Module:
        return ast.Module([object_], [])
