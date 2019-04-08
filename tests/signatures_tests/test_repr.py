from paradigm import signatures


def test_type(signature: signatures.Base) -> None:
    result = repr(signature)

    assert isinstance(result, str)


def test_nesting(overloaded_signature: signatures.Overloaded) -> None:
    result = repr(overloaded_signature)

    assert all(repr(signature) in result
               for signature in overloaded_signature.signatures)


def test_evaluation(signature: signatures.Base) -> None:
    signature_repr = repr(signature)

    result = eval(signature_repr, vars(signatures))

    assert result == signature
