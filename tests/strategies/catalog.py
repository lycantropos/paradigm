from hypothesis import strategies

from paradigm import catalog
from paradigm.namespaces import replacing_modules_names
from .definitions import modules
from .utils import (identifiers,
                    pack,
                    to_homogeneous_tuples)

objects_paths = to_homogeneous_tuples(identifiers).map(pack(catalog.Path))
modules_paths = modules.map(catalog.from_module)
modules_paths_from_replacing_modules_names = (
    strategies.lists(strategies.sampled_from(list(replacing_modules_names)),
                     unique=True,
                     min_size=1
                     ).map(pack(catalog.Path)))
