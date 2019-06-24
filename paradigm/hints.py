from typing import (Any,
                    Callable,
                    Dict,
                    TypeVar)

Domain = TypeVar('Domain')
Range = TypeVar('Range')
Map = Callable[[Domain], Range]
Operator = Map[Domain, Domain]
Predicate = Map[Domain, bool]

try:
    from types import MethodDescriptorType
except ImportError:
    MethodDescriptorType = type(list.append)
try:
    from types import WrapperDescriptorType
except ImportError:
    WrapperDescriptorType = type(list.__init__)

Namespace = Dict[str, Any]
