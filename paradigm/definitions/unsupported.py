import platform
import sys
from itertools import chain
from types import ModuleType
from typing import Set

from .utils import (_add,
                    _add_module,
                    _to_callables,
                    _update,
                    _update_modules,
                    stdlib_modules_names as _stdlib_modules_names)

# importing will cause unwanted side effects such as raising error
stdlib_modules_names = {'antigravity', 'crypt', 'this', 'tkinter', 'turtle'}

if sys.platform == 'win32':
    stdlib_modules_names.update({'curses',
                                 'pty',
                                 'tty'})

if platform.python_implementation() == 'PyPy':
    stdlib_modules_names.update(
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
                  for name in _stdlib_modules_names
                  if name.startswith(('__pypy', '_ctypes', '_pypy', '_test',
                                      'test'))]
            }
    )
    if sys.platform != 'win32':
        stdlib_modules_names.update({'_overlapped',
                                     '_winapi',
                                     'msvcrt'})
    if sys.version_info >= (3, 9):
        stdlib_modules_names.add('_ssl_build')

stdlib_modules: Set[ModuleType] = set()

if platform.python_implementation() != 'PyPy':
    # not supported by ``typeshed`` package
    _update_modules(stdlib_modules, ['_collections',
                                     '_codecs_hk',
                                     '_codecs_iso2022',
                                     '_codecs_jp',
                                     '_codecs_kr',
                                     '_codecs_cn',
                                     '_codecs_tw',
                                     '_lsprof',
                                     '_multibytecodec',
                                     '_multiprocessing',
                                     '_sha3',
                                     '_string',
                                     'audioop',
                                     'parser',
                                     'xxsubtype'])

    if (3, 7) <= sys.version_info < (3, 7, 1):
        _add_module(stdlib_modules, '_blake2')

stdlib_modules_callables = list(chain.from_iterable(map(_to_callables,
                                                        stdlib_modules)))

built_in_functions: Set[str] = set()

if platform.python_implementation() != 'PyPy':
    # not supported by ``typeshed`` package
    _add(built_in_functions, '_json', 'encode_basestring')
    _update(built_in_functions, '_thread', ['allocate',
                                            'exit_thread',
                                            'start_new'])
    _update(built_in_functions, 'codecs', ['backslashreplace_errors',
                                           'ignore_errors',
                                           'namereplace_errors',
                                           'replace_errors',
                                           'strict_errors',
                                           'xmlcharrefreplace_errors'])
    _update(built_in_functions, 'ctypes', ['_dlopen', 'pointer'])
    _add(built_in_functions, 'socket', 'dup')
    if sys.version_info < (3, 8):
        _update(built_in_functions, '_hashlib', ['openssl_md5',
                                                 'openssl_sha1',
                                                 'openssl_sha224',
                                                 'openssl_sha256',
                                                 'openssl_sha384',
                                                 'openssl_sha512'])
        _update(built_in_functions, 'sys', ['callstats',
                                            'getallocatedblocks',
                                            'get_coroutine_wrapper',
                                            'set_coroutine_wrapper'])
    else:
        _update(built_in_functions, '_xxsubinterpreters', ['channel_send',
                                                           'get_current',
                                                           'channel_recv',
                                                           'is_running',
                                                           'channel_create',
                                                           'list_all',
                                                           'channel_close',
                                                           'channel_release',
                                                           'destroy',
                                                           'is_shareable',
                                                           'get_main',
                                                           'channel_destroy',
                                                           'create',
                                                           'channel_list_all',
                                                           'run_string'])

    if sys.version_info >= (3, 9):
        _add(built_in_functions, '_xxsubinterpreters',
             'channel_list_interpreters')

    if sys.platform == 'win32':
        if sys.version_info >= (3, 7):
            _add(built_in_functions, '_uuid', 'UuidCreate')
    else:
        _update(built_in_functions, '_locale', ['bind_textdomain_codeset',
                                                'bindtextdomain',
                                                'dcgettext',
                                                'dgettext',
                                                'gettext',
                                                'textdomain'])

        if sys.version_info >= (3, 7):
            _add(built_in_functions, '_uuid', 'generate_time_safe')
            _add(built_in_functions, 'time', 'pthread_getcpuclockid')
        if sys.version_info >= (3, 8):
            _update(built_in_functions, 'posix', ['posix_spawn',
                                                  'posix_spawnp'])

classes: Set[str] = set()

if platform.python_implementation() != 'PyPy':
    # not supported by ``typeshed`` package
    _add(classes, '_collections_abc', 'mappingproxy')
    _update(classes, '_io', ['_BufferedIOBase',
                             '_IOBase',
                             '_RawIOBase',
                             '_TextIOBase'])
    _add(classes, '_ssl', '_SSLContext')
    _update(classes, '_thread', ['RLock', '_local'])
    _add(classes, 'asyncio.events', '_RunningLoop')
    _add(classes, 'ctypes', '_CFuncPtr')
    _add(classes, 'encodings', 'CodecRegistryError')
    _update(classes, 'itertools', ['_grouper', '_tee_dataobject'])

    if sys.version_info < (3, 7):
        _add(classes, '_collections_abc', 'range_iterator')
    if sys.version_info < (3, 8):
        _add(classes, 'itertools', '_tee')
        _add(classes, 'random', '_MethodType')
    else:
        _add(classes, '_xxsubinterpreters', 'InterpreterID')
        _update(classes, 'types', ['CellType', 'MethodType'])

    if sys.platform == 'win32' and sys.version_info < (3, 7):
        _update(classes, 'os', ['uname_result', 'statvfs_result'])

methods_descriptors: Set[str] = set()

if platform.python_implementation() != 'PyPy':
    # not supported by ``typeshed`` package
    _update(methods_descriptors, '_collections_abc', ['dict_items.isdisjoint',
                                                      'dict_keys.isdisjoint',
                                                      'generator.close',
                                                      'generator.send',
                                                      'generator.throw',
                                                      'coroutine.close',
                                                      'coroutine.send',
                                                      'coroutine.throw'])
    _update(methods_descriptors, '_thread', ['LockType.acquire_lock',
                                             'LockType.locked_lock',
                                             'LockType.release_lock'])
    _update(methods_descriptors, 'collections', ['OrderedDict.clear',
                                                 'OrderedDict.pop',
                                                 'OrderedDict.update'])

    if sys.version_info >= (3, 6):
        _update(methods_descriptors, '_collections_abc',
                ['async_generator.aclose',
                 'async_generator.asend',
                 'async_generator.athrow'])

    if sys.version_info < (3, 7):
        _add(methods_descriptors, 'collections', 'OrderedDict.setdefault')

wrappers_descriptors: Set[str] = set()

if platform.python_implementation() != 'PyPy':
    # not supported by ``typeshed`` package
    _update(wrappers_descriptors, '_collections_abc', ['coroutine.__del__',
                                                       'generator.__del__'])

    if sys.version_info >= (3, 6):
        _add(wrappers_descriptors, '_collections_abc',
             'async_generator.__del__')
        _add(wrappers_descriptors, '_socket', 'socket.__del__')
