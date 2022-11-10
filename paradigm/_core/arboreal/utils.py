import functools as _functools
import sys as _sys
import typing as _t

singledispatchmethod: _t.Any

if _sys.version_info >= (3, 8):
    singledispatchmethod = _functools.singledispatchmethod
else:
    _T1 = _t.TypeVar('_T1')
    _T2 = _t.TypeVar('_T2')


    class _singledispatchmethod:
        dispatcher: _t.Any
        func: _t.Callable[..., _T1]

        def __new__(cls,
                    func: _t.Callable[..., _T1]) -> '_singledispatchmethod':
            if not callable(func) and not hasattr(func, '__get__'):
                raise TypeError(f'{func!r} is not callable or a descriptor')
            self = super().__new__(cls)
            self.dispatcher, self.func = _functools.singledispatch(func), func
            return self

        @_t.overload
        def register(self,
                     cls: _t.Type,
                     method: _t.Callable[..., _T1]) -> _t.Callable[..., _T1]:
            return self.dispatcher.register(cls, method)

        @_t.overload
        def register(self, cls: _t.Type) -> _t.Callable[
            [_t.Callable[..., _T1]], _t.Callable[..., _T1]
        ]:
            return self.dispatcher.register(cls)

        def register(self, cls, method=None):
            return self.dispatcher.register(cls, method)

        def __get__(self,
                    instance: _T2,
                    cls: _t.Optional[_T2] = None) -> _t.Callable[..., _T1]:
            def dispatchable_method(*args: _t.Any, **kwargs: _t.Any) -> _t.Any:
                method = self.dispatcher.dispatch(args[0].__class__)
                return method.__get__(instance, cls)(*args, **kwargs)

            result: _t.Any = dispatchable_method
            result.__isabstractmethod__ = self.__isabstractmethod__
            result.register = self.register
            _functools.update_wrapper(result, self.func)
            return result

        @property
        def __isabstractmethod__(self) -> bool:
            return getattr(self.func, '__isabstractmethod__', False)


    singledispatchmethod = _singledispatchmethod
