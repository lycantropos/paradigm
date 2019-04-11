import sys
from functools import partial
from pathlib import Path
from types import (BuiltinFunctionType,
                   FunctionType,
                   MethodType,
                   ModuleType)
from typing import (Any,
                    Callable)

import pytest
from py._path.local import LocalPath

from paradigm.hints import (MethodDescriptorType,
                            WrapperDescriptorType)
from tests import strategies
from tests.utils import (find,
                         negate)


@pytest.fixture(scope='function')
def built_in_function() -> BuiltinFunctionType:
    return find(strategies.built_in_functions)


@pytest.fixture(scope='function')
def callable_() -> Callable[..., Any]:
    return find(strategies.callables)


@pytest.fixture(scope='function')
def second_callable() -> Callable[..., Any]:
    return find(strategies.callables)


@pytest.fixture(scope='function')
def third_callable() -> Callable[..., Any]:
    return find(strategies.callables)


@pytest.fixture(scope='function')
def class_() -> type:
    return find(strategies.classes)


@pytest.fixture(scope='function')
def function() -> FunctionType:
    return find(strategies.functions)


@pytest.fixture(scope='function')
def method() -> MethodType:
    return find(strategies.methods)


@pytest.fixture(scope='function')
def method_descriptor() -> MethodDescriptorType:
    return find(strategies.methods_descriptors)


@pytest.fixture(scope='function')
def overloaded_callable() -> Callable[..., Any]:
    return find(strategies.overloaded_callables)


@pytest.fixture(scope='function')
def partial_callable() -> partial:
    return find(strategies.partial_callables)


@pytest.fixture(scope='function')
def unsupported_callable() -> Callable[..., Any]:
    return find(strategies.unsupported_callables)


@pytest.fixture(scope='function')
def wrapper_descriptor() -> WrapperDescriptorType:
    return find(strategies.methods_descriptors)


@pytest.fixture(scope='function')
def non_existent_file_path() -> Path:
    return find(strategies.paths.filter(negate(Path.exists)))


@pytest.fixture(scope='function')
def non_python_file_path(tmpdir: LocalPath) -> Path:
    source = find(strategies.invalid_sources)
    raw_file = tmpdir.join(find(strategies.identifiers))
    raw_file.write_text(source,
                        encoding=sys.getdefaultencoding())
    try:
        yield Path(raw_file.strpath)
    finally:
        raw_file.remove()


@pytest.fixture(scope='function')
def module() -> ModuleType:
    return find(strategies.modules)


@pytest.fixture(scope='function')
def plain_python_module() -> ModuleType:
    return find(strategies.plain_python_modules)


@pytest.fixture(scope='function')
def python_package() -> ModuleType:
    return find(strategies.python_packages)
