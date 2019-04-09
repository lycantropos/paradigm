from paradigm import catalog
from tests.utils import equivalence


def test_relation_to_parent(object_path: catalog.Path) -> None:
    assert equivalence(catalog.is_attribute(object_path),
                       len(object_path.parent.parts) > 0)