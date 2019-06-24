import platform
import sys
from itertools import chain

from .utils import (_add,
                    _safe_import,
                    _to_callables,
                    _update)

# importing will cause unwanted side effects such as raising error
stdlib_modules_names = {'antigravity', 'this'}

if sys.platform == 'win32':
    stdlib_modules_names.update({'crypt',
                                 'curses',
                                 'pty',
                                 'tty'})

if platform.python_implementation() == 'PyPy':
    stdlib_modules_names.update({'msilib',
                                 'symtable',
                                 'tracemalloc'})

stdlib_modules = set()

if platform.python_implementation() != 'PyPy':
    # not supported by ``typeshed`` package
    stdlib_modules.update(map(_safe_import,
                              ['_collections',
                               '_codecs_hk',
                               '_codecs_iso2022',
                               '_codecs_jp',
                               '_codecs_kr',
                               '_codecs_cn',
                               '_codecs_tw',
                               '_lsprof',
                               '_multibytecodec',
                               '_multiprocessing',
                               '_string',
                               'audioop',
                               'parser',
                               'xxsubtype']))

    if sys.version_info >= (3, 6):
        stdlib_modules.add(_safe_import('_sha3'))

    if ((3, 6) <= sys.version_info < (3, 6, 7)
            or (3, 7) <= sys.version_info < (3, 7, 1)):
        stdlib_modules.add(_safe_import('_blake2'))

    if sys.platform == 'win32':
        stdlib_modules.add(_safe_import('_msi'))

stdlib_modules_callables = list(chain.from_iterable(map(_to_callables,
                                                        stdlib_modules)))

built_in_functions = set()

if platform.python_implementation() != 'PyPy':
    # not supported by ``typeshed`` package
    _update(built_in_functions, '_hashlib', ['openssl_md5',
                                             'openssl_sha1',
                                             'openssl_sha1',
                                             'openssl_sha224',
                                             'openssl_sha256',
                                             'openssl_sha384',
                                             'openssl_sha512'])
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
    _update(built_in_functions, 'sys', ['callstats',
                                        'getallocatedblocks',
                                        'get_coroutine_wrapper',
                                        'set_coroutine_wrapper'])
    if sys.version_info >= (3, 6):
        _update(built_in_functions, 'sys', ['getfilesystemencodeerrors',
                                            'get_asyncgen_hooks',
                                            'set_asyncgen_hooks'])

    if sys.version_info >= (3, 7):
        _add(built_in_functions, 'socket', 'close')

    if sys.platform == 'linux':
        _update(built_in_functions, '_locale', ['bind_textdomain_codeset',
                                                'bindtextdomain',
                                                'dcgettext',
                                                'dgettext',
                                                'gettext',
                                                'textdomain'])

        if sys.version_info >= (3, 7):
            _add(built_in_functions, 'time', 'pthread_getcpuclockid')

classes = set()

if platform.python_implementation() != 'PyPy':
    # not supported by ``typeshed`` package
    _add(classes, '_collections_abc', 'mappingproxy')
    _update(classes, '_io', ['_BufferedIOBase',
                             '_IOBase',
                             '_RawIOBase',
                             '_TextIOBase'])
    _add(classes, '_ssl', '_SSLContext')
    _update(classes, '_thread', ['RLock', '_local'])
    _update(classes, 'itertools', ['_grouper', '_tee', '_tee_dataobject'])
    _add(classes, 'asyncio.events', '_RunningLoop')
    _add(classes, 'ctypes', '_CFuncPtr')
    _add(classes, 'encodings', 'CodecRegistryError')
    _add(classes, 'random', '_MethodType')

    if sys.version_info < (3, 7):
        _add(classes, '_collections_abc', 'range_iterator')

    if sys.platform == 'win32':
        _update(classes, 'msilib', ['UuidCreate',
                                    'FCICreate',
                                    'OpenDatabase',
                                    'CreateRecord'])

        if sys.version_info < (3, 7):
            _update(classes, 'os', ['uname_result', 'statvfs_result'])

methods_descriptors = set()

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
    _add(methods_descriptors, '_io', 'BufferedRWPair.peek')
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
        if sys.platform == 'linux':
            _add(methods_descriptors, 'socket', 'socket.sendmsg_afalg')

    if sys.version_info >= (3, 7):
        _add(methods_descriptors, 'socket', 'socket.getblocking')
    else:
        _add(methods_descriptors, 'collections', 'OrderedDict.setdefault')
        _add(methods_descriptors, 'zipimport', 'zipimporter.find_loader')

    if sys.platform == 'win32':
        _add(methods_descriptors, 'socket', 'socket.share')

wrappers_descriptors = set()

if platform.python_implementation() != 'PyPy':
    # not supported by ``typeshed`` package
    _update(wrappers_descriptors, '_collections_abc', ['coroutine.__del__',
                                                       'generator.__del__'])

    if sys.version_info >= (3, 6):
        _add(wrappers_descriptors, '_collections_abc',
             'async_generator.__del__')
        _add(wrappers_descriptors, '_socket', 'socket.__del__')
