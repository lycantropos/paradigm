from hypothesis import given

from paradigm._core.models import Parameter
from paradigm.base import OverloadedSignature, PlainSignature
from tests.utils import ArgT, round_trip_pickle

from .strategies import (
    overloaded_signature_strategy,
    parameter_strategy,
    plain_signatures,
)


@given(parameter_strategy, plain_signatures, overloaded_signature_strategy)
def test_models(
    parameter: Parameter,
    plain_signature: PlainSignature[ArgT],
    overloaded_signature: OverloadedSignature[ArgT],
) -> None:
    for object_ in (parameter, plain_signature, overloaded_signature):
        result = round_trip_pickle(object_)

        assert isinstance(result, type(object_))
        assert result is not object_
        assert result == object_
