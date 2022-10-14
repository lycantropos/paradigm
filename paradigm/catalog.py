import builtins
import contextvars
import inspect
import pathlib
import ssl
import struct
import types
import weakref
from functools import singledispatch
from itertools import chain
from typing import (Any,
                    Callable,
                    Optional,
                    Tuple,
                    Type,
                    Union)

from memoir import cached

from . import modules
from .file_system import INIT_MODULE_NAME
from .hints import (MethodDescriptorType,
                    WrapperDescriptorType)


class Path:
    __slots__ = '_parts',

    SEPARATOR = '.'

    def __new__(cls, *parts: str) -> 'Path':
        assert all(cls.SEPARATOR not in part for part in parts), parts
        self = super().__new__(cls)
        self._parts = parts
        return self

    @property
    def parts(self) -> Tuple[str, ...]:
        return self._parts

    def __str__(self) -> str:
        return self.SEPARATOR.join(self._parts)

    def __repr__(self) -> str:
        return (type(self).__qualname__
                + '(' + ', '.join(map(repr, self._parts)) + ')')

    def __eq__(self, other: 'Path') -> bool:
        if not isinstance(other, Path):
            return NotImplemented
        return self._parts == other._parts

    def __hash__(self) -> int:
        return hash(self._parts)

    def join(self, other: 'Path') -> 'Path':
        if not isinstance(other, Path):
            return NotImplemented
        return type(self)(*self._parts, *other._parts)

    @property
    def parent(self) -> 'Path':
        return type(self)(*self._parts[:-1])

    def with_parent(self, parent: 'Path') -> 'Path':
        return type(self)(*parent._parts, *self._parts[len(parent._parts):])

    def is_child_of(self, parent: 'Path') -> bool:
        return self._parts[:len(parent._parts)] == parent._parts


def is_attribute(path: Path) -> bool:
    return len(path.parts) > 1


WILDCARD_IMPORT_NAME = '*'
WILDCARD_IMPORT_PATH = Path(WILDCARD_IMPORT_NAME)


def from_module(object_: types.ModuleType) -> Path:
    return from_string(object_.__name__)


def from_relative_file_path(path: pathlib.Path) -> Path:
    if path.is_absolute():
        raise ValueError('Path should be relative.')
    *parts, module_file_name = path.parts

    def to_module_name(file_name: str) -> Optional[str]:
        if file_name == '.':
            return None
        result = inspect.getmodulename(file_name)
        if result == INIT_MODULE_NAME:
            return None
        return result

    module_name = to_module_name(module_file_name)
    if module_name is not None:
        parts = chain(parts, (module_name,))
    return Path(*parts)


names_replacements = {'Protocol': '_Protocol'}


@singledispatch
def from_callable(callable_: Callable[..., Any]) -> Path:
    raise TypeError(callable_)


@from_callable.register(types.FunctionType)
@from_callable.register(MethodDescriptorType)
@from_callable.register(types.ClassMethodDescriptorType)
@from_callable.register(types.WrapperDescriptorType)
@from_callable.register(types.MethodWrapperType)
@from_callable.register(types.MethodType)
@from_callable.register(types.BuiltinFunctionType)
@from_callable.register(types.BuiltinMethodType)
def _(callable_: Callable[..., Any]) -> Path:
    return from_string(callable_.__qualname__)


@from_callable.register(type)
def from_type(type_: Type[Any]) -> Path:
    return from_string(type_.__qualname__)


def from_string(string: str) -> Path:
    parts = string.split(Path.SEPARATOR)
    parts = map(names_replacements.get, parts, parts)
    return Path(*parts)


@singledispatch
def module_name_factory(object_: Any) -> str:
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


module_name_from_class_or_function_cache = {
    contextvars.Context: contextvars.__name__,
    contextvars.ContextVar: contextvars.__name__,
    contextvars.Token: contextvars.__name__,
    ssl.Purpose: ssl.__name__,
    struct.Struct: struct.__name__,
    types.CodeType: types.__name__,
    types.FrameType: types.__name__,
    types.ModuleType: types.__name__,
    types.TracebackType: types.__name__,
    weakref.ref: weakref.__name__,
}


@module_name_factory.register(types.BuiltinMethodType)
@module_name_factory.register(types.MethodType)
@module_name_factory.register(types.FunctionType)
@module_name_factory.register(type)
@cached.map_(types.MappingProxyType(module_name_from_class_or_function_cache))
def _(
        object_: Union[types.BuiltinMethodType, types.FunctionType,
                       types.MethodType, type]
) -> str:
    result = object_.__module__
    if result is None:
        result = object_.__self__.__class__.__module__
    assert isinstance(result, str)
    return result


@module_name_factory.register(MethodDescriptorType)
@module_name_factory.register(WrapperDescriptorType)
def _(object_: Union[MethodDescriptorType, WrapperDescriptorType]) -> str:
    return module_name_factory(object_.__objclass__)


def is_package(module_path: Path) -> bool:
    return hasattr(modules.safe_import(str(module_path)), '__path__')


BUILTINS_MODULE_PATH = from_module(builtins)
