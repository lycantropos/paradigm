import pytest

from paradigm import catalog
from tests import strategies
from tests.utils import find


@pytest.fixture(scope='function')
def object_path() -> catalog.Path:
    return find(strategies.objects_paths)


@pytest.fixture(scope='function')
def module_path() -> catalog.Path:
    return find(strategies.modules_paths)


@pytest.fixture(scope='function')
def module_path_from_replacing_modules_names() -> catalog.Path:
    return find(strategies.modules_paths_from_replacing_modules_names)
