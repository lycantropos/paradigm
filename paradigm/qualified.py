import platform
import types
from functools import (singledispatch,
                       wraps)
from typing import (Any,
                    Callable,
                    Optional,
                    Tuple,
                    TypeVar,
                    Union)

Name = Tuple[Optional[str], str]


@singledispatch
def name_from(value: Any) -> Name:
    return None, ''


_T1 = TypeVar('_T1')
_T2 = TypeVar('_T2')


def _identity(value: _T1) -> _T1:
    return value


def _decorate_if(decorator: Callable[[_T1], _T2],
                 condition: bool) -> Callable[[_T1], Union[_T1, _T2]]:
    @wraps(decorator)
    def wrapper(wrapped: _T1) -> Union[_T1, _T2]:
        return decorator(wrapped) if condition else wrapped

    return wrapper


@name_from.register(types.BuiltinFunctionType)
@_decorate_if(name_from.register(types.BuiltinMethodType),
              platform.python_implementation() != 'PyPy')
def _(value: Union[types.BuiltinFunctionType,
                   types.BuiltinMethodType]) -> Name:
    return ((value.__self__.__module__, value.__qualname__)
            if isinstance(value.__self__, type)
            else ((value.__self__.__spec__.name, value.__qualname__)
                  if isinstance(value.__self__, types.ModuleType)
                  else (type(value.__self__).__module__, value.__qualname__)))


@name_from.register(types.FunctionType)
def _(value: types.FunctionType) -> Name:
    return value.__module__, value.__qualname__


@_decorate_if(name_from.register(types.MethodDescriptorType),
              platform.python_implementation() != 'PyPy')
@_decorate_if(name_from.register(types.WrapperDescriptorType),
              platform.python_implementation() != 'PyPy')
def _(
        value: Union[types.MemberDescriptorType, types.MethodDescriptorType,
                     types.MethodWrapperType, types.WrapperDescriptorType]
) -> Name:
    return value.__objclass__.__module__, value.__qualname__


@_decorate_if(name_from.register(types.MemberDescriptorType),
              platform.python_implementation() != 'PyPy')
@_decorate_if(name_from.register(types.MethodWrapperType),
              platform.python_implementation() != 'PyPy')
def _(
        value: Union[types.MemberDescriptorType, types.MethodDescriptorType,
                     types.MethodWrapperType, types.WrapperDescriptorType]
) -> Name:
    return value.__objclass__.__module__, value.__qualname__


@_decorate_if(name_from.register(types.MemberDescriptorType),
              platform.python_implementation() == 'PyPy')
def _(
        value: Union[types.MemberDescriptorType, types.MethodDescriptorType,
                     types.MethodWrapperType, types.WrapperDescriptorType]
) -> Name:
    return (value.__objclass__.__module__,
            value.__objclass__.__qualname__ + '.' + value.__name__)


@name_from.register(type)
def _(value: type) -> Name:
    return value.__module__, value.__qualname__
