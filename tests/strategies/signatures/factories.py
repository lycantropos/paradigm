from functools import (reduce,
                       singledispatch)
from operator import attrgetter
from typing import (Dict,
                    Tuple)

from hypothesis import strategies
from hypothesis.searchstrategy import SearchStrategy

from paradigm.hints import (Domain,
                            Range)
from paradigm.signatures import (Base,
                                 Overloaded,
                                 Parameter,
                                 Plain,
                                 to_parameters_by_name)
from tests.strategies.utils import (identifiers,
                                    to_homogeneous_tuples)
from tests.utils import (negate,
                         pack)


def to_parameters(*,
                  names: SearchStrategy[str] = identifiers,
                  kinds: SearchStrategy[Parameter.Kind],
                  has_default_flags: SearchStrategy[bool] =
                  strategies.booleans()) -> SearchStrategy[Parameter]:
    return strategies.builds(Parameter,
                             name=names,
                             kind=kinds,
                             has_default=has_default_flags)


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
                             min_size: int = 2,
                             max_size: int = None
                             ) -> SearchStrategy[Base]:
    return (strategies.lists(bases,
                             min_size=min_size,
                             max_size=max_size)
            .map(pack(Overloaded)))


def to_expected_args(signature: Base,
                     *,
                     values: SearchStrategy[Domain] = strategies.none()
                     ) -> SearchStrategy[Tuple[Domain, ...]]:
    count = signature_to_min_positionals_count(signature)
    return to_homogeneous_tuples(values,
                                 max_size=count)


def to_expected_kwargs(signature: Base,
                       *,
                       values: SearchStrategy[Domain] = strategies.none()
                       ) -> SearchStrategy[Dict[str, Domain]]:
    keywords = signature_to_keywords_intersection(signature)
    if not keywords:
        return strategies.fixed_dictionaries({})
    return strategies.dictionaries(strategies.sampled_from(list(keywords
                                                                .keys())),
                                   values)


def to_unexpected_args(signature: Base,
                       *,
                       values: SearchStrategy[Domain] = strategies.none()
                       ) -> SearchStrategy[Tuple[Domain, ...]]:
    count = signature_to_max_positionals_count(signature) + 1
    return to_homogeneous_tuples(values,
                                 min_size=count)


def to_unexpected_kwargs(signature: Base,
                         *,
                         values: SearchStrategy[Domain] = strategies.none()
                         ) -> SearchStrategy[Dict[str, Domain]]:
    keywords = signature_to_keywords_union(signature)
    is_unexpected = negate(keywords.__contains__)
    return (strategies.dictionaries(identifiers.filter(is_unexpected), values)
            .filter(bool))


@singledispatch
def signature_to_max_positionals_count(signature: Base) -> int:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@singledispatch
def signature_to_min_positionals_count(signature: Base) -> int:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@signature_to_max_positionals_count.register(Plain)
@signature_to_min_positionals_count.register(Plain)
def plain_signature_to_positionals_count(signature: Plain) -> int:
    positionals = (signature.parameters_by_kind[
                       Parameter.Kind.POSITIONAL_ONLY]
                   + signature.parameters_by_kind[
                       Parameter.Kind.POSITIONAL_OR_KEYWORD])
    return len(positionals)


@signature_to_max_positionals_count.register(Overloaded)
def overloaded_signature_to_max_positionals_count(signature: Overloaded
                                                  ) -> int:
    return max(map(signature_to_max_positionals_count, signature.signatures),
               default=0)


@signature_to_min_positionals_count.register(Overloaded)
def overloaded_signature_to_min_positionals_count(signature: Overloaded
                                                  ) -> int:
    return min(map(signature_to_min_positionals_count, signature.signatures),
               default=0)


@singledispatch
def signature_to_keywords_intersection(signature: Base
                                       ) -> Dict[str, Parameter]:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@singledispatch
def signature_to_keywords_union(signature: Base) -> Dict[str, Parameter]:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@signature_to_keywords_union.register(Plain)
@signature_to_keywords_intersection.register(Plain)
def plain_signature_to_keywords(signature: Plain) -> Dict[str, Parameter]:
    keywords = (signature.parameters_by_kind[
                    Parameter.Kind.POSITIONAL_OR_KEYWORD]
                + signature.parameters_by_kind[
                    Parameter.Kind.KEYWORD_ONLY])
    return to_parameters_by_name(keywords)


@signature_to_keywords_intersection.register(Overloaded)
def overloaded_signature_to_keywords_intersection(signature: Overloaded
                                                  ) -> Dict[str, Parameter]:
    if not signature.signatures:
        return {}

    def intersect(left_dictionary: Dict[Domain, Range],
                  right_dictionary: Dict[Domain, Range]
                  ) -> Dict[Domain, Range]:
        common_keys = left_dictionary.keys() & right_dictionary.keys()
        return {key: right_dictionary[key] for key in common_keys}

    return reduce(intersect,
                  map(signature_to_keywords_intersection,
                      signature.signatures))


@signature_to_keywords_union.register(Overloaded)
def overloaded_signature_to_keywords_union(signature: Overloaded
                                           ) -> Dict[str, Parameter]:
    if not signature.signatures:
        return {}

    def unite(left_dictionary: Dict[Domain, Range],
              right_dictionary: Dict[Domain, Range]) -> Dict[Domain, Range]:
        return {**left_dictionary, **right_dictionary}

    return reduce(unite,
                  map(signature_to_keywords_union, signature.signatures))
