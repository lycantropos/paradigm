import ast
import importlib.machinery
import importlib.util
import os
import sys
from functools import singledispatch
from operator import methodcaller
from pathlib import Path
from types import (BuiltinFunctionType,
                   FunctionType,
                   ModuleType)
from typing import (Any,
                    Callable,
                    Iterable,
                    Optional,
                    Union)

from paradigm import catalog
from paradigm.hints import (MethodDescriptorType,
                            WrapperDescriptorType)
from . import unsupported


@singledispatch
def is_supported(object_: Any) -> bool:
    """
    Checks if object metadata extraction is supported.
    """
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


def find_stdlib_modules_names(directory_path: Path = Path(os.__file__).parent,
                              ) -> Iterable[str]:
    yield from sys.builtin_module_names

    def is_stdlib_module_path(path: Path) -> bool:
        base_name = path.stem
        # skips 'LICENSE', '__pycache__', 'site-packages', etc.
        return not (base_name.isupper()
                    or base_name.startswith('__')
                    or '-' in base_name)

    sources_paths = filter(is_stdlib_module_path, directory_path.iterdir())
    sources_relative_paths = map(methodcaller(Path.relative_to.__name__,
                                              directory_path),
                                 sources_paths)
    yield from map(str, map(methodcaller(Path.with_suffix.__name__, ''),
                            sources_relative_paths))


stdlib_modules_names = set(find_stdlib_modules_names())


@is_supported.register(ModuleType)
def is_module_supported(object_: ModuleType) -> bool:
    module_name = object_.__name__
    return (module_name in stdlib_modules_names
            and module_name not in unsupported.stdlib_modules_names
            and object_ not in unsupported.stdlib_modules
            or has_supported_python_source_file(object_))


@is_supported.register(Path)
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
    return True


@is_supported.register(catalog.Path)
def is_module_path_supported(module_path: catalog.Path) -> bool:
    module_name = str(module_path)
    if module_name in stdlib_modules_names:
        if module_name in unsupported.stdlib_modules_names:
            return False
        module = importlib.import_module(module_name)
        return is_supported(module)
    spec = find_spec(module_path)
    if spec is None:
        return False
    source_path_string = spec.origin
    if source_path_string is None:
        return False
    return is_supported(Path(source_path_string))


def find_spec(module_path: catalog.Path
              ) -> Optional[importlib.machinery.ModuleSpec]:
    module_name = str(module_path)
    try:
        return importlib.util.find_spec(module_name)
    except (ImportError, ValueError):
        return None


@is_supported.register(BuiltinFunctionType)
def is_built_in_function_supported(object_: BuiltinFunctionType) -> bool:
    return (is_stdlib_callable_supported(object_)
            and is_not_private(object_)
            and has_module(object_)
            and object_ not in unsupported.built_in_functions)


@is_supported.register(type)
def is_class_supported(object_: type) -> bool:
    return (is_stdlib_callable_supported(object_)
            and is_not_private(object_)
            and object_ not in unsupported.classes
            or not is_stdlib_object(object_)
            and has_module(object_)
            and is_supported(catalog.factory(object_.__module__)))


@is_supported.register(FunctionType)
def is_function_supported(object_: FunctionType) -> bool:
    return (has_module(object_)
            and is_supported(catalog.factory(object_.__module__)))


@is_supported.register(MethodDescriptorType)
def is_method_descriptor_supported(object_: MethodDescriptorType) -> bool:
    return (is_stdlib_callable_supported(object_)
            and is_not_private(object_)
            and object_ not in unsupported.methods_descriptors)


@is_supported.register(WrapperDescriptorType)
def is_wrapper_descriptor_supported(object_: WrapperDescriptorType) -> bool:
    return (is_stdlib_callable_supported(object_)
            and object_ not in unsupported.wrappers_descriptors)


def has_supported_python_source_file(module: ModuleType) -> bool:
    try:
        file_path_string = module.__file__
    except AttributeError:
        return False
    return is_supported(Path(file_path_string))


def is_stdlib_object(object_: Any) -> bool:
    if not has_module(object_):
        return False
    top_module_name = catalog.factory(object_.__module__).parts[0]
    return top_module_name in stdlib_modules_names


def is_stdlib_callable_supported(callable_: Callable[..., Any]) -> bool:
    return callable_ not in unsupported.stdlib_modules_callables


def is_not_private(object_: Union[BuiltinFunctionType,
                                  MethodDescriptorType,
                                  type]) -> bool:
    return not object_.__name__.startswith('_')


def has_module(object_: Any) -> bool:
    return (hasattr(object_, '__module__')
            and object_.__module__)
