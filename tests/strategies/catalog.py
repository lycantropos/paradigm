from paradigm import catalog
from tests.utils import pack
from .utils import (identifiers,
                    to_homogeneous_tuples)

objects_paths = to_homogeneous_tuples(identifiers).map(pack(catalog.Path))
