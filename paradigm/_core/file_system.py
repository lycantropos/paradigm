import os
from collections.abc import Iterator
from importlib.machinery import SOURCE_SUFFIXES
from itertools import chain, repeat, starmap
from operator import itemgetter, truediv
from pathlib import Path
from typing import Final

INIT_MODULE_NAME: Final[str] = '__init__'
MODULE_FILE_SUFFIX: Final[str] = SOURCE_SUFFIXES[0]


def find_files_paths(directory: Path) -> Iterator[Path]:
    def to_files_paths(root: str, files: list[str]) -> Iterator[Path]:
        yield from map(truediv, repeat(Path(root)), files)

    yield from chain.from_iterable(
        starmap(to_files_paths, map(itemgetter(0, 2), os.walk(str(directory))))
    )
