from keyword import iskeyword
from operator import attrgetter
from string import ascii_letters

from hypothesis import strategies
from hypothesis.searchstrategy import SearchStrategy

from paradigm.signatures import (Base,
                                 Overloaded,
                                 Parameter,
                                 Plain)
from tests.configs import MAX_ARGUMENTS_COUNT
from tests.utils import (negate,
                         pack)

identifiers_characters = strategies.sampled_from(ascii_letters + '_')
identifiers = (strategies.text(identifiers_characters,
                               min_size=1)
               .filter(str.isidentifier)
               .filter(negate(iskeyword)))
positionals_kinds = strategies.sampled_from([
    Parameter.Kind.POSITIONAL_ONLY,
    Parameter.Kind.POSITIONAL_OR_KEYWORD])
keywords_kinds = strategies.sampled_from([Parameter.Kind.POSITIONAL_OR_KEYWORD,
                                          Parameter.Kind.KEYWORD_ONLY])
variadic_kinds = strategies.sampled_from([Parameter.Kind.VARIADIC_KEYWORD,
                                          Parameter.Kind.VARIADIC_POSITIONAL])


def to_parameters(*,
                  names: SearchStrategy[str] = identifiers,
                  kinds: SearchStrategy[Parameter.Kind],
                  has_default_flags: SearchStrategy[bool] =
                  strategies.booleans()) -> SearchStrategy[Parameter]:
    return strategies.builds(Parameter,
                             name=names,
                             kind=kinds,
                             has_default=has_default_flags)


positionals_parameters = to_parameters(kinds=positionals_kinds)
keywords_parameters = to_parameters(kinds=keywords_kinds)
non_variadic_parameters = positionals_parameters | keywords_parameters
variadic_parameters = to_parameters(kinds=variadic_kinds)


def to_signatures(parameters: SearchStrategy[Parameter],
                  *,
                  min_size: int = 0,
                  max_size: int = None) -> SearchStrategy[Base]:
    plain_signatures = to_plain_signatures(parameters,
                                           min_size=min_size,
                                           max_size=max_size)
    overloaded_signatures = to_overloaded_signatures(plain_signatures,
                                                     min_size=min_size,
                                                     max_size=max_size)
    return plain_signatures | overloaded_signatures


def to_plain_signatures(parameters: SearchStrategy[Parameter],
                        *,
                        min_size: int = 0,
                        max_size: int = None
                        ) -> SearchStrategy[Base]:
    return (strategies.lists(parameters,
                             min_size=min_size,
                             max_size=max_size,
                             unique_by=attrgetter('name'))
            .map(pack(Plain)))


def to_overloaded_signatures(bases: SearchStrategy[Base],
                             *,
                             min_size: int = 0,
                             max_size: int = None
                             ) -> SearchStrategy[Base]:
    return (strategies.lists(bases,
                             min_size=min_size,
                             max_size=max_size)
            .map(pack(Overloaded)))


signatures = to_signatures(non_variadic_parameters | variadic_parameters,
                           max_size=MAX_ARGUMENTS_COUNT)
non_variadic_signatures = to_signatures(non_variadic_parameters,
                                        max_size=MAX_ARGUMENTS_COUNT)
