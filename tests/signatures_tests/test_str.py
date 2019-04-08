from paradigm import signatures


def test_type(signature: signatures.Base) -> None:
    result = str(signature)

    assert isinstance(result, str)


def test_nesting(overloaded_signature: signatures.Overloaded) -> None:
    result = str(overloaded_signature)

    assert all(str(signature) in result
               for signature in overloaded_signature.signatures)
