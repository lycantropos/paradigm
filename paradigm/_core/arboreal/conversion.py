import ast
import sys
import typing as t
from functools import singledispatch
from itertools import chain

from paradigm._core import catalog

RawAstNode = t.NewType('RawAstNode', str)


@singledispatch
def to_names(ast_node: ast.AST) -> t.List[str]:
    raise TypeError(type(ast_node))


@to_names.register(ast.AsyncFunctionDef)
@to_names.register(ast.FunctionDef)
@to_names.register(ast.ClassDef)
def _(
        ast_node: t.Union[ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef]
) -> t.List[str]:
    return [ast_node.name]


@to_names.register(ast.AnnAssign)
def _(ast_node: ast.AnnAssign) -> t.List[str]:
    return to_names(ast_node.target)


@to_names.register(ast.Assign)
def _(ast_node: ast.Assign) -> t.List[str]:
    return list(chain.from_iterable(to_names(target)
                                    for target in ast_node.targets))


@to_names.register(ast.Name)
def _(ast_node: ast.Name) -> t.List[str]:
    assert isinstance(ast_node.ctx, ast.Store), ast_node
    return [ast_node.id]


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


def to_raw(ast_node: ast.AST) -> RawAstNode:
    return RawAstNode(ast.dump(ast_node,
                               annotate_fields=False))


@singledispatch
def to_str(ast_node: ast.AST) -> str:
    raise TypeError(type(ast_node))


@to_str.register(ast.Name)
def _(ast_node: ast.Name) -> str:
    return ast_node.id


@to_str.register(ast.BitOr)
def _(ast_node: ast.BitOr) -> str:
    return '|'


@to_str.register(ast.BitAnd)
def _(ast_node: ast.BitAnd) -> str:
    return '&'


@to_str.register(ast.BitXor)
def _(ast_node: ast.BitXor) -> str:
    return '^'


@to_str.register(ast.UAdd)
def _(ast_node: ast.UAdd) -> str:
    return '+'


@to_str.register(ast.USub)
def _(ast_node: ast.USub) -> str:
    return '-'


@to_str.register(ast.UnaryOp)
def _(ast_node: ast.UnaryOp) -> str:
    return f'{to_str(ast_node.op)}({to_str(ast_node.operand)})'


@to_str.register(ast.Constant)
def _(ast_node: ast.Constant) -> str:
    return str(ast_node.value)


@to_str.register(ast.Attribute)
def _(ast_node: ast.Attribute) -> str:
    return f'{to_str(ast_node.value)}.{ast_node.attr}'


@to_str.register(ast.Subscript)
def _(ast_node: ast.Subscript) -> str:
    return (f'{to_str(ast_node.value)}'
            f'[{to_str(ast_node.slice)}]')


@to_str.register(ast.Tuple)
def _(ast_node: ast.Tuple) -> str:
    elements_strings = [to_str(element)
                        for element in ast_node.elts]
    return (f'({elements_strings[0]},)'
            if len(elements_strings) == 1
            else f'({", ".join(elements_strings)})')


@to_str.register(ast.List)
def _(ast_node: ast.List) -> str:
    elements_strings = [to_str(element)
                        for element in ast_node.elts]
    return f'[{", ".join(elements_strings)}]'


if sys.version_info < (3, 8):
    @to_str.register(ast.Ellipsis)
    def _(ast_node: ast.Ellipsis) -> str:
        return str(Ellipsis)

    @to_str.register(ast.NameConstant)
    def _(ast_node: ast.NameConstant) -> str:
        return str(ast_node.value)


    @to_str.register(ast.Num)
    def _(ast_node: ast.Num) -> str:
        return str(ast_node.n)


    @to_str.register(ast.Str)
    def _(ast_node: ast.Str) -> str:
        return ast_node.s

if sys.version_info < (3, 10):
    @to_str.register(ast.BinOp)
    def _(ast_node: ast.BinOp) -> str:
        assert isinstance(ast_node.op, ast.BitOr), ast_node
        left_operand = to_str(ast_node.left)
        right_operand = to_str(ast_node.right)
        return f'{t.__name__}.Union[{left_operand}, {right_operand}]'


    if sys.version_info < (3, 9):
        @to_str.register(ast.Index)
        def _(ast_node: ast.Index) -> str:
            return to_str(ast_node.value)
else:
    @to_str.register(ast.BinOp)
    def _(ast_node: ast.BinOp) -> str:
        left_operand = to_str(ast_node.left)
        right_operand = to_str(ast_node.right)
        return f'{left_operand} {to_str(ast_node.op)} {right_operand}'


@singledispatch
def to_path(ast_node: ast.expr) -> catalog.Path:
    raise TypeError(type(ast_node))


@to_path.register(ast.Name)
def _(ast_node: ast.Name) -> catalog.Path:
    return (ast_node.id,)


@to_path.register(ast.Attribute)
def _(ast_node: ast.Attribute) -> catalog.Path:
    return to_path(ast_node.value) + (ast_node.attr,)


@singledispatch
def to_maybe_path(ast_node: ast.expr) -> t.Optional[catalog.Path]:
    return None


@to_maybe_path.register(ast.Name)
def _(ast_node: ast.Name) -> t.Optional[catalog.Path]:
    return (ast_node.id,)


@to_maybe_path.register(ast.Attribute)
def _(ast_node: ast.Attribute) -> t.Optional[catalog.Path]:
    value_maybe_path = to_maybe_path(ast_node.value)
    return (None
            if value_maybe_path is None
            else (*value_maybe_path, ast_node.attr))
