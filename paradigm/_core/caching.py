import sys
import warnings
from compileall import compile_file
from importlib import import_module
from importlib.machinery import SOURCE_SUFFIXES
from operator import attrgetter
from pathlib import Path
from typing import Any, Final

from . import pretty

FILE_SUFFIX: Final[str] = SOURCE_SUFFIXES[0]


def load(path: Path, name: str, /, *names: str) -> tuple[Any, ...]:
    parent_path = next(
        candidate_path
        for candidate_path_string in sys.path
        if path.is_relative_to(candidate_path := Path(candidate_path_string))
    )
    return attrgetter(name, *names)(
        import_module(
            '.'.join(path.relative_to(parent_path).with_suffix('').parts)
        )
    )


def save(path: Path, /, **values: Any) -> None:
    try:
        with path.open('w', encoding='utf-8') as file:
            for name, value in values.items():
                file.write(f'{name} = ' + pretty.repr_from(value, 4, 0) + '\n')
        compile_file(path, quiet=2)
    except Exception as error:
        warnings.warn(
            f'Failed saving "{path}". '
            f'Reason:\n{pretty.format_exception(error)}',
            UserWarning,
            stacklevel=2,
        )
