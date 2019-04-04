from typing import (Any,
                    Dict,
                    Tuple)

import pytest

from paradigm import signatures
from tests import strategies
from tests.utils import (find,
                         is_signature_empty,
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
def non_empty_signature() -> signatures.Base:
    return find(strategies.signatures.filter(negate(is_signature_empty)))


@pytest.fixture(scope='function')
def non_variadic_signature() -> signatures.Base:
    return find(strategies.non_variadic_signatures)


@pytest.fixture(scope='function')
def non_empty_signature_expected_kwargs(non_empty_signature: signatures.Base
                                        ) -> Dict[str, Any]:
    return find(strategies.to_expected_kwargs(non_empty_signature))


@pytest.fixture(scope='function')
def non_empty_signature_expected_args(non_empty_signature: signatures.Base
                                      ) -> Tuple[Any, ...]:
    return find(strategies.to_expected_args(non_empty_signature))


@pytest.fixture(scope='function')
def non_variadic_signature_expected_args(
        non_variadic_signature: signatures.Base) -> Tuple[Any, ...]:
    return find(strategies.to_expected_args(non_variadic_signature))


@pytest.fixture(scope='function')
def non_variadic_signature_expected_kwargs(
        non_variadic_signature: signatures.Base) -> Dict[str, Any]:
    return find(strategies.to_expected_kwargs(non_variadic_signature))


@pytest.fixture(scope='function')
def non_variadic_signature_unexpected_args(
        non_variadic_signature: signatures.Base) -> Tuple[Any, ...]:
    return find(strategies.to_unexpected_args(non_variadic_signature))


@pytest.fixture(scope='function')
def non_variadic_signature_unexpected_kwargs(
        non_variadic_signature: signatures.Base) -> Dict[str, Any]:
    return find(strategies.to_unexpected_kwargs(non_variadic_signature))
