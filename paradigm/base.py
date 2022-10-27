import typing as _t
from ._core import (models as _models,
                    signatures as _signatures)

OverloadedSignature = _models.OverloadedSignature
Parameter = _models.Parameter
PlainSignature = _models.PlainSignature


def signature_from_callable(
        _callable: _t.Callable[..., _t.Any]
) -> _t.Union[OverloadedSignature, PlainSignature]:
    return _signatures.from_callable(_callable)
