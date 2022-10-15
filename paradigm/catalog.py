import builtins
import contextvars
import inspect
import pathlib
import ssl
import struct
import sys
import threading
import types
import weakref
from collections import abc
from functools import singledispatch
from itertools import chain
from typing import (Any,
                    Callable,
                    Container,
                    Dict,
                    Iterator,
                    Optional,
                    Tuple,
                    Type,
                    Union)

from memoir import cached

from . import modules
from .file_system import INIT_MODULE_NAME


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


@singledispatch
def from_callable(callable_: Callable[..., Any]) -> Path:
    raise TypeError(callable_)


def _to_corrected_objects_paths(
        module: types.ModuleType,
        *objects_types: type,
        builtins_names: Container[str] = vars(builtins).keys()
) -> Dict[type, Path]:
    namespace = vars(module)
    return {value: Path(name)
            for name, value in namespace.items()
            if (isinstance(value, objects_types)
                and not name.startswith('_')
                and value.__name__ not in namespace
                and (value.__module__ != builtins.__name__
                     or value.__name__ not in builtins_names))}


modules_to_correct = [contextvars, struct, threading, types,
                      ssl, sys, weakref]
object_path_from_class_cache = weakref.WeakKeyDictionary(
        dict(chain.from_iterable(_to_corrected_objects_paths(module,
                                                             type).items()
                                 for module in modules_to_correct))
)
object_path_from_function_cache = weakref.WeakKeyDictionary(
        dict(chain.from_iterable(
                _to_corrected_objects_paths(module, types.BuiltinFunctionType,
                                            types.FunctionType).items()
                for module in modules_to_correct
        ))
)
object_path_from_string_cache = {
    candidate.__qualname__: type_path.join(Path(candidate_name))
    for type_, type_path in object_path_from_class_cache.items()
    for candidate_name, candidate in vars(type_).items()
    if callable(candidate)
}


@cached.map_(types.MappingProxyType(object_path_from_string_cache))
def from_string(string: str) -> Path:
    return Path(*string.split(Path.SEPARATOR))


@from_callable.register(types.FunctionType)
@from_callable.register(types.BuiltinFunctionType)
@cached.map_(types.MappingProxyType(object_path_from_function_cache))
def _(callable_: Callable[..., Any]) -> Path:
    return from_string(callable_.__qualname__)


@from_callable.register(types.MethodDescriptorType)
@from_callable.register(types.ClassMethodDescriptorType)
@from_callable.register(types.WrapperDescriptorType)
@from_callable.register(types.MethodWrapperType)
@from_callable.register(types.MethodType)
@from_callable.register(types.BuiltinMethodType)
def _(callable_: Callable[..., Any]) -> Path:
    return from_string(callable_.__qualname__)


@from_callable.register(type)
@cached.map_(types.MappingProxyType(object_path_from_class_cache))
def from_type(type_: Type[Any]) -> Path:
    return from_string(type_.__qualname__)


@singledispatch
def module_name_factory(object_: Any) -> str:
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


def _to_corrected_modules_names(
        module: types.ModuleType,
) -> Dict[type, str]:
    return {value: module.__name__
            for name, value in vars(module).items()
            if (isinstance(value, type)
                and not name.startswith('_')
                and value.__module__ != module.__name__
                and getattr(module, from_type(value).parts[-1],
                            None) is value
                and getattr(modules.safe_import(value.__module__),
                            from_type(value).parts[-1],
                            None) is None)}


module_name_from_type_cache = weakref.WeakKeyDictionary(
        dict(chain.from_iterable(_to_corrected_modules_names(module).items()
                                 for module in modules_to_correct))
)
module_name_from_method_cache = {
    candidate: module_name
    for type_, module_name in module_name_from_type_cache.items()
    for candidate_name, candidate in vars(type_).items()
    if callable(candidate)
}


class _UnhashableLookupMappingProxyType(abc.Mapping):
    def __new__(cls,
                *args: Any,
                **kwargs: Any) -> '_UnhashableLookupMappingProxyType':
        self = super().__new__(cls)
        self._inner = types.MappingProxyType(*args, **kwargs)
        return self

    def __len__(self) -> int:
        return len(self._inner)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._inner)

    def __getitem__(self, key: Any) -> Any:
        try:
            return self._inner[key]
        except TypeError as error:
            raise KeyError(key) from error


@module_name_factory.register(types.BuiltinMethodType)
@module_name_factory.register(types.MethodType)
@cached.map_(_UnhashableLookupMappingProxyType(module_name_from_method_cache))
def _(
        object_: Union[types.BuiltinMethodType, types.MethodType,
                       types.MethodDescriptorType]
) -> str:
    result = object_.__module__
    if result is None:
        result = object_.__self__.__class__.__module__
    return result or builtins.__name__


@module_name_factory.register(types.BuiltinFunctionType)
@module_name_factory.register(types.FunctionType)
def _(object_: types.FunctionType) -> str:
    return object_.__module__ or builtins.__name__


@module_name_factory.register(type)
@cached.map_(types.MappingProxyType(module_name_from_type_cache))
def _(object_: type) -> str:
    return object_.__module__ or builtins.__name__


if types.MethodDescriptorType is not types.FunctionType:
    @module_name_factory.register(types.MethodDescriptorType)
    @module_name_factory.register(types.WrapperDescriptorType)
    def _(object_: Union[types.MethodDescriptorType,
                         types.WrapperDescriptorType]) -> str:
        return module_name_factory(object_.__objclass__)


def is_package(module_path: Path) -> bool:
    return hasattr(modules.safe_import(str(module_path)), '__path__')


BUILTINS_MODULE_PATH = from_module(builtins)
