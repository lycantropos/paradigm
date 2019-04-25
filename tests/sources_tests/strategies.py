from types import ModuleType

from tests.strategies import modules
from tests.utils import negate


def is_python_module(module: ModuleType) -> bool:
    try:
        module.__file__
    except AttributeError:
        return False
    else:
        return True


python_modules = modules.filter(is_python_module)


def is_python_package(module: ModuleType) -> bool:
    try:
        module.__path__
    except AttributeError:
        return False
    else:
        return True


plain_python_modules = python_modules.filter(negate(is_python_package))
python_packages = modules.filter(is_python_package)
