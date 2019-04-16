from typing import (Any,
                    Dict,
                    Tuple)

import pytest

from paradigm import models
from tests import strategies
from tests.utils import (find,
                         is_signature_empty,
                         negate)


@pytest.fixture(scope='function')
def signature() -> models.Base:
    return find(strategies.signatures)


@pytest.fixture(scope='function')
def other_signature() -> models.Base:
    return find(strategies.signatures)


@pytest.fixture(scope='function')
def another_signature() -> models.Base:
    return find(strategies.signatures)


@pytest.fixture(scope='function')
def overloaded_signature() -> models.Overloaded:
    return find(strategies.overloaded_signatures)


@pytest.fixture(scope='function')
def plain_signature() -> models.Plain:
    return find(strategies.plain_signatures)


@pytest.fixture(scope='function')
def non_empty_signature() -> models.Base:
    return find(strategies.signatures.filter(negate(is_signature_empty)))


@pytest.fixture(scope='function')
def non_variadic_signature() -> models.Base:
    return find(strategies.non_variadic_signatures)


@pytest.fixture(scope='function')
def non_empty_signature_expected_kwargs(non_empty_signature: models.Base
                                        ) -> Dict[str, Any]:
    return find(strategies.to_expected_kwargs(non_empty_signature))


@pytest.fixture(scope='function')
def non_empty_signature_expected_args(non_empty_signature: models.Base
                                      ) -> Tuple[Any, ...]:
    return find(strategies.to_expected_args(non_empty_signature))


@pytest.fixture(scope='function')
def non_variadic_signature_expected_args(
        non_variadic_signature: models.Base) -> Tuple[Any, ...]:
    return find(strategies.to_expected_args(non_variadic_signature))


@pytest.fixture(scope='function')
def non_variadic_signature_expected_kwargs(
        non_variadic_signature: models.Base) -> Dict[str, Any]:
    return find(strategies.to_expected_kwargs(non_variadic_signature))


@pytest.fixture(scope='function')
def non_variadic_signature_unexpected_args(
        non_variadic_signature: models.Base) -> Tuple[Any, ...]:
    return find(strategies.to_unexpected_args(non_variadic_signature))


@pytest.fixture(scope='function')
def non_variadic_signature_unexpected_kwargs(
        non_variadic_signature: models.Base) -> Dict[str, Any]:
    return find(strategies.to_unexpected_kwargs(non_variadic_signature))
