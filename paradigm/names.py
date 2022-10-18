import inspect as _inspect
import typing as _t
from importlib import import_module as _import_module
from multiprocessing import current_process as _current_process
from pathlib import Path as _Path

_QualifiedNames = _t.Dict[_t.Optional[str],
                          _t.Dict[str, _t.List[_t.Tuple[str, str]]]]

_CACHE_PATH = _Path(__file__).with_name('_' + _Path(__file__).name)
_QUALIFIED_NAMES_FIELD_NAME = 'qualified_names'

try:
    qualified_names = getattr(
            _import_module(_inspect.getmodulename(_CACHE_PATH)),
            _QUALIFIED_NAMES_FIELD_NAME
    )
except Exception:
    if _current_process().name == 'MainProcess':
        import sys as _sys
        import traceback as _traceback
        import types as _types
        import warnings as _warnings

        from paradigm.catalog import (
            qualified_name_from as _qualified_name_from
        )
        from paradigm.discovery import (
            supported_stdlib_modules_names as _supported_stdlib_modules_names
        )


        def _format_exception(value: BaseException) -> str:
            return '\n'.join(_traceback.format_exception(type(value), value,
                                                         value.__traceback__))


        def _qualify_names(names: _QualifiedNames,
                           object_: _t.Union[_types.ModuleType, type],
                           *,
                           module_name: str,
                           prefix: str,
                           visited_classes: _t.Set[type]) -> None:
            for name, value in vars(object_).items():
                if isinstance(value, type):
                    if value not in visited_classes:
                        qualified_module_name, qualified_object_name = (
                            _qualified_name_from(value)
                        )
                        (names.setdefault(qualified_module_name, {})
                         .setdefault(qualified_object_name, [])
                         .append((module_name, prefix + name)))
                        _qualify_names(names, value,
                                       module_name=module_name,
                                       prefix=prefix + name + '.',
                                       visited_classes={*visited_classes,
                                                        value})
                else:
                    qualified_module_name, qualified_object_name = (
                        _qualified_name_from(value)
                    )
                    if (qualified_module_name is not None
                            or qualified_object_name):
                        (names.setdefault(qualified_module_name, {})
                         .setdefault(qualified_object_name, [])
                         .append((module_name, prefix + name)))


        def _qualify_module_names(names: _QualifiedNames,
                                  module_name: str) -> None:
            try:
                module = _import_module(module_name)
            except Exception as error:
                _warnings.warn(f'Failed importing module "{module_name}". '
                               f'Reason:\n{_format_exception(error)}',
                               ImportWarning)
            else:
                _qualify_names(names, module,
                               module_name=module_name,
                               prefix='',
                               visited_classes=set())


        def _qualify_modules_names(
                modules_names: _t.Iterable[str]
        ) -> _QualifiedNames:
            names = {}
            for module_name in modules_names:
                _qualify_module_names(names, module_name)
            return names


        def _load_qualified_names(
                modules_names: _t.Iterable[str]
        ) -> _QualifiedNames:
            if getattr(_sys, 'ps1', None) is None:  # pragma: no branch
                return _qualify_modules_names(modules_names)
            else:
                import concurrent.futures

                with concurrent.futures.ProcessPoolExecutor(1) as pool:
                    return pool.submit(_qualify_modules_names,
                                       modules_names).result()


        qualified_names = _load_qualified_names(
                _supported_stdlib_modules_names
        )


        def _save_qualified_names(names: _QualifiedNames) -> None:
            from functools import singledispatch

            @singledispatch
            def pretty_format(value: _t.Any, indent: int, depth: int) -> str:
                return repr(value)

            @pretty_format.register(dict)
            def _(value: dict, indent: int, depth: int) -> str:
                return (
                    ('{\n'
                     + ',\n'.join(sorted([
                                indent * ' ' * (depth + 1)
                                + pretty_format(key, indent, depth + 1)
                                + ': '
                                + pretty_format(sub_value, indent,
                                                depth + 1)
                                for key, sub_value in value.items()
                            ]))
                     + '\n' + indent * ' ' * depth + '}')
                    if value
                    else '{}'
                )

            @pretty_format.register(list)
            def _(value: list, indent: int, depth: int) -> str:
                if value:
                    return ('[\n'
                            + ',\n'.join([indent * ' ' * (depth + 1) +
                                          pretty_format(sub_value, indent,
                                                        depth + 1)
                                          for sub_value in value])
                            + '\n' + indent * ' ' * depth + ']')
                else:
                    return '[]'

            try:
                with _CACHE_PATH.open('w',
                                      encoding='utf-8') as file:
                    file.write(f'{_QUALIFIED_NAMES_FIELD_NAME} = '
                               + pretty_format(names, 4, 0)
                               + '\n')
            except Exception as error:
                _warnings.warn('Failed saving qualified names. '
                               f'Reason:\n{_format_exception(error)}',
                               UserWarning)


        _save_qualified_names(qualified_names)
