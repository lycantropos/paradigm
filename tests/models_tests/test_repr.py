from hypothesis import given

from paradigm import (models,
                      signatures)
from . import strategies


@given(strategies.signatures)
def test_type(signature: models.Base) -> None:
    result = repr(signature)

    assert isinstance(result, str)


@given(strategies.plain_signatures)
def test_plain(plain_signature: models.Plain) -> None:
    result = repr(plain_signature)

    assert all(repr(parameter) in result
               for parameter in plain_signature.parameters)


@given(strategies.overloaded_signatures)
def test_nesting(overloaded_signature: models.Overloaded) -> None:
    result = repr(overloaded_signature)

    assert all(repr(signature) in result
               for signature in overloaded_signature.signatures)


@given(strategies.signatures)
def test_evaluation(signature: models.Base) -> None:
    signature_repr = repr(signature)

    result = eval(signature_repr, vars(signatures))

    assert result == signature
