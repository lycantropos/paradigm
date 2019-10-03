from typing import Tuple

from hypothesis import given

from paradigm import catalog
from paradigm.hints import Namespace
from paradigm.namespaces import contains
from . import strategies


@given(strategies.namespaces_with_non_empty_objects_paths)
def test_basic(namespace_with_object_path: Tuple[Namespace, catalog.Path]
               ) -> None:
    namespace, object_path = namespace_with_object_path

    result = contains(namespace, object_path)

    assert isinstance(result, bool)
