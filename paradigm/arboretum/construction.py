import ast
from pathlib import Path


def from_source_path(object_: Path) -> ast.Module:
    return ast.parse(object_.read_text())


def from_node(object_: ast.AST) -> ast.Module:
    return ast.Module([object_])
