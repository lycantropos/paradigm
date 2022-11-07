import builtins
import sys
import types
import typing as t
from functools import singledispatch

Path = t.Tuple[str, ...]
QualifiedPath = t.Tuple[Path, Path]
SEPARATOR = '.'


def path_from_string(value: str) -> Path:
    assert isinstance(value, str), value
    return tuple(value.split('.'))


def path_to_parent(value: Path) -> Path:
    return value[:-1]


def path_to_string(value: Path) -> str:
    return SEPARATOR.join(value)


@singledispatch
def qualified_path_from(value: t.Any) -> QualifiedPath:
    return (), ()


_T1 = t.TypeVar('_T1')
_T2 = t.TypeVar('_T2')


def _identity(value: _T1) -> _T1:
    return value


def _decorate_if(decorator: t.Callable[[_T1], _T2],
                 condition: bool) -> t.Union[t.Callable[[_T1], _T1],
                                             t.Callable[[_T1], _T2]]:
    return decorator if condition else _identity


@qualified_path_from.register(types.BuiltinFunctionType)
@_decorate_if(qualified_path_from.register(types.BuiltinMethodType),
              sys.implementation.name != 'pypy')
def _(
        value: t.Union[types.BuiltinFunctionType, types.BuiltinMethodType]
) -> QualifiedPath:
    self = value.__self__
    return ((path_from_string(self.__module__),
             path_from_string(value.__qualname__))
            if isinstance(self, type)
            else ((path_from_string(self.__name__
                                    if self.__spec__ is None
                                    else self.__spec__.name),
                   path_from_string(value.__qualname__))
                  if isinstance(self, types.ModuleType)
                  else ((),
                        path_from_string(value.__qualname__)
                        if self is None
                        else ())))


@qualified_path_from.register(types.FunctionType)
def _(value: types.FunctionType) -> QualifiedPath:
    return (()
            if value.__module__ is None
            else path_from_string(value.__module__),
            path_from_string(value.__qualname__))


@_decorate_if(qualified_path_from.register(types.MethodDescriptorType),
              sys.implementation.name != 'pypy')
@_decorate_if(qualified_path_from.register(types.WrapperDescriptorType),
              sys.implementation.name != 'pypy')
def _(
        value: t.Union[types.MemberDescriptorType, types.MethodDescriptorType,
                       types.MethodWrapperType, types.WrapperDescriptorType]
) -> QualifiedPath:
    return (path_from_string(value.__objclass__.__module__),
            path_from_string(value.__qualname__))


@_decorate_if(qualified_path_from.register(types.MemberDescriptorType),
              sys.implementation.name == 'pypy')
@_decorate_if(qualified_path_from.register(types.MethodWrapperType),
              sys.implementation.name != 'pypy')
def _(
        value: t.Union[types.MemberDescriptorType, types.MethodWrapperType]
) -> QualifiedPath:
    return (path_from_string(value.__objclass__.__module__),
            path_from_string(value.__qualname__))


@_decorate_if(qualified_path_from.register(types.MemberDescriptorType),
              sys.implementation.name == 'pypy')
def _(value: types.MemberDescriptorType) -> QualifiedPath:
    return (path_from_string(value.__objclass__.__module__),
            (*path_from_string(value.__objclass__.__qualname__),
             value.__name__))


@qualified_path_from.register(type)
def _(value: type) -> QualifiedPath:
    return (path_from_string(value.__module__),
            path_from_string(value.__qualname__))


def is_attribute(path: Path) -> bool:
    return len(path) > 1


WILDCARD_IMPORT_NAME = '*'
WILDCARD_IMPORT_PATH = (WILDCARD_IMPORT_NAME,)


def module_path_from_module(object_: types.ModuleType) -> Path:
    return path_from_string(object_.__name__
                            if object_.__spec__ is None
                            else object_.__spec__.name)


def object_path_from_callable(value: t.Callable[..., t.Any]) -> Path:
    _, object_path = qualified_path_from(value)
    return object_path


BUILTINS_MODULE_PATH = module_path_from_module(builtins)
