import os
from itertools import (chain,
                       repeat,
                       starmap)
from operator import (itemgetter,
                      truediv)
from pathlib import Path
from typing import (Iterator,
                    List)

INIT_MODULE_NAME = '__init__'


def find_files_paths(directory: Path) -> Iterator[Path]:
    def to_files_paths(root: str, files: List[str]) -> Iterator[Path]:
        yield from map(truediv, repeat(Path(root)), files)

    yield from chain.from_iterable(starmap(to_files_paths,
                                           map(itemgetter(0, 2),
                                               os.walk(str(directory)))))
