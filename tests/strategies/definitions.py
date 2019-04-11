import importlib
import inspect
import platform
from functools import (partial,
                       reduce)
from types import ModuleType
from typing import (Any,
                    Union)

from hypothesis import strategies
from hypothesis.searchstrategy import SearchStrategy

from paradigm.definitions import (is_supported,
                                  stdlib_modules_names,
                                  to_contents,
                                  unsupported)
from paradigm.hints import (MethodDescriptorType,
                            WrapperDescriptorType)
from tests.utils import negate

stdlib_modules = list(map(importlib.import_module,
                          stdlib_modules_names
                          - unsupported.stdlib_modules_names))
modules = (strategies.sampled_from(stdlib_modules)
           .filter(is_supported))


def is_python_module(module: ModuleType) -> bool:
    try:
        module.__file__
    except AttributeError:
        return False
    else:
        return True


python_modules = modules.filter(is_python_module)


def is_python_package(module: ModuleType) -> bool:
    try:
        module.__path__
    except AttributeError:
        return False
    else:
        return True


plain_python_modules = python_modules.filter(negate(is_python_package))
python_packages = modules.filter(is_python_package)


def flatten_module_or_class(object_: Union[ModuleType, type]
                            ) -> SearchStrategy:
    return strategies.sampled_from(to_contents(object_))


modules_callables = (modules.flatmap(flatten_module_or_class)
                     .filter(callable))
classes = (modules_callables.filter(inspect.isclass)
           .filter(is_supported))
classes_callables = (classes.flatmap(flatten_module_or_class)
                     .filter(callable))
methods = classes_callables.filter(inspect.isfunction)


def is_method_descriptor(object_: Any) -> bool:
    return isinstance(object_, MethodDescriptorType)


methods_descriptors = (classes_callables.filter(is_method_descriptor)
                       .filter(is_supported))


def is_wrapper_descriptor(object_: Any) -> bool:
    return isinstance(object_, WrapperDescriptorType)


wrappers_descriptors = (classes_callables.filter(is_wrapper_descriptor)
                        .filter(is_supported))
functions = (modules_callables.filter(inspect.isfunction)
             .filter(is_supported))
built_in_functions = (modules_callables.filter(inspect.isbuiltin)
                      .filter(is_supported))
unsupported_callables = strategies.sampled_from(
        list(unsupported.built_in_functions
             | unsupported.classes
             | unsupported.methods_descriptors
             | unsupported.wrappers_descriptors))
callables = (built_in_functions
             | classes
             | functions
             | methods
             | methods_descriptors
             | wrappers_descriptors)
partial_callables = callables.map(partial)
if platform.python_implementation() == 'PyPy':
    overloaded_callables = strategies.nothing()
else:
    overloaded_callables = strategies.sampled_from([int, reduce, super, type])
