import sys as _sys
from collections.abc import (
    Iterator as _Iterator,
    Mapping as _Mapping,
    Sequence as _Sequence,
)
from types import ModuleType

from . import (
    catalog as _catalog,
    index as _index,
    scoping as _scoping,
    stubs as _stubs,
)


class _State(
    _Mapping[
        _catalog.Path,
        _Mapping[_catalog.Path, _Sequence[_catalog.QualifiedPath]],
    ]
):
    def __getitem__(
        self, module_path: _catalog.Path, /
    ) -> _Mapping[_catalog.Path, _Sequence[_catalog.QualifiedPath]]:
        try:
            return self._inner[module_path]
        except KeyError as error:
            module_name = _catalog.path_to_string(module_path)
            try:
                module = _sys.modules[module_name]
            except KeyError:
                raise error from None
            _process_module(
                module,
                self._inner,
                self._definitions,
                self._references,
                self._submodules,
                self._superclasses,
            )
            return self._inner[module_path]

    def __init__(
        self,
        definitions: _Mapping[_catalog.Path, _scoping.Scope],
        references: _Mapping[_catalog.Path, _scoping.ModuleReferences],
        submodules: _Mapping[_catalog.Path, _scoping.ModuleSubmodules],
        superclasses: _Mapping[_catalog.Path, _scoping.ModuleSuperclasses],
        /,
    ) -> None:
        (
            self._definitions,
            self._references,
            self._submodules,
            self._superclasses,
        ) = definitions, references, submodules, superclasses
        self._inner: dict[
            _catalog.Path, dict[_catalog.Path, list[_catalog.QualifiedPath]]
        ] = {}

    def __iter__(self, /) -> _Iterator[_catalog.Path]:
        return iter(self._inner)

    def __len__(self, /) -> int:
        return len(self._inner)


def _process_module(
    module: ModuleType,
    state: dict[
        _catalog.Path, dict[_catalog.Path, list[_catalog.QualifiedPath]]
    ],
    definitions: _Mapping[_catalog.Path, _scoping.Scope],
    references: _Mapping[_catalog.Path, _scoping.ModuleReferences],
    submodules: _Mapping[_catalog.Path, _scoping.ModuleSubmodules],
    superclasses: _Mapping[_catalog.Path, _scoping.ModuleSuperclasses],
    /,
) -> None:
    module_index = _index.from_module(module)
    for module_path, module_qualified_paths in module_index.items():
        supported_module_qualified_paths = state.setdefault(module_path, {})
        for (
            object_path,
            object_qualified_paths,
        ) in module_qualified_paths.items():
            if (
                len(
                    supported_object_qualified_paths := [
                        (located_module_path, located_object_path)
                        for (
                            located_module_path,
                            located_object_path,
                        ) in object_qualified_paths
                        if _scoping.contains_object_path(
                            located_module_path,
                            (),
                            located_object_path,
                            definitions,
                            references,
                            submodules,
                            superclasses,
                        )
                    ]
                )
                > 0
            ):
                supported_module_qualified_paths.setdefault(
                    object_path, []
                ).extend(supported_object_qualified_paths)


supported_stdlib_qualified_paths = _State(
    _stubs.definitions,
    _stubs.references,
    _stubs.submodules,
    _stubs.superclasses,
)
