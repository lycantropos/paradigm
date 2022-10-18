import builtins
import importlib.util
import pathlib
import platform
import types
from functools import (singledispatch,
                       wraps)
from typing import (Any,
                    Callable,
                    Optional,
                    Tuple,
                    TypeVar,
                    Union)

from . import file_system


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


QualifiedName = Tuple[Optional[str], str]


def is_attribute(path: Path) -> bool:
    return len(path.parts) > 1


WILDCARD_IMPORT_NAME = '*'
WILDCARD_IMPORT_PATH = Path(WILDCARD_IMPORT_NAME)


def module_path_from_callable(value: Any) -> Path:
    result, _ = qualified_name_from(value)
    return path_from_string(result)


def module_path_from_module(object_: types.ModuleType) -> Path:
    return path_from_string(object_.__name__)


def object_path_from_callable(value: Callable[..., Any]) -> Path:
    _, object_name = qualified_name_from(value)
    return path_from_string(object_name)


def path_from_string(string: str) -> Path:
    return Path(*string.split(Path.SEPARATOR))


def is_package(module_path: Path) -> bool:
    spec = importlib.util.find_spec(str(module_path))
    return (spec.origin is not None
            and pathlib.Path(spec.origin).stem == file_system.INIT_MODULE_NAME)


@singledispatch
def qualified_name_from(value: Any) -> QualifiedName:
    return None, ''


@qualified_name_from.register(types.BuiltinFunctionType)
@qualified_name_from.register(types.BuiltinMethodType)
def _(value: Union[types.BuiltinFunctionType,
                   types.BuiltinMethodType]) -> QualifiedName:
    return ((value.__self__.__module__, value.__qualname__)
            if isinstance(value.__self__, type)
            else ((value.__self__.__spec__.name, value.__qualname__)
                  if isinstance(value.__self__, types.ModuleType)
                  else (type(value.__self__).__module__, value.__qualname__)))


@qualified_name_from.register(types.FunctionType)
def _(value: types.FunctionType) -> QualifiedName:
    return value.__module__, value.__qualname__


_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')


def _identity(value: _T1) -> _T1:
    return value


def _decorate_if(decorator: Callable[[_T1], _T2],
                 condition: bool) -> Callable[[_T1], Union[_T1, _T2]]:
    @wraps(decorator)
    def wrapper(wrapped: _T1) -> Union[_T1, _T2]:
        return decorator(wrapped) if condition else wrapped

    return wrapper


@_decorate_if(qualified_name_from.register(types.MethodDescriptorType),
              platform.python_implementation() != 'PyPy')
@_decorate_if(qualified_name_from.register(types.WrapperDescriptorType),
              platform.python_implementation() != 'PyPy')
def _(
        value: Union[types.MemberDescriptorType, types.MethodDescriptorType,
                     types.MethodWrapperType, types.WrapperDescriptorType]
) -> QualifiedName:
    return value.__objclass__.__module__, value.__qualname__


@_decorate_if(qualified_name_from.register(types.MemberDescriptorType),
              platform.python_implementation() != 'PyPy')
@_decorate_if(qualified_name_from.register(types.MethodWrapperType),
              platform.python_implementation() != 'PyPy')
def _(
        value: Union[types.MemberDescriptorType, types.MethodDescriptorType,
                     types.MethodWrapperType, types.WrapperDescriptorType]
) -> QualifiedName:
    return value.__objclass__.__module__, value.__qualname__


@_decorate_if(qualified_name_from.register(types.MemberDescriptorType),
              platform.python_implementation() == 'PyPy')
def _(
        value: Union[types.MemberDescriptorType, types.MethodDescriptorType,
                     types.MethodWrapperType, types.WrapperDescriptorType]
) -> QualifiedName:
    return (value.__objclass__.__module__,
            value.__objclass__.__qualname__ + '.' + value.__name__)


@qualified_name_from.register(types.MethodType)
def _(value: types.MethodType) -> QualifiedName:
    return type(value.__self__).__module__, value.__qualname__


@qualified_name_from.register(type)
def _(value: type) -> QualifiedName:
    return value.__module__, value.__qualname__


BUILTINS_MODULE_PATH = module_path_from_module(builtins)
