from paradigm import catalog
from tests.strategies import (identifiers,
                              to_homogeneous_tuples)
from tests.utils import pack

objects_paths = to_homogeneous_tuples(identifiers).map(pack(catalog.Path))
