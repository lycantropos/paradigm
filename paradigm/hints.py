from typing import (Any,
                    Callable,
                    Dict,
                    TypeVar)

Domain = TypeVar('Domain')
Range = TypeVar('Range')
Map = Callable[[Domain], Range]
Operator = Map[Domain, Domain]
Predicate = Map[Domain, bool]
Namespace = Dict[str, Any]
