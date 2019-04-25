from hypothesis import given

from paradigm import models
from tests.utils import equivalence
from . import strategies


@given(strategies.signatures, strategies.signatures)
def test_relation_with_equality(signature: models.Base,
                                other_signature: models.Base) -> None:
    signature_hash = hash(signature)
    other_signature_hash = hash(other_signature)

    assert equivalence(type(signature) is type(other_signature)
                       and signature_hash == other_signature_hash,
                       signature == other_signature)
