from typing import (Callable,
                    TypeVar)

Domain = TypeVar('Domain')
Range = TypeVar('Range')
Map = Callable[[Domain], Range]
Operator = Map[Domain, Domain]

try:
    from types import MethodDescriptorType
except ImportError:
    MethodDescriptorType = type(list.append)
try:
    from types import WrapperDescriptorType
except ImportError:
    WrapperDescriptorType = type(list.__init__)
