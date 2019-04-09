from paradigm import catalog
from paradigm.definitions.base import (find_spec,
                                       is_module_path_supported)
from tests.utils import implication


def test_relation_with_find_spec(object_path: catalog.Path) -> None:
    assert implication(is_module_path_supported(object_path),
                       find_spec(object_path) is not None)
