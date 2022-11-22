import functools
import sys
import typing as t

_T1 = t.TypeVar('_T1')
_T2 = t.TypeVar('_T2')


def decorate_if(decorator: t.Callable[[_T1], _T2],
                condition: bool) -> t.Union[t.Callable[[_T1], _T1],
                                            t.Callable[[_T1], _T2]]:
    return decorator if condition else _identity


singledispatchmethod: t.Any
if sys.version_info < (3, 8):

    class _singledispatchmethod:
        dispatcher: t.Any
        func: t.Callable[..., _T1]

        def __new__(cls,
                    func: t.Callable[
                        ..., _T1]) -> '_singledispatchmethod':
            if not callable(func) and not hasattr(func, '__get__'):
                raise TypeError(f'{func!r} is not callable or a descriptor')
            self = super().__new__(cls)
            self.dispatcher, self.func = functools.singledispatch(func), func
            return self

        @t.overload
        def register(self,
                     cls: t.Type,
                     method: t.Callable[..., _T1]) -> t.Callable[..., _T1]:
            return self.dispatcher.register(cls, method)

        @t.overload
        def register(self, cls: t.Type) -> t.Callable[
            [t.Callable[..., _T1]], t.Callable[..., _T1]
        ]:
            return self.dispatcher.register(cls)

        def register(self, cls, method=None):
            return self.dispatcher.register(cls, method)

        def __get__(self,
                    instance: _T2,
                    cls: t.Optional[_T2] = None) -> t.Callable[..., _T1]:
            def dispatchable_method(*args: t.Any,
                                    **kwargs: t.Any) -> t.Any:
                method = self.dispatcher.dispatch(args[0].__class__)
                return method.__get__(instance, cls)(*args, **kwargs)

            result: t.Any = dispatchable_method
            result.__isabstractmethod__ = self.__isabstractmethod__
            result.register = self.register
            functools.update_wrapper(result, self.func)
            return result

        @property
        def __isabstractmethod__(self) -> bool:
            return getattr(self.func, '__isabstractmethod__', False)


    singledispatchmethod = _singledispatchmethod
else:
    singledispatchmethod = functools.singledispatchmethod


def _identity(value: _T1) -> _T1:
    return value
