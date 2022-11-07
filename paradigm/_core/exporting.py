import warnings
from compileall import compile_file
from pathlib import Path
from typing import Any

from . import pretty


def save(path: Path, **values: Any) -> None:
    try:
        with path.open('w',
                       encoding='utf-8') as file:
            for name, value in values.items():
                file.write(f'{name} = '
                           + pretty.repr_from(value, 4, 0)
                           + '\n')
        compile_file(path,
                     quiet=2)
    except Exception as error:
        warnings.warn(f'Failed saving "{path}". '
                      f'Reason:\n{pretty.format_exception(error)}',
                      UserWarning)
