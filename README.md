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
>>> from paradigm.base import (PlainSignature,
...                            SignatureParameter,
...                            signature_from_callable)

```
for user-defined functions
```python
>>> def func(foo, bar=None, **kwargs):
...     pass
>>> signature_from_callable(func) == PlainSignature(
...     SignatureParameter(name='foo',
...                        kind=SignatureParameter.Kind.POSITIONAL_OR_KEYWORD,
...                        has_default=False),
...     SignatureParameter(name='bar',
...                        kind=SignatureParameter.Kind.POSITIONAL_OR_KEYWORD,
...                        has_default=True),
...     SignatureParameter(name='kwargs',
...                        kind=SignatureParameter.Kind.VARIADIC_KEYWORD,
...                        has_default=False)
... )
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
>>> signature_from_callable(UpperOut) == PlainSignature(
...     SignatureParameter(name='outfile',
...                        kind=SignatureParameter.Kind.POSITIONAL_OR_KEYWORD,
...                        has_default=False)
... )
True

```
for user-defined classes methods
```python
>>> signature_from_callable(UpperOut.write) == PlainSignature(
...     SignatureParameter(name='self',
...                        kind=SignatureParameter.Kind.POSITIONAL_OR_KEYWORD,
...                        has_default=False),
...     SignatureParameter(name='s',
...               kind=SignatureParameter.Kind.POSITIONAL_OR_KEYWORD,
...               has_default=False)
... )
True

```
for built-in functions
```python
>>> import platform
>>> signature_from_callable(any) == PlainSignature(
...     SignatureParameter(name='__iterable',
...                        kind=SignatureParameter.Kind.POSITIONAL_ONLY,
...                        has_default=False)
... )
True

```
for built-in classes
```python
>>> signature_from_callable(float) == PlainSignature(
...     SignatureParameter(name='x', 
...                        kind=SignatureParameter.Kind.POSITIONAL_ONLY,
...                        has_default=True)
... )
True

```
for built-in classes methods
```python
>>> signature_from_callable(float.as_integer_ratio) == PlainSignature(
...     SignatureParameter(name='self',
...                        kind=SignatureParameter.Kind.POSITIONAL_ONLY,
...                        has_default=False)
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

PlainSignature
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
