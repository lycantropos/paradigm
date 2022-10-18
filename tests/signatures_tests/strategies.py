import inspect
import platform
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
from tests.unsupported import (load_and_add,
                               load_and_update,
                               to_contents)


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
top_coverage_callables = set()
load_and_add(top_coverage_callables, '_compression', 'BaseStream')
load_and_update(top_coverage_callables, 'builtins', ['dict',
                                                     'set.__init__',
                                                     'set.__lt__'])
load_and_add(top_coverage_callables, 'configparser', 'DuplicateSectionError')
load_and_add(top_coverage_callables, 'ctypes', 'c_byte')
load_and_add(top_coverage_callables,
             'formatter', 'NullFormatter.pop_alignment')
load_and_update(top_coverage_callables, 'inspect', ['Signature.__init__',
                                                    'getinnerframes'])
load_and_add(top_coverage_callables, 'logging', 'Handler.get_name')
load_and_add(top_coverage_callables, 'os', 'times_result')
load_and_add(top_coverage_callables, 'sqlite3', 'Connection.rollback')
load_and_add(top_coverage_callables, 'symtable', 'Symbol.is_global')
load_and_add(top_coverage_callables, 'tarfile', 'EOFHeaderError')
load_and_add(top_coverage_callables, 'telnetlib', 'Telnet.fileno')
load_and_add(top_coverage_callables, 'time', 'struct_time')
load_and_update(top_coverage_callables, 'tkinter', ['Misc.focus_force',
                                                    'Wm.iconmask'])
load_and_add(top_coverage_callables, 'turtle', 'RawTurtle.turtlesize')
load_and_add(top_coverage_callables, 'weakref', 'ref')
load_and_add(top_coverage_callables, 'zipfile', 'error')
top_coverage_callables = strategies.sampled_from(list(top_coverage_callables))
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
unsupported_callables = strategies.sampled_from(
        list(unsupported.built_in_functions
             | unsupported.classes
             | unsupported.methods_descriptors
             | unsupported.wrappers_descriptors))
