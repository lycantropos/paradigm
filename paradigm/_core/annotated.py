import sys
import types
import typing as t
from collections import abc
from functools import singledispatch

from typing_extensions import (Literal,
                               ParamSpec,
                               ParamSpecArgs,
                               ParamSpecKwargs)

_T = t.TypeVar('_T')
GenericAlias: t.Any = type(t.List[_T])
del _T


@singledispatch
def are_equal(left: t.Any, right: t.Any) -> bool:
    return left == right


@are_equal.register(GenericAlias)
@are_equal.register(type(t.Union[int, None]))
@are_equal.register(type)
def _(left: t.Union[GenericAlias, t.Type[t.Any]], right: t.Any) -> bool:
    left_args, right_args = to_arguments(left), to_arguments(right)
    left_origin, right_origin = (to_origin(left) or left,
                                 to_origin(right) or right)
    return (left_origin is right_origin
            and len(left_args) == len(right_args)
            and (all(any(are_equal(left_arg, right_arg)
                         for right_arg in right_args)
                     for left_arg in left_args)
                 if (left_origin is t.Union or left_origin is Literal)
                 else all(map(are_equal, left_args, right_args))))


@are_equal.register(abc.Sequence)
def _(left: t.Sequence[t.Any], right: t.Any) -> bool:
    return (type(left) is type(right)
            and len(left) == len(right)
            and all(map(are_equal, left, right)))


@are_equal.register(ParamSpec)
def _(left: ParamSpec, right: t.Any) -> bool:
    return (type(left) is type(right)
            and left.__name__ == right.__name__
            and are_equal(left.__bound__, right.__bound__)
            and left.__contravariant__ is right.__contravariant__
            and left.__covariant__ is right.__covariant__)


@are_equal.register(ParamSpecArgs)
def _(left: ParamSpecArgs, right: t.Any) -> bool:
    return (type(left) is type(right)
            and are_equal(left.__origin__, right.__origin__))


if sys.version_info < (3, 10):
    @are_equal.register(types.LambdaType)
    def _(left: types.LambdaType,
          right: t.Any,
          *,
          _sentinel: t.Any = object()) -> bool:
        left_supertype = getattr(left, '__supertype__', _sentinel)
        right_supertype = getattr(right, '__supertype__', _sentinel)
        return (type(left) is type(right)
                and are_equal(left_supertype, right_supertype))
else:
    are_equal.register(types.UnionType, are_equal.dispatch(type))


    @are_equal.register(t.NewType)
    def _(left: t.NewType,
          right: t.Any,
          *,
          _sentinel: t.Any = object()) -> bool:
        return (type(left) is type(right)
                and (getattr(left, '__qualname__', _sentinel)
                     == getattr(right, '__qualname__', _sentinel))
                and are_equal(left.__supertype__, right.__supertype__))


@are_equal.register(ParamSpecKwargs)
def _(left: ParamSpecKwargs, right: t.Any) -> bool:
    return (type(left) is type(right)
            and are_equal(left.__origin__, right.__origin__))


@are_equal.register(t.TypeVar)
def _(left: t.TypeVar, right: t.Any) -> bool:
    left_constraints, right_constraints = (
        getattr(left, '__constraints__', ()),
        getattr(right, '__constraints__', ())
    )
    return (type(left) is type(right)
            and left.__name__ == right.__name__
            and are_equal(left.__bound__, right.__bound__)
            and left.__contravariant__ is right.__contravariant__
            and left.__covariant__ is right.__covariant__
            and len(left_constraints) == len(right_constraints)
            and all(map(are_equal, left_constraints,
                        right_constraints)))


@are_equal.register(bytes)
@are_equal.register(str)
def _(left: t.Union[bytes, str], right: t.Any) -> bool:
    return left == right


if sys.version_info >= (3, 8):
    to_arguments = t.get_args
    to_origin = t.get_origin
else:
    def to_arguments(annotation: t.Any) -> t.Tuple[t.Any, ...]:
        if isinstance(annotation, GenericAlias):
            result = annotation.__args__
            if (result
                    and to_origin(annotation) is abc.Callable
                    and result[0] is not Ellipsis):
                result = (list(result[:-1]), result[-1])
            return result
        return ()


    def to_origin(annotation: t.Any) -> t.Any:
        if isinstance(annotation, GenericAlias):
            return annotation.__origin__
        elif annotation is t.Generic:
            return t.Generic
        else:
            return None


@singledispatch
def to_repr(value: t.Any) -> str:
    return repr(value)


@to_repr.register(list)
def _(value: t.List[t.Any]) -> str:
    return f'[{", ".join(to_repr(element) for element in value)}]'


@to_repr.register(tuple)
def _(value: t.Tuple[t.Any, ...]) -> str:
    return (f'({to_repr(value[0])},)'
            if len(value) == 1
            else f'({", ".join(to_repr(element) for element in value)})')


@to_repr.register(type)
def _(value: type) -> str:
    if value in (type(None), type(NotImplemented), type(Ellipsis)):
        return f'{type.__qualname__}({value()!r})'
    else:
        args = to_arguments(value)
        result = f'{value.__module__}.{value.__qualname__}'
        return (f'{result}[{", ".join(map(to_repr, args))}]'
                if args
                else result)


@to_repr.register(GenericAlias)
def _(value: GenericAlias) -> str:
    origin = to_origin(value)
    arguments = to_arguments(value)
    return (((f'{to_repr(t.Optional)}'
              f'[{to_repr(arguments[arguments[0] is type(None)])}]')
             if len(arguments) == 2 and type(None) in arguments
             else (f'{to_repr(origin)}'
                   f'[{", ".join(map(to_repr, arguments))}]'))
            if origin is t.Union
            else (((f'{to_repr(origin)}'
                    f'[{", ".join(map(to_repr, arguments))}]')
                   if arguments
                   else f'{to_repr(origin)}[()]')
                  if value._name is None
                  else ((f'{value.__module__}.{value._name}'
                         f'[{", ".join(map(to_repr, arguments))}]')
                        if arguments
                        else f'{value.__module__}.{value._name}[()]')))


@to_repr.register(t.TypeVar)
def _(value: t.TypeVar) -> str:
    arguments = [repr(value.__name__)]
    arguments.extend(map(to_repr, value.__constraints__))
    if value.__bound__ is not None:
        arguments.append(f'bound={to_repr(value.__bound__)}')
    if value.__contravariant__:
        arguments.append('contravariant=True')
    if value.__covariant__:
        arguments.append('covariant=True')
    return f'{to_repr(type(value))}({", ".join(arguments)})'
