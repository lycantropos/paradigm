from __future__ import annotations

import functools
import sys
import typing as t

import typing_extensions as te

_Params = te.ParamSpec('_Params')
_T1 = t.TypeVar('_T1')
_T2 = t.TypeVar('_T2')


def decorate_if(
        decorator: t.Callable[[t.Callable[_Params, _T1]], t.Any],
        condition: bool
) -> t.Callable[[t.Callable[_Params, _T1]], t.Any]:
    return decorator if condition else _identity_decorator


singledispatchmethod: t.Any
if sys.version_info < (3, 8):

    class _singledispatchmethod:
        dispatcher: t.Any
        func: t.Callable[..., _T1]

        def __new__(cls, func: t.Callable[..., t.Any]) -> te.Self:
            if not callable(func) and not hasattr(func, '__get__'):
                raise TypeError(f'{func!r} is not callable or a descriptor')
            self = super().__new__(cls)
            self.dispatcher, self.func = functools.singledispatch(func), func
            return self

        @t.overload
        def register(self,
                     cls: t.Type[t.Any],
                     method: t.Callable[..., _T1]) -> t.Any:
            return self.dispatcher.register(cls, method)

        @t.overload
        def register(self, cls: t.Type[t.Any]) -> t.Any:
            return self.dispatcher.register(cls)

        def register(self,
                     cls: t.Type[t.Any],
                     method: t.Optional[t.Callable[..., _T1]] = None) -> t.Any:
            return self.dispatcher.register(cls, method)

        @property
        def __isabstractmethod__(self) -> bool:
            return getattr(self.func, '__isabstractmethod__', False)

        def __get__(self,
                    instance: _T2,
                    cls: t.Optional[_T2] = None) -> t.Any:
            def dispatchable_method(*args: t.Any,
                                    **kwargs: t.Any) -> t.Any:
                method = self.dispatcher.dispatch(args[0].__class__)
                return method.__get__(instance, cls)(*args, **kwargs)

            result: t.Any = dispatchable_method
            result.__isabstractmethod__ = self.__isabstractmethod__
            result.register = self.register
            functools.update_wrapper(result, self.func)
            return result


    singledispatchmethod = _singledispatchmethod
else:
    singledispatchmethod = functools.singledispatchmethod


def _identity_decorator(
        value: t.Callable[_Params, _T1]
) -> t.Callable[_Params, _T1]:
    return value
