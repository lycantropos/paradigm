from typing import Tuple

from hypothesis import strategies

from paradigm import catalog
from paradigm.hints import Namespace
from paradigm.namespaces import from_module
from tests.strategies import (modules,
                              modules_paths,
                              non_empty_objects_paths)
from tests.utils import Strategy

modules_paths = modules_paths
namespaces = modules.map(from_module)


def to_namespaces_with_non_empty_objects_paths(
        namespace: Namespace) -> Strategy[Tuple[Namespace, catalog.Path]]:
    return strategies.tuples(
            strategies.just(namespace),
            strategies.sampled_from([catalog.path_from_string(name)
                                     for name in namespace])
            | non_empty_objects_paths
    )


namespaces_with_non_empty_objects_paths = namespaces.flatmap(
        to_namespaces_with_non_empty_objects_paths
)
