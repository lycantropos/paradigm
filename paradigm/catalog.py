import importlib
import inspect
import pathlib
import struct
import sys
import types
import weakref
from functools import singledispatch
from itertools import chain
from types import (BuiltinMethodType,
                   FunctionType,
                   ModuleType)
from typing import (Any,
                    Iterable,
                    Optional,
                    Tuple,
                    Union)

from memoir import cached

from .file_system import INIT_MODULE_NAME
from .hints import (MethodDescriptorType,
                    WrapperDescriptorType)


class Path:
    __slots__ = ('_parts',)

    SEPARATOR = '.'

    def __init__(self, *parts: str) -> None:
        self._parts = parts

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


WILDCARD_IMPORT = Path('*')


def paths_factory(object_: Union[BuiltinMethodType, FunctionType,
                                 MethodDescriptorType, type],
                  *,
                  max_depth: int = 2) -> Iterable[Path]:
    module = importlib.import_module(module_name_factory(object_))
    propertyspaces = iter(((Path(), module, 0),))
    while True:
        try:
            parent_path, propertyspace, depth = next(propertyspaces)
        except StopIteration:
            break

        def to_path(object_name: str) -> Path:
            return parent_path.join(from_string(object_name))

        namespace = dict(vars(propertyspace))
        yield from (to_path(name)
                    for name, content in namespace.items()
                    if content is object_)
        next_depth = depth + 1
        if next_depth < max_depth:
            propertyspaces = chain(propertyspaces,
                                   [(to_path(name), content, next_depth)
                                    for name, content in namespace.items()
                                    if inspect.isclass(content)])
    yield from_string(object_.__qualname__)


def from_module(object_: ModuleType) -> Path:
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


def from_string(string: str) -> Path:
    parts = string.split(Path.SEPARATOR)
    parts = map(names_replacements.get, parts, parts)
    return Path(*parts)


@singledispatch
def module_name_factory(object_: Any) -> str:
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


replacements = {'nt': 'os',
                'posix': 'os'}


@module_name_factory.register(str)
def module_name_from_string(object_: str) -> str:
    return replacements.get(object_, object_)


module_name_from_class_or_function_cache = {
    struct.Struct: struct.__name__,
    types.CodeType: types.__name__,
    types.FrameType: types.__name__,
    types.ModuleType: types.__name__,
    weakref.ref: weakref.__name__,
}

if sys.version_info >= (3, 7):
    import contextvars

    module_name_from_class_or_function_cache.update(
            {contextvars.Context: contextvars.__name__,
             contextvars.ContextVar: contextvars.__name__,
             contextvars.Token: contextvars.__name__,
             types.TracebackType: types.__name__})


@module_name_factory.register(BuiltinMethodType)
@module_name_factory.register(FunctionType)
@module_name_factory.register(type)
@cached.map_(types.MappingProxyType(module_name_from_class_or_function_cache))
def module_name_from_class_or_function(object_: Union[BuiltinMethodType,
                                                      FunctionType, type]
                                       ) -> str:
    result = object_.__module__
    if result is None:
        result = object_.__self__.__class__.__module__
    return module_name_factory(result)


@module_name_factory.register(MethodDescriptorType)
@module_name_factory.register(WrapperDescriptorType)
def module_name_from_method_descriptor(object_: MethodDescriptorType) -> str:
    return module_name_factory(object_.__objclass__)


def is_package(module_path: Path) -> bool:
    return hasattr(importlib.import_module(str(module_path)), '__path__')
