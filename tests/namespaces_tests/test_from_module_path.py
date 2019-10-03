from hypothesis import given

from paradigm import catalog
from paradigm.namespaces import from_module_path
from . import strategies


@given(strategies.modules_paths)
def test_basic(module_path: catalog.Path) -> None:
    result = from_module_path(module_path)

    assert isinstance(result, dict)
    assert all(isinstance(name, str) for name in result)
