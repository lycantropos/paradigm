import traceback
from functools import singledispatch
from typing import Any


def format_exception(value: BaseException, /) -> str:
    return ''.join(
        traceback.format_exception(type(value), value, value.__traceback__)
    )


@singledispatch
def repr_from(value: Any, _indent: int, _depth: int, /) -> str:
    return repr(value)


@repr_from.register(dict)
def _(value: dict[Any, Any], indent: int, depth: int, /) -> str:
    return (
        (
            '{\n'
            + ',\n'.join(
                sorted(
                    [
                        indent * ' ' * (depth + 1)
                        + repr_from(key, indent, depth + 1)
                        + ': '
                        + repr_from(sub_value, indent, depth + 1)
                        for key, sub_value in value.items()
                    ]
                )
            )
            + '\n'
            + indent * ' ' * depth
            + '}'
        )
        if value
        else repr(value)
    )


@repr_from.register(list)
def _(value: list[Any], indent: int, depth: int, /) -> str:
    return (
        (
            '[\n'
            + ',\n'.join(
                [
                    indent * ' ' * (depth + 1)
                    + repr_from(sub_value, indent, depth + 1)
                    for sub_value in value
                ]
            )
            + '\n'
            + indent * ' ' * depth
            + ']'
        )
        if value
        else repr(value)
    )


@repr_from.register(tuple)
def _(value: tuple[Any, ...], indent: int, depth: int, /) -> str:
    if len(value) > 1:
        return (
            '(\n'
            + ',\n'.join(
                [
                    indent * ' ' * (depth + 1)
                    + repr_from(sub_value, indent, depth + 1)
                    for sub_value in value
                ]
            )
            + '\n'
            + indent * ' ' * depth
            + ')'
        )
    if value:
        return f'({repr_from(value[0], indent, depth)},)'
    return repr(value)


@repr_from.register(set)
def _(value: set[Any], indent: int, depth: int, /) -> str:
    return (
        (
            '{\n'
            + ',\n'.join(
                [
                    indent * ' ' * (depth + 1)
                    + repr_from(sub_value, indent, depth + 1)
                    for sub_value in value
                ]
            )
            + '\n'
            + indent * ' ' * depth
            + '}'
        )
        if value
        else repr(value)
    )
