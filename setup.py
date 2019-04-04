from pathlib import Path

from setuptools import (find_packages,
                        setup)

import paradigm

project_base_url = 'https://github.com/lycantropos/paradigm/'

install_requires = [
    'typing_extensions>=3.6.5',
    'mypy>=0.700; platform_python_implementation != "PyPy"'
]
setup_requires = [
    'pytest-runner>=4.2',
]
tests_require = [
    'pytest>=3.8.1',
    'pytest-cov>=2.6.0',
    'hypothesis>=3.73.1',
]

setup(name='paradigm',
      packages=find_packages(exclude=('tests', 'tests.*',)),
      version=paradigm.__version__,
      description=paradigm.__doc__,
      long_description=Path('README.md').read_text(encoding='utf-8'),
      long_description_content_type='text/markdown',
      author='Azat Ibrakov',
      author_email='azatibrakov@gmail.com',
      url=project_base_url,
      download_url=project_base_url + 'archive/master.zip',
      python_requires='>=3.5.3',
      install_requires=install_requires,
      setup_requires=setup_requires,
      tests_require=tests_require)
