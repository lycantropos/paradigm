import inspect
from functools import (partial,
                       reduce)
from itertools import chain
from types import (MethodDescriptorType,
                   ModuleType,
                   WrapperDescriptorType)
from typing import (Any,
                    List,
                    Union)

from hypothesis import strategies

from tests import unsupported
from tests.contracts import is_supported
from tests.strategies import modules_list
from tests.utils import to_contents


def to_inner_callables(objects: List[Union[ModuleType, type]]) -> List[Any]:
    return list(filter(callable,
                       chain.from_iterable(map(to_contents, objects))))


modules_callables_list = to_inner_callables(modules_list)
modules_callables = strategies.sampled_from(modules_callables_list)
classes_list = list(filter(is_supported,
                           filter(inspect.isclass, modules_callables_list)))
classes_callables_list = to_inner_callables(classes_list)
classes = strategies.sampled_from(classes_list)
classes_callables = strategies.sampled_from(classes_callables_list)
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
callables = (built_in_functions
             | classes
             | functions
             | methods
             | methods_descriptors
             | wrappers_descriptors)
partial_callables = callables.map(partial)
overloaded_callables = strategies.sampled_from([int, reduce, super, type])
unsupported_callables = strategies.sampled_from(
        list(unsupported.built_in_functions
             | unsupported.classes
             | unsupported.methods_descriptors
             | unsupported.wrappers_descriptors))
