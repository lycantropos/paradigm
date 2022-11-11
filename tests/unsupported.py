import importlib
import sys
import types
import warnings
from typing import (Any,
                    Callable,
                    Iterable,
                    Optional,
                    Set,
                    Union)

from paradigm._core import (catalog,
                            namespacing)
from .utils import to_contents


def _load_and_add(set_: Set[Any], module_name: str, object_name: str) -> None:
    module = _safe_import(module_name)
    if module is None:
        return
    path = catalog.path_from_string(object_name)
    try:
        object_ = _search_by_path(module, path)
    except KeyError:
        warnings.warn(f'Module "{module_name}" has no object '
                      f'with name "{path[0]}".')
    except AttributeError:
        warnings.warn(f'Module "{module_name}" has no object '
                      f'with path "{path}".')
    else:
        set_.add(object_)


def _load_and_update(set_: Set[Any],
                     module_name: str,
                     names: Iterable[str]) -> None:
    for name in names:
        _load_and_add(set_, module_name, name)


def _safe_import(name: str) -> Optional[types.ModuleType]:
    try:
        return importlib.import_module(name)
    except ImportError:
        warnings.warn(f'Failed to import module "{name}".', ImportWarning)
        return None


def _search_by_path(module: types.ModuleType, path: catalog.Path) -> Any:
    return namespacing.search(vars(module), path)


stdlib_modules: Set[types.ModuleType] = set()
built_in_functions: Set[types.BuiltinFunctionType] = set()
classes: Set[type] = set()
methods_descriptors: Set[types.MethodDescriptorType] = set()
wrappers_descriptors: Set[types.WrapperDescriptorType] = set()

if sys.platform == 'linux':
    if sys.implementation.name == 'pypy':
        _load_and_update(classes, '_cffi_backend', ['FFI',
                                                    'buffer'])
        _load_and_update(classes, '_collections', ['deque_iterator',
                                                   'deque_reverse_iterator'])
        _load_and_add(classes, '_cppyy', 'CPPInstance')
        _load_and_update(classes, '_ctypes.basics', ['_CDataMeta',
                                                     'bufferable'])
        _load_and_add(classes, '_ctypes.function', 'CFuncPtrType')
        _load_and_update(classes, '_ffi', ['CDLL',
                                           'Field'])
        _load_and_update(classes, '_io', ['_BufferedIOBase',
                                          '_IOBase',
                                          '_RawIOBase',
                                          '_TextIOBase'])
        _load_and_add(classes, '_jitlog', 'JitlogError')
        _load_and_add(classes, '_lsprof', 'Profiler')
        _load_and_add(classes, '_md5', 'md5')
        _load_and_add(classes, '_minimal_curses', 'error')
        _load_and_update(classes,
                         '_multibytecodec', ['MultibyteIncrementalDecoder',
                                             'MultibyteIncrementalEncoder'])
        _load_and_add(classes, '_multiprocessing', 'SemLock')
        _load_and_update(classes, '_rawffi', ['Array',
                                              'CDLL',
                                              'CallbackPtr',
                                              'FuncPtr',
                                              'SegfaultException',
                                              'Structure'])
        _load_and_add(classes, '_rawffi.alt', '_StructDescr')
        _load_and_add(classes, '_vmprof', 'VMProfError')
        _load_and_add(classes, 'ast', 'RevDBMetaVar')
        _load_and_update(
                classes,
                'asyncio.events', ['_RunningLoop',
                                   'BaseDefaultEventLoopPolicy._Local']
        )
        _load_and_add(classes, 'builtins', 'NoneType')
        _load_and_update(classes, 'cffi._pycparser.ply.yacc', ['GrammarError',
                                                               'LALRError',
                                                               'VersionError',
                                                               'YaccError'])
        _load_and_add(classes, 'cffi._pycparser.plyparser', 'ParseError')
        _load_and_add(classes, 'cffi.backend_ctypes', 'CTypesType')
        _load_and_update(classes, 'cffi.error', ['CDefError',
                                                 'FFIError',
                                                 'PkgConfigError',
                                                 'VerificationError',
                                                 'VerificationMissing'])
        _load_and_update(classes, 'datetime', ['dateinterop',
                                               'deltainterop',
                                               'timeinterop'])
        _load_and_add(classes, 'distutils.command.bdist', 'ListCompat')
        _load_and_add(classes, 'distutils.filelist', '_UniqueDirs')
        _load_and_add(classes, 'doctest', '_SpoofOut')
        _load_and_add(classes, 'email._encoded_words', '_QByteMap')
        _load_and_update(classes, 'greenlet', ['GreenletExit',
                                               '_continulet',
                                               'error'])
        _load_and_add(classes, 'hpy.debug.leakdetector', 'HPyDebugError')
        _load_and_add(classes, 'hpy.devel', 'HPyExtensionName')
        _load_and_add(classes, 'importlib._bootstrap', '_DeadlockError')
        _load_and_add(classes, 'importlib.util', '_LazyModule')
        _load_and_update(classes, 'itertools', ['_groupby',
                                                '_tee',
                                                '_tee_dataobject'])
        _load_and_add(classes, 'json.encoder', 'StringBuilder')
        _load_and_add(classes, 'lib2to3.patcomp', 'PatternSyntaxError')
        _load_and_add(classes, 'lib2to3.refactor', '_EveryNode')
        _load_and_update(classes, 'logging.config', ['ConvertingDict',
                                                     'ConvertingList',
                                                     'ConvertingTuple'])
        _load_and_add(classes, 'macpath', 'norm_error')
        _load_and_add(classes,
                      'multiprocessing.process', 'AuthenticationString')
        _load_and_add(classes, 'pickle', 'BytesBuilder')
        _load_and_add(
                classes,
                'pypy_tools.build_cffi_imports', 'MissingDependenciesError'
        )
        _load_and_update(classes, 'pypyjit', ['DebugMergePoint',
                                              'GuardOp',
                                              'JitLoopInfo',
                                              'ResOperation',
                                              'not_from_assembler'])
        _load_and_add(classes, 'pyrepl._minimal_curses', 'error')
        _load_and_add(classes, 'pyrepl.curses', 'error')
        _load_and_add(classes, 'pyrepl.keymap', 'KeySpecError')
        _load_and_add(classes, 'pyrepl.unix_console', 'InvalidTerminal')
        _load_and_add(classes, 'runpy', '_Error')
        _load_and_add(classes, 'shutil', '_GiveupOnFastCopy')
        _load_and_add(classes, 'socket', '_GiveupOnSendfile')
        _load_and_add(classes, 'socketserver', '_Threads')
        _load_and_update(classes, 'stackless', ['CoroutineExit',
                                                'TaskletExit'])
        _load_and_update(classes, 'tarfile', ['EOFHeaderError',
                                              'EmptyHeaderError',
                                              'InvalidHeaderError',
                                              'SubsequentHeaderError',
                                              'TruncatedHeaderError'])
        _load_and_add(classes, 'threading', '_CRLock')
        _load_and_add(classes, 'typing_extensions', '_AnyMeta')
        _load_and_update(classes, 'unittest.case', ['_ShouldStop',
                                                    '_UnexpectedSuccess'])

        if sys.version_info < (3, 9):
            _load_and_add(classes, 'dataclasses', '_InitVarMeta')
        else:
            _load_and_add(classes, '_collections_abc', 'EllipsisType')
            _load_and_add(classes, 'unittest.mock', '_AnyComparer')
    else:
        _load_and_add(built_in_functions, '_codecs_cn', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_hk', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_iso2022', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_jp', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_kr', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_tw', 'getcodec')
        _load_and_add(built_in_functions, '_collections', '_count_elements')
        _load_and_update(built_in_functions, '_ctypes', ['PyObj_FromPtr',
                                                         'Py_DECREF',
                                                         'Py_INCREF',
                                                         '_unpickle',
                                                         'buffer_info',
                                                         'call_cdeclfunction',
                                                         'call_function',
                                                         'dlclose',
                                                         'dlsym'])
        _load_and_add(built_in_functions, '_hashlib', 'new')
        _load_and_update(built_in_functions,
                         '_string', ['formatter_field_name_split',
                                     'formatter_parser'])
        _load_and_add(built_in_functions, '_uuid', 'generate_time_safe')
        _load_and_add(built_in_functions, '_xxtestfuzz', 'run')
        _load_and_update(built_in_functions, '_thread', ['allocate',
                                                         'exit_thread',
                                                         'start_new'])
        _load_and_add(built_in_functions, 'ctypes', '_dlopen')
        _load_and_update(built_in_functions,
                         'faulthandler', ['_fatal_error_c_thread',
                                          '_read_null',
                                          '_sigabrt',
                                          '_sigfpe',
                                          '_sigsegv',
                                          '_stack_overflow'])
        _load_and_update(built_in_functions, 'heapq', ['_heappop_max',
                                                       '_heapreplace_max'])
        _load_and_update(built_in_functions, 'json.decoder', ['c_scanstring',
                                                              'scanstring'])
        _load_and_update(built_in_functions,
                         'json.encoder', ['c_encode_basestring',
                                          'c_encode_basestring_ascii',
                                          'encode_basestring',
                                          'encode_basestring_ascii'])
        _load_and_update(built_in_functions, 'locale', ['_localeconv',
                                                        '_setlocale'])
        _load_and_add(built_in_functions, 'logging', 'Formatter.converter')
        _load_and_add(built_in_functions,
                      'multiprocessing.synchronize', 'sem_unlink')
        _load_and_add(built_in_functions, 'parser', '_pickler')
        _load_and_add(built_in_functions, 'pty', 'select')
        _load_and_add(built_in_functions, 'random', '_log')
        _load_and_add(built_in_functions,
                      'selectors', 'PollSelector._selector_cls')
        _load_and_add(built_in_functions, 'threading', '_set_sentinel')
        _load_and_add(built_in_functions, 'timeit', 'default_timer')
        _load_and_update(built_in_functions, 'tty', ['tcdrain',
                                                     'tcflow',
                                                     'tcflush',
                                                     'tcgetattr',
                                                     'tcsendbreak',
                                                     'tcsetattr'])
        _load_and_add(built_in_functions, 'warnings', '_filters_mutated')
        _load_and_add(built_in_functions, 'xxsubtype', 'bench')

        _load_and_update(classes, '_collections', ['_deque_iterator',
                                                   '_deque_reverse_iterator'])
        _load_and_update(classes, '_io', ['_BufferedIOBase',
                                          '_IOBase',
                                          '_RawIOBase',
                                          '_TextIOBase'])
        _load_and_add(classes, '_lsprof', 'Profiler')
        _load_and_update(classes,
                         '_multibytecodec', ['MultibyteIncrementalDecoder',
                                             'MultibyteIncrementalEncoder',
                                             'MultibyteStreamReader',
                                             'MultibyteStreamWriter'])
        _load_and_add(classes, '_multiprocessing', 'SemLock')
        _load_and_update(
                classes,
                'asyncio.events', ['BaseDefaultEventLoopPolicy._Local',
                                   '_RunningLoop']
        )
        _load_and_add(classes, 'csv', '_Dialect')
        _load_and_add(classes, 'ctypes', '_CFuncPtr')
        _load_and_update(classes, 'ctypes._endian', ['_array_type',
                                                     '_swapped_meta'])
        _load_and_add(classes, 'curses.panel', 'error')
        _load_and_add(classes, 'distutils.command.bdist', 'ListCompat')
        _load_and_add(classes, 'distutils.filelist', '_UniqueDirs')
        _load_and_add(classes, 'email._encoded_words', '_QByteMap')
        _load_and_update(classes, 'encodings.big5', ['IncrementalDecoder',
                                                     'IncrementalEncoder',
                                                     'StreamReader',
                                                     'StreamWriter'])
        _load_and_update(classes, 'encodings.big5hkscs', ['IncrementalDecoder',
                                                          'IncrementalEncoder',
                                                          'StreamReader',
                                                          'StreamWriter'])
        _load_and_update(classes, 'encodings.cp932', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes, 'encodings.cp949', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes, 'encodings.cp950', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.euc_jis_2004', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.euc_jisx0213', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes, 'encodings.euc_jp', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes, 'encodings.euc_kr', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes, 'encodings.gb18030', ['IncrementalDecoder',
                                                        'IncrementalEncoder',
                                                        'StreamReader',
                                                        'StreamWriter'])
        _load_and_update(classes, 'encodings.gb2312', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes, 'encodings.gbk', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes, 'encodings.hz', ['IncrementalDecoder',
                                                   'IncrementalEncoder',
                                                   'StreamReader',
                                                   'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp', ['IncrementalDecoder',
                                                  'IncrementalEncoder',
                                                  'StreamReader',
                                                  'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_1', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_2', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_2004', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_3', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_ext', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_kr', ['IncrementalDecoder',
                                                  'IncrementalEncoder',
                                                  'StreamReader',
                                                  'StreamWriter'])
        _load_and_update(classes, 'encodings.johab', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.shift_jis', ['IncrementalDecoder',
                                                 'IncrementalEncoder',
                                                 'StreamReader',
                                                 'StreamWriter'])
        _load_and_update(classes,
                         'encodings.shift_jis_2004', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.shift_jisx0213', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_add(classes, 'importlib._bootstrap', '_DeadlockError')
        _load_and_update(classes, 'itertools', ['_grouper',
                                                '_tee',
                                                '_tee_dataobject'])
        _load_and_add(classes, 'json.encoder', 'c_make_encoder')
        _load_and_update(classes, 'json.scanner', ['c_make_scanner',
                                                   'make_scanner'])
        _load_and_add(classes, 'lib2to3.patcomp', 'PatternSyntaxError')
        _load_and_add(classes, 'lib2to3.refactor', '_EveryNode')
        _load_and_add(classes, 'logging.config', 'ConvertingDict')
        _load_and_add(classes,
                      'multiprocessing.process', 'AuthenticationString')
        _load_and_add(classes, 'runpy', '_Error')
        _load_and_add(classes, 'selectors', 'DefaultSelector._selector_cls')
        _load_and_add(classes, 'socket', '_GiveupOnSendfile')
        _load_and_add(classes, 'ssl', '_SSLContext')
        _load_and_update(classes, 'tarfile', ['EOFHeaderError',
                                              'EmptyHeaderError',
                                              'InvalidHeaderError',
                                              'SubsequentHeaderError',
                                              'TruncatedHeaderError'])
        _load_and_add(classes, 'threading', '_CRLock')
        _load_and_add(classes, 'tty', 'error')
        _load_and_add(classes, 'typing_extensions', '_AnyMeta')
        _load_and_update(classes, 'unittest.case', ['_ShouldStop',
                                                    '_UnexpectedSuccess'])
        _load_and_add(classes, 'xxsubtype', 'spamdict')

        _load_and_update(
                methods_descriptors,
                '_collections', ['_deque_iterator.__length_hint__',
                                 '_deque_iterator.__reduce__',
                                 '_deque_reverse_iterator.__length_hint__',
                                 '_deque_reverse_iterator.__reduce__']
        )
        _load_and_update(
                methods_descriptors,
                '_collections_abc', ['bytearray_iterator.__length_hint__',
                                     'bytearray_iterator.__setstate__',
                                     'bytes_iterator.__length_hint__',
                                     'bytes_iterator.__reduce__',
                                     'bytes_iterator.__setstate__',
                                     'dict_itemiterator.__length_hint__',
                                     'dict_itemiterator.__reduce__',
                                     'dict_keyiterator.__length_hint__',
                                     'dict_keyiterator.__reduce__',
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
                                     'tuple_iterator.__setstate__']
        )
        _load_and_update(methods_descriptors, '_io', ['_BufferedIOBase.read',
                                                      '_BufferedIOBase.read1',
                                                      '_BufferedIOBase.write',
                                                      '_IOBase.__enter__',
                                                      '_IOBase.__exit__',
                                                      '_IOBase._checkClosed',
                                                      '_IOBase._checkReadable',
                                                      '_IOBase._checkSeekable',
                                                      '_IOBase._checkWritable',
                                                      '_IOBase.seek',
                                                      '_IOBase.truncate',
                                                      '_RawIOBase.readinto',
                                                      '_RawIOBase.write',
                                                      '_TextIOBase.detach',
                                                      '_TextIOBase.read',
                                                      '_TextIOBase.readline',
                                                      '_TextIOBase.write'])
        _load_and_update(methods_descriptors, '_hashlib', ['HASH.copy',
                                                           'HASH.digest',
                                                           'HASH.hexdigest',
                                                           'HASH.update'])
        _load_and_update(methods_descriptors,
                         '_lsprof', ['Profiler.clear',
                                     'Profiler.disable',
                                     'Profiler.enable',
                                     'Profiler.getstats',
                                     'profiler_entry.__reduce__',
                                     'profiler_subentry.__reduce__'])
        _load_and_update(methods_descriptors,
                         '_multiprocessing', ['SemLock.__enter__',
                                              'SemLock.__exit__',
                                              'SemLock._after_fork',
                                              'SemLock._count',
                                              'SemLock._get_value',
                                              'SemLock._is_mine',
                                              'SemLock._is_zero',
                                              'SemLock.acquire',
                                              'SemLock.release'])
        _load_and_add(methods_descriptors, '_ssl', '_SSLSocket.read')
        _load_and_update(methods_descriptors,
                         '_thread', ['LockType.acquire_lock',
                                     'LockType.locked_lock',
                                     'LockType.release_lock'])
        _load_and_update(methods_descriptors,
                         'builtins', ['complex.__getnewargs__',
                                      'reversed.__setstate__'])
        _load_and_add(methods_descriptors,
                      'ctypes', '_SimpleCData.__ctypes_from_outparam__')
        _load_and_update(
                methods_descriptors,
                'ctypes._endian', ['_array_type.from_address',
                                   '_array_type.from_buffer',
                                   '_array_type.from_buffer_copy',
                                   '_array_type.from_param',
                                   '_array_type.in_dll']
        )
        _load_and_add(methods_descriptors,
                      'datetime', 'timezone.__getinitargs__')
        _load_and_update(methods_descriptors,
                         'decimal', ['Context._apply',
                                     'Decimal.__sizeof__'])
        _load_and_add(methods_descriptors, 'functools', 'partial.__setstate__')
        _load_and_update(methods_descriptors,
                         'io', ['BufferedRandom._dealloc_warn',
                                'BufferedReader._dealloc_warn',
                                'BufferedWriter._dealloc_warn',
                                'BytesIO.__getstate__',
                                'BytesIO.__setstate__',
                                'FileIO._dealloc_warn',
                                'StringIO.__getstate__',
                                'StringIO.__setstate__'])
        _load_and_update(
                methods_descriptors,
                'itertools', ['_grouper.__reduce__',
                              '_tee.__copy__',
                              '_tee.__reduce__',
                              '_tee.__setstate__',
                              '_tee_dataobject.__reduce__',
                              'accumulate.__setstate__',
                              'chain.__setstate__',
                              'combinations.__setstate__',
                              'combinations_with_replacement.__setstate__',
                              'cycle.__setstate__',
                              'dropwhile.__setstate__',
                              'groupby.__setstate__',
                              'islice.__setstate__',
                              'permutations.__setstate__',
                              'product.__setstate__',
                              'takewhile.__setstate__',
                              'zip_longest.__setstate__']
        )
        _load_and_add(methods_descriptors, 'socket', 'SocketType._accept')
        _load_and_update(methods_descriptors,
                         'threading', ['_CRLock.__enter__',
                                       '_CRLock.__exit__',
                                       '_CRLock._acquire_restore',
                                       '_CRLock._is_owned',
                                       '_CRLock._release_save',
                                       '_CRLock.acquire',
                                       '_CRLock.release'])
        _load_and_add(methods_descriptors, 'weakref', 'ProxyType.__bytes__')
        _load_and_update(methods_descriptors,
                         'xxsubtype', ['spamdict.getstate',
                                       'spamdict.setstate',
                                       'spamlist.getstate',
                                       'spamlist.setstate'])

        _load_and_add(wrappers_descriptors, '_io', '_IOBase.__del__')
        _load_and_add(wrappers_descriptors, 'socket', 'SocketType.__del__')
        _load_and_update(wrappers_descriptors,
                         'types', ['AsyncGeneratorType.__del__',
                                   'CoroutineType.__del__',
                                   'GeneratorType.__del__'])
        _load_and_add(wrappers_descriptors, 'xxlimited', 'Xxo.__del__')

        if sys.byteorder == 'little':
            _load_and_update(classes,
                             'ctypes', ['c_double.__ctype_be__',
                                        'c_float.__ctype_be__',
                                        'c_int16.__ctype_be__',
                                        'c_int32.__ctype_be__',
                                        'c_int64.__ctype_be__',
                                        'c_uint16.__ctype_be__',
                                        'c_uint32.__ctype_be__',
                                        'c_uint64.__ctype_be__'])
        elif sys.byteorder == 'big':
            _load_and_update(classes,
                             'ctypes', ['c_double.__ctype_le__',
                                        'c_float.__ctype_le__',
                                        'c_int16.__ctype_le__',
                                        'c_int32.__ctype_le__',
                                        'c_int64.__ctype_le__',
                                        'c_uint16.__ctype_le__',
                                        'c_uint32.__ctype_le__',
                                        'c_uint64.__ctype_le__'])

        if sys.version_info < (3, 8):
            _load_and_add(classes, 'macpath', 'norm_error')
            _load_and_update(methods_descriptors,
                             'bz2', ['BZ2Compressor.__getstate__',
                                     'BZ2Decompressor.__getstate__'])
            _load_and_update(methods_descriptors,
                             'io', ['BufferedRWPair.__getstate__',
                                    'BufferedRandom.__getstate__',
                                    'BufferedReader.__getstate__',
                                    'BufferedWriter.__getstate__',
                                    'FileIO.__getstate__',
                                    'TextIOWrapper.__getstate__'])
            _load_and_update(methods_descriptors,
                             'lzma', ['LZMACompressor.__getstate__',
                                      'LZMADecompressor.__getstate__'])
        else:
            _load_and_update(built_in_functions,
                             '_xxsubinterpreters', ['_channel_id',
                                                    'channel_close',
                                                    'channel_create',
                                                    'channel_destroy',
                                                    'channel_list_all',
                                                    'channel_recv',
                                                    'channel_release',
                                                    'channel_send',
                                                    'create',
                                                    'destroy',
                                                    'get_current',
                                                    'get_main',
                                                    'is_running',
                                                    'is_shareable',
                                                    'list_all',
                                                    'run_string'])
            _load_and_add(built_in_functions, 'math', 'hypot')
            _load_and_add(built_in_functions, 'threading', 'excepthook')

            _load_and_update(classes,
                             '_xxsubinterpreters', ['ChannelClosedError',
                                                    'ChannelEmptyError',
                                                    'ChannelError',
                                                    'ChannelNotEmptyError',
                                                    'ChannelNotFoundError',
                                                    'InterpreterID',
                                                    'RunFailedError'])
            _load_and_add(classes, 'collections', '_tuplegetter')
            _load_and_add(classes, 'shutil', '_GiveupOnFastCopy')

            _load_and_add(methods_descriptors,
                          'collections', '_tuplegetter.__reduce__')
        if sys.version_info < (3, 9):
            _load_and_add(classes, 'dataclasses', '_InitVarMeta')
        else:
            _load_and_update(built_in_functions,
                             '_peg_parser', ['compile_string',
                                             'parse_string'])
            _load_and_add(built_in_functions,
                          '_xxsubinterpreters', 'channel_list_interpreters')
            _load_and_add(built_in_functions, 'uuid', '_generate_time_safe')

            _load_and_add(classes, '_collections_abc', 'EllipsisType')
            _load_and_update(classes, '_hashlib', ['HASH',
                                                   'HASHXOF',
                                                   'HMAC'])
            _load_and_update(classes, '_sha3', ['sha3_224',
                                                'sha3_256',
                                                'sha3_384',
                                                'sha3_512',
                                                'shake_128',
                                                'shake_256'])

            _load_and_add(methods_descriptors,
                          '_thread', 'LockType._at_fork_reinit')
            _load_and_update(methods_descriptors,
                             'typing', ['GenericAlias.__instancecheck__',
                                        'GenericAlias.__mro_entries__',
                                        'GenericAlias.__subclasscheck__'])
            _load_and_add(methods_descriptors,
                          'weakref', 'ProxyType.__reversed__')
        if sys.version_info < (3, 10):
            _load_and_add(built_in_functions, 'faulthandler', '_fatal_error')
        else:
            _load_and_update(built_in_functions, 'xxlimited_35', ['foo',
                                                                  'new',
                                                                  'roj'])

            _load_and_add(classes, '_hashlib', 'UnsupportedDigestmodError')
            _load_and_update(classes,
                             '_multibytecodec', ['MultibyteIncrementalDecoder',
                                                 'MultibyteIncrementalEncoder',
                                                 'MultibyteStreamReader',
                                                 'MultibyteStreamWriter'])
            _load_and_add(classes,
                          'importlib.metadata', 'FreezableDefaultDict')
            _load_and_add(classes, 'importlib.metadata._text', 'FoldedCase')
            _load_and_add(classes, 'mailcap', 'UnsafeMailcapInput')
            _load_and_add(classes, 'unittest.mock', 'InvalidSpecError')
            _load_and_update(classes, 'xxlimited_35', ['Null',
                                                       'Str',
                                                       'error'])

            _load_and_update(methods_descriptors, '_csv', ['Writer.writerow',
                                                           'Writer.writerows'])
            _load_and_add(methods_descriptors,
                          '_ssl', 'Certificate.public_bytes')
            _load_and_update(methods_descriptors,
                             'builtins', ['property.__set_name__',
                                          'zip.__setstate__'])
            _load_and_add(methods_descriptors,
                          'collections', 'deque.__reversed__')
            _load_and_update(methods_descriptors,
                             'types', ['UnionType.__instancecheck__',
                                       'UnionType.__subclasscheck__'])
            _load_and_add(methods_descriptors, 'xxlimited_35', 'Xxo.demo')

            _load_and_add(wrappers_descriptors, 'xxlimited_35', 'Xxo.__del__')
elif sys.platform == 'darwin':
    if sys.implementation.name == 'pypy':
        _load_and_update(classes, '_cffi_backend', ['FFI',
                                                    'buffer'])
        _load_and_update(classes, '_collections', ['deque_iterator',
                                                   'deque_reverse_iterator'])
        _load_and_add(classes, '_cppyy', 'CPPInstance')
        _load_and_update(classes, '_ctypes.basics', ['_CDataMeta',
                                                     'bufferable'])
        _load_and_add(classes, '_ctypes.function', 'CFuncPtrType')
        _load_and_update(classes, '_ffi', ['CDLL',
                                           'Field'])
        _load_and_update(classes, '_io', ['_BufferedIOBase',
                                          '_IOBase',
                                          '_RawIOBase',
                                          '_TextIOBase'])
        _load_and_add(classes, '_jitlog', 'JitlogError')
        _load_and_add(classes, '_lsprof', 'Profiler')
        _load_and_add(classes, '_md5', 'md5')
        _load_and_add(classes, '_minimal_curses', 'error')
        _load_and_update(classes,
                         '_multibytecodec', ['MultibyteIncrementalDecoder',
                                             'MultibyteIncrementalEncoder'])
        _load_and_add(classes, '_multiprocessing', 'SemLock')
        _load_and_update(classes, '_rawffi', ['Array',
                                              'CDLL',
                                              'CallbackPtr',
                                              'FuncPtr',
                                              'SegfaultException',
                                              'Structure'])
        _load_and_add(classes, '_rawffi.alt', '_StructDescr')
        _load_and_add(classes, '_vmprof', 'VMProfError')
        _load_and_add(classes, 'ast', 'RevDBMetaVar')
        _load_and_update(
                classes,
                'asyncio.events', ['_RunningLoop',
                                   'BaseDefaultEventLoopPolicy._Local']
        )
        _load_and_add(classes, 'builtins', 'NoneType')
        _load_and_update(classes, 'cffi._pycparser.ply.yacc', ['GrammarError',
                                                               'LALRError',
                                                               'VersionError',
                                                               'YaccError'])
        _load_and_add(classes, 'cffi._pycparser.plyparser', 'ParseError')
        _load_and_add(classes, 'cffi.backend_ctypes', 'CTypesType')
        _load_and_update(classes, 'cffi.error', ['CDefError',
                                                 'FFIError',
                                                 'PkgConfigError',
                                                 'VerificationError',
                                                 'VerificationMissing'])
        _load_and_update(classes, 'datetime', ['dateinterop',
                                               'deltainterop',
                                               'timeinterop'])
        _load_and_add(classes, 'doctest', '_SpoofOut')
        _load_and_add(classes, 'email._encoded_words', '_QByteMap')
        _load_and_update(classes, 'greenlet', ['GreenletExit',
                                               '_continulet',
                                               'error'])
        _load_and_add(classes, 'hpy.debug.leakdetector', 'HPyDebugError')
        _load_and_add(classes, 'hpy.devel', 'HPyExtensionName')
        _load_and_add(classes, 'importlib._bootstrap', '_DeadlockError')
        _load_and_add(classes, 'importlib.util', '_LazyModule')
        _load_and_update(classes, 'itertools', ['_groupby',
                                                '_tee',
                                                '_tee_dataobject'])
        _load_and_add(classes, 'json.encoder', 'StringBuilder')
        _load_and_add(classes, 'lib2to3.patcomp', 'PatternSyntaxError')
        _load_and_add(classes, 'lib2to3.refactor', '_EveryNode')
        _load_and_update(classes, 'logging.config', ['ConvertingDict',
                                                     'ConvertingList',
                                                     'ConvertingTuple'])
        _load_and_add(classes, 'macpath', 'norm_error')
        _load_and_add(classes,
                      'multiprocessing.process', 'AuthenticationString')
        _load_and_add(classes, 'pickle', 'BytesBuilder')
        _load_and_add(
                classes,
                'pypy_tools.build_cffi_imports', 'MissingDependenciesError'
        )
        _load_and_update(classes, 'pypyjit', ['DebugMergePoint',
                                              'GuardOp',
                                              'JitLoopInfo',
                                              'ResOperation',
                                              'not_from_assembler'])
        _load_and_add(classes, 'pyrepl._minimal_curses', 'error')
        _load_and_add(classes, 'pyrepl.curses', 'error')
        _load_and_add(classes, 'pyrepl.keymap', 'KeySpecError')
        _load_and_add(classes, 'pyrepl.unix_console', 'InvalidTerminal')
        _load_and_add(classes, 'runpy', '_Error')
        _load_and_add(classes, 'shutil', '_GiveupOnFastCopy')
        _load_and_add(classes, 'socket', '_GiveupOnSendfile')
        _load_and_add(classes, 'socketserver', '_Threads')
        _load_and_update(classes, 'stackless', ['CoroutineExit',
                                                'TaskletExit'])
        _load_and_update(classes, 'tarfile', ['EOFHeaderError',
                                              'EmptyHeaderError',
                                              'InvalidHeaderError',
                                              'SubsequentHeaderError',
                                              'TruncatedHeaderError'])
        _load_and_add(classes, 'threading', '_CRLock')
        _load_and_add(classes, 'typing_extensions', '_AnyMeta')
        _load_and_update(classes, 'unittest.case', ['_ShouldStop',
                                                    '_UnexpectedSuccess'])

        if sys.version_info < (3, 9):
            _load_and_add(classes, 'dataclasses', '_InitVarMeta')
        else:
            _load_and_add(classes, '_collections_abc', 'EllipsisType')
            _load_and_add(classes, 'unittest.mock', '_AnyComparer')
    else:
        _load_and_add(built_in_functions, '_codecs_cn', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_hk', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_iso2022', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_jp', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_kr', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_tw', 'getcodec')
        _load_and_update(built_in_functions, '_ctypes', ['PyObj_FromPtr',
                                                         'Py_DECREF',
                                                         'Py_INCREF',
                                                         '_unpickle',
                                                         'buffer_info',
                                                         'call_cdeclfunction',
                                                         'call_function',
                                                         'dlclose',
                                                         'dlsym'])
        _load_and_add(built_in_functions, '_hashlib', 'new')
        _load_and_add(built_in_functions, '_uuid', 'generate_time_safe')
        _load_and_add(built_in_functions, '_xxtestfuzz', 'run')
        _load_and_add(built_in_functions, 'locale', '_localeconv')
        _load_and_add(built_in_functions, 'logging', 'Formatter.converter')
        _load_and_add(built_in_functions, 'parser', '_pickler')
        _load_and_update(built_in_functions, 'sys', ['__breakpointhook__',
                                                     'breakpointhook'])
        _load_and_add(built_in_functions, 'timeit', 'default_timer')
        _load_and_update(built_in_functions,
                         'urllib.request', ['_get_proxies',
                                            '_get_proxy_settings'])

        _load_and_add(built_in_functions, '_collections', '_count_elements')
        _load_and_update(built_in_functions,
                         '_string', ['formatter_field_name_split',
                                     'formatter_parser'])
        _load_and_update(built_in_functions, '_thread', ['allocate',
                                                         'exit_thread',
                                                         'start_new'])
        _load_and_add(built_in_functions, 'ctypes', '_dlopen')
        _load_and_update(built_in_functions,
                         'faulthandler', ['_fatal_error_c_thread',
                                          '_read_null',
                                          '_sigabrt',
                                          '_sigfpe',
                                          '_sigsegv',
                                          '_stack_overflow'])
        _load_and_update(built_in_functions, 'heapq', ['_heappop_max',
                                                       '_heapreplace_max'])
        _load_and_update(built_in_functions, 'json.decoder', ['c_scanstring',
                                                              'scanstring'])
        _load_and_update(built_in_functions,
                         'json.encoder', ['c_encode_basestring',
                                          'c_encode_basestring_ascii',
                                          'encode_basestring',
                                          'encode_basestring_ascii'])
        _load_and_add(built_in_functions, 'locale', '_setlocale')
        _load_and_add(built_in_functions,
                      'multiprocessing.synchronize', 'sem_unlink')
        _load_and_add(built_in_functions, 'pty', 'select')
        _load_and_add(built_in_functions, 'random', '_log')
        _load_and_add(built_in_functions, 'threading', '_set_sentinel')
        _load_and_update(built_in_functions, 'tty', ['tcdrain',
                                                     'tcflow',
                                                     'tcflush',
                                                     'tcgetattr',
                                                     'tcsendbreak',
                                                     'tcsetattr'])
        _load_and_add(built_in_functions, 'warnings', '_filters_mutated')
        _load_and_add(built_in_functions, 'xxsubtype', 'bench')
        _load_and_add(built_in_functions,
                      'socketserver', '_ServerSelector._selector_cls')

        _load_and_update(classes, '_collections', ['_deque_iterator',
                                                   '_deque_reverse_iterator'])
        _load_and_add(classes, '_lsprof', 'Profiler')
        _load_and_update(classes,
                         '_multibytecodec', ['MultibyteIncrementalDecoder',
                                             'MultibyteIncrementalEncoder',
                                             'MultibyteStreamReader',
                                             'MultibyteStreamWriter'])
        _load_and_add(classes, '_multiprocessing', 'SemLock')
        _load_and_update(
                classes,
                'asyncio.events', ['_RunningLoop',
                                   'BaseDefaultEventLoopPolicy._Local']
        )
        _load_and_add(classes, 'csv', '_Dialect')
        _load_and_add(classes, 'ctypes', '_CFuncPtr')
        _load_and_update(classes, 'ctypes._endian', ['_array_type',
                                                     '_swapped_meta'])
        _load_and_add(classes, 'curses.panel', 'error')
        _load_and_add(classes, 'email._encoded_words', '_QByteMap')
        _load_and_update(classes, 'encodings.big5', ['IncrementalDecoder',
                                                     'IncrementalEncoder',
                                                     'StreamReader',
                                                     'StreamWriter'])
        _load_and_update(classes, 'encodings.big5hkscs', ['IncrementalDecoder',
                                                          'IncrementalEncoder',
                                                          'StreamReader',
                                                          'StreamWriter'])
        _load_and_update(classes, 'encodings.cp932', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes, 'encodings.cp949', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes, 'encodings.cp950', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.euc_jis_2004', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.euc_jisx0213', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes, 'encodings.euc_jp', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes, 'encodings.euc_kr', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes, 'encodings.gb18030', ['IncrementalDecoder',
                                                        'IncrementalEncoder',
                                                        'StreamReader',
                                                        'StreamWriter'])
        _load_and_update(classes, 'encodings.gb2312', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes, 'encodings.gbk', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes, 'encodings.hz', ['IncrementalDecoder',
                                                   'IncrementalEncoder',
                                                   'StreamReader',
                                                   'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp', ['IncrementalDecoder',
                                                  'IncrementalEncoder',
                                                  'StreamReader',
                                                  'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_1', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_2', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_2004', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_3', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_ext', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_kr', ['IncrementalDecoder',
                                                  'IncrementalEncoder',
                                                  'StreamReader',
                                                  'StreamWriter'])
        _load_and_update(classes, 'encodings.johab', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes, 'encodings.shift_jis', ['IncrementalDecoder',
                                                          'IncrementalEncoder',
                                                          'StreamReader',
                                                          'StreamWriter'])
        _load_and_update(classes,
                         'encodings.shift_jis_2004', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.shift_jisx0213', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_add(classes, 'importlib._bootstrap', '_DeadlockError')
        _load_and_update(classes, '_io', ['_BufferedIOBase',
                                          '_IOBase',
                                          '_RawIOBase',
                                          '_TextIOBase'])
        _load_and_update(classes, 'itertools', ['_grouper',
                                                '_tee',
                                                '_tee_dataobject'])
        _load_and_add(classes, 'json.encoder', 'c_make_encoder')
        _load_and_update(classes, 'json.scanner', ['c_make_scanner',
                                                   'make_scanner'])
        _load_and_add(classes, 'lib2to3.patcomp', 'PatternSyntaxError')
        _load_and_add(classes, 'lib2to3.refactor', '_EveryNode')
        _load_and_add(classes, 'logging.config', 'ConvertingDict')
        _load_and_add(classes,
                      'multiprocessing.process', 'AuthenticationString')
        _load_and_add(classes, 'runpy', '_Error')
        _load_and_add(classes, 'socket', '_GiveupOnSendfile')
        _load_and_add(classes, 'ssl', '_SSLContext')
        _load_and_update(classes, 'tarfile', ['EOFHeaderError',
                                              'EmptyHeaderError',
                                              'InvalidHeaderError',
                                              'SubsequentHeaderError',
                                              'TruncatedHeaderError'])
        _load_and_add(classes, 'threading', '_CRLock')
        _load_and_add(classes, 'tty', 'error')
        _load_and_update(classes, 'unittest.case', ['_ShouldStop',
                                                    '_UnexpectedSuccess'])
        _load_and_add(classes, 'xxsubtype', 'spamdict')

        _load_and_update(
                methods_descriptors,
                '_collections', ['_deque_iterator.__length_hint__',
                                 '_deque_iterator.__reduce__',
                                 '_deque_reverse_iterator.__length_hint__',
                                 '_deque_reverse_iterator.__reduce__']
        )
        _load_and_update(
                methods_descriptors,
                '_collections_abc', ['bytearray_iterator.__length_hint__',
                                     'bytearray_iterator.__setstate__',
                                     'bytes_iterator.__length_hint__',
                                     'bytes_iterator.__reduce__',
                                     'bytes_iterator.__setstate__',
                                     'dict_itemiterator.__length_hint__',
                                     'dict_itemiterator.__reduce__',
                                     'dict_keyiterator.__length_hint__',
                                     'dict_keyiterator.__reduce__',
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
                                     'tuple_iterator.__setstate__']
        )
        _load_and_update(methods_descriptors, '_hashlib', ['HASH.copy',
                                                           'HASH.digest',
                                                           'HASH.hexdigest',
                                                           'HASH.update'])
        _load_and_update(methods_descriptors, '_io', ['_BufferedIOBase.read',
                                                      '_BufferedIOBase.read1',
                                                      '_BufferedIOBase.write',
                                                      '_IOBase.__enter__',
                                                      '_IOBase.__exit__',
                                                      '_IOBase._checkClosed',
                                                      '_IOBase._checkReadable',
                                                      '_IOBase._checkSeekable',
                                                      '_IOBase._checkWritable',
                                                      '_IOBase.seek',
                                                      '_IOBase.truncate',
                                                      '_RawIOBase.readinto',
                                                      '_RawIOBase.write',
                                                      '_TextIOBase.detach',
                                                      '_TextIOBase.read',
                                                      '_TextIOBase.readline',
                                                      '_TextIOBase.write'])
        _load_and_update(methods_descriptors,
                         '_lsprof', ['Profiler.clear',
                                     'Profiler.disable',
                                     'Profiler.enable',
                                     'Profiler.getstats',
                                     'profiler_entry.__reduce__',
                                     'profiler_subentry.__reduce__'])
        _load_and_update(methods_descriptors,
                         '_multiprocessing', ['SemLock.__enter__',
                                              'SemLock.__exit__',
                                              'SemLock._after_fork',
                                              'SemLock._count',
                                              'SemLock._get_value',
                                              'SemLock._is_mine',
                                              'SemLock._is_zero',
                                              'SemLock.acquire',
                                              'SemLock.release'])
        _load_and_add(methods_descriptors, '_ssl', '_SSLSocket.read')
        _load_and_update(methods_descriptors,
                         '_thread', ['LockType.acquire_lock',
                                     'LockType.locked_lock',
                                     'LockType.release_lock'])
        _load_and_update(methods_descriptors,
                         'builtins', ['complex.__getnewargs__',
                                      'reversed.__setstate__'])
        _load_and_add(methods_descriptors,
                      'ctypes', '_SimpleCData.__ctypes_from_outparam__')
        _load_and_update(methods_descriptors,
                         'ctypes._endian', ['_array_type.from_address',
                                            '_array_type.from_buffer',
                                            '_array_type.from_buffer_copy',
                                            '_array_type.from_param',
                                            '_array_type.in_dll'])
        _load_and_add(methods_descriptors,
                      'datetime', 'timezone.__getinitargs__')
        _load_and_update(methods_descriptors,
                         'decimal', ['Context._apply',
                                     'Decimal.__sizeof__'])
        _load_and_add(methods_descriptors, 'functools', 'partial.__setstate__')
        _load_and_update(methods_descriptors,
                         'io', ['BufferedRandom._dealloc_warn',
                                'BufferedReader._dealloc_warn',
                                'BufferedWriter._dealloc_warn',
                                'BytesIO.__getstate__',
                                'BytesIO.__setstate__',
                                'FileIO._dealloc_warn',
                                'StringIO.__getstate__',
                                'StringIO.__setstate__'])
        _load_and_update(
                methods_descriptors,
                'itertools', ['_grouper.__reduce__',
                              '_tee.__copy__',
                              '_tee.__reduce__',
                              '_tee.__setstate__',
                              '_tee_dataobject.__reduce__',
                              'accumulate.__setstate__',
                              'chain.__setstate__',
                              'combinations.__setstate__',
                              'combinations_with_replacement.__setstate__',
                              'cycle.__setstate__',
                              'dropwhile.__setstate__',
                              'groupby.__setstate__',
                              'islice.__setstate__',
                              'permutations.__setstate__',
                              'product.__setstate__',
                              'takewhile.__setstate__',
                              'zip_longest.__setstate__']
        )
        _load_and_add(methods_descriptors, 'socket', 'SocketType._accept')
        _load_and_update(methods_descriptors,
                         'threading', ['_CRLock.__enter__',
                                       '_CRLock.__exit__',
                                       '_CRLock._acquire_restore',
                                       '_CRLock._is_owned',
                                       '_CRLock._release_save',
                                       '_CRLock.acquire',
                                       '_CRLock.release'])
        _load_and_add(methods_descriptors, 'weakref', 'ProxyType.__bytes__')
        _load_and_update(methods_descriptors,
                         'xxsubtype', ['spamdict.getstate',
                                       'spamdict.setstate',
                                       'spamlist.getstate',
                                       'spamlist.setstate'])

        _load_and_add(wrappers_descriptors, '_io', '_IOBase.__del__')
        _load_and_add(wrappers_descriptors, 'socket', 'SocketType.__del__')
        _load_and_update(wrappers_descriptors,
                         'types', ['AsyncGeneratorType.__del__',
                                   'CoroutineType.__del__',
                                   'GeneratorType.__del__'])
        _load_and_add(wrappers_descriptors, 'xxlimited', 'Xxo.__del__')

        if sys.byteorder == 'little':
            _load_and_update(classes,
                             'ctypes', ['c_double.__ctype_be__',
                                        'c_float.__ctype_be__',
                                        'c_int16.__ctype_be__',
                                        'c_int32.__ctype_be__',
                                        'c_int64.__ctype_be__',
                                        'c_uint16.__ctype_be__',
                                        'c_uint32.__ctype_be__',
                                        'c_uint64.__ctype_be__'])
        elif sys.byteorder == 'big':
            _load_and_update(classes,
                             'ctypes', ['c_double.__ctype_le__',
                                        'c_float.__ctype_le__',
                                        'c_int16.__ctype_le__',
                                        'c_int32.__ctype_le__',
                                        'c_int64.__ctype_le__',
                                        'c_uint16.__ctype_le__',
                                        'c_uint32.__ctype_le__',
                                        'c_uint64.__ctype_le__'])

        if sys.version_info < (3, 8):
            _load_and_add(classes, 'distutils.command.bdist', 'ListCompat')
            _load_and_add(classes, 'distutils.filelist', '_UniqueDirs')
            _load_and_add(classes, 'macpath', 'norm_error')

            _load_and_update(methods_descriptors,
                             'bz2', ['BZ2Compressor.__getstate__',
                                     'BZ2Decompressor.__getstate__'])
            _load_and_update(methods_descriptors,
                             'io', ['BufferedRWPair.__getstate__',
                                    'BufferedRandom.__getstate__',
                                    'BufferedReader.__getstate__',
                                    'BufferedWriter.__getstate__',
                                    'FileIO.__getstate__',
                                    'TextIOWrapper.__getstate__'])
            _load_and_update(methods_descriptors,
                             'lzma', ['LZMACompressor.__getstate__',
                                      'LZMADecompressor.__getstate__'])
        else:
            _load_and_update(built_in_functions,
                             '_xxsubinterpreters', ['_channel_id',
                                                    'channel_close',
                                                    'channel_create',
                                                    'channel_destroy',
                                                    'channel_list_all',
                                                    'channel_recv',
                                                    'channel_release',
                                                    'channel_send',
                                                    'create',
                                                    'destroy',
                                                    'get_current',
                                                    'get_main',
                                                    'is_running',
                                                    'is_shareable',
                                                    'list_all',
                                                    'run_string'])
            _load_and_add(
                    built_in_functions,
                    'ctypes.macholib.dyld', '_dyld_shared_cache_contains_path'
            )
            _load_and_add(built_in_functions, 'math', 'hypot')
            _load_and_add(built_in_functions, 'threading', 'excepthook')

            _load_and_add(classes, '_gdbm', 'error')
            _load_and_update(classes,
                             '_xxsubinterpreters', ['ChannelClosedError',
                                                    'ChannelEmptyError',
                                                    'ChannelError',
                                                    'ChannelNotEmptyError',
                                                    'ChannelNotFoundError',
                                                    'InterpreterID',
                                                    'RunFailedError'])
            _load_and_add(classes, 'collections', '_tuplegetter')
            _load_and_add(classes, 'distutils.command.bdist', 'ListCompat')
            _load_and_add(classes, 'distutils.filelist', '_UniqueDirs')
            _load_and_add(classes, 'shutil', '_GiveupOnFastCopy')

            _load_and_add(methods_descriptors,
                          'collections', '_tuplegetter.__reduce__')
        if sys.version_info < (3, 9):
            _load_and_add(classes, 'dataclasses', '_InitVarMeta')
        else:
            _load_and_update(built_in_functions,
                             '_peg_parser', ['compile_string',
                                             'parse_string'])
            _load_and_add(built_in_functions,
                          '_xxsubinterpreters', 'channel_list_interpreters')
            _load_and_add(built_in_functions, 'sys', 'breakpointhook')
            _load_and_add(built_in_functions, 'uuid', '_generate_time_safe')

            _load_and_add(classes, '_collections_abc', 'EllipsisType')
            _load_and_update(classes, '_hashlib', ['HASH',
                                                   'HASHXOF',
                                                   'HMAC'])
            _load_and_update(classes, '_sha3', ['sha3_224',
                                                'sha3_256',
                                                'sha3_384',
                                                'sha3_512',
                                                'shake_128',
                                                'shake_256'])

            _load_and_add(methods_descriptors,
                          '_thread', 'LockType._at_fork_reinit')
            _load_and_update(methods_descriptors,
                             'typing', ['GenericAlias.__instancecheck__',
                                        'GenericAlias.__mro_entries__',
                                        'GenericAlias.__subclasscheck__'])
            _load_and_add(methods_descriptors,
                          'weakref', 'ProxyType.__reversed__')
        if sys.version_info < (3, 10):
            _load_and_add(built_in_functions, 'faulthandler', '_fatal_error')
            _load_and_add(classes, 'typing_extensions', '_AnyMeta')
        else:
            _load_and_update(built_in_functions, 'xxlimited_35', ['foo',
                                                                  'new',
                                                                  'roj'])

            _load_and_add(classes, '_hashlib', 'UnsupportedDigestmodError')
            _load_and_update(classes, '_multibytecodec',
                             ['MultibyteIncrementalDecoder',
                              'MultibyteIncrementalEncoder',
                              'MultibyteStreamReader',
                              'MultibyteStreamWriter'])
            _load_and_add(
                    classes,
                    'importlib.metadata._collections', 'FreezableDefaultDict'
            )
            _load_and_add(classes, 'importlib.metadata._text', 'FoldedCase')
            _load_and_add(classes, 'mailcap', 'UnsafeMailcapInput')
            _load_and_add(classes, 'unittest.mock', 'InvalidSpecError')
            _load_and_update(classes, 'xxlimited_35', ['Null',
                                                       'Str',
                                                       'error'])

            _load_and_update(methods_descriptors, '_csv', ['Writer.writerow',
                                                           'Writer.writerows'])
            _load_and_add(methods_descriptors,
                          '_ssl', 'Certificate.public_bytes')
            _load_and_update(methods_descriptors,
                             'builtins', ['property.__set_name__',
                                          'zip.__setstate__'])
            _load_and_add(methods_descriptors,
                          'collections', 'deque.__reversed__')
            _load_and_update(methods_descriptors,
                             'types', ['UnionType.__instancecheck__',
                                       'UnionType.__subclasscheck__'])
            _load_and_add(methods_descriptors, 'xxlimited_35', 'Xxo.demo')

            _load_and_add(wrappers_descriptors, 'xxlimited_35', 'Xxo.__del__')
elif sys.platform == 'win32':
    if sys.implementation.name == 'pypy':
        _load_and_update(classes, '_cffi_backend', ['FFI',
                                                    'buffer'])
        _load_and_update(classes, '_collections', ['deque_iterator',
                                                   'deque_reverse_iterator'])
        _load_and_update(classes, '_ctypes.basics', ['_CDataMeta',
                                                     'bufferable'])
        _load_and_add(classes, '_ctypes.function', 'CFuncPtrType')
        _load_and_update(classes, '_ffi', ['CDLL',
                                           'Field',
                                           'WinDLL'])
        _load_and_update(classes, '_io', ['_BufferedIOBase',
                                          '_IOBase',
                                          '_RawIOBase',
                                          '_TextIOBase'])
        _load_and_add(classes, '_jitlog', 'JitlogError')
        _load_and_add(classes, '_lsprof', 'Profiler')
        _load_and_add(classes, '_md5', 'md5')
        _load_and_update(classes,
                         '_multibytecodec', ['MultibyteIncrementalDecoder',
                                             'MultibyteIncrementalEncoder'])
        _load_and_add(classes, '_multiprocessing', 'SemLock')
        _load_and_update(classes, '_rawffi', ['Array',
                                              'CDLL',
                                              'CallbackPtr',
                                              'FuncPtr',
                                              'SegfaultException',
                                              'Structure'])
        _load_and_add(classes, '_rawffi.alt', '_StructDescr')
        _load_and_add(classes, 'ast', 'RevDBMetaVar')
        _load_and_update(
                classes,
                'asyncio.events', ['_RunningLoop',
                                   'BaseDefaultEventLoopPolicy._Local']
        )
        _load_and_add(classes, 'builtins', 'NoneType')
        _load_and_update(classes, 'cffi._pycparser.ply.yacc', ['GrammarError',
                                                               'LALRError',
                                                               'VersionError',
                                                               'YaccError'])
        _load_and_add(classes, 'cffi._pycparser.plyparser', 'ParseError')
        _load_and_add(classes, 'cffi.backend_ctypes', 'CTypesType')
        _load_and_update(classes, 'cffi.error', ['CDefError',
                                                 'FFIError',
                                                 'PkgConfigError',
                                                 'VerificationError',
                                                 'VerificationMissing'])
        _load_and_update(classes, 'datetime', ['dateinterop',
                                               'deltainterop',
                                               'timeinterop'])
        _load_and_add(classes, 'distutils.command.bdist', 'ListCompat')
        _load_and_add(classes, 'distutils.filelist', '_UniqueDirs')
        _load_and_add(classes, 'doctest', '_SpoofOut')
        _load_and_add(classes, 'email._encoded_words', '_QByteMap')
        _load_and_update(classes, 'greenlet', ['GreenletExit',
                                               '_continulet',
                                               'error'])
        _load_and_add(classes, 'hpy.debug.leakdetector', 'HPyDebugError')
        _load_and_add(classes, 'hpy.devel', 'HPyExtensionName')
        _load_and_add(classes, 'importlib._bootstrap', '_DeadlockError')
        _load_and_add(classes, 'importlib.util', '_LazyModule')
        _load_and_add(classes, 'io', '_WindowsConsoleIO')
        _load_and_update(classes, 'itertools', ['_groupby',
                                                '_tee',
                                                '_tee_dataobject'])
        _load_and_add(classes, 'json.encoder', 'StringBuilder')
        _load_and_add(classes, 'lib2to3.patcomp', 'PatternSyntaxError')
        _load_and_add(classes, 'lib2to3.refactor', '_EveryNode')
        _load_and_update(classes, 'logging.config', ['ConvertingDict',
                                                     'ConvertingList',
                                                     'ConvertingTuple'])
        _load_and_add(classes, 'macpath', 'norm_error')
        _load_and_add(classes,
                      'multiprocessing.process', 'AuthenticationString')
        _load_and_add(classes, 'pickle', 'BytesBuilder')
        _load_and_add(
                classes,
                'pypy_tools.build_cffi_imports', 'MissingDependenciesError'
        )
        _load_and_update(classes, 'pypyjit', ['DebugMergePoint',
                                              'GuardOp',
                                              'JitLoopInfo',
                                              'ResOperation',
                                              'not_from_assembler'])
        _load_and_add(classes, 'pyrepl.keymap', 'KeySpecError')
        _load_and_add(classes, 'runpy', '_Error')
        _load_and_add(classes, 'shutil', '_GiveupOnFastCopy')
        _load_and_add(classes, 'signal', 'ItimerError')
        _load_and_add(classes, 'socket', '_GiveupOnSendfile')
        _load_and_add(classes, 'socketserver', '_Threads')
        _load_and_update(classes, 'stackless', ['CoroutineExit',
                                                'TaskletExit'])
        _load_and_add(classes, 'subprocess', 'Handle')
        _load_and_update(classes, 'tarfile', ['EOFHeaderError',
                                              'EmptyHeaderError',
                                              'InvalidHeaderError',
                                              'SubsequentHeaderError',
                                              'TruncatedHeaderError'])
        _load_and_add(classes, 'threading', '_CRLock')
        _load_and_add(classes, 'typing_extensions', '_AnyMeta')
        _load_and_update(classes, 'unittest.case', ['_ShouldStop',
                                                    '_UnexpectedSuccess'])

        if sys.version_info < (3, 9):
            _load_and_add(classes, 'dataclasses', '_InitVarMeta')
        else:
            _load_and_add(classes, '_collections_abc', 'EllipsisType')
            _load_and_add(classes, 'unittest.mock', '_AnyComparer')
    else:
        _load_and_add(built_in_functions, '_codecs_cn', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_hk', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_iso2022', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_jp', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_kr', 'getcodec')
        _load_and_add(built_in_functions, '_codecs_tw', 'getcodec')
        _load_and_update(built_in_functions, '_ctypes', ['CopyComPointer',
                                                         'FreeLibrary',
                                                         'PyObj_FromPtr',
                                                         'Py_DECREF',
                                                         'Py_INCREF',
                                                         '_unpickle',
                                                         'buffer_info',
                                                         'call_cdeclfunction',
                                                         'call_function'])
        _load_and_add(built_in_functions, '_hashlib', 'new')
        _load_and_add(built_in_functions, '_locale', '_getdefaultlocale')
        _load_and_add(built_in_functions, '_multiprocessing', 'closesocket')
        _load_and_update(built_in_functions,
                         '_overlapped', ['BindLocal',
                                         'ConnectPipe',
                                         'CreateEvent',
                                         'CreateIoCompletionPort',
                                         'FormatMessage',
                                         'GetQueuedCompletionStatus',
                                         'PostQueuedCompletionStatus',
                                         'RegisterWaitWithQueue',
                                         'ResetEvent',
                                         'SetEvent',
                                         'UnregisterWait',
                                         'UnregisterWaitEx'])
        _load_and_update(built_in_functions,
                         '_string', ['formatter_field_name_split',
                                     'formatter_parser'])
        _load_and_update(built_in_functions, '_thread', ['allocate',
                                                         'exit_thread',
                                                         'start_new'])
        _load_and_add(built_in_functions, 'collections', '_count_elements')
        _load_and_update(built_in_functions, 'ctypes', ['_check_HRESULT',
                                                        '_dlopen'])
        _load_and_update(built_in_functions,
                         'faulthandler', ['_fatal_error_c_thread',
                                          '_raise_exception',
                                          '_read_null',
                                          '_sigabrt',
                                          '_sigfpe',
                                          '_sigsegv'])
        _load_and_update(built_in_functions, 'heapq', ['_heappop_max',
                                                       '_heapreplace_max'])
        _load_and_update(built_in_functions,
                         'json.encoder', ['c_encode_basestring',
                                          'encode_basestring'])
        _load_and_update(built_in_functions, 'locale', ['_localeconv',
                                                        '_setlocale'])
        _load_and_update(built_in_functions,
                         'multiprocessing.connection', ['Connection._read',
                                                        'Connection._write'])
        _load_and_add(built_in_functions,
                      'multiprocessing.synchronize', 'sem_unlink')
        _load_and_add(built_in_functions, 'threading', '_set_sentinel')
        _load_and_add(built_in_functions, 'warnings', '_filters_mutated')
        _load_and_add(built_in_functions, 'xxsubtype', 'bench')

        _load_and_update(classes, '_collections', ['_deque_iterator',
                                                   '_deque_reverse_iterator'])
        _load_and_add(classes, '_ctypes', 'COMError')
        _load_and_update(classes, '_io', ['_BufferedIOBase',
                                          '_IOBase',
                                          '_RawIOBase',
                                          '_TextIOBase'])
        _load_and_add(classes, '_lsprof', 'Profiler')
        _load_and_update(classes,
                         '_multibytecodec', ['MultibyteIncrementalDecoder',
                                             'MultibyteIncrementalEncoder',
                                             'MultibyteStreamReader',
                                             'MultibyteStreamWriter'])
        _load_and_add(classes, '_multiprocessing', 'SemLock')
        _load_and_add(classes, '_overlapped', 'Overlapped')
        _load_and_update(
                classes,
                'asyncio.events', ['_RunningLoop',
                                   'BaseDefaultEventLoopPolicy._Local']
        )
        _load_and_add(classes, 'ctypes', '_CFuncPtr')
        _load_and_update(classes, 'ctypes._endian', ['_array_type',
                                                     '_swapped_meta'])
        _load_and_update(classes, 'ctypes.wintypes', ['LPBOOL',
                                                      'LPBYTE',
                                                      'LPCOLORREF',
                                                      'LPDWORD',
                                                      'LPFILETIME',
                                                      'LPHANDLE',
                                                      'LPHKL',
                                                      'LPINT',
                                                      'LPLONG',
                                                      'LPMSG',
                                                      'LPPOINT',
                                                      'LPRECT',
                                                      'LPRECTL',
                                                      'LPSC_HANDLE',
                                                      'LPSIZE',
                                                      'LPSIZEL',
                                                      'LPUINT',
                                                      'LPWIN32_FIND_DATAA',
                                                      'LPWIN32_FIND_DATAW',
                                                      'LPWORD',
                                                      'PBOOL',
                                                      'PBOOLEAN',
                                                      'PBYTE',
                                                      'PCHAR',
                                                      'PDWORD',
                                                      'PFILETIME',
                                                      'PFLOAT',
                                                      'PHANDLE',
                                                      'PHKEY',
                                                      'PINT',
                                                      'PLARGE_INTEGER',
                                                      'PLCID',
                                                      'PLONG',
                                                      'PMSG',
                                                      'PPOINT',
                                                      'PPOINTL',
                                                      'PRECT',
                                                      'PRECTL',
                                                      'PSHORT',
                                                      'PSIZE',
                                                      'PSIZEL',
                                                      'PSMALL_RECT',
                                                      'PUINT',
                                                      'PULARGE_INTEGER',
                                                      'PULONG',
                                                      'PUSHORT',
                                                      'PWCHAR',
                                                      'PWIN32_FIND_DATAA',
                                                      'PWIN32_FIND_DATAW',
                                                      'PWORD'])
        _load_and_add(classes, 'distutils.command.bdist', 'ListCompat')
        _load_and_add(classes, 'distutils.filelist', '_UniqueDirs')
        _load_and_add(classes, 'email._encoded_words', '_QByteMap')
        _load_and_update(classes, 'encodings.big5', ['IncrementalDecoder',
                                                     'IncrementalEncoder',
                                                     'StreamReader',
                                                     'StreamWriter'])
        _load_and_update(classes, 'encodings.big5hkscs', ['IncrementalDecoder',
                                                          'IncrementalEncoder',
                                                          'StreamReader',
                                                          'StreamWriter'])
        _load_and_update(classes, 'encodings.cp932', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes, 'encodings.cp949', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes, 'encodings.cp950', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.euc_jis_2004', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.euc_jisx0213', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes, 'encodings.euc_jp', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes, 'encodings.euc_kr', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes, 'encodings.gb18030', ['IncrementalDecoder',
                                                        'IncrementalEncoder',
                                                        'StreamReader',
                                                        'StreamWriter'])
        _load_and_update(classes, 'encodings.gb2312', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes, 'encodings.gbk', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes, 'encodings.hz', ['IncrementalDecoder',
                                                   'IncrementalEncoder',
                                                   'StreamReader',
                                                   'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp', ['IncrementalDecoder',
                                                  'IncrementalEncoder',
                                                  'StreamReader',
                                                  'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_1', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_2', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_2004', ['IncrementalDecoder',
                                                       'IncrementalEncoder',
                                                       'StreamReader',
                                                       'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_3', ['IncrementalDecoder',
                                                    'IncrementalEncoder',
                                                    'StreamReader',
                                                    'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_jp_ext', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.iso2022_kr', ['IncrementalDecoder',
                                                  'IncrementalEncoder',
                                                  'StreamReader',
                                                  'StreamWriter'])
        _load_and_update(classes, 'encodings.johab', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes, 'encodings.shift_jis', ['IncrementalDecoder',
                                                          'IncrementalEncoder',
                                                          'StreamReader',
                                                          'StreamWriter'])
        _load_and_update(classes,
                         'encodings.shift_jis_2004', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_update(classes,
                         'encodings.shift_jisx0213', ['IncrementalDecoder',
                                                      'IncrementalEncoder',
                                                      'StreamReader',
                                                      'StreamWriter'])
        _load_and_add(classes, 'importlib._bootstrap', '_DeadlockError')
        _load_and_update(classes, 'itertools', ['_grouper',
                                                '_tee',
                                                '_tee_dataobject'])
        _load_and_add(classes, 'lib2to3.patcomp', 'PatternSyntaxError')
        _load_and_add(classes, 'lib2to3.refactor', '_EveryNode')
        _load_and_add(classes, 'logging.config', 'ConvertingDict')
        _load_and_add(classes, 'msilib', 'MSIError')
        _load_and_add(classes,
                      'multiprocessing.process', 'AuthenticationString')
        _load_and_add(classes, 'runpy', '_Error')
        _load_and_add(classes, 'socket', '_GiveupOnSendfile')
        _load_and_add(classes, 'ssl', '_SSLContext')
        _load_and_add(classes, 'subprocess', 'Handle')
        _load_and_update(classes, 'tarfile', ['EOFHeaderError',
                                              'EmptyHeaderError',
                                              'InvalidHeaderError',
                                              'SubsequentHeaderError',
                                              'TruncatedHeaderError'])
        _load_and_add(classes, 'threading', '_CRLock')
        _load_and_add(classes, 'typing_extensions', '_AnyMeta')
        _load_and_update(classes, 'unittest.case', ['_ShouldStop',
                                                    '_UnexpectedSuccess'])
        _load_and_add(classes, 'xxsubtype', 'spamdict')

        _load_and_update(
                methods_descriptors,
                '_collections', ['_deque_iterator.__length_hint__',
                                 '_deque_iterator.__reduce__',
                                 '_deque_reverse_iterator.__length_hint__',
                                 '_deque_reverse_iterator.__reduce__']
        )
        _load_and_update(
                methods_descriptors,
                '_collections_abc', ['bytearray_iterator.__length_hint__',
                                     'bytearray_iterator.__setstate__',
                                     'bytes_iterator.__length_hint__',
                                     'bytes_iterator.__reduce__',
                                     'bytes_iterator.__setstate__',
                                     'dict_itemiterator.__length_hint__',
                                     'dict_itemiterator.__reduce__',
                                     'dict_keyiterator.__length_hint__',
                                     'dict_keyiterator.__reduce__',
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
                                     'tuple_iterator.__setstate__']
        )
        _load_and_update(methods_descriptors, '_hashlib', ['HASH.copy',
                                                           'HASH.digest',
                                                           'HASH.hexdigest',
                                                           'HASH.update'])
        _load_and_update(methods_descriptors,
                         '_io', ['_BufferedIOBase.read',
                                 '_BufferedIOBase.read1',
                                 '_BufferedIOBase.write',
                                 '_IOBase.__enter__',
                                 '_IOBase.__exit__',
                                 '_IOBase._checkClosed',
                                 '_IOBase._checkReadable',
                                 '_IOBase._checkSeekable',
                                 '_IOBase._checkWritable',
                                 '_IOBase.seek',
                                 '_IOBase.truncate',
                                 '_RawIOBase.readinto',
                                 '_RawIOBase.write',
                                 '_TextIOBase.detach',
                                 '_TextIOBase.read',
                                 '_TextIOBase.readline',
                                 '_TextIOBase.write'])
        _load_and_update(methods_descriptors,
                         '_lsprof', ['Profiler.clear',
                                     'Profiler.disable',
                                     'Profiler.enable',
                                     'Profiler.getstats',
                                     'profiler_entry.__reduce__',
                                     'profiler_subentry.__reduce__'])
        _load_and_update(methods_descriptors,
                         '_multiprocessing', ['SemLock.__enter__',
                                              'SemLock.__exit__',
                                              'SemLock._after_fork',
                                              'SemLock._count',
                                              'SemLock._get_value',
                                              'SemLock._is_mine',
                                              'SemLock._is_zero',
                                              'SemLock.acquire',
                                              'SemLock.release'])
        _load_and_update(methods_descriptors,
                         '_overlapped', ['Overlapped.AcceptEx',
                                         'Overlapped.ConnectEx',
                                         'Overlapped.ConnectNamedPipe',
                                         'Overlapped.DisconnectEx',
                                         'Overlapped.ReadFile',
                                         'Overlapped.ReadFileInto',
                                         'Overlapped.TransmitFile',
                                         'Overlapped.WSARecv',
                                         'Overlapped.WSARecvInto',
                                         'Overlapped.WSASend',
                                         'Overlapped.WriteFile',
                                         'Overlapped.cancel',
                                         'Overlapped.getresult'])
        _load_and_add(methods_descriptors, '_ssl', '_SSLSocket.read')
        _load_and_update(methods_descriptors,
                         '_thread', ['LockType.acquire_lock',
                                     'LockType.locked_lock',
                                     'LockType.release_lock'])
        _load_and_update(methods_descriptors,
                         'builtins', ['complex.__getnewargs__',
                                      'reversed.__setstate__'])
        _load_and_add(methods_descriptors,
                      'ctypes', '_SimpleCData.__ctypes_from_outparam__')
        _load_and_update(methods_descriptors,
                         'ctypes._endian', ['_array_type.from_address',
                                            '_array_type.from_buffer',
                                            '_array_type.from_buffer_copy',
                                            '_array_type.from_param',
                                            '_array_type.in_dll'])
        _load_and_add(methods_descriptors,
                      'datetime', 'timezone.__getinitargs__')
        _load_and_update(methods_descriptors,
                         'decimal', ['Context._apply',
                                     'Decimal.__sizeof__'])
        _load_and_add(methods_descriptors, 'functools', 'partial.__setstate__')
        _load_and_update(methods_descriptors,
                         'io', ['BufferedRandom._dealloc_warn',
                                'BufferedReader._dealloc_warn',
                                'BufferedWriter._dealloc_warn',
                                'BytesIO.__getstate__',
                                'BytesIO.__setstate__',
                                'FileIO._dealloc_warn',
                                'StringIO.__getstate__',
                                'StringIO.__setstate__'])
        _load_and_update(
                methods_descriptors,
                'itertools', ['_grouper.__reduce__',
                              '_tee.__copy__',
                              '_tee.__reduce__',
                              '_tee.__setstate__',
                              '_tee_dataobject.__reduce__',
                              'accumulate.__setstate__',
                              'chain.__setstate__',
                              'combinations.__setstate__',
                              'combinations_with_replacement.__setstate__',
                              'cycle.__setstate__',
                              'dropwhile.__setstate__',
                              'groupby.__setstate__',
                              'islice.__setstate__',
                              'permutations.__setstate__',
                              'product.__setstate__',
                              'takewhile.__setstate__',
                              'zip_longest.__setstate__']
        )
        _load_and_add(methods_descriptors, 'socket', 'SocketType._accept')
        _load_and_update(methods_descriptors,
                         'threading', ['_CRLock.__enter__',
                                       '_CRLock.__exit__',
                                       '_CRLock._acquire_restore',
                                       '_CRLock._is_owned',
                                       '_CRLock._release_save',
                                       '_CRLock.acquire',
                                       '_CRLock.release'])
        _load_and_add(methods_descriptors, 'weakref', 'ProxyType.__bytes__')
        _load_and_update(methods_descriptors,
                         'xxsubtype', ['spamdict.getstate',
                                       'spamdict.setstate',
                                       'spamlist.getstate',
                                       'spamlist.setstate'])

        _load_and_add(wrappers_descriptors, '_io', '_IOBase.__del__')
        _load_and_add(wrappers_descriptors, 'socket', 'SocketType.__del__')
        _load_and_update(wrappers_descriptors,
                         'types', ['AsyncGeneratorType.__del__',
                                   'CoroutineType.__del__',
                                   'GeneratorType.__del__'])

        if sys.maxsize == 0x7fffffff:
            _load_and_update(methods_descriptors,
                             'decimal', ['Context._unsafe_setemax',
                                         'Context._unsafe_setemin',
                                         'Context._unsafe_setprec'])

        if sys.byteorder == 'little':
            _load_and_update(classes,
                             'ctypes', ['HRESULT.__ctype_be__',
                                        'c_double.__ctype_be__',
                                        'c_float.__ctype_be__',
                                        'c_int16.__ctype_be__',
                                        'c_int32.__ctype_be__',
                                        'c_int64.__ctype_be__',
                                        'c_uint16.__ctype_be__',
                                        'c_uint32.__ctype_be__',
                                        'c_uint64.__ctype_be__'])
        elif sys.byteorder == 'big':
            _load_and_update(classes,
                             'ctypes', ['HRESULT.__ctype_le__',
                                        'c_double.__ctype_le__',
                                        'c_float.__ctype_le__',
                                        'c_int16.__ctype_le__',
                                        'c_int32.__ctype_le__',
                                        'c_int64.__ctype_le__',
                                        'c_uint16.__ctype_le__',
                                        'c_uint32.__ctype_le__',
                                        'c_uint64.__ctype_le__'])

        if sys.version_info < (3, 8):
            _load_and_add(classes, 'macpath', 'norm_error')

            _load_and_add(methods_descriptors,
                          '_io', '_WindowsConsoleIO.__getstate__')
            _load_and_update(methods_descriptors,
                             'bz2', ['BZ2Compressor.__getstate__',
                                     'BZ2Decompressor.__getstate__'])
            _load_and_update(methods_descriptors,
                             'io', ['BufferedRWPair.__getstate__',
                                    'BufferedRandom.__getstate__',
                                    'BufferedReader.__getstate__',
                                    'BufferedWriter.__getstate__',
                                    'FileIO.__getstate__',
                                    'TextIOWrapper.__getstate__'])
            _load_and_update(methods_descriptors,
                             'lzma', ['LZMACompressor.__getstate__',
                                      'LZMADecompressor.__getstate__'])
        else:
            _load_and_add(built_in_functions, '_overlapped', 'WSAConnect')
            _load_and_update(built_in_functions,
                             '_xxsubinterpreters', ['_channel_id',
                                                    'channel_close',
                                                    'channel_create',
                                                    'channel_destroy',
                                                    'channel_list_all',
                                                    'channel_recv',
                                                    'channel_release',
                                                    'channel_send',
                                                    'create',
                                                    'destroy',
                                                    'get_current',
                                                    'get_main',
                                                    'is_running',
                                                    'is_shareable',
                                                    'list_all',
                                                    'run_string'])
            _load_and_add(built_in_functions, 'threading', 'excepthook')

            _load_and_update(classes,
                             '_xxsubinterpreters', ['ChannelClosedError',
                                                    'ChannelEmptyError',
                                                    'ChannelError',
                                                    'ChannelNotEmptyError',
                                                    'ChannelNotFoundError',
                                                    'InterpreterID',
                                                    'RunFailedError'])
            _load_and_add(classes, 'collections', '_tuplegetter')
            _load_and_add(classes, 'shutil', '_GiveupOnFastCopy')

            _load_and_add(methods_descriptors,
                          'collections', '_tuplegetter.__reduce__')

        if sys.version_info < (3, 9):
            _load_and_add(classes, 'dataclasses', '_InitVarMeta')
        else:
            _load_and_update(built_in_functions, '_peg_parser',
                             ['compile_string',
                              'parse_string'])
            _load_and_add(built_in_functions,
                          '_xxsubinterpreters', 'channel_list_interpreters')
            _load_and_add(built_in_functions, 'uuid', '_UuidCreate')

            _load_and_add(classes, '_collections_abc', 'EllipsisType')
            _load_and_update(classes, '_hashlib', ['HASH',
                                                   'HASHXOF',
                                                   'HMAC'])
            _load_and_update(classes, '_sha3', ['sha3_224',
                                                'sha3_256',
                                                'sha3_384',
                                                'sha3_512',
                                                'shake_128',
                                                'shake_256'])

            _load_and_add(methods_descriptors,
                          '_collections_abc', 'EllipsisType.__reduce__')
            _load_and_update(methods_descriptors,
                             'typing', ['GenericAlias.__instancecheck__',
                                        'GenericAlias.__mro_entries__',
                                        'GenericAlias.__subclasscheck__'])
            _load_and_add(methods_descriptors,
                          'weakref', 'ProxyType.__reversed__')

        if sys.version_info < (3, 10):
            _load_and_add(built_in_functions, 'faulthandler', '_fatal_error')
            _load_and_add(built_in_functions, 'parser', '_pickler')
        else:
            _load_and_add(classes, '_hashlib', 'UnsupportedDigestmodError')
            _load_and_add(classes,
                          'importlib.metadata', 'FreezableDefaultDict')
            _load_and_add(classes, 'importlib.metadata._text', 'FoldedCase')
            _load_and_add(classes, 'unittest.mock', 'InvalidSpecError')

            _load_and_update(methods_descriptors, '_csv', ['Writer.writerow',
                                                           'Writer.writerows'])
            _load_and_add(methods_descriptors,
                          '_ssl', 'Certificate.public_bytes')
            _load_and_update(methods_descriptors,
                             'builtins', ['property.__set_name__',
                                          'zip.__setstate__'])
            _load_and_add(methods_descriptors,
                          'collections', 'deque.__reversed__')
            _load_and_update(methods_descriptors,
                             'types', ['UnionType.__instancecheck__',
                                       'UnionType.__subclasscheck__'])

            if sys.maxsize == 0x7fffffff:
                _load_and_add(classes, 'distutils.filelist', '_UniqueDirs')
            else:
                _load_and_add(classes, 'mailcap', 'UnsafeMailcapInput')
