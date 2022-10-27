import typing as _t

from ._core import models as _models

AnySignature = _t.TypeVar('AnySignature', _models.Overloaded, _models.Plain)
OverloadedSignature = _models.Overloaded
PlainSignature = _models.Plain
Parameter = _models.Parameter
