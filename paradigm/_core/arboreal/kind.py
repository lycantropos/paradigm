from enum import IntEnum, auto


class StatementNodeKind(IntEnum):
    ANNOTATED_ASSIGNMENT = auto()
    ASSIGNMENT = auto()
    ASYNC_FUNCTION = auto()
    CLASS = auto()
    FUNCTION = auto()

    def __repr__(self) -> str:
        return repr(self.value)
