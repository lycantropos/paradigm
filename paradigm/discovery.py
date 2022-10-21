import importlib.machinery
import os
import platform
import sys
from collections import deque
from pathlib import Path
from typing import (Container,
                    Iterable,
                    Sequence,
                    Set)


def find_stdlib_modules_names(
        directory_path: Path = Path(os.__file__).parent,
) -> Iterable[str]:
    yield from sys.builtin_module_names

    def is_stdlib_module_path(path: Path,
                              suffixes: Container[str] = tuple(
                                      importlib.machinery.all_suffixes()
                              )) -> bool:
        return (path.name.endswith(suffixes)
                and is_stdlib_module_path_parts(path.parts))

    def is_stdlib_module_path_parts(parts: Sequence[str]) -> bool:
        return not any((component.startswith('test')
                        or component.startswith('__')
                        or '-' in component)
                       for component in parts)

    queue = deque(directory_path.iterdir())
    while queue:
        candidate = queue.pop()
        candidate_module_path = candidate.relative_to(directory_path)
        if candidate.is_dir():
            if is_stdlib_module_path_parts(candidate_module_path.parts):
                yield '.'.join(candidate_module_path.parts)
            queue.extendleft(candidate.iterdir())
        elif is_stdlib_module_path(candidate_module_path):
            yield '.'.join(candidate_module_path.with_name(
                    candidate_module_path.name.split('.', 1)[0]
            ).parts)


stdlib_modules_names = set(find_stdlib_modules_names())
# importing will cause unwanted side effects such as raising error
unsupported_stdlib_modules_names = {'antigravity', 'crypt', 'this', 'tkinter',
                                    'turtle'}

if sys.platform == 'win32':
    unsupported_stdlib_modules_names.update({'curses',
                                             'pty',
                                             'tty'})

if platform.python_implementation() == 'PyPy':
    unsupported_stdlib_modules_names.update(
            {
                '_crypt',
                '_curses_build',
                '_msi',
                '_scproxy',
                'future_builtins',
                'identity_dict',
                'msilib',
                'symtable',
                'tracemalloc',
                *[name
                  for name in stdlib_modules_names
                  if name.startswith(('__pypy', '_ctypes_', '_pypy', '_test',
                                      'ctypes_', 'test'))]
            }
    )
    if sys.platform == 'win32':
        unsupported_stdlib_modules_names.update({'_curses',
                                                 '_curses_panel',
                                                 '_dbm',
                                                 '_gdbm',
                                                 '_gdbm_cffi',
                                                 '_posixshmem',
                                                 '_pwdgrp_cffi',
                                                 '_resource_build',
                                                 '_sqlite3_build',
                                                 '_sysconfigdata',
                                                 'resource',
                                                 'grp',
                                                 'readline',
                                                 'syslog'})
    else:
        unsupported_stdlib_modules_names.update({'_overlapped',
                                                 '_winapi',
                                                 'msvcrt'})
    if sys.version_info >= (3, 9):
        unsupported_stdlib_modules_names.add('_ssl_build')

supported_stdlib_modules_names = (stdlib_modules_names
                                  - unsupported_stdlib_modules_names)
