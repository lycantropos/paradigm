import builtins
import pathlib
import types
from importlib.util import find_spec
from typing import (Any,
                    Callable,
                    Optional,
                    Tuple)

from . import (file_system,
               qualified)


class Path:
    __slots__ = '_parts',

    SEPARATOR = '.'

    def __new__(cls, *parts: str) -> 'Path':
        assert all(cls.SEPARATOR not in part for part in parts), parts
        self = super().__new__(cls)
        self._parts = parts
        return self

    @property
    def final_name(self) -> str:
        return self._parts[-1]

    @property
    def first_name(self) -> str:
        return self._parts[0]

    @property
    def parent(self) -> 'Path':
        return type(self)(*self._parts[:-1])

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

    def suffix(self, part: str) -> 'Path':
        return type(self)(*self._parts, part)

    def join(self, other: 'Path') -> 'Path':
        assert isinstance(other, Path), other
        return type(self)(*self._parts, *other._parts)

    def with_parent(self, parent: 'Path') -> 'Path':
        return type(self)(*parent._parts, *self._parts[len(parent._parts):])

    def is_child_of(self, parent: 'Path') -> bool:
        return self._parts[:len(parent._parts)] == parent._parts


def is_attribute(path: Path) -> bool:
    return len(path.parts) > 1


WILDCARD_IMPORT_NAME = '*'
WILDCARD_IMPORT_PATH = Path(WILDCARD_IMPORT_NAME)


def module_path_from_callable(value: Any) -> Optional[Path]:
    module_name, _ = qualified.name_from(value)
    return None if module_name is None else path_from_string(module_name)


def module_path_from_module(object_: types.ModuleType) -> Path:
    return path_from_string(object_.__name__)


def object_path_from_callable(value: Callable[..., Any]) -> Path:
    _, object_name = qualified.name_from(value)
    return path_from_string(object_name)


def path_from_string(string: str) -> Path:
    return Path(*string.split(Path.SEPARATOR))


def is_package(module_path: Path) -> bool:
    spec = find_spec(str(module_path))
    return (spec.origin is not None
            and pathlib.Path(spec.origin).stem == file_system.INIT_MODULE_NAME)


BUILTINS_MODULE_PATH = module_path_from_module(builtins)
