import traceback
import typing as t
from functools import singledispatch


def format_exception(value: BaseException) -> str:
    return ''.join(
        traceback.format_exception(type(value), value, value.__traceback__)
    )


@singledispatch
def repr_from(value: t.Any, _indent: int, _depth: int, /) -> str:
    return repr(value)


@repr_from.register(dict)
def _(value: dict[t.Any, t.Any], indent: int, depth: int, /) -> str:
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
def _(value: list[t.Any], indent: int, depth: int, /) -> str:
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
def _(value: tuple[t.Any, ...], indent: int, depth: int, /) -> str:
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
def _(value: set[t.Any], indent: int, depth: int, /) -> str:
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
