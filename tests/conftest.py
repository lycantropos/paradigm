import os
import pkgutil
import sys
from functools import partial
from typing import Iterator

from hypothesis import (HealthCheck,
                        settings)

base_directory_path = os.path.dirname(__file__)
sys.path.append(base_directory_path)


def explore_pytest_plugins(package_path: str) -> Iterator[str]:
    directories = find_directories(package_path)
    packages_paths = [
        file_finder.path
        for file_finder, _, is_package in pkgutil.iter_modules(directories)
        if not is_package]
    if not packages_paths:
        return
    common_path = os.path.dirname(os.path.commonpath(packages_paths))
    for module_info in pkgutil.iter_modules(packages_paths):
        file_finder, module_name, is_package = module_info
        if is_package:
            continue
        package_path = os.path.relpath(file_finder.path,
                                       start=common_path)
        package_name = path_to_module_name(package_path)
        yield '{package}.{module}'.format(package=package_name,
                                          module=module_name)


def find_directories(root: str) -> Iterator[str]:
    if not os.path.isdir(root):
        return
    yield root
    for root, sub_directories, _ in os.walk(root):
        yield from map(partial(os.path.join, root),
                       sub_directories)


def path_to_module_name(path: str) -> str:
    if os.path.isabs(path):
        err_msg = ('Invalid path: "{path}", '
                   'should be relative.'
                   .format(path=path))
        raise ValueError(err_msg)
    return os.path.normpath(path).replace(os.sep, '.')


fixtures_package_path = os.path.join(base_directory_path, 'fixtures')
pytest_plugins = list(explore_pytest_plugins(fixtures_package_path))

settings.register_profile('default',
                          deadline=None,
                          suppress_health_check=[HealthCheck.filter_too_much,
                                                 HealthCheck.too_slow])
