from functools import (partial,
                       reduce,
                       singledispatch)
from operator import (attrgetter,
                      le)
from typing import (Any,
                    Dict,
                    Optional,
                    Tuple)

from hypothesis import strategies
from hypothesis.searchstrategy import SearchStrategy

from paradigm.hints import (Domain,
                            Map,
                            Range)
from paradigm.models import (Base,
                             Overloaded,
                             Parameter,
                             Plain,
                             to_parameters_by_kind,
                             to_parameters_by_name)
from tests.strategies.utils import (identifiers,
                                    to_homogeneous_tuples)
from tests.utils import (negate,
                         pack)


def to_plain_signatures(*,
                        parameters_names: SearchStrategy[str] = identifiers,
                        parameters_kinds: SearchStrategy[Parameter.Kind],
                        parameters_has_default_flags: SearchStrategy[bool] =
                        strategies.booleans(),
                        min_size: int = 0,
                        max_size: int
                        ) -> SearchStrategy[Base]:
    if min_size < 0:
        raise ValueError('Min size '
                         'should not be negative, '
                         'but found {min_size}.'
                         .format(min_size=min_size))
    if min_size > max_size:
        raise ValueError('Min size '
                         'should not be greater '
                         'than max size, '
                         'but found {min_size} > {max_size}.'
                         .format(min_size=min_size,
                                 max_size=max_size))

    empty = strategies.builds(Plain)
    if max_size == 0:
        return empty

    def to_parameters(*,
                      names: SearchStrategy[str] = identifiers,
                      kinds: SearchStrategy[Parameter.Kind],
                      has_default_flags: SearchStrategy[bool] =
                      strategies.booleans()) -> SearchStrategy[Parameter]:
        def normalize_mapping(mapping: Dict[str, Any]) -> Dict[str, Any]:
            if mapping['kind'] not in (Parameter.positionals_kinds
                                       | Parameter.keywords_kinds):
                return {**mapping, 'has_default': False}
            return mapping

        return (strategies.fixed_dictionaries(dict(
                name=names,
                kind=kinds,
                has_default=has_default_flags))
                .map(normalize_mapping)
                .map(lambda mapping: Parameter(**mapping)))

    @strategies.composite
    def extend(draw: Map[SearchStrategy[Domain], Domain],
               base: SearchStrategy[Tuple[Parameter, ...]]
               ) -> SearchStrategy[Tuple[Parameter, ...]]:
        precursors = draw(base)
        precursors_names = set(map(attrgetter('name'), precursors))
        precursors_kinds = to_parameters_by_kind(precursors)
        last_precursor = precursors[-1]

        def is_kind_valid(parameter: Parameter) -> bool:
            if parameter.kind not in (Parameter.positionals_kinds
                                      | Parameter.keywords_kinds):
                return not precursors_kinds[parameter.kind]
            return True

        def normalize(parameter: Parameter) -> Parameter:
            if parameter.kind in Parameter.positionals_kinds:
                if last_precursor.has_default and not parameter.has_default:
                    return Parameter(name=parameter.name,
                                     kind=parameter.kind,
                                     has_default=True)
            return parameter

        follower = draw(to_parameters(
                names=identifiers.filter(negate(precursors_names
                                                .__contains__)),
                kinds=(parameters_kinds
                       .filter(partial(le, max(precursors_kinds)))),
                has_default_flags=parameters_has_default_flags)
                        .filter(is_kind_valid)
                        .map(normalize))
        return precursors + (follower,)

    base_parameters = to_parameters(names=parameters_names,
                                    kinds=parameters_kinds,
                                    has_default_flags=
                                    parameters_has_default_flags)
    non_empty = (strategies.recursive(strategies.tuples(base_parameters),
                                      extend,
                                      max_leaves=max_size)
                 .map(pack(Plain)))
    if min_size == 0:
        return empty | non_empty
    return non_empty


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
