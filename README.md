paradigm
========

[![](https://github.com/lycantropos/paradigm/workflows/CI/badge.svg)](https://github.com/lycantropos/paradigm/actions/workflows/ci.yml "Github Actions")
[![](https://codecov.io/gh/lycantropos/paradigm/branch/master/graph/badge.svg)](https://codecov.io/gh/lycantropos/paradigm "Codecov")
[![](https://img.shields.io/github/license/lycantropos/paradigm.svg)](https://github.com/lycantropos/paradigm/blob/master/LICENSE "License")
[![](https://badge.fury.io/py/paradigm.svg)](https://badge.fury.io/py/paradigm "PyPI")

In what follows `python` is an alias for `python3.5` or `pypy3.5`
or any later version (`python3.6`, `pypy3.6` and so on).

Installation
------------

Install the latest `pip` & `setuptools` packages versions
```bash
python -m pip install --upgrade pip setuptools
```

### User

Download and install the latest stable version from `PyPI` repository
```bash
python -m pip install --upgrade paradigm
```

### Developer

Download the latest version from `GitHub` repository
```bash
git clone https://github.com/lycantropos/paradigm.git
cd paradigm
```

Install dependencies
```bash
python -m pip install -r requirements.txt
```

Install
```bash
python setup.py install
```

Usage
-----

`paradigm` can be used to obtain signature
```python
>>> from paradigm import signatures
>>> from paradigm.models import Parameter, Plain

```
for user-defined functions
```python
>>> def func(foo, bar=None, **kwargs):
...     pass
>>> (signatures.factory(func)
...  == Plain(Parameter(name='foo',
...                     kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
...                     has_default=False),
...           Parameter(name='bar',
...                     kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
...                     has_default=True),
...           Parameter(name='kwargs',
...                     kind=Parameter.Kind.VARIADIC_KEYWORD,
...                     has_default=False)))
True

```
for user-defined classes
```python
>>> class UpperOut:
...     def __init__(self, outfile):
...         self._outfile = outfile
... 
...     def write(self, s):
...         self._outfile.write(s.upper())
... 
...     def __getattr__(self, name):
...         return getattr(self._outfile, name)
>>> (signatures.factory(UpperOut)
...  == Plain(Parameter(name='outfile',
...                     kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
...                     has_default=False)))
True

```
for user-defined classes methods
```python
>>> (signatures.factory(UpperOut.write)
...  == Plain(Parameter(name='self',
...                     kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
...                     has_default=False),
...           Parameter(name='s',
...                     kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
...                     has_default=False)))
True

```
for built-in functions
```python
>>> import platform
>>> from paradigm.models import Parameter, Plain
>>> signatures.factory(any) == (
...     Plain(Parameter(name='__iterable',
...                     kind=Parameter.Kind.POSITIONAL_ONLY,
...                     has_default=False))
...  )
True

```
for built-in classes
```python
>>> signatures.factory(float) == (
...     Plain(Parameter(name='x', 
...                     kind=Parameter.Kind.POSITIONAL_ONLY,
...                     has_default=True))
... )
True

```
for built-in classes methods
```python
>>> from paradigm.models import Parameter, Plain
>>> signatures.factory(float.as_integer_ratio) == (
...     Plain(Parameter(name='self',
...                     kind=Parameter.Kind.POSITIONAL_ONLY,
...                     has_default=False))
... )
True

```

Development
-----------

### Bumping version

#### Preparation

Install
[bump2version](https://github.com/c4urself/bump2version#installation).

#### Pre-release

Choose which version number category to bump following [semver
specification](http://semver.org/).

Test bumping version
```bash
bump2version --dry-run --verbose $CATEGORY
```

where `$CATEGORY` is the target version number category name, possible
values are `patch`/`minor`/`major`.

Bump version
```bash
bump2version --verbose $CATEGORY
```

This will set version to `major.minor.patch-alpha`. 

#### Release

Test bumping version
```bash
bump2version --dry-run --verbose release
```

Bump version
```bash
bump2version --verbose release
```

This will set version to `major.minor.patch`.

### Running tests

Install dependencies
```bash
python -m pip install -r requirements-tests.txt
```

Plain
```bash
pytest
```

Inside `Docker` container:
- with `CPython`
  ```bash
  docker-compose --file docker-compose.cpython.yml up
  ```
- with `PyPy`
  ```bash
  docker-compose --file docker-compose.pypy.yml up
  ```

`Bash` script (e.g. can be used in `Git` hooks):
- with `CPython`
  ```bash
  ./run-tests.sh
  ```
  or
  ```bash
  ./run-tests.sh cpython
  ```

- with `PyPy`
  ```bash
  ./run-tests.sh pypy
  ```

`PowerShell` script (e.g. can be used in `Git` hooks):
- with `CPython`
  ```powershell
  .\run-tests.ps1
  ```
  or
  ```powershell
  .\run-tests.ps1 cpython
  ```
- with `PyPy`
  ```powershell
  .\run-tests.ps1 pypy
  ```
