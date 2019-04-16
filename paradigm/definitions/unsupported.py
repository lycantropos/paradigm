import platform
import sys
from itertools import chain
from types import ModuleType
from typing import (Callable,
                    Iterable,
                    Union)

from .utils import to_contents

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
    import _collections
    import _codecs_hk
    import _codecs_iso2022
    import _codecs_jp
    import _codecs_kr
    import _codecs_cn
    import _codecs_tw
    import _lsprof
    import _multibytecodec
    import _multiprocessing
    import _string
    import aifc
    import audioop
    import bdb
    import ctypes
    import faulthandler
    import mailbox
    import parser
    import turtle
    import unittest
    import xxsubtype

    # not supported by ``typeshed`` package
    stdlib_modules.update({_collections,
                           _codecs_hk,
                           _codecs_iso2022,
                           _codecs_jp,
                           _codecs_kr,
                           _codecs_cn,
                           _codecs_tw,
                           _lsprof,
                           _multibytecodec,
                           _multiprocessing,
                           _string,
                           aifc,
                           audioop,
                           bdb,
                           ctypes,
                           faulthandler,
                           mailbox,
                           parser,
                           turtle,
                           unittest,
                           xxsubtype})

    if sys.version_info >= (3, 6):
        import _sha3

        stdlib_modules.add(_sha3)

    if ((3, 6) <= sys.version_info < (3, 6, 7)
            or (3, 7) <= sys.version_info < (3, 7, 1)):
        import _blake2

        stdlib_modules.add(_blake2)

    if sys.platform == 'win32':
        import _msi

        stdlib_modules.add(_msi)


def to_callables(object_: Union[ModuleType, type]) -> Iterable[Callable]:
    yield from filter(callable, to_contents(object_))


stdlib_modules_callables = list(chain.from_iterable(map(to_callables,
                                                        stdlib_modules)))

built_in_functions = set()

if platform.python_implementation() != 'PyPy':
    import _hashlib
    import _json
    import _thread
    import codecs
    import socket

    # not supported by ``typeshed`` package
    built_in_functions.update({_hashlib.openssl_md5,
                               _hashlib.openssl_sha1,
                               _hashlib.openssl_sha224,
                               _hashlib.openssl_sha256,
                               _hashlib.openssl_sha384,
                               _hashlib.openssl_sha512,
                               _json.encode_basestring,
                               _thread.allocate,
                               _thread.exit_thread,
                               _thread.interrupt_main,
                               _thread.stack_size,
                               _thread.start_new_thread,
                               codecs.backslashreplace_errors,
                               codecs.ignore_errors,
                               codecs.namereplace_errors,
                               codecs.replace_errors,
                               codecs.strict_errors,
                               codecs.xmlcharrefreplace_errors,
                               socket.dup,
                               sys.callstats,
                               sys.getallocatedblocks,
                               sys.get_coroutine_wrapper,
                               sys.set_coroutine_wrapper})
    if sys.version_info >= (3, 6):
        built_in_functions.update({sys.getfilesystemencodeerrors,
                                   sys.get_asyncgen_hooks,
                                   sys.set_asyncgen_hooks})

    if sys.version_info >= (3, 7):
        built_in_functions.update({socket.close,
                                   sys.breakpointhook})

    if sys.platform != 'win32':
        import _locale

        built_in_functions.update({_locale.bind_textdomain_codeset,
                                   _locale.bindtextdomain,
                                   _locale.dcgettext,
                                   _locale.dgettext,
                                   _locale.gettext,
                                   _locale.textdomain})

        if sys.version_info >= (3, 7):
            import time

            built_in_functions.add(time.pthread_getcpuclockid)

classes = set()

if platform.python_implementation() != 'PyPy':
    import _collections_abc
    import _io
    import _ssl
    import _thread
    import asyncio.events
    import encodings
    import imaplib
    import itertools
    import macpath
    import pdb
    import random
    import runpy
    import smtplib
    import socket
    import tarfile
    import tkinter
    import unittest
    import warnings

    # not supported by ``typeshed`` package
    classes.update({_collections_abc.mappingproxy,
                    _io._BufferedIOBase,
                    _io._IOBase,
                    _io._RawIOBase,
                    _io._TextIOBase,
                    _ssl._SSLContext,
                    _thread.RLock,
                    _thread._local,
                    asyncio.events._RunningLoop,
                    imaplib.IMAP4.abort,
                    imaplib.IMAP4.error,
                    imaplib.IMAP4.readonly,
                    itertools._grouper,
                    itertools._tee,
                    itertools._tee_dataobject,
                    encodings.CodecRegistryError,
                    macpath.norm_error,
                    pdb._rstr,
                    random._MethodType,
                    runpy._Error,
                    smtplib.SMTPNotSupportedError,
                    socket._GiveupOnSendfile,
                    tarfile.EmptyHeaderError,
                    tarfile.EOFHeaderError,
                    tarfile.InvalidHeaderError,
                    tarfile.TruncatedHeaderError,
                    tarfile.SubsequentHeaderError,
                    tkinter.TclError,
                    unittest.case.SkipTest,
                    warnings._OptionError})

    if sys.version_info >= (3, 6):
        import _ast
        import asyncio.base_futures

        classes.update({_ast.Constant,
                        asyncio.base_futures.InvalidStateError})

    if sys.version_info < (3, 7):
        import os
        import plistlib

        classes.update({_collections_abc.range_iterator,
                        plistlib._InternalDict})
    else:
        import dataclasses
        import typing

        classes.update({asyncio.events.SendfileNotAvailableError,
                        dataclasses._InitVarMeta,
                        typing._ProtocolMeta})

    if sys.platform == 'win32':
        import msilib
        import subprocess

        classes.update({msilib.UuidCreate,
                        msilib.FCICreate,
                        msilib.OpenDatabase,
                        msilib.CreateRecord,
                        msilib.MSIError,
                        subprocess.Handle})

        if sys.version_info < (3, 7):
            import os

            classes.update({os.uname_result,
                            os.statvfs_result})
    else:
        import termios

        classes.add(termios.error)

methods_descriptors = set()

if platform.python_implementation() != 'PyPy':
    import _collections_abc
    import _io
    import _thread
    import collections

    # not supported by ``typeshed`` package
    methods_descriptors.update({_collections_abc.dict_items.isdisjoint,
                                _collections_abc.dict_keys.isdisjoint,
                                _collections_abc.generator.close,
                                _collections_abc.generator.send,
                                _collections_abc.generator.throw,
                                _collections_abc.coroutine.close,
                                _collections_abc.coroutine.send,
                                _collections_abc.coroutine.throw,
                                _io.BufferedRWPair.peek,
                                _thread.LockType.acquire_lock,
                                _thread.LockType.locked,
                                _thread.LockType.locked_lock,
                                _thread.LockType.release_lock,
                                collections.OrderedDict.clear,
                                collections.OrderedDict.pop,
                                collections.OrderedDict.update})

    if sys.version_info >= (3, 6):
        methods_descriptors.update({_collections_abc.async_generator.aclose,
                                    _collections_abc.async_generator.asend,
                                    _collections_abc.async_generator.athrow})
        if sys.platform == 'linux':
            import socket

            methods_descriptors.add(socket.socket.sendmsg_afalg)

    if sys.version_info >= (3, 7):
        import socket

        methods_descriptors.add(socket.socket.getblocking)
    else:
        import zipimport

        methods_descriptors.update({collections.OrderedDict.setdefault,
                                    zipimport.zipimporter.find_loader})

    if sys.platform == 'win32':
        import socket

        methods_descriptors.add(socket.socket.share)

wrappers_descriptors = set()

if platform.python_implementation() != 'PyPy':
    import _collections_abc

    # not supported by ``typeshed`` package
    wrappers_descriptors.update({
        _collections_abc.coroutine.__del__,
        _collections_abc.generator.__del__})

    if sys.version_info >= (3, 6):
        import _socket

        wrappers_descriptors.update({_collections_abc.async_generator.__del__,
                                     _socket.socket.__del__})
