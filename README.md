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

With setup
```python
>>> import typing
>>> from paradigm.base import (Parameter,
...                            PlainSignature,
...                            signature_from_callable)
>>> from typing_extensions import Self
>>> class UpperOut:
...     def __init__(self, outfile: typing.IO[typing.AnyStr]) -> None:
...         self._outfile = outfile
... 
...     def write(self, s: typing.AnyStr) -> None:
...         self._outfile.write(s.upper())
... 
...     def __getattr__(self, name: str) -> typing.Any:
...         return getattr(self._outfile, name)
>>> def func(foo: int, bar: bool = False, **kwargs: str) -> None:
...     pass

```
we can obtain a signature of
- user-defined functions
  ```python
  >>> signature_from_callable(func) == PlainSignature(
  ...     Parameter(annotation=int,
  ...               has_default=False,
  ...               kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
  ...               name='foo'),
  ...     Parameter(annotation=bool,
  ...               has_default=True,
  ...               kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
  ...               name='bar'),
  ...     Parameter(annotation=str,
  ...               has_default=False,
  ...               kind=Parameter.Kind.VARIADIC_KEYWORD,
  ...               name='kwargs'),
  ...     returns=None
  ... )
  True
  
  ```
- user-defined classes
  ```python
  >>> signature_from_callable(UpperOut) == PlainSignature(
  ...     Parameter(annotation=typing.IO[typing.AnyStr],
  ...               has_default=False,
  ...               kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
  ...               name='outfile'),
  ...     returns=Self
  ... )
  True
  
  ```
- user-defined classes methods
  ```python
  >>> signature_from_callable(UpperOut.write) == PlainSignature(
  ...     Parameter(annotation=typing.Any,
  ...               has_default=False,
  ...               kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
  ...               name='self'),
  ...     Parameter(annotation=typing.AnyStr,
  ...               has_default=False,
  ...               kind=Parameter.Kind.POSITIONAL_OR_KEYWORD,
  ...               name='s'),
  ...     returns=None
  ... )
  True
  
  ```
- built-in functions
  ```python
  >>> signature_from_callable(any) == PlainSignature(
  ...     Parameter(annotation=typing.Iterable[object],
  ...               has_default=False,
  ...               kind=Parameter.Kind.POSITIONAL_ONLY,
  ...               name='__iterable'),
  ...     returns=bool
  ... )
  True
  
  ```
- built-in classes
  ```python
  >>> signature_from_callable(bool) == PlainSignature(
  ...     Parameter(annotation=object,
  ...               has_default=True,
  ...               kind=Parameter.Kind.POSITIONAL_ONLY,
  ...               name='__o'),
  ...     returns=Self
  ... )
  True
  
  ```
- built-in classes methods
  ```python
  >>> signature_from_callable(float.hex) == PlainSignature(
  ...     Parameter(annotation=Self,
  ...               has_default=False,
  ...               kind=Parameter.Kind.POSITIONAL_ONLY,
  ...               name='self'),
  ...     returns=str
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
