from functools import (reduce,
                       singledispatch)
from itertools import repeat
from typing import (Any,
                    Dict,
                    Tuple)

import pytest

from paradigm import signatures
from paradigm.hints import (Domain,
                            Range)
from tests import strategies
from tests.utils import (find,
                         negate)


@pytest.fixture(scope='function')
def signature() -> signatures.Base:
    return find(strategies.signatures)


@pytest.fixture(scope='function')
def other_signature() -> signatures.Base:
    return find(strategies.signatures)


@pytest.fixture(scope='function')
def another_signature() -> signatures.Base:
    return find(strategies.signatures)


@pytest.fixture(scope='function')
def non_variadic_signature() -> signatures.Base:
    return find(strategies.non_variadic_signatures)


@pytest.fixture(scope='function')
def unexpected_positionals(non_variadic_signature: signatures.Base
                           ) -> Tuple[Any, ...]:
    count = signature_to_max_positionals_count(non_variadic_signature) + 1
    return tuple(repeat(None, count))


@pytest.fixture(scope='function')
def unexpected_keywords(signature: signatures.Base) -> Dict[str, Any]:
    keywords = signature_to_all_keywords(signature)
    unexpected_keyword_name = find(strategies.identifiers
                                   .filter(negate(keywords.__contains__)))
    return dict(zip(list(keywords.keys()) + [unexpected_keyword_name],
                    repeat(None)))


@singledispatch
def signature_to_max_positionals_count(signature: signatures.Base) -> int:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@signature_to_max_positionals_count.register(signatures.Plain)
def plain_signature_to_max_positionals_count(signature: signatures.Plain
                                             ) -> int:
    positionals = (signature.parameters_by_kind[
                       signatures.Parameter.Kind.POSITIONAL_ONLY]
                   + signature.parameters_by_kind[
                       signatures.Parameter.Kind.POSITIONAL_OR_KEYWORD])
    return len(positionals)


@signature_to_max_positionals_count.register(signatures.Overloaded)
def overloaded_signature_to_max_positionals_count(
        signature: signatures.Overloaded) -> int:
    return max(map(signature_to_max_positionals_count, signature.signatures),
               default=0)


@singledispatch
def signature_to_all_keywords(signature: signatures.Base
                              ) -> Dict[str, signatures.Parameter]:
    raise TypeError('Unsupported signature type: {type}.'
                    .format(type=type(signature)))


@signature_to_all_keywords.register(signatures.Plain)
def plain_signature_to_all_keywords(signature: signatures.Plain
                                    ) -> Dict[str, signatures.Parameter]:
    keywords = (signature.parameters_by_kind[
                    signatures.Parameter.Kind.POSITIONAL_OR_KEYWORD]
                + signature.parameters_by_kind[
                    signatures.Parameter.Kind.KEYWORD_ONLY])
    return signatures.to_parameters_by_name(keywords)


@signature_to_all_keywords.register(signatures.Overloaded)
def overloaded_signature_to_all_keywords(signature: signatures.Overloaded
                                         ) -> Dict[str, signatures.Parameter]:
    def merge_dictionaries(left_dictionary: Dict[Domain, Range],
                           right_dictionary: Dict[Domain, Range]
                           ) -> Dict[Domain, Range]:
        return {**left_dictionary, **right_dictionary}

    return reduce(merge_dictionaries,
                  map(signature_to_all_keywords, signature.signatures),
                  {})
