from paradigm import signatures


def test_type(signature: signatures.Base) -> None:
    result = repr(signature)

    assert isinstance(result, str)


def test_evaluation(signature: signatures.Base) -> None:
    signature_repr = repr(signature)

    result = eval(signature_repr, vars(signatures))

    assert result == signature
