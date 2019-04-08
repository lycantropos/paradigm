from paradigm import signatures


def test_type(signature: signatures.Base) -> None:
    result = str(signature)

    assert isinstance(result, str)
