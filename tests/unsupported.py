import importlib
import platform
import sys
import warnings
from types import ModuleType
from typing import (Any,
                    Callable,
                    Iterable,
                    List,
                    Optional,
                    Set,
                    Union)

from paradigm import (catalog,
                      namespaces)


def load_and_add(set_: Set[Any], module_name: str, name: str) -> None:
    module = _safe_import(module_name)
    if module is None:
        return
    path = catalog.path_from_string(name)
    try:
        object_ = _search_by_path(module, path)
    except KeyError:
        warnings.warn(f'Module "{module_name}" has no object '
                      f'with name "{path.parts[0]}".')
    except AttributeError:
        warnings.warn(f'Module "{module_name}" has no object '
                      f'with path "{path}".')
    else:
        set_.add(object_)


def load_and_update(set_: Set[Any],
                    module_name: str,
                    names: Iterable[str]) -> None:
    for name in names:
        load_and_add(set_, module_name, name)


def _load_and_add_module(set_: Set[Any], module_name: str) -> None:
    module = _safe_import(module_name)
    if module is None:
        return
    set_.add(module)


def _safe_import(name: str) -> Optional[ModuleType]:
    try:
        return importlib.import_module(name)
    except ImportError:
        warnings.warn('Failed to import module "{module}".'
                      .format(module=name))
        return None


def _search_by_path(module: ModuleType, path: catalog.Path) -> Any:
    return namespaces.search(namespaces.from_module(module), path)


def _to_callables(object_: Union[ModuleType, type]) -> Iterable[Callable]:
    yield from filter(callable, to_contents(object_))


def to_contents(object_: Union[ModuleType, type]) -> List[Any]:
    return list(vars(object_).values())


def _load_and_update_modules(set_: Set[Any],
                             modules_names: Iterable[str]) -> None:
    for module_name in modules_names:
        _load_and_add_module(set_, module_name)


stdlib_modules: Set[ModuleType] = set()
_load_and_add_module(stdlib_modules, '_io')

if platform.python_implementation() != 'PyPy':
    _load_and_update_modules(stdlib_modules, ['_collections',
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
        _load_and_add_module(stdlib_modules, '_blake2')

built_in_functions: Set[str] = set()

if platform.python_implementation() != 'PyPy':
    load_and_add(built_in_functions, '_json', 'encode_basestring')
    load_and_add(built_in_functions, '_locale', 'setlocale')
    load_and_update(built_in_functions, '_thread', ['allocate',
                                                    'exit_thread',
                                                    'start_new'])
    load_and_update(built_in_functions, 'codecs', ['backslashreplace_errors',
                                                   'ignore_errors',
                                                   'namereplace_errors',
                                                   'replace_errors',
                                                   'strict_errors',
                                                   'xmlcharrefreplace_errors'])
    load_and_add(built_in_functions, 'collections', '_count_elements')
    load_and_update(built_in_functions, 'ctypes', ['_dlopen', 'pointer'])
    load_and_update(built_in_functions,
                    'faulthandler', ['_fatal_error',
                                     '_fatal_error_c_thread',
                                     '_read_null',
                                     '_sigabrt',
                                     '_sigfpe',
                                     '_sigsegv',
                                     '_stack_overflow'])
    load_and_update(built_in_functions, 'heapq', ['_heappop_max',
                                                  '_heapreplace_max'])
    load_and_add(built_in_functions, 'locale', '_setlocale')
    load_and_add(built_in_functions, 'pty', 'select')
    load_and_add(built_in_functions, 'random', '_log')
    load_and_add(built_in_functions, 'socket', 'dup')
    load_and_update(built_in_functions, 'sys', ['__breakpointhook__',
                                                '__displayhook__',
                                                'displayhook'])
    load_and_add(built_in_functions, 'threading', '_set_sentinel')
    load_and_update(built_in_functions, 'tty', ['tcdrain',
                                                'tcflow',
                                                'tcflush',
                                                'tcgetattr',
                                                'tcsendbreak',
                                                'tcsetattr'])
    load_and_add(built_in_functions, 'warnings', '_filters_mutated')
    if sys.version_info >= (3, 8):
        load_and_add(built_in_functions, '_thread', '_excepthook')
        load_and_add(built_in_functions, 'plistlib', 'ParserCreate')
        load_and_add(built_in_functions, 'statistics', 'hypot')

    if sys.version_info >= (3, 9):
        load_and_add(built_in_functions, 'uuid', '_generate_time_safe')

    if sys.platform == 'win32':
        load_and_update(built_in_functions, '_uuid', ['UuidCreate',
                                                      'generate_time_safe'])

classes: Set[str] = set()

if platform.python_implementation() == 'PyPy':
    load_and_add(classes, '_ast', 'RevDBMetaVar')
    load_and_update(classes, '_cffi_backend', ['FFI',
                                               'buffer'])
    load_and_update(classes, '_collections', ['deque_iterator',
                                              'deque_reverse_iterator'])
    load_and_update(classes, '_continuation', ['continulet',
                                               'error'])
    load_and_add(classes, '_cppyy', 'CPPInstance')
    load_and_update(classes, '_ffi', ['CDLL',
                                      'Field'])
    load_and_add(classes, '_gdbm', 'error')
    load_and_add(classes, '_jitlog', 'JitlogError')
    load_and_add(classes, '_lsprof', 'Profiler')
    load_and_add(classes, '_md5', 'md5')
    load_and_add(classes, '_minimal_curses', 'error')
    load_and_update(classes,
                    '_multibytecodec', ['MultibyteIncrementalDecoder',
                                        'MultibyteIncrementalEncoder'])
    load_and_add(classes, '_multiprocessing', 'SemLock')
    load_and_update(classes, '_rawffi', ['Array',
                                         'CDLL',
                                         'CallbackPtr',
                                         'FuncPtr',
                                         'SegfaultException',
                                         'Structure'])
    load_and_update(classes, '_rawffi.alt', ['CDLL',
                                             'Field',
                                             '_StructDescr'])
    load_and_add(classes, '_thread', 'RLock')
    load_and_add(classes, '_vmprof', 'VMProfError')
    load_and_add(classes, 'ast', 'RevDBMetaVar')
    load_and_add(classes, 'builtins', 'NoneType')
    load_and_update(classes, 'cffi', ['CDefError',
                                      'FFIError',
                                      'PkgConfigError',
                                      'VerificationError',
                                      'VerificationMissing'])
    load_and_add(classes, 'dataclasses', '_InitVarMeta')
    load_and_update(classes, 'datetime', ['dateinterop',
                                          'deltainterop',
                                          'timeinterop'])
    load_and_add(classes, 'doctest', '_SpoofOut')
    load_and_add(classes, 'functools', 'RLock')
    load_and_update(classes, 'greenlet', ['GreenletExit',
                                          '_continulet',
                                          'error'])
    load_and_update(classes, 'itertools', ['_groupby',
                                           '_tee',
                                           '_tee_dataobject'])
    load_and_add(classes, 'macpath', 'norm_error')
    load_and_add(classes, 'pickle', 'BytesBuilder')
    load_and_update(classes, 'pypyjit', ['DebugMergePoint',
                                         'GuardOp',
                                         'JitLoopInfo',
                                         'ResOperation',
                                         'not_from_assembler'])
    load_and_add(classes, 'runpy', '_Error')
    load_and_add(classes, 'shutil', '_GiveupOnFastCopy')
    load_and_add(classes, 'socket', '_GiveupOnSendfile')
    load_and_add(classes, 'socketserver', '_Threads')
    load_and_update(classes, 'stackless', ['CoroutineExit',
                                           'TaskletExit'])
    load_and_update(classes, 'tarfile', ['EOFHeaderError',
                                         'EmptyHeaderError',
                                         'InvalidHeaderError',
                                         'SubsequentHeaderError',
                                         'TruncatedHeaderError'])
    load_and_add(classes, 'threading', '_CRLock')

    if sys.platform == 'win32':
        load_and_add(classes, '_ffi', 'WinDLL')
        load_and_add(classes, 'io', '_WindowsConsoleIO')
        load_and_add(classes, 'signal', 'ItimerError')
        load_and_add(classes, 'subprocess', 'Handle')
else:
    load_and_update(classes, '_io', ['_BufferedIOBase',
                                     '_IOBase',
                                     '_RawIOBase',
                                     '_TextIOBase'])
    load_and_add(classes, '_thread', 'RLock')
    load_and_add(classes, 'asyncio.events', '_RunningLoop')
    load_and_add(classes, 'csv', '_Dialect')
    load_and_add(classes, 'ctypes', '_CFuncPtr')
    load_and_update(classes, 'itertools', ['_grouper',
                                           '_tee',
                                           '_tee_dataobject'])
    load_and_add(classes, 'dataclasses', '_InitVarMeta')
    load_and_add(classes, 'macpath', 'norm_error')
    load_and_add(classes, 'runpy', '_Error')
    load_and_add(classes, 'socket', '_GiveupOnSendfile')
    load_and_add(classes, 'ssl', '_SSLContext')
    load_and_update(classes, 'tarfile', ['EOFHeaderError',
                                         'EmptyHeaderError',
                                         'InvalidHeaderError',
                                         'SubsequentHeaderError',
                                         'TruncatedHeaderError'])
    load_and_add(classes, 'tty', 'error')

    if sys.version_info >= (3, 8):
        load_and_add(classes, 'collections', '_tuplegetter')
        load_and_add(classes, 'shutil', '_GiveupOnFastCopy')
    if sys.version_info >= (3, 10):
        load_and_add(classes, 'mailcap', 'UnsafeMailcapInput')

methods_descriptors: Set[str] = set()

if platform.python_implementation() != 'PyPy':
    load_and_update(methods_descriptors,
                    '_collections_abc',
                    ['bytearray_iterator.__length_hint__',
                     'bytearray_iterator.__setstate__',
                     'bytes_iterator.__length_hint__',
                     'bytes_iterator.__reduce__',
                     'bytes_iterator.__setstate__',
                     'dict_itemiterator.__length_hint__',
                     'dict_itemiterator.__reduce__',
                     'dict_items.isdisjoint',
                     'dict_keyiterator.__length_hint__',
                     'dict_keyiterator.__reduce__',
                     'dict_keys.isdisjoint',
                     'dict_valueiterator.__length_hint__',
                     'dict_valueiterator.__reduce__',
                     'list_iterator.__length_hint__',
                     'list_iterator.__reduce__',
                     'list_iterator.__setstate__',
                     'list_reverseiterator.__length_hint__',
                     'list_reverseiterator.__reduce__',
                     'list_reverseiterator.__setstate__',
                     'longrange_iterator.__length_hint__',
                     'longrange_iterator.__reduce__',
                     'longrange_iterator.__setstate__',
                     'range_iterator.__length_hint__',
                     'range_iterator.__reduce__',
                     'range_iterator.__setstate__',
                     'set_iterator.__length_hint__',
                     'set_iterator.__reduce__',
                     'str_iterator.__length_hint__',
                     'str_iterator.__reduce__',
                     'str_iterator.__setstate__',
                     'tuple_iterator.__length_hint__',
                     'tuple_iterator.__reduce__',
                     'tuple_iterator.__setstate__'])
    load_and_update(methods_descriptors,
                    '_thread', ['LockType.acquire_lock',
                                'LockType.locked_lock',
                                'LockType.release_lock'])
    load_and_update(methods_descriptors,
                    'builtins', ['complex.__getnewargs__',
                                 'reversed.__setstate__'])
    load_and_update(methods_descriptors,
                    'bz2', ['BZ2Compressor.__getstate__',
                            'BZ2Decompressor.__getstate__'])
    load_and_update(methods_descriptors, 'cgi', ['StringIO.__getstate__',
                                                 'StringIO.__setstate__'])
    load_and_add(methods_descriptors, 'ctypes',
                 '_SimpleCData.__ctypes_from_outparam__')
    load_and_add(methods_descriptors, 'datetime', 'timezone.__getinitargs__')
    load_and_add(methods_descriptors, 'decimal', 'Context._apply')
    load_and_add(methods_descriptors, 'functools', 'partial.__setstate__')
    load_and_update(methods_descriptors, 'io', ['BufferedRWPair.__getstate__',
                                                'BufferedRandom.__getstate__',
                                                'BufferedRandom._dealloc_warn',
                                                'BufferedReader.__getstate__',
                                                'BufferedReader._dealloc_warn',
                                                'BufferedWriter.__getstate__',
                                                'BufferedWriter._dealloc_warn',
                                                'FileIO.__getstate__',
                                                'FileIO._dealloc_warn'])
    load_and_update(methods_descriptors,
                    'itertools', ['_grouper.__reduce__',
                                  '_tee.__copy__',
                                  '_tee.__reduce__',
                                  '_tee.__setstate__',
                                  'accumulate.__setstate__',
                                  'combinations.__setstate__',
                                  'combinations_with_replacement.__setstate__',
                                  'cycle.__setstate__',
                                  'dropwhile.__setstate__',
                                  'groupby.__setstate__',
                                  'islice.__setstate__',
                                  'permutations.__setstate__',
                                  'product.__setstate__',
                                  'takewhile.__setstate__',
                                  'zip_longest.__setstate__'])
    load_and_update(methods_descriptors, 'lzma',
                    ['LZMACompressor.__getstate__',
                     'LZMADecompressor.__getstate__'])
    load_and_add(methods_descriptors, 'socket', 'SocketType._accept')
    load_and_update(methods_descriptors, 'tokenize',
                    ['TextIOWrapper.__getstate__',
                     'chain.__setstate__'])
    load_and_update(methods_descriptors, 'types', ['CoroutineType.close',
                                                   'CoroutineType.send',
                                                   'CoroutineType.throw'])
    load_and_add(methods_descriptors, 'weakref', 'ProxyType.__bytes__')
    load_and_update(methods_descriptors, 'xdrlib', ['BytesIO.__getstate__',
                                                    'BytesIO.__setstate__'])

    if sys.version_info >= (3, 8):
        load_and_add(methods_descriptors, 'itertools', 'chain.__setstate__')
    if sys.version_info >= (3, 9):
        methods_descriptors.add(type(Ellipsis).__reduce__)
        load_and_add(methods_descriptors,
                     '_thread', 'LockType._at_fork_reinit')
        load_and_update(methods_descriptors, 'typing',
                        ['GenericAlias.__instancecheck__',
                         'GenericAlias.__mro_entries__',
                         'GenericAlias.__subclasscheck__'])
        load_and_add(methods_descriptors, 'weakref', 'ProxyType.__reversed__')
    if sys.version_info >= (3, 10):
        load_and_update(methods_descriptors,
                        'builtins', ['property.__set_name__',
                                     'zip.__setstate__'])
        load_and_update(methods_descriptors,
                        'types', ['UnionType.__instancecheck__',
                                  'UnionType.__subclasscheck__'])

wrappers_descriptors: Set[str] = set()

if platform.python_implementation() != 'PyPy':
    load_and_update(wrappers_descriptors,
                    '_collections_abc', ['async_generator.__del__',
                                         'coroutine.__del__',
                                         'generator.__del__'])
    load_and_add(wrappers_descriptors, '_socket', 'socket.__del__')
    load_and_update(wrappers_descriptors,
                    'types', ['AsyncGeneratorType.__del__',
                              'GeneratorType.__del__'])
