from paradigm import catalog
from paradigm.namespaces import from_module_path


def test_basic(module_path: catalog.Path) -> None:
    result = from_module_path(module_path)

    assert result['__name__'] == str(module_path)


def test_replacing_modules_names(
        module_path_from_replacing_modules_names: catalog.Path) -> None:
    result = from_module_path(module_path_from_replacing_modules_names)

    assert isinstance(result, dict)
    assert (result['__name__']
            not in module_path_from_replacing_modules_names.parts)
