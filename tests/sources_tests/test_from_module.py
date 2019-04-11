from importlib.machinery import SOURCE_SUFFIXES
from pathlib import Path
from types import ModuleType

from paradigm.sources import from_module


def test_plain_module(plain_python_module: ModuleType) -> None:
    result = from_module(plain_python_module)

    assert isinstance(result, Path)
    assert result.exists()
    assert result.is_file()
    assert all(suffix in SOURCE_SUFFIXES for suffix in result.suffixes)


def test_package(python_package: ModuleType) -> None:
    result = from_module(python_package)

    assert isinstance(result, Path)
    assert result.exists()
    assert result.is_dir()
