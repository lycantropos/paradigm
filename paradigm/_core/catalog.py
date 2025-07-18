from __future__ import annotations

import sys as _sys
import types as _types
import typing as _t
from functools import singledispatch as _singledispatch
from typing import Final, TypeAlias

from .utils import decorate_if as _decorate_if

Path: TypeAlias = tuple[str, ...]
QualifiedPath: TypeAlias = tuple[Path, Path]
SEPARATOR: Final[str] = '.'


def join_components(base: Path, /, *components: str) -> Path:
    return (*base, *components)


def join_paths(left: Path, right: Path, /) -> Path:
    return (*left, *right)


def path_from_string(value: str, /) -> Path:
    assert isinstance(value, str), value
    return tuple(value.split('.'))


def path_to_string(value: Path, /) -> str:
    return SEPARATOR.join(value)


@_singledispatch
def qualified_path_from(_value: _t.Any, /) -> QualifiedPath:
    return (), ()


@qualified_path_from.register(_types.BuiltinFunctionType)
@_decorate_if(
    qualified_path_from.register(_types.BuiltinMethodType),
    _sys.implementation.name != 'pypy',
)
def _(
    value: _types.BuiltinFunctionType | _types.BuiltinMethodType, /
) -> QualifiedPath:
    self = value.__self__
    return (
        (
            path_from_string(self.__module__),
            path_from_string(value.__qualname__),
        )
        if isinstance(self, type)
        else (
            (
                path_from_string(
                    self.__name__
                    if self.__spec__ is None
                    else self.__spec__.name
                ),
                path_from_string(value.__qualname__),
            )
            if isinstance(self, _types.ModuleType)
            else (
                (),
                path_from_string(value.__qualname__) if self is None else (),
            )
        )
    )


@qualified_path_from.register(_types.FunctionType)
def _(value: _types.FunctionType, /) -> QualifiedPath:
    return (
        () if value.__module__ is None else path_from_string(value.__module__),
        path_from_string(value.__qualname__),
    )


@_decorate_if(
    qualified_path_from.register(_types.MemberDescriptorType),
    _sys.implementation.name == 'pypy',
)
@_decorate_if(
    qualified_path_from.register(_types.MethodDescriptorType),
    _sys.implementation.name != 'pypy',
)
@_decorate_if(
    qualified_path_from.register(_types.MethodWrapperType),
    _sys.implementation.name != 'pypy',
)
@_decorate_if(
    qualified_path_from.register(_types.WrapperDescriptorType),
    _sys.implementation.name != 'pypy',
)
def _(
    value: (
        _types.MemberDescriptorType
        | _types.MethodDescriptorType
        | _types.MethodWrapperType
        | _types.WrapperDescriptorType
    ),
    /,
) -> QualifiedPath:
    return (
        path_from_string(value.__objclass__.__module__),
        path_from_string(value.__qualname__),
    )


@_decorate_if(
    qualified_path_from.register(_types.MemberDescriptorType),
    _sys.implementation.name == 'pypy',
)
def _(value: _types.MemberDescriptorType, /) -> QualifiedPath:
    return (
        path_from_string(value.__objclass__.__module__),
        (*path_from_string(value.__objclass__.__qualname__), value.__name__),
    )


@qualified_path_from.register(type)
def _(value: type, /) -> QualifiedPath:
    return (
        path_from_string(value.__module__),
        path_from_string(value.__qualname__),
    )


def module_path_from_module(module: _types.ModuleType, /) -> Path:
    return path_from_string(
        module.__name__
        if (module_spec := getattr(module, '__spec__', None)) is None
        else module_spec.name
    )


def object_path_from_callable(value: _t.Callable[..., _t.Any], /) -> Path:
    _, object_path = qualified_path_from(value)
    return object_path
