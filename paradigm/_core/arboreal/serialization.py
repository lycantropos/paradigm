import ast
import sys
from functools import singledispatch


@singledispatch
def to_identifier(ast_node: ast.AST) -> str:
    raise TypeError(type(ast_node))


@to_identifier.register(ast.Subscript)
def _(ast_node: ast.Subscript) -> str:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return (to_identifier(ast_node.value)
            + '_getitem_'
            + to_identifier(ast_node.slice))


@to_identifier.register(ast.Ellipsis)
def _(ast_node: ast.Subscript) -> str:
    return repr(Ellipsis)


@to_identifier.register(ast.Constant)
@to_identifier.register(ast.NameConstant)
def _(ast_node: ast.NameConstant) -> str:
    return repr(ast_node.value)


@to_identifier.register(ast.BitAnd)
def _(ast_node: ast.BitAnd) -> str:
    return 'bitand'


@to_identifier.register(ast.BitOr)
def _(ast_node: ast.BitOr) -> str:
    return 'bitor'


@to_identifier.register(ast.BitXor)
def _(ast_node: ast.BitXor) -> str:
    return 'bitxor'


@to_identifier.register(ast.BinOp)
def _(ast_node: ast.BinOp) -> str:
    return (to_identifier(ast_node.left)
            + '_' + to_identifier(ast_node.op) + '_'
            + to_identifier(ast_node.right))


@to_identifier.register(ast.Tuple)
def _(ast_node: ast.Tuple) -> str:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return '_'.join(to_identifier(element) for element in ast_node.elts)


@to_identifier.register(ast.Name)
def _(ast_node: ast.Name) -> str:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return ast_node.id


@to_identifier.register(ast.Attribute)
def _(ast_node: ast.Attribute) -> str:
    assert isinstance(ast_node.ctx, ast.Load), ast_node
    return to_identifier(ast_node.value) + '_' + ast_node.attr


if sys.version_info < (3, 9):
    @to_identifier.register(ast.Index)
    def _(ast_node: ast.Index) -> str:
        return to_identifier(ast_node.value)
