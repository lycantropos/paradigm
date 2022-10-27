import ast
import importlib.machinery
import importlib.util
import platform
import types
from functools import singledispatch
from pathlib import Path
from typing import (Any,
                    Optional,
                    Union)

from paradigm._core import (catalog,
                            qualified)
from paradigm._core.discovery import (stdlib_modules_names,
                                      unsupported_stdlib_modules_names)
from tests import unsupported


@singledispatch
def is_supported(object_: Any) -> bool:
    """
    Checks if object metadata extraction is supported.
    """
    return False


@is_supported.register(types.ModuleType)
def _(object_: types.ModuleType) -> bool:
    module_name = object_.__name__
    return (module_name in stdlib_modules_names
            and module_name not in unsupported_stdlib_modules_names
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
    module_name = str(module_path)
    if module_name in stdlib_modules_names:
        if module_name in unsupported_stdlib_modules_names:
            return False
        module = importlib.import_module(module_name)
        return is_supported(module)
    spec = find_spec(module_path)
    if spec is None:
        return False
    source_path_string = spec.origin
    if source_path_string is None:
        return False
    return is_source_path_supported(Path(source_path_string))


def find_spec(
        module_path: catalog.Path
) -> Optional[importlib.machinery.ModuleSpec]:
    module_name = str(module_path)
    try:
        return importlib.util.find_spec(module_name)
    except (ImportError, ValueError):
        return None


@is_supported.register(types.BuiltinFunctionType)
@is_supported.register(types.BuiltinMethodType)
def _(object_: Union[types.BuiltinFunctionType,
                     types.BuiltinMethodType]) -> bool:
    return ((object_.__self__.__name__ not in unsupported_stdlib_modules_names
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
    module_path = catalog.module_path_from_callable(object_)
    return module_path is not None and is_module_path_supported(module_path)


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
    module_name, _ = qualified.name_from(object_)
    return module_name is not None and module_name in stdlib_modules_names
