import pytest

from paradigm import catalog
from tests import strategies
from tests.utils import find


@pytest.fixture(scope='function')
def object_path() -> catalog.Path:
    return find(strategies.objects_paths)
