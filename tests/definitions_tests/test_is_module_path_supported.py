from hypothesis import given

from paradigm import catalog
from paradigm.definitions.base import (find_spec,
                                       is_module_path_supported)
from tests import strategies
from tests.utils import implication


@given(strategies.modules_paths)
def test_relation_with_find_spec(module_path: catalog.Path) -> None:
    assert implication(is_module_path_supported(module_path),
                       find_spec(module_path) is not None)
