import ast
from functools import partial
from itertools import chain
from typing import (Callable,
                    Iterable,
                    Optional,
                    Type)

from typed_ast import ast3

from paradigm.hints import Domain

TypedToPlainMethod = Callable[[ast3.NodeTransformer, ast3.AST],
                              Optional[ast.AST]]


def to_typed_to_plain_visitor(cls: Type[ast3.AST]) -> TypedToPlainMethod:
    try:
        plain_cls = getattr(ast, cls.__name__)
    except AttributeError:
        if issubclass(cls, ast3.stmt):
            def passer(_: ast3.NodeTransformer, node: cls) -> None:
                return ast.copy_location(ast.Pass(), node)

            return passer

        def deleter(_: ast3.NodeTransformer, __: cls) -> None:
            return None

        return deleter

    def visit(self: ast3.NodeTransformer, node: ast3.AST) -> ast.AST:
        node = self.generic_visit(node)
        result = plain_cls(*map(partial(getattr, node), plain_cls._fields))
        return ast3.copy_location(result, node)

    return visit


def to_subclasses(cls: Type[Domain]) -> Iterable[Type[Domain]]:
    result = cls.__subclasses__()
    yield from result
    yield from chain.from_iterable(map(to_subclasses, result))


class TypedToPlain(ast3.NodeTransformer):
    visitors = {'visit_' + cls.__name__: to_typed_to_plain_visitor(cls)
                for cls in set(to_subclasses(ast3.AST))}

    def __getattr__(self, name: str) -> TypedToPlainMethod:
        return partial(self.visitors[name], self)

    def generic_visit(self, node: ast3.AST) -> ast3.AST:
        for field, old_value in ast3.iter_fields(node):
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, ast3.AST):
                        value = self.visit(value)
                        if value is None:
                            continue
                        elif not isinstance(value, ast.AST):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, ast3.AST):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node


typed_to_plain = TypedToPlain().visit
