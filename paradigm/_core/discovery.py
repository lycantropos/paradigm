import sys
import typing as t

from typing_extensions import Final

from . import catalog
from .sources import stdlib_modules_paths


def _recursively_update_modules_paths(
        set_: t.Set[catalog.Path],
        *names: str,
) -> None:
    paths = [catalog.path_from_string(name) for name in names]
    assert all(path in stdlib_modules_paths for path in paths), [
        path for path in paths if path not in stdlib_modules_paths
    ]
    set_.update({*paths,
                 *[candidate
                   for candidate in stdlib_modules_paths
                   if any(candidate[:len(path)] == path for path in paths)]})


# importing will cause unwanted side effects such as raising error
unsupported_stdlib_modules_paths: t.Set[catalog.Path] = set()
_recursively_update_modules_paths(unsupported_stdlib_modules_paths,
                                  'antigravity',
                                  'crypt',
                                  'idlelib',
                                  'lib2to3.pgen2.conv',
                                  'this',
                                  'tkinter',
                                  'turtle',
                                  'turtledemo')

if sys.implementation.name == 'pypy':
    _recursively_update_modules_paths(unsupported_stdlib_modules_paths,
                                      '__decimal',
                                      '_crypt',
                                      '_curses_build',
                                      '_scproxy',
                                      'future_builtins',
                                      'identity_dict',
                                      'msilib',
                                      'symtable',
                                      'tracemalloc')
    unsupported_stdlib_modules_paths.update(
            [path
             for path in stdlib_modules_paths
             if (path[0].startswith(('__pypy', '_pypy'))
                 or '__pycache__' in path)]
    )
    if sys.platform == 'win32':
        _recursively_update_modules_paths(unsupported_stdlib_modules_paths,
                                          '_curses',
                                          '_curses_panel',
                                          '_dbm',
                                          '_gdbm',
                                          '_posixshmem',
                                          '_resource_build',
                                          '_sqlite3_build',
                                          '_sysconfigdata',
                                          '_tkinter',
                                          'asyncio.unix_events',
                                          'cffi._pycparser._build_tables',
                                          'ctypes_support',
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
        _recursively_update_modules_paths(unsupported_stdlib_modules_paths,
                                          '_overlapped',
                                          '_tkinter',
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
        _recursively_update_modules_paths(unsupported_stdlib_modules_paths,
                                          '_cffi_ssl._cffi_src.build_openssl',
                                          '_ssl_build')
else:
    _recursively_update_modules_paths(unsupported_stdlib_modules_paths,
                                      'distutils.command.bdist_msi')

    if sys.version_info < (3, 10):
        _recursively_update_modules_paths(
                unsupported_stdlib_modules_paths,
                'distutils.command.bdist_wininst'
        )

    if sys.platform == 'win32':
        _recursively_update_modules_paths(unsupported_stdlib_modules_paths,
                                          'curses',
                                          'pty',
                                          'tty')
        _recursively_update_modules_paths(
                unsupported_stdlib_modules_paths,
                'asyncio.unix_events',
                'dbm.gnu',
                'dbm.ndbm',
                'multiprocessing.popen_fork',
                'multiprocessing.popen_forkserver',
                'multiprocessing.popen_spawn_posix'
        )
    else:
        _recursively_update_modules_paths(unsupported_stdlib_modules_paths,
                                          'asyncio.windows_events',
                                          'asyncio.windows_utils',
                                          'ctypes.wintypes',
                                          'distutils.msvc9compiler',
                                          'encodings.mbcs',
                                          'encodings.oem',
                                          'multiprocessing.popen_spawn_win32')
        if sys.version_info < (3, 8):
            _recursively_update_modules_paths(unsupported_stdlib_modules_paths,
                                              'distutils._msvccompiler',
                                              'encodings.cp65001')
        if sys.platform == 'darwin':
            if sys.version_info >= (3, 8):
                _recursively_update_modules_paths(
                        unsupported_stdlib_modules_paths,
                        'dbm.gnu',
                        'distutils._msvccompiler',
                )

supported_stdlib_modules_paths: Final[t.Iterable[catalog.Path]] = [
    module_path
    for module_path in stdlib_modules_paths
    if module_path not in unsupported_stdlib_modules_paths
]
