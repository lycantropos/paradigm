paradigm
========

[![](https://travis-ci.org/lycantropos/paradigm.svg?branch=master)](https://travis-ci.org/lycantropos/paradigm "Travis CI")
[![](https://ci.appveyor.com/api/projects/status/github/lycantropos/paradigm?branch=master&svg=true)](https://ci.appveyor.com/project/lycantropos/paradigm "AppVeyor")
[![](https://codecov.io/gh/lycantropos/paradigm/branch/master/graph/badge.svg)](https://codecov.io/gh/lycantropos/paradigm "Codecov")
[![](https://img.shields.io/github/license/lycantropos/paradigm.svg)](https://github.com/lycantropos/paradigm/blob/master/LICENSE "License")
[![](https://badge.fury.io/py/paradigm.svg)](https://badge.fury.io/py/paradigm "PyPI")

In what follows
- `python` is an alias for `python3.5` or any later
version (`python3.6` and so on),
- `pypy` is an alias for `pypy3.5` or any later
version (`pypy3.6` and so on).

Installation
------------

Install the latest `pip` & `setuptools` packages versions:
- with `CPython`
  ```bash
  python -m pip install --upgrade pip setuptools
  ```
- with `PyPy`
  ```bash
  pypy -m pip install --upgrade pip setuptools
  ```

### User

Download and install the latest stable version from `PyPI` repository:
- with `CPython`
  ```bash
  python -m pip install --upgrade paradigm
  ```
- with `PyPy`
  ```bash
  pypy -m pip install --upgrade paradigm
  ```

### Developer

Download the latest version from `GitHub` repository
```bash
git clone https://github.com/lycantropos/paradigm.git
cd paradigm
```

Install:
- with `CPython`
  ```bash
  python setup.py install
  ```
- with `PyPy`
  ```bash
  pypy setup.py install
  ```

Usage
-----

`paradigm` can be used to obtain signature
```python
>>> from paradigm import signatures
```
for user-defined functions
```python
>>> def func(foo, bar=None, **kwargs):
        pass
>>> signatures.factory(func)
Plain(Parameter(name='foo', kind=Parameter.Kind.POSITIONAL_OR_KEYWORD, has_default=False), Parameter(name='bar', kind=Parameter.Kind.POSITIONAL_OR_KEYWORD, has_default=True), Parameter(name='kwargs', kind=Parameter.Kind.VARIADIC_KEYWORD, has_default=False))
```
for user-defined classes
```python
>>> class UpperOut:
        def __init__(self, outfile):
            self._outfile = outfile
    
        def write(self, s):
            self._outfile.write(s.upper())
    
        def __getattr__(self, name):
            return getattr(self._outfile, name)
>>> signatures.factory(UpperOut)
Plain(Parameter(name='outfile', kind=Parameter.Kind.POSITIONAL_OR_KEYWORD, has_default=False))
```
for user-defined classes methods
```python
>>> signatures.factory(UpperOut.write)
Plain(Parameter(name='self', kind=Parameter.Kind.POSITIONAL_OR_KEYWORD, has_default=False), Parameter(name='s', kind=Parameter.Kind.POSITIONAL_OR_KEYWORD, has_default=False))
```
for built-in functions
```python
>>> signatures.factory(any)
# CPython
Plain(Parameter(name='iterable', kind=Parameter.Kind.POSITIONAL_ONLY, has_default=False))
# PyPy
Plain(Parameter(name='seq', kind=Parameter.Kind.POSITIONAL_OR_KEYWORD, has_default=False))
```
for built-in classes
```python
>>> signatures.factory(float)
# CPython
Plain(Parameter(name='x', kind=Parameter.Kind.POSITIONAL_ONLY, has_default=True))
# PyPy
Plain(Parameter(name='x', kind=Parameter.Kind.POSITIONAL_OR_KEYWORD, has_default=True))
```
for built-in classes methods
```python
>>> signatures.factory(float.as_integer_ratio)
# CPython
Plain(Parameter(name='self', kind=Parameter.Kind.POSITIONAL_ONLY, has_default=False))
# PyPy
Plain(Parameter(name='self', kind=Parameter.Kind.POSITIONAL_OR_KEYWORD, has_default=False))
```

Checking if object is supported by `paradigm` can be done with
```python
>>> from paradigm import definitions
>>> definitions.is_supported(int.bit_length)
True
>>> definitions.is_supported(int.conjugate)
False
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

#### Notes

To avoid inconsistency between branches and pull requests,
bumping version should be merged into `master` branch as separate pull
request.

### Running tests

Plain:
- with `CPython`
  ```bash
  python setup.py test
  ```
- with `PyPy`
  ```bash
  pypy setup.py test
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
