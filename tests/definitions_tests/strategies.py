from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from tests.strategies import (invalid_sources,
                              modules_paths,
                              paths)
from tests.utils import negate

modules_paths = modules_paths
non_existent_files_paths = paths.filter(negate(Path.exists))


def to_non_python_file(source: str) -> Any:
    result = NamedTemporaryFile(mode='w')
    result.file.write(source)
    result.file.close()
    return result


non_python_files = invalid_sources.map(to_non_python_file)
