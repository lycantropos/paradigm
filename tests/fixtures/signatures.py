import pytest

from paradigm import signatures
from tests import strategies
from tests.utils import find


@pytest.fixture(scope='function')
def signature() -> signatures.Base:
    return find(strategies.signatures)


@pytest.fixture(scope='function')
def second_signature() -> signatures.Base:
    return find(strategies.signatures)


@pytest.fixture(scope='function')
def third_signature() -> signatures.Base:
    return find(strategies.signatures)
