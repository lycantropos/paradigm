import warnings
from compileall import compile_file
from importlib.util import module_from_spec, spec_from_file_location
from operator import attrgetter
from pathlib import Path
from typing import Any

from . import pretty


def load(path: Path, name: str, /, *names: str) -> tuple[Any, ...]:
    spec = spec_from_file_location(path.stem, path)
    assert spec is not None, path
    module = module_from_spec(spec)
    spec_loader = spec.loader
    assert spec_loader is not None, path
    spec_loader.exec_module(module)
    return attrgetter(name, *names)(module)


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
