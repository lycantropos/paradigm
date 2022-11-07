import ast
import platform
import types
from functools import singledispatch
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import (Any,
                    Union)

from paradigm._core import catalog
from paradigm._core.discovery import unsupported_stdlib_modules_paths
from paradigm._core.sources import stdlib_modules_paths
from tests import unsupported


@singledispatch
def is_supported(object_: Any) -> bool:
    """
    Checks if object metadata extraction is supported.
    """
    return False


@is_supported.register(types.ModuleType)
def _(object_: types.ModuleType) -> bool:
    module_path = catalog.module_path_from_module(object_)
    return (module_path in stdlib_modules_paths
            and module_path not in unsupported_stdlib_modules_paths
            and object_ not in unsupported.stdlib_modules
            or has_supported_python_source_file(object_))


def is_source_path_supported(source_path: Path) -> bool:
    try:
        source = source_path.read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return False
    try:
        ast.parse(source,
                  filename=str(source_path))
    except SyntaxError:
        return False
    else:
        return True


def is_module_path_supported(module_path: catalog.Path) -> bool:
    module_name = catalog.path_to_string(module_path)
    if module_path in stdlib_modules_paths:
        if module_path in unsupported_stdlib_modules_paths:
            return False
        module = import_module(module_name)
        return is_supported(module)
    try:
        spec = find_spec(module_name)
    except (ImportError, ValueError):
        return False
    if spec is None:
        return False
    source_path_string = spec.origin
    if source_path_string is None:
        return False
    return is_source_path_supported(Path(source_path_string))


@is_supported.register(types.BuiltinFunctionType)
@is_supported.register(types.BuiltinMethodType)
def _(object_: Union[types.BuiltinFunctionType,
                     types.BuiltinMethodType]) -> bool:
    return (((catalog.module_path_from_module(object_.__self__)
              not in unsupported_stdlib_modules_paths)
             and object_.__self__ not in unsupported.stdlib_modules
             and object_ not in unsupported.built_in_functions)
            if isinstance(object_.__self__, types.ModuleType)
            else (object_.__self__ not in unsupported.classes
                  if isinstance(object_.__self__, type)
                  else is_supported(type(object_.__self__))))


@is_supported.register(types.MethodType)
def _(object_: types.MethodType) -> bool:
    return is_supported(object_.__func__)


@is_supported.register(type)
def _(object_: type) -> bool:
    return (object_ not in unsupported.classes
            or (not is_stdlib_object(object_)
                and is_module_path_supported(
                            catalog.path_from_string(object_.__module__)
                    )))


@is_supported.register(types.FunctionType)
def _(object_: types.FunctionType) -> bool:
    return is_module_path_supported(module_path_from_callable(object_))


def module_path_from_callable(value: Any) -> catalog.Path:
    module_path, _ = catalog.qualified_path_from(value)
    return module_path


if platform.python_implementation() != 'PyPy':
    @is_supported.register(types.MethodDescriptorType)
    def _(object_: types.MethodDescriptorType) -> bool:
        return (object_.__objclass__ not in unsupported.classes
                and object_ not in unsupported.methods_descriptors)


    @is_supported.register(types.WrapperDescriptorType)
    def _(object_: types.WrapperDescriptorType) -> bool:
        return (object_.__objclass__ not in unsupported.classes
                and object_ not in unsupported.wrappers_descriptors)


def has_supported_python_source_file(module: types.ModuleType) -> bool:
    try:
        file_path_string = module.__file__
    except AttributeError:
        return False
    return (file_path_string is not None
            and is_source_path_supported(Path(file_path_string)))


def is_stdlib_object(object_: Any) -> bool:
    module_path, _ = catalog.qualified_path_from(object_)
    return module_path is not None and module_path in stdlib_modules_paths
