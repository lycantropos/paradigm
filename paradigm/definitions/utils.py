from types import ModuleType
from typing import (Any,
                    List,
                    Union)


def to_contents(object_: Union[ModuleType, type]) -> List[Any]:
    return list(vars(object_).values())
