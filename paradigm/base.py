from __future__ import annotations

import typing as _t

from ._core import models as _models, signatures as _signatures

OptionalParameter = _models.OptionalParameter
OverloadedSignature = _models.OverloadedSignature
ParameterKind = _models.ParameterKind
PlainSignature = _models.PlainSignature
RequiredParameter = _models.RequiredParameter


def signature_from_callable(
    _callable: _t.Callable[..., _t.Any],
) -> OverloadedSignature | PlainSignature:
    return _signatures.from_callable(_callable)
