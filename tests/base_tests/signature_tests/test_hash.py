from hypothesis import given

from tests.utils import Signature, implication

from . import strategies


@given(strategies.hashable_signatures, strategies.hashable_signatures)
def test_relation_with_equality(
    signature: Signature, other_signature: Signature
) -> None:
    signature_hash = hash(signature)
    other_signature_hash = hash(other_signature)

    assert implication(
        signature == other_signature, signature_hash == other_signature_hash
    )
