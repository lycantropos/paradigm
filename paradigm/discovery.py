import os
import platform
import sys
from operator import methodcaller
from pathlib import Path
from typing import Iterable


def find_stdlib_modules_names(
        directory_path: Path = Path(os.__file__).parent,
) -> Iterable[str]:
    yield from sys.builtin_module_names

    def is_stdlib_module_path(path: Path) -> bool:
        base_name = path.stem
        # skips 'LICENSE', '__pycache__', 'site-packages', etc.
        return not (base_name.isupper()
                    or base_name.startswith('__')
                    or '-' in base_name
                    or '.' in base_name)

    sources_paths = filter(is_stdlib_module_path, directory_path.iterdir())
    sources_relative_paths = map(methodcaller(Path.relative_to.__name__,
                                              directory_path),
                                 sources_paths)
    yield from map(str, map(methodcaller(Path.with_suffix.__name__, ''),
                            sources_relative_paths))


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
