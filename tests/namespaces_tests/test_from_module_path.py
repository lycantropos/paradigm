from paradigm import catalog
from paradigm.arboretum.namespaces import from_module_path


def test_basic(module_path: catalog.Path) -> None:
    result = from_module_path(module_path)

    assert result['__name__'] == str(module_path)
