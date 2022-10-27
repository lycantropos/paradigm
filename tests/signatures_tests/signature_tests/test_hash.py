from hypothesis import given

from tests.utils import (AnySignature,
                         equivalence)
from . import strategies


@given(strategies.signatures, strategies.signatures)
def test_relation_with_equality(signature: AnySignature,
                                other_signature: AnySignature) -> None:
    signature_hash = hash(signature)
    other_signature_hash = hash(other_signature)

    assert equivalence(type(signature) is type(other_signature)
                       and signature_hash == other_signature_hash,
                       signature == other_signature)
