from hypothesis import given

from paradigm.base import (OverloadedSignature,
                           Parameter,
                           PlainSignature)
from tests.utils import round_trip_pickle
from . import strategies


@given(strategies.parameters,
       strategies.plain_signatures,
       strategies.overloaded_signatures)
def test_models(parameter: Parameter,
                plain_signature: PlainSignature,
                overloaded_signature: OverloadedSignature) -> None:
    for object_ in (parameter, plain_signature, overloaded_signature):
        result = round_trip_pickle(object_)

        assert isinstance(result, type(object_))
        assert result is not object_
        assert result == object_
