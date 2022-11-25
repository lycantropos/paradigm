import sys as _sys
import types as _types
import typing as _t
from functools import singledispatch as _singledispatch

from .utils import decorate_if as _decorate_if

Path = _t.Tuple[str, ...]
QualifiedPath = _t.Tuple[Path, Path]
SEPARATOR = '.'


def path_from_string(value: str) -> Path:
    assert isinstance(value, str), value
    return tuple(value.split('.'))


def path_to_parent(value: Path) -> Path:
    return value[:-1]


def path_to_string(value: Path) -> str:
    return SEPARATOR.join(value)


@_singledispatch
def qualified_path_from(value: _t.Any) -> QualifiedPath:
    return (), ()


@qualified_path_from.register(_types.BuiltinFunctionType)
@_decorate_if(qualified_path_from.register(_types.BuiltinMethodType),
              _sys.implementation.name != 'pypy')
def _(
        value: _t.Union[_types.BuiltinFunctionType, _types.BuiltinMethodType]
) -> QualifiedPath:
    self = value.__self__
    return ((path_from_string(self.__module__),
             path_from_string(value.__qualname__))
            if isinstance(self, type)
            else ((path_from_string(self.__name__
                                    if self.__spec__ is None
                                    else self.__spec__.name),
                   path_from_string(value.__qualname__))
                  if isinstance(self, _types.ModuleType)
                  else ((),
                        path_from_string(value.__qualname__)
                        if self is None
                        else ())))


@qualified_path_from.register(_types.FunctionType)
def _(value: _types.FunctionType) -> QualifiedPath:
    return (()
            if value.__module__ is None
            else path_from_string(value.__module__),
            path_from_string(value.__qualname__))


@_decorate_if(qualified_path_from.register(_types.MemberDescriptorType),
              _sys.implementation.name == 'pypy')
@_decorate_if(qualified_path_from.register(_types.MethodDescriptorType),
              _sys.implementation.name != 'pypy')
@_decorate_if(qualified_path_from.register(_types.MethodWrapperType),
              _sys.implementation.name != 'pypy')
@_decorate_if(qualified_path_from.register(_types.WrapperDescriptorType),
              _sys.implementation.name != 'pypy')
def _(
        value: _t.Union[_types.MemberDescriptorType,
                        _types.MethodDescriptorType, _types.MethodWrapperType,
                        _types.WrapperDescriptorType]
) -> QualifiedPath:
    return (path_from_string(value.__objclass__.__module__),
            path_from_string(value.__qualname__))


@_decorate_if(qualified_path_from.register(_types.MemberDescriptorType),
              _sys.implementation.name == 'pypy')
def _(value: _types.MemberDescriptorType) -> QualifiedPath:
    return (path_from_string(value.__objclass__.__module__),
            (*path_from_string(value.__objclass__.__qualname__),
             value.__name__))


@qualified_path_from.register(type)
def _(value: type) -> QualifiedPath:
    return (path_from_string(value.__module__),
            path_from_string(value.__qualname__))


def is_attribute(path: Path) -> bool:
    return len(path) > 1


def module_path_from_module(object_: _types.ModuleType) -> Path:
    return path_from_string(object_.__name__
                            if object_.__spec__ is None
                            else object_.__spec__.name)


def object_path_from_callable(value: _t.Callable[..., _t.Any]) -> Path:
    _, object_path = qualified_path_from(value)
    return object_path
