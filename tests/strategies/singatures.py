from keyword import iskeyword
from operator import attrgetter
from string import ascii_letters

from hypothesis import strategies

from paradigm.signatures import (Overloaded,
                                 Parameter,
                                 Plain)
from tests.config import MAX_ARGUMENTS_COUNT
from tests.utils import (negate,
                         pack)

identifiers_characters = strategies.sampled_from(ascii_letters + '_')
identifiers = (strategies.text(identifiers_characters,
                               min_size=1)
               .filter(str.isidentifier)
               .filter(negate(iskeyword)))
parameters = strategies.builds(Parameter,
                               name=identifiers,
                               kind=strategies.sampled_from(Parameter.Kind),
                               has_default=strategies.booleans())
plain_signatures = (strategies.lists(parameters,
                                     max_size=MAX_ARGUMENTS_COUNT,
                                     unique_by=attrgetter('name'))
                    .map(pack(Plain)))
overloaded_signatures = (strategies.lists(plain_signatures,
                                          max_size=MAX_ARGUMENTS_COUNT)
                         .map(pack(Overloaded)))
signatures = plain_signatures | overloaded_signatures
