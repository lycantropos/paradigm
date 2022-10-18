from paradigm import catalog
from tests.utils import pack
from .utils import (identifiers,
                    modules,
                    to_homogeneous_tuples)

objects_paths = to_homogeneous_tuples(identifiers).map(pack(catalog.Path))
non_empty_objects_paths = (to_homogeneous_tuples(identifiers,
                                                 min_size=1)
                           .map(pack(catalog.Path)))
modules_paths = modules.map(catalog.module_path_from_module)
