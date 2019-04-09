from pathlib import Path

from paradigm.definitions.base import is_source_path_supported


def test_non_existent_file_path(non_existent_file_path: Path) -> None:
    assert not is_source_path_supported(non_existent_file_path)


def test_non_python_file_path(non_python_file_path: Path) -> None:
    assert not is_source_path_supported(non_python_file_path)
