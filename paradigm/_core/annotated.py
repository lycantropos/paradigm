from __future__ import annotations

import types
from collections import abc
from collections.abc import Sequence
from functools import singledispatch
from typing import (
    Any,
    Generic,
    Literal,
    NewType,
    Optional,
    ParamSpec,
    ParamSpecArgs,
    ParamSpecKwargs,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from paradigm._core.utils import MISSING

LegacyGenericAlias: Any = type(Generic[TypeVar('_T')])  # type: ignore[index]


@singledispatch
def are_equal(left: Any, right: Any, /) -> bool:
    result = left == right
    assert isinstance(result, bool), result
    return result


@are_equal.register(LegacyGenericAlias)
@are_equal.register(types.GenericAlias)
@are_equal.register(types.UnionType)  # pyright: ignore[reportArgumentType, reportCallIssue]
@are_equal.register(type)
@are_equal.register(type(Union[int, None]))  # noqa: UP007
def _(left: Any, right: Any, /) -> bool:
    left_args, right_args = to_arguments(left), to_arguments(right)
    left_origin, right_origin = (
        to_origin(left) or left,
        to_origin(right) or right,
    )
    return (
        left_origin is right_origin
        and len(left_args) == len(right_args)
        and (
            (
                all(
                    any(
                        are_equal(left_arg, right_arg)
                        for right_arg in right_args
                    )
                    for left_arg in left_args
                )
                and all(
                    any(
                        are_equal(left_arg, right_arg)
                        for left_arg in left_args
                    )
                    for right_arg in right_args
                )
            )
            if (left_origin is Union or left_origin is Literal)
            else all(map(are_equal, left_args, right_args))
        )
    )


@are_equal.register(abc.Sequence)
def _(left: Sequence[Any], right: Any, /) -> bool:
    return (
        type(left) is type(right)
        and len(left) == len(right)
        and all(map(are_equal, left, right))
    )


@are_equal.register(ParamSpec)
def _(left: ParamSpec, right: Any, /) -> bool:
    return (
        type(left) is type(right)
        and left.__name__ == right.__name__
        and are_equal(left.__bound__, right.__bound__)
        and left.__contravariant__ is right.__contravariant__
        and left.__covariant__ is right.__covariant__
    )


@are_equal.register(ParamSpecArgs)
def _(left: ParamSpecArgs, right: Any, /) -> bool:
    return type(left) is type(right) and are_equal(
        left.__origin__, right.__origin__
    )


@are_equal.register(NewType)
def _(left: NewType, right: Any, /) -> bool:
    return (
        type(left) is type(right)
        and (
            getattr(left, '__qualname__', MISSING)
            == getattr(right, '__qualname__', MISSING)
        )
        and are_equal(left.__supertype__, right.__supertype__)
    )


@are_equal.register(ParamSpecKwargs)
def _(left: ParamSpecKwargs, right: Any, /) -> bool:
    return type(left) is type(right) and are_equal(
        left.__origin__, right.__origin__
    )


@are_equal.register(TypeVar)
def _(left: TypeVar, right: Any, /) -> bool:
    left_constraints, right_constraints = (
        getattr(left, '__constraints__', ()),
        getattr(right, '__constraints__', ()),
    )
    return (
        type(left) is type(right)
        and left.__name__ == right.__name__
        and are_equal(
            getattr(left, '__bound__', MISSING),
            getattr(left, '__bound__', MISSING),
        )
        and (
            getattr(left, '__contravariant__', MISSING)
            is getattr(right, '__contravariant__', MISSING)
        )
        and (
            getattr(left, '__covariant__', MISSING)
            is getattr(right, '__covariant__', MISSING)
        )
        and len(left_constraints) == len(right_constraints)
        and all(map(are_equal, left_constraints, right_constraints))
    )


@are_equal.register(bytes)
@are_equal.register(str)
def _(left: bytes | str, right: Any, /) -> bool:
    result = left == right
    assert isinstance(result, bool), result
    return result


to_arguments = get_args
to_origin = get_origin


@singledispatch
def to_repr(value: Any, /) -> str:
    return repr(value)


@to_repr.register(list)
def _(value: list[Any], /) -> str:
    return f'[{", ".join(to_repr(element) for element in value)}]'


@to_repr.register(tuple)
def _(value: tuple[Any, ...], /) -> str:
    return (
        f'({to_repr(value[0])},)'
        if len(value) == 1
        else f'({", ".join(to_repr(element) for element in value)})'
    )


@to_repr.register(type)
def _(value: type, /) -> str:
    if value in (type(None), type(NotImplemented), type(Ellipsis)):
        return f'{type.__qualname__}({value()!r})'
    args = to_arguments(value)
    result = f'{value.__module__}.{value.__qualname__}'
    return f'{result}[{", ".join(map(to_repr, args))}]' if args else result


@to_repr.register(LegacyGenericAlias)
@to_repr.register(type(Union[int, None]))  # noqa: UP007
def _(value: Any, /) -> str:
    origin = to_origin(value)
    arguments = to_arguments(value)
    return (
        (
            (
                f'{to_repr(Optional)}'
                f'[{to_repr(arguments[arguments[0] is type(None)])}]'
            )
            if len(arguments) == 2 and type(None) in arguments
            else (f'{to_repr(origin)}[{", ".join(map(to_repr, arguments))}]')
        )
        if origin is Union
        else (
            (
                (
                    f'{value.__module__}.{name}'
                    f'[{", ".join(map(to_repr, arguments))}]'
                )
                if arguments
                else f'{value.__module__}.{name}[()]'
            )
            if (name := getattr(value, '_name', None)) is not None
            else (
                (f'{to_repr(origin)}[{", ".join(map(to_repr, arguments))}]')
                if arguments
                else f'{to_repr(origin)}[()]'
            )
        )
    )


@to_repr.register(types.GenericAlias)
@to_repr.register(types.UnionType)  # pyright: ignore[reportArgumentType, reportCallIssue]
def _(value: Any, /) -> str:
    origin = to_origin(value)
    arguments = to_arguments(value)
    return (
        (
            f'{to_repr(arguments[arguments[0] is type(None)])} | None'
            if len(arguments) == 2 and type(None) in arguments
            else ' | '.join(map(to_repr, arguments))
        )
        if origin is types.UnionType
        else (
            (f'{to_repr(origin)}[{", ".join(map(to_repr, arguments))}]')
            if arguments
            else f'{to_repr(origin)}[()]'
        )
    )


@to_repr.register(TypeVar)
def _(value: TypeVar, /) -> str:
    arguments = [repr(value.__name__)]
    arguments.extend(map(to_repr, getattr(value, '__constraints__', ())))
    if getattr(value, '__bound__', MISSING) is not MISSING:
        arguments.append(f'bound={to_repr(value.__bound__)}')
    if value.__contravariant__:
        arguments.append('contravariant=True')
    if value.__covariant__:
        arguments.append('covariant=True')
    return f'{to_repr(type(value))}({", ".join(arguments)})'
