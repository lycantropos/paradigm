from hypothesis import given

from paradigm import catalog
from paradigm.definitions.base import (find_spec,
                                       is_module_path_supported,
                                       stdlib_modules_names)
from tests.utils import implication
from . import strategies


@given(strategies.modules_paths)
def test_relation_with_find_spec(module_path: catalog.Path) -> None:
    assert implication(is_module_path_supported(module_path),
                       str(module_path) in stdlib_modules_names
                       or find_spec(module_path) is not None)
