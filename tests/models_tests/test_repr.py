from paradigm import (models,
                      signatures)


def test_type(signature: models.Base) -> None:
    result = repr(signature)

    assert isinstance(result, str)


def test_nesting(overloaded_signature: models.Overloaded) -> None:
    result = repr(overloaded_signature)

    assert all(repr(signature) in result
               for signature in overloaded_signature.signatures)


def test_evaluation(signature: models.Base) -> None:
    signature_repr = repr(signature)

    result = eval(signature_repr, vars(signatures))

    assert result == signature
