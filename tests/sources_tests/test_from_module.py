from importlib.machinery import SOURCE_SUFFIXES
from pathlib import Path
from types import ModuleType

from hypothesis import given

from paradigm.sources import from_module
from . import strategies


@given(strategies.plain_python_modules)
def test_plain_module(module: ModuleType) -> None:
    result = from_module(module)

    assert isinstance(result, Path)
    assert result.exists()
    assert result.is_file()
    assert all(suffix in SOURCE_SUFFIXES for suffix in result.suffixes)


@given(strategies.python_packages)
def test_package(package: ModuleType) -> None:
    result = from_module(package)

    assert isinstance(result, Path)
    assert result.exists()
    assert result.is_dir()
