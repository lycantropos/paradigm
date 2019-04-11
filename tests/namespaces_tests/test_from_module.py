from types import ModuleType

from paradigm.namespaces import from_module


def test_basic(module: ModuleType) -> None:
    result = from_module(module)

    assert isinstance(result, dict)
    assert all(map(str.__instancecheck__, result.keys()))
    assert all(hasattr(module, key)
               for key in result)
    assert all(getattr(module, key) is value
               for key, value in result.items())
