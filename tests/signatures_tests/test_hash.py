from paradigm import signatures
from tests.utils import equivalence


def test_relation_with_equality(signature: signatures.Base,
                                other_signature: signatures.Base) -> None:
    signature_hash = hash(signature)
    other_signature_hash = hash(other_signature)

    assert equivalence(signature_hash == other_signature_hash,
                       signature == other_signature)
