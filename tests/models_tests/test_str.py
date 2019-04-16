from paradigm import models


def test_type(signature: models.Base) -> None:
    result = str(signature)

    assert isinstance(result, str)


def test_plain(plain_signature: models.Plain) -> None:
    result = str(plain_signature)

    assert all(str(parameter) in result
               for parameter in plain_signature.parameters)


def test_nesting(overloaded_signature: models.Overloaded) -> None:
    result = str(overloaded_signature)

    assert all(str(signature) in result
               for signature in overloaded_signature.signatures)
