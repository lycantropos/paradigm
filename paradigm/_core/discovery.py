import importlib.machinery
import math
import os
import platform
import sys
from collections import deque
from itertools import chain
from pathlib import Path
from typing import (Container,
                    Iterable,
                    Sequence,
                    Set)


def find_stdlib_modules_names(directory_path: Path) -> Iterable[str]:
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


stdlib_modules_names = set(chain(
        sys.builtin_module_names,
        find_stdlib_modules_names(Path(os.__file__).parent),
        find_stdlib_modules_names(Path(math.__file__).parent)
        if math.__spec__.has_location
        else []
))


def _recursively_update_modules_names(
        set_: Set[str],
        *names: str,
        _stdlib_modules_names: Iterable[str] = stdlib_modules_names
) -> None:
    set_.update({*names,
                 *[name
                   for name in _stdlib_modules_names
                   if name.startswith(tuple(name + '.' for name in names))]})


# importing will cause unwanted side effects such as raising error
unsupported_stdlib_modules_names = set()
_recursively_update_modules_names(unsupported_stdlib_modules_names,
                                  'antigravity',
                                  'crypt',
                                  'idlelib',
                                  'lib2to3.pgen2.conv',
                                  'this',
                                  'tkinter',
                                  'turtle',
                                  'turtledemo')

if platform.python_implementation() == 'PyPy':
    _recursively_update_modules_names(unsupported_stdlib_modules_names,
                                      '_crypt',
                                      '_curses_build',
                                      '_scproxy',
                                      'future_builtins',
                                      'identity_dict',
                                      'msilib',
                                      'symtable',
                                      'tracemalloc')
    unsupported_stdlib_modules_names.update(
            [name
             for name in stdlib_modules_names
             if name.startswith(('__pypy', '_ctypes_', '_pypy', '_test',
                                 'ctypes_'))]
    )
    if sys.platform == 'win32':
        _recursively_update_modules_names(unsupported_stdlib_modules_names,
                                          '_curses',
                                          '_curses_panel',
                                          '_dbm',
                                          '_gdbm',
                                          '_posixshmem',
                                          '_resource_build',
                                          '_sqlite3_build',
                                          '_sysconfigdata',
                                          '_tkinter.tklib_build',
                                          'asyncio.unix_events',
                                          'cffi._pycparser._build_tables',
                                          'curses',
                                          'dbm.gnu',
                                          'dbm.ndbm',
                                          'distutils.command.bdist_msi',
                                          'distutils.command.bdist_wininst',
                                          'distutils.sysconfig_cpython',
                                          'distutils.sysconfig_pypy',
                                          'grp',
                                          'multiprocessing.popen_fork',
                                          'multiprocessing.popen_forkserver',
                                          'multiprocessing.popen_spawn_posix',
                                          'pty',
                                          'pyrepl._minimal_curses',
                                          'pyrepl.curses',
                                          'pyrepl.fancy_termios',
                                          'pyrepl.keymaps',
                                          'pyrepl.pygame_console',
                                          'pyrepl.pygame_keymap',
                                          'pyrepl.readline',
                                          'pyrepl.simple_interact',
                                          'pyrepl.unix_console',
                                          'pyrepl.unix_eventqueue',
                                          'readline',
                                          'resource',
                                          'syslog',
                                          'tty')
    else:
        _recursively_update_modules_names(unsupported_stdlib_modules_names,
                                          '_overlapped',
                                          '_tkinter.tklib_build',
                                          '_winapi',
                                          'asyncio.windows_events',
                                          'asyncio.windows_utils',
                                          'cffi._pycparser._build_tables',
                                          'distutils._msvccompiler',
                                          'distutils.command.bdist_wininst',
                                          'distutils.command.bdist_msi',
                                          'distutils.msvc9compiler',
                                          'distutils.sysconfig_cpython',
                                          'distutils.sysconfig_pypy',
                                          'encodings.mbcs',
                                          'encodings.oem',
                                          'msvcrt',
                                          'multiprocessing.popen_spawn_win32',
                                          'pyrepl.keymaps',
                                          'pyrepl.pygame_console',
                                          'pyrepl.pygame_keymap')
    if sys.version_info >= (3, 9):
        _recursively_update_modules_names(unsupported_stdlib_modules_names,
                                          '_cffi_ssl._cffi_src.build_openssl')
        _recursively_update_modules_names(unsupported_stdlib_modules_names,
                                          '_ssl_build')
else:
    _recursively_update_modules_names(unsupported_stdlib_modules_names,
                                      'distutils.command.bdist_msi')

    if sys.version_info < (3, 10):
        _recursively_update_modules_names(
                unsupported_stdlib_modules_names,
                'distutils.command.bdist_wininst'
        )

    if sys.platform == 'win32':
        _recursively_update_modules_names(unsupported_stdlib_modules_names,
                                          'curses',
                                          'pty',
                                          'tty')
        _recursively_update_modules_names(
                unsupported_stdlib_modules_names,
                'asyncio.unix_events',
                'dbm.gnu',
                'dbm.ndbm',
                'multiprocessing.popen_fork',
                'multiprocessing.popen_forkserver',
                'multiprocessing.popen_spawn_posix'
        )
    else:
        _recursively_update_modules_names(unsupported_stdlib_modules_names,
                                          'asyncio.windows_events',
                                          'asyncio.windows_utils',
                                          'ctypes.wintypes',
                                          'distutils.msvc9compiler',
                                          'encodings.mbcs',
                                          'encodings.oem',
                                          'multiprocessing.popen_spawn_win32')
        if sys.version_info < (3, 8):
            _recursively_update_modules_names(unsupported_stdlib_modules_names,
                                              'distutils._msvccompiler',
                                              'encodings.cp65001')
        if sys.platform == 'darwin':
            if sys.version_info >= (3, 8):
                _recursively_update_modules_names(
                        unsupported_stdlib_modules_names,
                        'dbm.gnu',
                        'distutils._msvccompiler',
                )

supported_stdlib_modules_names = (stdlib_modules_names
                                  - unsupported_stdlib_modules_names)
