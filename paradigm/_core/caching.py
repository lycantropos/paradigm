import typing as t
import warnings
from compileall import compile_file
from importlib import import_module
from importlib.machinery import SOURCE_SUFFIXES
from operator import attrgetter
from pathlib import Path

import typing_extensions as te

from . import pretty

FILE_SUFFIX: te.Final[str] = SOURCE_SUFFIXES[0]


def load(*names: str, path: Path) -> t.Tuple[t.Any, ...]:
    return attrgetter(*names)(
            import_module((''
                           if __name__ in ('__main__', '__mp_main__')
                           else __name__.rsplit('.', maxsplit=1)[0] + '.')
                          + path.stem)
    )


def save(*, path: Path, **values: t.Any) -> None:
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
