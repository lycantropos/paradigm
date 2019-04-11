from paradigm import catalog
from .definitions import modules
from .utils import (identifiers,
                    pack,
                    to_homogeneous_tuples)

objects_paths = to_homogeneous_tuples(identifiers).map(pack(catalog.Path))
modules_paths = modules.map(catalog.from_module)
