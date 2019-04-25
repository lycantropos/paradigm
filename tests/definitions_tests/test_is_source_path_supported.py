from contextlib import closing
from pathlib import Path
from typing import Any

from hypothesis import given

from paradigm.definitions.base import is_source_path_supported
from . import strategies


@given(strategies.non_existent_files_paths)
def test_non_existent_file_path(non_existent_file_path: Path) -> None:
    assert not is_source_path_supported(non_existent_file_path)


@given(strategies.non_python_files)
def test_non_python_file_path(file: Any) -> None:
    with closing(file):
        file_path = Path(file.name)

        assert not is_source_path_supported(file_path)
