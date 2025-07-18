from __future__ import annotations

import ast as _ast
import builtins as _builtins
import sys
import typing as _typing
from collections.abc import (
    Callable as _Callable,
    Collection as _Collection,
    Iterator as _Iterator,
    Mapping as _Mapping,
    Sequence as _Sequence,
)
from copy import deepcopy as _deepcopy
from functools import singledispatch as _singledispatch
from importlib import import_module as _import_module
from itertools import chain as _chain
from pathlib import Path as _Path
from typing import (
    Any as _Any,
    Final as _Final,
    NamedTuple as _NamedTuple,
    TypeAlias as _TypeAlias,
    TypeGuard as _TypeGuard,
    TypeVar as _TypeVar,
)

import mypy as _mypy
import typing_extensions as _typing_extensions
from mypy.version import __version__ as _mypy_version
from typing_extensions import override as _override

import paradigm
from paradigm import __version__ as _version

from . import (
    caching as _caching,
    catalog as _catalog,
    file_system as _file_system,
    namespacing as _namespacing,
    scoping as _scoping,
    sources as _sources,
)
from .arboreal import construction as _construction, conversion as _conversion
from .arboreal.execution import execute_statement as _execute_statement
from .arboreal.kind import StatementNodeKind as _StatementNodeKind
from .arboreal.utils import (
    is_dependency_name as _is_dependency_name,
    recursively_iterate_children as _recursively_iterate_children,
    subscript_to_item as _subscript_to_item,
    to_parent_module_path as _to_parent_module_path,
)
from .sources import stubs_stdlib_modules_paths as _stdlib_modules_paths
from .utils import MISSING as _MISSING, Missing as _Missing

_CACHE_ROOT_DIRECTORY_NAME_PREFIX: _Final[str] = (
    '_'
    + _mypy.__name__
    + '_'
    + _mypy_version.replace('.', '_')
    + '_'
    + sys.platform
    + '_'
    + sys.implementation.name
    + '_'
    + '_'.join(map(str, sys.version_info))
)
_CACHE_ROOT_DIRECTORY_PATH: _Final[_Path] = (
    _Path.home()
    / '.cache'
    / paradigm.__name__
    / (_CACHE_ROOT_DIRECTORY_NAME_PREFIX + '_' + _Path(__file__).stem)
)
_CACHE_ROOT_DIRECTORY_PATH.mkdir(exist_ok=True, parents=True)


class _GenericFieldName:
    CLASSES_BASES_RAW_NODES = 'classes_bases_raw_nodes'
    DEFINITIONS = 'definitions'
    GENERICS_PARAMETERS_PATHS = 'generics_parameters_paths'
    RAW_STATEMENTS_NODES = 'raw_statements_nodes'
    RAW_STATEMENTS_NODES_KINDS = 'raw_statements_nodes_kinds'
    REFERENCES = 'references'
    SUBMODULES = 'submodules'
    VERSION = 'version'


class _SpecializedFieldName:
    DEFINITIONS = 'definitions'
    REFERENCES = 'references'
    SPECIALIZATIONS_RAW_STATEMENTS_NODES = (
        'specializations_raw_statements_nodes'
    )
    SPECIALIZATIONS_RAW_STATEMENTS_NODES_KINDS = (
        'specializations_raw_statements_nodes_kinds'
    )
    SUPERCLASSES = 'superclasses'
    VERSION = 'version'


_ObjectStatementsNodes: _TypeAlias = list[_ast.stmt]
_ModuleRawNodes: _TypeAlias = dict[_catalog.Path, list[_conversion.RawNode]]
_ModuleReferences: _TypeAlias = dict[_catalog.Path, _catalog.QualifiedPath]
_ModuleStatementsNodes: _TypeAlias = dict[
    _catalog.Path, _ObjectStatementsNodes
]
_ModuleStatementsNodesKinds: _TypeAlias = dict[
    _catalog.Path, _StatementNodeKind
]
_ModuleSubmodules: _TypeAlias = list[_catalog.Path]
_ModuleSuperclasses: _TypeAlias = dict[
    _catalog.Path, list[_catalog.QualifiedPath]
]
_ScopeDefinitions: _TypeAlias = dict[str, '_ScopeDefinitions']


def _named_tuple_to_constructor_node(
    node: _ast.ClassDef, /
) -> _ast.FunctionDef:
    annotations_nodes: list[_ast.AnnAssign] = [
        child_node
        for child_node in node.body
        if isinstance(child_node, _ast.AnnAssign)
    ]
    assert all(
        isinstance(node.target, _ast.Name) for node in annotations_nodes
    ), node
    return _construct_function_def(
        '__new__',
        _annotations_to_signature(annotations_nodes),
        [_ast.Expr(_ast.Constant(Ellipsis))],
        [],
        _ast.Name(node.name, _ast.Load()),
    )


if sys.version_info >= (3, 12) and sys.version_info < (3, 13):

    def _construct_function_def(
        name: str,
        args: _ast.arguments,
        body: list[_ast.stmt],
        decorator_list: list[_ast.expr],
        returns: _ast.expr,
        /,
    ) -> _ast.FunctionDef:
        return _ast.FunctionDef(
            name, args, body, decorator_list, returns, None, []
        )
else:

    def _construct_function_def(
        name: str,
        args: _ast.arguments,
        body: list[_ast.stmt],
        decorator_list: list[_ast.expr],
        returns: _ast.expr,
        /,
    ) -> _ast.FunctionDef:
        return _ast.FunctionDef(name, args, body, decorator_list, returns)


def _annotations_to_signature(
    nodes: _Sequence[_ast.AnnAssign], /
) -> _ast.arguments:
    return _ast.arguments(
        [],
        [_ast.arg('cls', None)] + [_ann_assign_to_arg(node) for node in nodes],
        None,
        [],
        [],
        None,
        [node.value for node in nodes if node.value is not None],
    )


def _ann_assign_to_arg(node: _ast.AnnAssign, /) -> _ast.arg:
    assert isinstance(node.target, _ast.Name), node
    return _ast.arg(node.target.id, node.annotation)


def _evaluate_expression(
    node: _ast.expr,
    /,
    *,
    source_path: _Path,
    namespace: _namespacing.Namespace,
) -> _Any:
    # to avoid name conflicts
    # we're using name that won't be present
    # because it'll lead to ``SyntaxError`` otherwise
    # and no AST will be generated
    temporary_name = '@tmp'
    assignment = _expression_to_assignment(node, name=temporary_name)
    _execute_statement(
        assignment, source_path=source_path, namespace=namespace
    )
    return namespace.pop(temporary_name)


def _expression_to_assignment(node: _ast.expr, /, *, name: str) -> _ast.Assign:
    name_node = _ast.copy_location(_ast.Name(name, _ast.Store()), node)
    return _ast.copy_location(_ast.Assign([name_node], node), node)


def _is_generic_specialization(
    base_node: _ast.expr, /
) -> _TypeGuard[_ast.Subscript]:
    return isinstance(base_node, _ast.Subscript)


_T = _TypeVar('_T')
_T_co = _TypeVar('_T_co', covariant=True)


class _LazyMappingWrapper(_Mapping[_catalog.Path, _T_co]):
    def __getitem__(self, module_path: _catalog.Path, /) -> _T_co:
        try:
            return self._wrapped[module_path]
        except KeyError as error:
            try:
                source_path = _sources.from_module_path(module_path)
            except _sources.NotFound:
                raise error from None
            self._loader(source_path, module_path, self._state)
            return self._wrapped[module_path]

    def __init__(
        self,
        wrapped: _Mapping[_catalog.Path, _T_co],
        /,
        *,
        loader: _Callable[[_sources.Path, _catalog.Path, _State], _Any],
        state: _State,
    ) -> None:
        self._loader, self._state, self._wrapped = loader, state, wrapped

    def __iter__(self, /) -> _Iterator[_catalog.Path]:
        return iter(self._wrapped)

    def __len__(self, /) -> int:
        return len(self._wrapped)


def _to_specializations_module_path(
    parent_module_path: _catalog.Path, /
) -> _catalog.Path:
    return _catalog.join_components(parent_module_path, '__specializations')


class _State:
    all_modules_paths: _Collection[_catalog.Path]
    generics_parameters_paths: dict[
        _catalog.Path, dict[_catalog.Path, tuple[_catalog.Path, ...]]
    ]
    modules_classes_bases_nodes: dict[
        _catalog.Path, dict[_catalog.Path, list[_ast.expr]]
    ]
    modules_definitions: dict[_catalog.Path, _ScopeDefinitions]
    modules_references: dict[_catalog.Path, _ModuleReferences]
    modules_statements_nodes: dict[_catalog.Path, _ModuleStatementsNodes]
    modules_statements_nodes_kinds: dict[
        _catalog.Path, _ModuleStatementsNodesKinds
    ]
    modules_submodules: dict[_catalog.Path, _ModuleSubmodules]
    modules_superclasses: dict[_catalog.Path, _ModuleSuperclasses]

    def __init__(
        self, all_modules_paths: _Collection[_catalog.Path], /
    ) -> None:
        self.all_modules_paths = all_modules_paths
        self.generics_parameters_paths = {}
        self.modules_classes_bases_nodes = {}
        self.modules_definitions = {}
        self.modules_references = {}
        self.modules_statements_nodes = {}
        self.modules_statements_nodes_kinds = {}
        self.modules_submodules = {}
        self.modules_superclasses = {}
        builtins_module_path = _catalog.module_path_from_module(_builtins)
        _process_module(
            _sources.from_module_path(builtins_module_path),
            builtins_module_path,
            self,
        )


class _StateParser(_ast.NodeVisitor):
    def __init__(
        self,
        module_path: _catalog.Path,
        parent_path: _catalog.Path,
        source_path: _Path,
        scope: _ScopeDefinitions,
        module_nodes: _ModuleStatementsNodes,
        module_nodes_kinds: _ModuleStatementsNodesKinds,
        module_references: _ModuleReferences,
        state: _State,
        /,
    ) -> None:
        (
            self.module_nodes,
            self.module_nodes_kinds,
            self.module_path,
            self.module_references,
            self.parent_path,
            self.scope,
            self.source_path,
            self.state,
        ) = (
            module_nodes,
            module_nodes_kinds,
            module_path,
            module_references,
            parent_path,
            scope,
            source_path,
            state,
        )

    @_override
    def visit_AnnAssign(self, node: _ast.AnnAssign) -> None:
        target_path = _conversion.to_path(node.target)
        value_node = node.value
        value_path = (
            None
            if value_node is None
            else _conversion.to_maybe_path(value_node)
        )
        if value_path is None:
            self._add_statement_node(target_path, node)
            self._add_statement_node_kind(
                target_path, _StatementNodeKind.ANNOTATED_ASSIGNMENT
            )
            self._add_path_definition(target_path)
        else:
            value_module_path, value_object_path = self._to_qualified_path(
                value_path
            )
            self._add_reference(
                target_path, value_module_path, value_object_path
            )

    @_override
    def visit_Assign(self, node: _ast.Assign) -> None:
        value_path = _conversion.to_maybe_path(node.value)
        if value_path is None:
            for target in node.targets:
                target_path = _conversion.to_path(target)
                self._add_statement_node(target_path, node)
                self._add_statement_node_kind(
                    target_path, _StatementNodeKind.ASSIGNMENT
                )
                self._add_path_definition(target_path)
        else:
            value_module_path, value_object_path = self._to_qualified_path(
                value_path
            )
            for target in node.targets:
                target_path = _conversion.to_path(target)
                self._add_reference(
                    target_path, value_module_path, value_object_path
                )

    @_override
    def visit_AsyncFunctionDef(self, node: _ast.AsyncFunctionDef) -> None:
        function_name = node.name
        self._add_statement_node((function_name,), node)
        self._add_statement_node_kind(
            (function_name,), _StatementNodeKind.ASYNC_FUNCTION
        )
        self._add_name_definition(function_name)

    @_override
    def visit_ClassDef(
        self,
        node: _ast.ClassDef,
        *,
        generic_object_path: _catalog.Path = ('Generic',),
        protocol_object_path: _catalog.Path = ('Protocol',),
        named_tuple_object_path: _catalog.Path = _catalog.path_from_string(  # noqa: B008
            _NamedTuple.__qualname__
        ),
        typing_module_path: _catalog.Path = (
            _catalog.module_path_from_module(_typing)  # noqa: B008
        ),
        typing_extensions_module_path: _catalog.Path = (
            _catalog.module_path_from_module(_typing_extensions)  # noqa: B008
        ),
    ) -> None:
        class_name = node.name
        self._add_statement_node_kind((class_name,), _StatementNodeKind.CLASS)
        self._add_name_definition(class_name)
        class_object_path, module_path = (
            _catalog.join_components(self.parent_path, class_name),
            self.module_path,
        )
        class_bases_nodes = _set_absent_key(
            self.state.modules_classes_bases_nodes.setdefault(module_path, {}),
            class_object_path,
            [],
        )
        type_vars_local_paths = []
        for base_node in node.bases:
            if _is_generic_specialization(base_node):
                type_args_maybe_objects_paths = [
                    _conversion.to_maybe_path(argument)
                    for argument in _collect_type_args(base_node)
                ]
                type_vars_local_paths += [
                    maybe_object_path
                    for maybe_object_path in type_args_maybe_objects_paths
                    if (
                        maybe_object_path is not None
                        and self._is_type_var_object_path(maybe_object_path)
                    )
                ]
                base_origin_maybe_object_path = _conversion.to_maybe_path(
                    base_node.value
                )
                if base_origin_maybe_object_path is not None and (
                    self._resolve_object_path(base_origin_maybe_object_path)
                    in [
                        (typing_module_path, generic_object_path),
                        (typing_module_path, protocol_object_path),
                        (typing_extensions_module_path, protocol_object_path),
                    ]
                ):
                    continue
            else:
                base_reference_path = _conversion.to_path(base_node)
                assert base_reference_path is not None, (
                    module_path,
                    class_object_path,
                )
                base_module_path, base_object_path = self._to_qualified_path(
                    base_reference_path
                )
                if (
                    base_module_path == typing_module_path
                    and base_object_path == named_tuple_object_path
                ):
                    constructor_node = _named_tuple_to_constructor_node(node)
                    self._add_statement_node((class_name,), constructor_node)
                if (
                    base_module_path
                    in (typing_module_path, typing_extensions_module_path)
                ) and base_object_path == protocol_object_path:
                    continue
                assert not (
                    base_module_path == typing_module_path
                    and base_object_path == generic_object_path
                ), (module_path, class_object_path)
            class_bases_nodes.append(base_node)
        generic_parameters = tuple(dict.fromkeys(type_vars_local_paths))
        if generic_parameters:
            _set_absent_key(
                self.state.generics_parameters_paths.setdefault(
                    module_path, {}
                ),
                class_object_path,
                generic_parameters,
            )
        parse_child = _StateParser(
            module_path,
            class_object_path,
            self.source_path,
            self.scope[class_name],
            self.module_nodes,
            self.module_nodes_kinds,
            self.module_references,
            self.state,
        ).visit
        for child in node.body:
            parse_child(child)

    @_override
    def visit_FunctionDef(self, node: _ast.FunctionDef) -> None:
        function_name = node.name
        self._add_statement_node((function_name,), node)
        self._add_statement_node_kind(
            (function_name,), _StatementNodeKind.FUNCTION
        )
        self._add_name_definition(function_name)

    @_override
    def visit_If(self, node: _ast.If) -> None:
        namespace: _namespacing.Namespace = {}
        for dependency_name in {
            child.id
            for child in _recursively_iterate_children(node.test)
            if _is_dependency_name(child)
        }:
            module_path, object_path = self._resolve_object_path(
                (dependency_name,)
            )
            module = _import_module(_catalog.path_to_string(module_path))
            namespace[dependency_name] = (
                _namespacing.search(module, object_path)
                if object_path
                else module
            )
        condition = _evaluate_expression(
            node.test, source_path=self.source_path, namespace=namespace
        )
        for child in node.body if condition else node.orelse:
            self.visit(child)

    @_override
    def visit_Import(self, node: _ast.Import) -> None:
        for alias in node.names:
            module_path = _catalog.path_from_string(alias.name)
            if alias.asname is None:
                sub_module_path: _catalog.Path = ()
                for module_name_part in module_path:
                    sub_module_path = _catalog.join_components(
                        sub_module_path, module_name_part
                    )
                    self._add_reference(sub_module_path, sub_module_path, ())
            else:
                self._add_reference((alias.asname,), module_path, ())

    @_override
    def visit_ImportFrom(self, node: _ast.ImportFrom) -> None:
        parent_module_path = _to_parent_module_path(
            node, parent_module_path=self.module_path
        )
        for alias in node.names:
            if alias.name == '*':
                self._add_submodule(parent_module_path)
            else:
                actual_object_name = alias.name
                self._add_reference(
                    (alias.asname or actual_object_name,),
                    parent_module_path,
                    (actual_object_name,),
                )

    def _add_statement_node(
        self, path: _catalog.Path, node: _ast.stmt, /
    ) -> None:
        self.module_nodes.setdefault(
            _catalog.join_paths(self.parent_path, path), []
        ).append(node)

    def _add_statement_node_kind(
        self, path: _catalog.Path, node_kind: _StatementNodeKind, /
    ) -> None:
        self.module_nodes_kinds[
            _catalog.join_paths(self.parent_path, path)
        ] = node_kind

    def _add_name_definition(self, name: str) -> None:
        assert isinstance(name, str), name
        self.scope.setdefault(name, {})

    def _add_path_definition(self, path: _catalog.Path) -> None:
        scope = self.scope
        for part in path:
            scope = scope.setdefault(part, {})

    def _add_reference(
        self,
        reference_path: _catalog.Path,
        referent_module_path: _catalog.Path,
        referent_object_path: _catalog.Path,
    ) -> None:
        self.module_references[reference_path] = (
            referent_module_path,
            referent_object_path,
        )

    def _add_submodule(self, module_path: _catalog.Path) -> None:
        self.state.modules_submodules.setdefault(self.module_path, []).append(
            module_path
        )

    def _resolve_object_path(
        self, object_path: _catalog.Path
    ) -> _catalog.QualifiedPath:
        return _resolve_object_path(
            self.source_path,
            self.module_path,
            self.parent_path,
            object_path,
            self.state,
        )

    def _to_qualified_path(
        self, object_path: _catalog.Path
    ) -> _catalog.QualifiedPath:
        try:
            return self._resolve_object_path(object_path)
        except _ObjectNotFound:
            self._add_path_definition(object_path)
            return (self.module_path, object_path)

    def _is_type_var_object_path(
        self,
        object_path: _catalog.Path,
        /,
        *,
        type_var_object_path: _catalog.Path = _catalog.path_from_string(  # noqa: B008
            _TypeVar.__qualname__
        ),
        typing_module_path: _catalog.Path = (
            _catalog.module_path_from_module(  # noqa: B008
                _typing
            )
        ),
    ) -> bool:
        module_path, object_path = self._to_qualified_path(object_path)
        source_path = _sources.from_module_path(module_path)
        _parse_module_scope(source_path, module_path, self.state)
        module_nodes = self.state.modules_statements_nodes[module_path]
        nodes = module_nodes.get(object_path, [])
        if len(nodes) != 1:
            return False
        (node,) = nodes
        if not (
            isinstance(node, _ast.AnnAssign | _ast.Assign)
            and isinstance(node.value, _ast.Call)
        ):
            return False
        callable_maybe_object_path = _conversion.to_maybe_path(node.value.func)
        if callable_maybe_object_path is None:
            return False
        callable_module_path, callable_object_path = _resolve_object_path(
            source_path,
            module_path,
            (),
            callable_maybe_object_path,
            self.state,
        )
        return (
            callable_module_path == typing_module_path
            and callable_object_path == type_var_object_path
        )


class _ObjectNotFound(Exception):
    pass


def _resolve_object_path(
    source_path: _sources.Path,
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    object_path: _catalog.Path,
    state: _State,
    /,
    *,
    _builtins_module_path: _catalog.Path = (
        _catalog.module_path_from_module(  # noqa: B008
            _builtins
        )
    ),
) -> _catalog.QualifiedPath:
    first_name = object_path[0]
    module_definitions = _parse_module_scope(source_path, module_path, state)
    if _scoping.scope_contains_path(
        module_definitions, _catalog.join_components(parent_path, first_name)
    ):
        return module_path, _catalog.join_paths(parent_path, object_path)
    if first_name in module_definitions:
        return module_path, object_path
    for sub_module_path in state.modules_submodules.get(module_path, []):
        try:
            return _resolve_object_path(
                _sources.from_module_path(sub_module_path),
                sub_module_path,
                (),
                object_path,
                state,
            )
        except _ObjectNotFound:
            continue
    module_references = state.modules_references[module_path]
    for offset in range(len(object_path)):
        sub_object_path = object_path[: len(object_path) - offset]
        try:
            referent_module_name, referent_object_path = module_references[
                sub_object_path
            ]
        except KeyError:
            continue
        else:
            return (
                referent_module_name,
                _catalog.join_paths(
                    referent_object_path,
                    object_path[len(object_path) - offset :],
                ),
            )
    if _scoping.scope_contains_path(
        state.modules_definitions[_builtins_module_path], object_path
    ):
        return _builtins_module_path, object_path
    raise _ObjectNotFound(object_path)


def _parse_module_scope(
    source_path: _sources.Path,
    module_path: _catalog.Path,
    state: _State,
    /,
    *,
    cache_directory_path: _Path = _CACHE_ROOT_DIRECTORY_PATH / 'generic',
) -> _ScopeDefinitions:
    if (
        module_definitions := state.modules_definitions.get(
            module_path, _MISSING
        )
    ) is not _MISSING:
        assert not isinstance(module_definitions, _Missing)
        return module_definitions
    if source_path.stem == _file_system.INIT_MODULE_NAME:
        package_directory_path = cache_directory_path.joinpath(*module_path)
        package_directory_path.mkdir(exist_ok=True, parents=True)
        cache_file_path = package_directory_path / (
            f'{_file_system.INIT_MODULE_NAME}{_file_system.MODULE_FILE_SUFFIX}'
        )
    else:
        package_directory_path = cache_directory_path.joinpath(
            *module_path[:-1]
        )
        package_directory_path.mkdir(exist_ok=True, parents=True)
        cache_file_path = (
            package_directory_path
            / f'{module_path[-1]}{_file_system.MODULE_FILE_SUFFIX}'
        )
    module_classes_bases_raw_nodes: _ModuleRawNodes
    module_raw_statements_nodes: _ModuleRawNodes
    try:
        (
            module_classes_bases_raw_nodes,
            module_definitions,
            module_generics_parameters_paths,
            module_raw_statements_nodes,
            module_raw_statements_nodes_kinds,
            module_references,
            module_submodules,
            cached_version,
        ) = _caching.load(
            cache_file_path,
            _GenericFieldName.CLASSES_BASES_RAW_NODES,
            _GenericFieldName.DEFINITIONS,
            _GenericFieldName.GENERICS_PARAMETERS_PATHS,
            _GenericFieldName.RAW_STATEMENTS_NODES,
            _GenericFieldName.RAW_STATEMENTS_NODES_KINDS,
            _GenericFieldName.REFERENCES,
            _GenericFieldName.SUBMODULES,
            _GenericFieldName.VERSION,
        )
    except Exception:
        pass
    else:
        if cached_version == _version:
            _set_absent_key(
                state.modules_classes_bases_nodes,
                module_path,
                {
                    class_object_path: [
                        _construction.from_raw(raw_node, cls=_ast.expr)
                        for raw_node in class_bases_raw_nodes
                    ]
                    for class_object_path, class_bases_raw_nodes in (
                        module_classes_bases_raw_nodes.items()
                    )
                },
            )
            _set_absent_key(
                state.modules_definitions, module_path, module_definitions
            )
            _set_absent_key(
                state.generics_parameters_paths,
                module_path,
                module_generics_parameters_paths,
            )
            _set_absent_key(
                state.modules_references, module_path, module_references
            )
            _set_absent_key(
                state.modules_statements_nodes,
                module_path,
                {
                    object_path: [
                        _construction.from_raw(raw_node, cls=_ast.stmt)
                        for raw_node in raw_nodes
                    ]
                    for object_path, raw_nodes in (
                        module_raw_statements_nodes.items()
                    )
                },
            )
            _set_absent_key(
                state.modules_statements_nodes_kinds,
                module_path,
                {
                    object_path: _StatementNodeKind(raw_node_kind)
                    for object_path, raw_node_kind in (
                        module_raw_statements_nodes_kinds.items()
                    )
                },
            )
            _set_absent_key(
                state.modules_submodules, module_path, module_submodules
            )
            assert isinstance(module_definitions, dict), module_definitions
            return module_definitions
    (
        module_definitions,
        module_references,
        module_statements_nodes,
        module_statements_nodes_kinds,
    ) = _init_module_state(state, module_path)
    root_node = _construction.from_source_path(source_path)
    _StateParser(
        module_path,
        (),
        source_path,
        module_definitions,
        module_statements_nodes,
        module_statements_nodes_kinds,
        module_references,
        state,
    ).visit(root_node)
    _caching.save(
        cache_file_path,
        **{
            _GenericFieldName.CLASSES_BASES_RAW_NODES: {
                class_object_path: [
                    _conversion.to_raw(node) for node in bases_nodes
                ]
                for class_object_path, bases_nodes in (
                    state.modules_classes_bases_nodes.get(
                        module_path, {}
                    ).items()
                )
            },
            _GenericFieldName.DEFINITIONS: module_definitions,
            _GenericFieldName.GENERICS_PARAMETERS_PATHS: (
                state.generics_parameters_paths.get(module_path, {})
            ),
            _GenericFieldName.RAW_STATEMENTS_NODES: {
                object_path: [_conversion.to_raw(node) for node in nodes]
                for object_path, nodes in module_statements_nodes.items()
            },
            _GenericFieldName.RAW_STATEMENTS_NODES_KINDS: (
                module_statements_nodes_kinds
            ),
            _GenericFieldName.REFERENCES: module_references,
            _GenericFieldName.SUBMODULES: state.modules_submodules.get(
                module_path, []
            ),
            _GenericFieldName.VERSION: _version,
        },
    )
    return module_definitions


def _init_module_state(
    state: _State, module_path: _catalog.Path, /
) -> tuple[
    _ScopeDefinitions,
    _ModuleReferences,
    _ModuleStatementsNodes,
    _ModuleStatementsNodesKinds,
]:
    return (
        _set_absent_key(state.modules_definitions, module_path, {}),
        _set_absent_key(state.modules_references, module_path, {}),
        _set_absent_key(state.modules_statements_nodes, module_path, {}),
        _set_absent_key(state.modules_statements_nodes_kinds, module_path, {}),
    )


@_singledispatch
def _unpack_node(node: _ast.expr, /) -> tuple[_ast.expr, ...]:
    return (node,)


@_unpack_node.register(_ast.Tuple)
def _(node: _ast.Tuple, /) -> tuple[_ast.expr, ...]:
    assert isinstance(node.ctx, _ast.Load), node
    return tuple(node.elts)


def _collect_type_args(node: _ast.expr, /) -> list[_ast.expr]:
    if _is_generic_specialization(node):
        queue = [_subscript_to_item(node)]
        args: list[_ast.expr] = []
        while queue:
            specialization_node = queue.pop()
            candidates = _unpack_node(specialization_node)
            for candidate in reversed(candidates):
                if _is_generic_specialization(candidate):
                    queue.append(_subscript_to_item(candidate))
                else:
                    args.append(candidate)
        return args[::-1]
    return []


class _SpecializeGeneric(_ast.NodeTransformer):
    def __init__(self, table: dict[_catalog.Path, _ast.expr]) -> None:
        self.table = table

    def visit_Name(self, node: _ast.Name) -> _ast.expr:
        if not isinstance(node.ctx, _ast.Load):
            return node
        candidate = self.table.get(_conversion.to_path(node))
        return (
            node
            if candidate is None
            else _ast.copy_location(_deepcopy(candidate), node)
        )

    def visit_Attribute(self, node: _ast.Attribute) -> _ast.expr:
        if not isinstance(node.ctx, _ast.Load):
            return node
        candidate = self.table.get(_conversion.to_path(node))
        return (
            node
            if candidate is None
            else _ast.copy_location(_deepcopy(candidate), node)
        )


def _parse_modules_state(
    modules_paths: _Collection[_catalog.Path], /
) -> tuple[
    _Mapping[_catalog.Path, _ScopeDefinitions],
    _Mapping[_catalog.Path, _ModuleReferences],
    _Mapping[_catalog.Path, _ModuleStatementsNodes],
    _Mapping[_catalog.Path, _ModuleStatementsNodesKinds],
    _Mapping[_catalog.Path, _ModuleSubmodules],
    _Mapping[_catalog.Path, _ModuleSuperclasses],
]:
    state = _State(modules_paths)
    return (
        _LazyMappingWrapper(
            state.modules_definitions, loader=_parse_module_scope, state=state
        ),
        _LazyMappingWrapper(
            state.modules_references, loader=_parse_module_scope, state=state
        ),
        _LazyMappingWrapper(
            state.modules_statements_nodes,
            loader=_parse_module_scope,
            state=state,
        ),
        _LazyMappingWrapper(
            state.modules_statements_nodes_kinds,
            loader=_parse_module_scope,
            state=state,
        ),
        _LazyMappingWrapper(
            state.modules_submodules, loader=_parse_module_scope, state=state
        ),
        _LazyMappingWrapper(
            state.modules_superclasses, loader=_process_module, state=state
        ),
    )


def _process_module(
    source_path: _sources.Path, module_path: _catalog.Path, state: _State, /
) -> None:
    parsing_queue = {module_path: source_path}
    parsed_module_paths = set()
    while parsing_queue:
        dependency_module_path, dependency_source_path = (
            parsing_queue.popitem()
        )
        if dependency_module_path in parsed_module_paths:
            continue
        _parse_module_scope(
            dependency_source_path, dependency_module_path, state
        )
        parsed_module_paths.add(dependency_module_path)
        parsing_queue.update(
            _chain.from_iterable(
                (
                    (
                        referent_module_path,
                        _sources.from_module_path(referent_module_path),
                    ),
                    *(
                        (
                            (
                                referent_object_full_path,
                                _sources.from_module_path(
                                    referent_object_full_path
                                ),
                            ),
                        )
                        if (
                            (
                                referent_object_full_path := (
                                    _catalog.join_paths(
                                        referent_module_path,
                                        referent_object_path,
                                    )
                                )
                            )
                            in state.all_modules_paths
                        )
                        else ()
                    ),
                )
                for referent_module_path, referent_object_path in (
                    state.modules_references[dependency_module_path].values()
                )
            )
        )
        parsing_queue.update(
            (
                referent_module_path,
                _sources.from_module_path(referent_module_path),
            )
            for referent_module_path in state.modules_submodules.get(
                dependency_module_path, []
            )
        )
    _process_module_superclasses(
        source_path,
        module_path,
        state.modules_classes_bases_nodes.get(module_path, {}),
        state,
    )


def _process_module_superclasses(
    source_path: _sources.Path,
    module_path: _catalog.Path,
    module_classes_bases_nodes: dict[_catalog.Path, list[_ast.expr]],
    state: _State,
    /,
    *,
    cache_directory_path: _Path = _CACHE_ROOT_DIRECTORY_PATH / 'specialized',
) -> None:
    if state.modules_superclasses.get(module_path, _MISSING) is not _MISSING:
        return
    if source_path.stem == _file_system.INIT_MODULE_NAME:
        package_directory_path = cache_directory_path.joinpath(*module_path)
        package_directory_path.mkdir(exist_ok=True, parents=True)
        cache_file_path = package_directory_path / (
            f'{_file_system.INIT_MODULE_NAME}{_file_system.MODULE_FILE_SUFFIX}'
        )
    else:
        package_directory_path = cache_directory_path.joinpath(
            *module_path[:-1]
        )
        package_directory_path.mkdir(exist_ok=True, parents=True)
        cache_file_path = (
            package_directory_path
            / f'{module_path[-1]}{_file_system.MODULE_FILE_SUFFIX}'
        )
    specializations_scope_name = '@specializations'
    specializations_raw_statements_nodes: dict[
        _catalog.Path, list[_conversion.RawNode]
    ]
    try:
        (
            specializations_definitions,
            specializations_raw_statements_nodes,
            specializations_raw_statements_nodes_kinds,
            module_references,
            module_superclasses,
            cached_version,
        ) = _caching.load(
            cache_file_path,
            _SpecializedFieldName.DEFINITIONS,
            _SpecializedFieldName.SPECIALIZATIONS_RAW_STATEMENTS_NODES,
            _SpecializedFieldName.SPECIALIZATIONS_RAW_STATEMENTS_NODES_KINDS,
            _SpecializedFieldName.REFERENCES,
            _SpecializedFieldName.SUPERCLASSES,
            _SpecializedFieldName.VERSION,
        )
    except Exception:
        pass
    else:
        if cached_version == _version:
            _set_absent_key(
                state.modules_definitions[module_path],
                specializations_scope_name,
                specializations_definitions,
            )
            state.modules_statements_nodes[module_path].update(
                {
                    object_path: [
                        _construction.from_raw(raw_node, cls=_ast.stmt)
                        for raw_node in raw_nodes
                    ]
                    for object_path, raw_nodes in (
                        specializations_raw_statements_nodes.items()
                    )
                }
            )
            state.modules_statements_nodes_kinds[module_path].update(
                {
                    object_path: _StatementNodeKind(raw_node_kind)
                    for object_path, raw_node_kind in (
                        specializations_raw_statements_nodes_kinds.items()
                    )
                }
            )
            state.modules_references[module_path] = module_references
            _set_absent_key(
                state.modules_superclasses, module_path, module_superclasses
            )
            return
    module_superclasses = _set_absent_key(
        state.modules_superclasses, module_path, {}
    )
    specializations_definitions = _set_absent_key(
        state.modules_definitions[module_path], specializations_scope_name, {}
    )
    _set_absent_key(
        state.modules_statements_nodes_kinds[module_path],
        (specializations_scope_name,),
        _StatementNodeKind.CLASS,
    )
    for (
        class_object_path,
        class_bases_nodes,
    ) in module_classes_bases_nodes.items():
        for base_node in class_bases_nodes:
            base_module_path, base_object_path = _register_base_node(
                base_node,
                module_path,
                class_object_path,
                specializations_scope_name,
                specializations_definitions,
                state,
            )
            module_superclasses.setdefault(class_object_path, []).append(
                (base_module_path, base_object_path)
            )
    _caching.save(
        cache_file_path,
        **{
            _SpecializedFieldName.DEFINITIONS: specializations_definitions,
            _SpecializedFieldName.SPECIALIZATIONS_RAW_STATEMENTS_NODES: (
                {
                    object_path: [_conversion.to_raw(node) for node in nodes]
                    for object_path, nodes in (
                        state.modules_statements_nodes[module_path].items()
                    )
                    if object_path[0] == specializations_scope_name
                }
            ),
            _SpecializedFieldName.SPECIALIZATIONS_RAW_STATEMENTS_NODES_KINDS: (
                {
                    object_path: node_kind
                    for object_path, node_kind in (
                        state.modules_statements_nodes_kinds[
                            module_path
                        ].items()
                    )
                    if object_path[0] == specializations_scope_name
                }
            ),
            _SpecializedFieldName.REFERENCES: state.modules_references[
                module_path
            ],
            _SpecializedFieldName.SUPERCLASSES: module_superclasses,
            _SpecializedFieldName.VERSION: _version,
        },
    )


def _register_base_node(
    base_node: _ast.expr,
    child_module_path: _catalog.Path,
    child_object_path: _catalog.Path,
    specializations_scope_name: str,
    specializations_definitions: _ScopeDefinitions,
    state: _State,
) -> _catalog.QualifiedPath:
    if _is_generic_specialization(base_node):
        base_name = _conversion.to_identifier(base_node)
        base_object_path = (specializations_scope_name, base_name)
        if base_name not in specializations_definitions:
            specialization_args = _unpack_node(_subscript_to_item(base_node))
            generic_object_path = _conversion.to_path(base_node.value)
            generic_module_path, generic_object_path = (
                _scoping.resolve_object_path(
                    child_module_path,
                    child_object_path[:-1],
                    generic_object_path,
                    state.modules_definitions,
                    state.modules_references,
                    state.modules_submodules,
                    state.modules_superclasses,
                )
            )
            generic_parameters_paths = state.generics_parameters_paths[
                generic_module_path
            ][generic_object_path]
            _register_generic_specialization(
                generic_module_path,
                generic_object_path,
                child_module_path,
                base_object_path,
                generic_parameters_paths,
                specialization_args,
                state,
            )
            specialization_table = dict(
                zip(
                    generic_parameters_paths, specialization_args, strict=False
                )
            )
            specialize = _SpecializeGeneric(specialization_table).visit
            generic_bases = state.modules_classes_bases_nodes[
                generic_module_path
            ][generic_object_path]
            for generic_base in generic_bases:
                base_base_module_path: _catalog.Path
                base_base_object_path: _catalog.Path
                if _is_generic_specialization(generic_base):
                    base_base_node = specialize(_deepcopy(generic_base))
                    base_base_name = _conversion.to_identifier(base_base_node)
                    base_base_module_path, base_base_object_path = (
                        child_module_path,
                        (specializations_scope_name, base_base_name),
                    )
                    if base_base_name not in specializations_definitions:
                        generic_base_base_object_path = _conversion.to_path(
                            generic_base.value
                        )
                        (
                            generic_base_base_module_path,
                            generic_base_base_object_path,
                        ) = _scoping.resolve_object_path(
                            generic_module_path,
                            generic_object_path[:-1],
                            generic_base_base_object_path,
                            state.modules_definitions,
                            state.modules_references,
                            state.modules_submodules,
                            state.modules_superclasses,
                        )
                        generic_base_base_parameters_paths = (
                            state.generics_parameters_paths[
                                generic_base_base_module_path
                            ][generic_base_base_object_path]
                        )
                        base_base_specialization_args = _unpack_node(
                            _subscript_to_item(base_base_node)
                        )
                        _register_generic_specialization(
                            generic_base_base_module_path,
                            generic_base_base_object_path,
                            base_base_module_path,
                            base_base_object_path,
                            generic_base_base_parameters_paths,
                            base_base_specialization_args,
                            state,
                        )
                else:
                    base_base_object_path = _conversion.to_path(generic_base)
                    base_base_module_path, base_base_object_path = (
                        _scoping.resolve_object_path(
                            generic_module_path,
                            (),
                            base_base_object_path,
                            state.modules_definitions,
                            state.modules_references,
                            state.modules_submodules,
                            state.modules_superclasses,
                        )
                    )
                state.modules_superclasses.setdefault(
                    child_module_path, {}
                ).setdefault(base_object_path, []).append(
                    (base_base_module_path, base_base_object_path)
                )
        return child_module_path, base_object_path
    base_reference_path = _conversion.to_path(base_node)
    return _scoping.resolve_object_path(
        child_module_path,
        child_object_path[:-1],
        base_reference_path,
        state.modules_definitions,
        state.modules_references,
        state.modules_submodules,
        state.modules_superclasses,
    )


def _register_generic_specialization(
    generic_module_path: _catalog.Path,
    generic_object_path: _catalog.Path,
    specialization_module_path: _catalog.Path,
    specialization_object_path: _catalog.Path,
    generic_parameters_paths: _Sequence[_catalog.Path],
    specialization_args: _Sequence[_ast.expr],
    state: _State,
    builtins_module_path: _catalog.Path = _catalog.module_path_from_module(  # noqa: B008
        _builtins
    ),
) -> None:
    base_scope_definitions = state.modules_definitions[
        specialization_module_path
    ]
    for part in specialization_object_path:
        base_scope_definitions = base_scope_definitions.setdefault(part, {})
    generic_scope = state.modules_definitions[generic_module_path]
    for part in generic_object_path:
        generic_scope = generic_scope[part]
    base_scope_definitions.update(generic_scope)
    generic_module_nodes = state.modules_statements_nodes[generic_module_path]
    _set_absent_key(
        state.modules_statements_nodes_kinds[specialization_module_path],
        specialization_object_path,
        _StatementNodeKind.CLASS,
    )
    specialize = _SpecializeGeneric(
        dict(zip(generic_parameters_paths, specialization_args, strict=False))
    ).visit
    args_names = {
        arg.id for arg in specialization_args if _is_dependency_name(arg)
    } | {
        child.id
        for node in specialization_args
        for child in _recursively_iterate_children(node)
        if _is_dependency_name(child)
    }
    for name in generic_scope:
        generic_field_path = _catalog.join_components(
            generic_object_path, name
        )
        generic_nodes = generic_module_nodes[generic_field_path]
        specialization_field_path = _catalog.join_components(
            specialization_object_path, name
        )
        specialization_nodes = _set_absent_key(
            state.modules_statements_nodes[specialization_module_path],
            specialization_field_path,
            [specialize(_deepcopy(node)) for node in generic_nodes],
        )
        specialization_definitions_names = set(
            _chain.from_iterable(
                _conversion.statement_node_to_defined_names(node)
                for node in specialization_nodes
            )
        )
        for dependency_name in {
            child.id
            for node in specialization_nodes
            for child in _recursively_iterate_children(node)
            if _is_dependency_name(child)
        } - specialization_definitions_names:
            dependency_path = (dependency_name,)
            dependency_module_path, dependency_object_path = (
                _scoping.resolve_object_path(
                    (
                        specialization_module_path
                        if dependency_name in args_names
                        else generic_module_path
                    ),
                    (),
                    dependency_path,
                    state.modules_definitions,
                    state.modules_references,
                    state.modules_submodules,
                    state.modules_superclasses,
                )
            )
            if dependency_module_path != builtins_module_path:
                state.modules_references[specialization_module_path][
                    dependency_path
                ] = (dependency_module_path, dependency_object_path)
        _set_absent_key(
            state.modules_statements_nodes_kinds[specialization_module_path],
            specialization_field_path,
            state.modules_statements_nodes_kinds[generic_module_path][
                generic_field_path
            ],
        )


_KT = _TypeVar('_KT')
_VT = _TypeVar('_VT')


def _set_absent_key(
    destination: dict[_KT, _VT], key: _KT, value: _VT, /
) -> _VT:
    assert key not in destination, (destination[key], value)
    destination[key] = value
    return value


(
    definitions,
    references,
    statements_nodes,
    statements_nodes_kinds,
    submodules,
    superclasses,
) = _parse_modules_state(_stdlib_modules_paths)
