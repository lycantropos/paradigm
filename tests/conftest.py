import os
import sys
from datetime import timedelta

import pytest
from hypothesis import HealthCheck, settings

is_pypy = sys.implementation.name == 'pypy'
on_ci = bool(os.getenv('CI'))
max_examples = (
    -(-settings().max_examples // (20 if is_pypy else 5))
    if is_pypy and on_ci
    else settings().max_examples
)
settings.register_profile(
    'default',
    deadline=(timedelta(hours=1) / max_examples if on_ci else None),
    max_examples=max_examples,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(
    session: pytest.Session, exitstatus: pytest.ExitCode
) -> None:
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK
