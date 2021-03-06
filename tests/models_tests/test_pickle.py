from hypothesis import given

from paradigm import models
from tests.utils import round_trip_pickle
from . import strategies


@given(strategies.parameters,
       strategies.plain_signatures,
       strategies.overloaded_signatures)
def test_models(parameter: models.Parameter,
                plain_signature: models.Plain,
                overloaded_signature: models.Overloaded) -> None:
    for object_ in (parameter, plain_signature, overloaded_signature):
        result = round_trip_pickle(object_)

        assert isinstance(result, type(object_))
        assert result is not object_
        assert result == object_
