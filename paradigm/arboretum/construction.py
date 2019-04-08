from pathlib import Path

from typed_ast import ast3


def from_source_path(object_: Path) -> ast3.Module:
    return ast3.parse(object_.read_text())


def from_node(object_: ast3.AST) -> ast3.Module:
    return ast3.Module([object_], [])
