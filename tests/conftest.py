import os
import sys

import pytest
from hypothesis import settings

is_pypy = sys.implementation.name == 'pypy'
on_ci = bool(os.getenv('CI', False))
max_examples = (-(-settings.default.max_examples // (20 if is_pypy else 1))
                if on_ci
                else settings.default.max_examples)
settings.register_profile('default',
                          max_examples=max_examples)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session,
                         exitstatus: pytest.ExitCode) -> None:
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK
