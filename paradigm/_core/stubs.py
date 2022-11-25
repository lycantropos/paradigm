import sys as _sys
import typing as _t
from importlib import import_module as _import_module
from itertools import chain
from operator import attrgetter as _attrgetter
from pathlib import Path as _Path

import mypy as _mypy
from mypy.version import __version__ as _mypy_version

from paradigm import __version__ as _version
from . import (catalog as _catalog,
               scoping as _scoping)
from .arboreal import conversion as _serialization
from .arboreal.kind import NodeKind as _NodeKind

_CACHE_PATH = _Path(__file__).with_name(
        '_' + _mypy.__name__ + '_' + _mypy_version.replace('.', '_')
        + '_' + _sys.platform
        + '_' + _sys.implementation.name
        + '_' + '_'.join(map(str, _sys.version_info))
        + '_' + _Path(__file__).name
)
_DEFINITIONS_FIELD_NAME = 'definitions'
_NODES_KINDS_FIELD_NAME = 'nodes_kinds'
_RAW_AST_NODES_FIELD_NAME = 'raw_ast_nodes'
_REFERENCES_FIELD_NAME = 'references'
_SUBMODULES_FIELD_NAME = 'submodules'
_SUPERCLASSES_FIELD_NAME = 'superclasses'
_VERSION_FIELD_NAME = 'version'

ObjectRawAstNodes = _t.List[_serialization.RawAstNode]
_ModuleRawAstNodes = _t.Dict[_catalog.Path, ObjectRawAstNodes]

definitions: _t.Dict[_catalog.Path, _scoping.Scope]
nodes_kinds: _t.Dict[_catalog.Path, _scoping.ModuleAstNodesKinds]
raw_ast_nodes: _t.Dict[_catalog.Path, _ModuleRawAstNodes]
references: _t.Dict[_catalog.Path, _scoping.ModuleReferences]
submodules: _t.Dict[_catalog.Path, _scoping.ModuleSubmodules]
superclasses: _t.Dict[_catalog.Path, _scoping.ModuleSuperclasses]

try:
    (
        definitions, _raw_nodes_kinds, raw_ast_nodes, references, submodules,
        superclasses, _cached_version
    ) = _attrgetter(
            _DEFINITIONS_FIELD_NAME, _NODES_KINDS_FIELD_NAME,
            _RAW_AST_NODES_FIELD_NAME, _REFERENCES_FIELD_NAME,
            _SUBMODULES_FIELD_NAME, _SUPERCLASSES_FIELD_NAME,
            _VERSION_FIELD_NAME
    )(_import_module((''
                      if __name__ in ('__main__', '__mp_main__')
                      else __name__.rsplit('.', maxsplit=1)[
                               0] + '.')
                     + _CACHE_PATH.stem))
except Exception:
    _reload_cache = True
else:
    _reload_cache = _cached_version != _version
    if not _reload_cache:
        nodes_kinds = {
            module_path: {
                object_path: _NodeKind(raw_node_kind)
                for object_path, raw_node_kind in objects_kinds.items()
            }
            for module_path, objects_kinds in _raw_nodes_kinds.items()
        }
if _reload_cache:
    import ast as _ast
    import builtins as _builtins
    from copy import deepcopy as _deepcopy
    from functools import singledispatch as _singledispatch

    from typing_extensions import TypeGuard as _TypeGuard

    from . import (execution as _execution,
                   exporting as _exporting,
                   namespacing as _namespacing,
                   sources as _sources)
    from .arboreal.execution import execute_statement as _execute_statement
    from .arboreal.utils import (
        is_dependency_name,
        recursively_iterate_children as _recursively_iterate_children,
        subscript_to_item as _subscript_to_item,
        to_parent_module_path as _to_parent_module_path
    )
    from .arboreal import (construction as _construction,
                           conversion as _conversion)
    from .sources import stubs_stdlib_modules_paths as _stdlib_modules_paths

    _ObjectAstNodes = _t.List[_ast.AST]
    _ModuleAstNodes = _t.Dict[_catalog.Path, _ObjectAstNodes]
    _ModuleAstNodesKinds = _t.Dict[_catalog.Path, _NodeKind]
    _ModuleReferences = _t.Dict[_catalog.Path, _catalog.QualifiedPath]
    _ModuleSubmodules = _t.List[_catalog.Path]
    _ModuleSuperclasses = _t.Dict[_catalog.Path,
                                  _t.List[_catalog.QualifiedPath]]
    _Scope = _t.Dict[str, dict]


    def _named_tuple_to_constructor_ast_node(
            ast_node: _ast.ClassDef
    ) -> _ast.FunctionDef:
        annotations_ast_nodes: _t.List[_ast.AnnAssign] = [
            ast_child_node
            for ast_child_node in ast_node.body
            if isinstance(ast_child_node, _ast.AnnAssign)
        ]
        assert all(isinstance(ast_node.target, _ast.Name)
                   for ast_node in annotations_ast_nodes), ast_node
        return _ast.FunctionDef(
                '__new__',
                _annotations_to_signature(annotations_ast_nodes),
                [_ast.Expr(_ast.Ellipsis())], [],
                _ast.Name(ast_node.name, _ast.Load())
        )


    if _sys.version_info < (3, 8):
        def _annotations_to_signature(
                ast_nodes: _t.List[_ast.AnnAssign]
        ) -> _ast.arguments:
            return _ast.arguments([_ast.arg('cls', None)]
                                  + [_ann_assign_to_arg(ast_node)
                                     for ast_node in ast_nodes],
                                  None, [], [], None,
                                  [ast_node.value
                                   for ast_node in ast_nodes
                                   if ast_node.value is not None])
    else:
        def _annotations_to_signature(
                ast_nodes: _t.List[_ast.AnnAssign]
        ) -> _ast.arguments:
            return _ast.arguments([],
                                  [_ast.arg('cls', None)]
                                  + [_ann_assign_to_arg(ast_node)
                                     for ast_node in ast_nodes],
                                  None, [], [], None,
                                  [ast_node.value
                                   for ast_node in ast_nodes
                                   if ast_node.value is not None])


    def _ann_assign_to_arg(ast_node: _ast.AnnAssign) -> _ast.arg:
        assert isinstance(ast_node.target, _ast.Name), ast_node
        return _ast.arg(ast_node.target.id, ast_node.annotation)


    def _evaluate_expression(node: _ast.expr,
                             *,
                             source_path: _Path,
                             namespace: _namespacing.Namespace) -> _t.Any:
        # to avoid name conflicts
        # we're using name that won't be present
        # because it'll lead to ``SyntaxError`` otherwise
        # and no AST will be generated
        temporary_name = '@tmp'
        assignment = _expression_to_assignment(node,
                                               name=temporary_name)
        _execute_statement(assignment,
                           source_path=source_path,
                           namespace=namespace)
        return namespace.pop(temporary_name)


    def _expression_to_assignment(node: _ast.expr,
                                  *,
                                  name: str) -> _ast.Assign:
        name_node = _ast.copy_location(_ast.Name(name, _ast.Store()), node)
        return _ast.copy_location(_ast.Assign([name_node], node), node)


    def _is_generic_specialization(
            base: _ast.expr
    ) -> _TypeGuard[_ast.Subscript]:
        return isinstance(base, _ast.Subscript)


    class _StateParser(_ast.NodeVisitor):
        def __init__(
                self,
                module_path: _catalog.Path,
                parent_path: _catalog.Path,
                source_path: _Path,
                scope_definitions: _Scope,
                module_ast_nodes: _ModuleAstNodes,
                module_ast_nodes_kinds: _ModuleAstNodesKinds,
                module_references: _ModuleReferences,
                modules_ast_nodes: _t.Dict[_catalog.Path, _ModuleAstNodes],
                modules_ast_nodes_kinds: _t.Dict[_catalog.Path,
                                                 _ModuleAstNodesKinds],
                modules_definitions: _t.Dict[_catalog.Path, _Scope],
                modules_references: _t.Dict[_catalog.Path, _ModuleReferences],
                modules_submodules: _t.Dict[_catalog.Path, _ModuleSubmodules],
                modules_superclasses: _t.Dict[_catalog.Path,
                                              _ModuleSuperclasses],
                visited_modules_paths: _t.Set[_catalog.Path],
                classes_bases: _t.Dict[_catalog.QualifiedPath,
                                       _t.List[_ast.expr]],
                generics_parameters_paths: _t.Dict[
                    _catalog.QualifiedPath, _t.Tuple[_catalog.Path, ...]
                ]
        ) -> None:
            (
                self.generics_parameters_paths, self.module_ast_nodes,
                self.module_ast_nodes_kinds, self.module_path,
                self.module_references, self.modules_ast_nodes,
                self.modules_ast_nodes_kinds, self.modules_definitions,
                self.modules_references, self.modules_submodules,
                self.modules_superclasses, self.parent_path,
                self.scope_definitions, self.source_path, self.classes_bases,
                self.visited_modules_paths
            ) = (
                generics_parameters_paths, module_ast_nodes,
                module_ast_nodes_kinds, module_path, module_references,
                modules_ast_nodes, modules_ast_nodes_kinds,
                modules_definitions, modules_references, modules_submodules,
                modules_superclasses, parent_path, scope_definitions,
                source_path, classes_bases, visited_modules_paths
            )

        def visit_AnnAssign(self, node: _ast.AnnAssign) -> None:
            target_path = _conversion.to_path(node.target)
            value_ast_node = node.value
            value_path = (None
                          if value_ast_node is None
                          else _conversion.to_maybe_path(value_ast_node))
            if value_path is None:
                self._add_ast_node(target_path, node)
                self._add_ast_node_kind(target_path,
                                        _NodeKind.ANNOTATED_ASSIGNMENT)
                self._add_path_definition(target_path)
            else:
                value_module_path, value_object_path = self._to_qualified_path(
                        value_path
                )
                self._add_reference(target_path, value_module_path,
                                    value_object_path)

        def visit_Assign(self, node: _ast.Assign) -> None:
            value_path = _conversion.to_maybe_path(node.value)
            if value_path is None:
                for target in node.targets:
                    target_path = _conversion.to_path(target)
                    self._add_ast_node(target_path, node)
                    self._add_ast_node_kind(target_path, _NodeKind.ASSIGNMENT)
                    self._add_path_definition(target_path)
            else:
                value_module_path, value_object_path = self._to_qualified_path(
                        value_path
                )
                for target in node.targets:
                    target_path = _conversion.to_path(target)
                    self._add_reference(target_path, value_module_path,
                                        value_object_path)

        def visit_AsyncFunctionDef(self, node: _ast.AsyncFunctionDef) -> None:
            function_name = node.name
            self._add_ast_node((function_name,), node)
            self._add_ast_node_kind((function_name,), _NodeKind.ASYNC_FUNCTION)
            self._add_name_definition(function_name)

        def visit_ClassDef(
                self,
                node: _ast.ClassDef,
                *,
                builtins_module_path: _catalog.Path
                = _catalog.module_path_from_module(_builtins),
                generic_object_path: _catalog.Path = ('Generic',),
                protocol_object_path: _catalog.Path = ('Protocol',),
                named_tuple_object_path: _catalog.Path
                = _catalog.path_from_string(_t.NamedTuple.__qualname__),
                typing_module_path: _catalog.Path
                = _catalog.module_path_from_module(_t)
        ) -> None:
            class_name = node.name
            self._add_ast_node_kind((class_name,), _NodeKind.CLASS)
            self._add_name_definition(class_name)
            class_path, module_path = (self.parent_path + (class_name,),
                                       self.module_path)
            class_bases = self.classes_bases[(module_path, class_path)] = []
            type_vars_local_paths = []
            for base in node.bases:
                if _is_generic_specialization(base):
                    type_args_maybe_objects_paths = [
                        _conversion.to_maybe_path(argument)
                        for argument in _collect_type_args(base)
                    ]
                    type_vars_local_paths += [
                        maybe_object_path
                        for maybe_object_path in type_args_maybe_objects_paths
                        if (maybe_object_path is not None
                            and
                            self._is_type_var_object_path(maybe_object_path))
                    ]
                    base_origin_maybe_object_path = (
                        _conversion.to_maybe_path(base.value)
                    )
                    if (base_origin_maybe_object_path is not None
                            and self._resolve_object_path(
                                    base_origin_maybe_object_path
                            ) in [(typing_module_path, generic_object_path),
                                  (typing_module_path, protocol_object_path)]):
                        continue
                else:
                    base_reference_path = _conversion.to_path(base)
                    assert (
                            base_reference_path is not None
                    ), (module_path, class_path)
                    base_module_path, base_object_path = (
                        self._to_qualified_path(base_reference_path)
                    )
                    if (base_module_path == typing_module_path
                            and base_object_path == named_tuple_object_path):
                        constructor_node = (
                            _named_tuple_to_constructor_ast_node(node)
                        )
                        self._add_ast_node((class_name,), constructor_node)
                        self._add_superclass(class_path, base_module_path,
                                             base_object_path)
                        continue
                    elif (base_module_path == typing_module_path
                          and base_object_path == protocol_object_path):
                        continue
                    assert (
                        not (base_module_path == typing_module_path
                             and base_object_path == generic_object_path)
                    ), (module_path, class_path)
                class_bases.append(base)
            generic_parameters = tuple(dict.fromkeys(type_vars_local_paths))
            if generic_parameters:
                self.generics_parameters_paths[
                    (module_path, class_path)
                ] = generic_parameters
            parse_child = _StateParser(
                    module_path, class_path, self.source_path,
                    self.scope_definitions[class_name], self.module_ast_nodes,
                    self.module_ast_nodes_kinds, self.module_references,
                    self.modules_ast_nodes, self.modules_ast_nodes_kinds,
                    self.modules_definitions, self.modules_references,
                    self.modules_submodules, self.modules_superclasses,
                    self.visited_modules_paths, self.classes_bases,
                    self.generics_parameters_paths
            ).visit
            for child in node.body:
                parse_child(child)

        def visit_FunctionDef(self, node: _ast.FunctionDef) -> None:
            function_name = node.name
            self._add_ast_node((function_name,), node)
            self._add_ast_node_kind((function_name,), _NodeKind.FUNCTION)
            self._add_name_definition(function_name)

        def visit_If(self, node: _ast.If) -> None:
            namespace: _namespacing.Namespace = {}
            for dependency_name in {
                child.id
                for child in _recursively_iterate_children(node.test)
                if is_dependency_name(child)
            }:
                module_path, object_path = self._resolve_object_path(
                        (dependency_name,)
                )
                module = _import_module(_catalog.path_to_string(module_path))
                namespace[dependency_name] = (_namespacing.search(module,
                                                                  object_path)
                                              if object_path
                                              else module)
            condition = _evaluate_expression(node.test,
                                             source_path=self.source_path,
                                             namespace=namespace)
            for child in (node.body if condition else node.orelse):
                self.visit(child)

        def visit_Import(self, node: _ast.Import) -> None:
            for alias in node.names:
                module_path = _catalog.path_from_string(alias.name)
                if alias.asname is None:
                    sub_module_path: _catalog.Path = ()
                    for module_name_part in module_path:
                        sub_module_path += (module_name_part,)
                        self._add_reference(sub_module_path, sub_module_path,
                                            ())
                else:
                    self._add_reference((alias.asname,), module_path, ())

        def visit_ImportFrom(self, node: _ast.ImportFrom) -> None:
            parent_module_path = _to_parent_module_path(
                    node,
                    parent_module_path=self.module_path
            )
            for alias in node.names:
                if alias.name == '*':
                    self._add_submodule(parent_module_path)
                else:
                    actual_path = _catalog.path_from_string(alias.name)
                    self._add_reference(actual_path
                                        if alias.asname is None
                                        else (alias.asname,),
                                        parent_module_path, actual_path)

        def _add_ast_node(self,
                          path: _catalog.Path,
                          ast_node: _ast.AST) -> None:
            self.module_ast_nodes.setdefault(
                    self.parent_path + path, []
            ).append(ast_node)

        def _add_ast_node_kind(self,
                               path: _catalog.Path,
                               node_kind: _NodeKind) -> None:
            self.module_ast_nodes_kinds[self.parent_path + path] = node_kind

        def _add_name_definition(self, name: str) -> None:
            assert isinstance(name, str), name
            self.scope_definitions.setdefault(name, {})

        def _add_path_definition(self, path: _catalog.Path) -> None:
            scope_definitions = self.scope_definitions
            for part in path:
                scope_definitions = scope_definitions.setdefault(part, {})

        def _add_reference(self,
                           reference_path: _catalog.Path,
                           referent_module_path: _catalog.Path,
                           referent_object_path: _catalog.Path) -> None:
            self.module_references[reference_path] = (referent_module_path,
                                                      referent_object_path)

        def _add_submodule(self, module_path: _catalog.Path) -> None:
            self.modules_submodules.setdefault(
                    self.module_path, []
            ).append(module_path)

        def _add_superclass(self,
                            child_path: _catalog.Path,
                            base_module_path: _catalog.Path,
                            base_object_path: _catalog.Path) -> None:
            self.modules_superclasses.setdefault(
                    self.module_path, {}
            ).setdefault(child_path, []).append((base_module_path,
                                                 base_object_path))

        def _resolve_object_path(
                self, object_path: _catalog.Path
        ) -> _catalog.QualifiedPath:
            return _resolve_object_path(
                    self.module_path, self.parent_path, object_path,
                    self.modules_ast_nodes, self.modules_ast_nodes_kinds,
                    self.modules_definitions, self.modules_references,
                    self.modules_submodules, self.modules_superclasses,
                    self.visited_modules_paths, self.classes_bases,
                    self.generics_parameters_paths
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
                self, object_path: _catalog.Path,
                *,
                type_var_object_path: _catalog.Path
                = _catalog.path_from_string(_t.TypeVar.__qualname__),
                typing_module_path: _catalog.Path
                = _catalog.module_path_from_module(_t),
        ) -> bool:
            module_path, object_path = self._to_qualified_path(object_path)
            _parse_stub_scope(
                    module_path, self.modules_ast_nodes,
                    self.modules_ast_nodes_kinds, self.modules_definitions,
                    self.modules_references, self.modules_submodules,
                    self.modules_superclasses, self.visited_modules_paths,
                    self.classes_bases, self.generics_parameters_paths
            )
            module_ast_nodes = self.modules_ast_nodes[module_path]
            ast_nodes = module_ast_nodes.get(object_path, [])
            if len(ast_nodes) != 1:
                return False
            ast_node, = ast_nodes
            if not (isinstance(ast_node, (_ast.AnnAssign, _ast.Assign))
                    and isinstance(ast_node.value, _ast.Call)):
                return False
            callable_maybe_object_path = _conversion.to_maybe_path(
                    ast_node.value.func
            )
            if callable_maybe_object_path is None:
                return False
            callable_module_path, callable_object_path = (
                _resolve_object_path(
                        module_path, (), callable_maybe_object_path,
                        self.modules_ast_nodes, self.modules_ast_nodes_kinds,
                        self.modules_definitions, self.modules_references,
                        self.modules_submodules, self.modules_superclasses,
                        self.visited_modules_paths, self.classes_bases,
                        self.generics_parameters_paths
                )
            )
            return (callable_module_path == typing_module_path
                    and callable_object_path == type_var_object_path)


    class _ObjectNotFound(Exception):
        pass


    def _resolve_object_path(
            module_path: _catalog.Path,
            parent_path: _catalog.Path,
            object_path: _catalog.Path,
            modules_ast_nodes: _t.Dict[_catalog.Path, _ModuleAstNodes],
            modules_ast_nodes_kinds: _t.Dict[_catalog.Path,
                                             _ModuleAstNodesKinds],
            modules_definitions: _t.Dict[_catalog.Path, _Scope],
            modules_references: _t.Dict[_catalog.Path, _ModuleReferences],
            modules_submodules: _t.Dict[_catalog.Path, _ModuleSubmodules],
            modules_superclasses: _t.Dict[_catalog.Path, _ModuleSuperclasses],
            visited_modules_paths: _t.Set[_catalog.Path],
            classes_bases: _t.Dict[_catalog.QualifiedPath, _t.List[_ast.expr]],
            generics_parameters_paths: _t.Dict[_catalog.QualifiedPath,
                                               _t.Tuple[_catalog.Path, ...]],
            *,
            _builtins_module_path: _catalog.Path
            = _catalog.module_path_from_module(_builtins)
    ) -> _catalog.QualifiedPath:
        first_name = object_path[0]
        module_definitions = _parse_stub_scope(
                module_path, modules_ast_nodes, modules_ast_nodes_kinds,
                modules_definitions, modules_references, modules_submodules,
                modules_superclasses, visited_modules_paths, classes_bases,
                generics_parameters_paths
        )
        if _scoping.scope_contains_path(module_definitions,
                                        parent_path + (first_name,)):
            return module_path, parent_path + object_path
        elif first_name in module_definitions:
            return module_path, object_path
        else:
            for sub_module_path in modules_submodules.get(module_path, []):
                try:
                    return _resolve_object_path(
                            sub_module_path, (), object_path,
                            modules_ast_nodes, modules_ast_nodes_kinds,
                            modules_definitions, modules_references,
                            modules_submodules, modules_superclasses,
                            visited_modules_paths, classes_bases,
                            generics_parameters_paths
                    )
                except _ObjectNotFound:
                    continue
        module_references = modules_references[module_path]
        for offset in range(len(object_path)):
            sub_object_path = object_path[:len(object_path) - offset]
            try:
                referent_module_name, referent_object_path = (
                    module_references[sub_object_path]
                )
            except KeyError:
                continue
            else:
                return (referent_module_name,
                        (referent_object_path
                         + object_path[len(object_path) - offset:]))
        if _scoping.scope_contains_path(
                modules_definitions[_builtins_module_path], object_path
        ):
            return _builtins_module_path, object_path
        raise _ObjectNotFound(object_path)


    def _parse_stub_scope(
            module_path: _catalog.Path,
            modules_ast_nodes: _t.Dict[_catalog.Path, _ModuleAstNodes],
            modules_ast_nodes_kinds: _t.Dict[_catalog.Path,
                                             _ModuleAstNodesKinds],
            modules_definitions: _t.Dict[_catalog.Path, _Scope],
            modules_references: _t.Dict[_catalog.Path, _ModuleReferences],
            modules_submodules: _t.Dict[_catalog.Path, _ModuleSubmodules],
            modules_superclasses: _t.Dict[_catalog.Path, _ModuleSuperclasses],
            visited_modules_paths: _t.Set[_catalog.Path],
            classes_bases: _t.Dict[_catalog.QualifiedPath, _t.List[_ast.expr]],
            generics_parameters_paths: _t.Dict[_catalog.QualifiedPath,
                                               _t.Tuple[_catalog.Path, ...]]
    ) -> _Scope:
        if module_path in visited_modules_paths:
            return modules_definitions[module_path]
        visited_modules_paths.add(module_path)
        source_path = _sources.from_module_path(module_path)
        module_definitions = modules_definitions[module_path] = {}
        module_ast_nodes_kinds = modules_ast_nodes_kinds[module_path] = {}
        module_ast_nodes = modules_ast_nodes[module_path] = {}
        module_references = modules_references[module_path] = {}
        ast_node = _construction.from_source_path(source_path)
        _StateParser(
                module_path, (), source_path, module_definitions,
                module_ast_nodes, module_ast_nodes_kinds, module_references,
                modules_ast_nodes, modules_ast_nodes_kinds,
                modules_definitions, modules_references, modules_submodules,
                modules_superclasses, visited_modules_paths, classes_bases,
                generics_parameters_paths
        ).visit(ast_node)
        return module_definitions


    @_singledispatch
    def _unpack_ast_node(ast_node: _ast.expr) -> _t.Tuple[_ast.expr, ...]:
        return (ast_node,)


    @_unpack_ast_node.register(_ast.Tuple)
    def _(ast_node: _ast.Tuple) -> _t.Tuple[_ast.expr, ...]:
        assert isinstance(ast_node.ctx, _ast.Load), ast_node
        return tuple(ast_node.elts)


    def _collect_type_args(ast_node: _ast.expr) -> _t.List[_ast.expr]:
        if _is_generic_specialization(ast_node):
            queue = [_subscript_to_item(ast_node)]
            args: _t.List[_ast.expr] = []
            while queue:
                specialization_node = queue.pop()
                candidates = _unpack_ast_node(specialization_node)
                for candidate in reversed(candidates):
                    if _is_generic_specialization(candidate):
                        queue.append(_subscript_to_item(candidate))
                    else:
                        args.append(candidate)
            return args[::-1]
        else:
            return []


    class _SpecializeGeneric(_ast.NodeTransformer):
        def __init__(self, table: _t.Dict[_catalog.Path, _ast.expr]) -> None:
            self.table = table

        def visit_Name(self, node: _ast.Name) -> _ast.expr:
            if not isinstance(node.ctx, _ast.Load):
                return node
            candidate = self.table.get(_conversion.to_path(node))
            return (node
                    if candidate is None
                    else _ast.copy_location(_deepcopy(candidate), node))

        def visit_Attribute(self, node: _ast.Attribute) -> _ast.expr:
            if not isinstance(node.ctx, _ast.Load):
                return node
            candidate = self.table.get(_conversion.to_path(node))
            return (node
                    if candidate is None
                    else _ast.copy_location(_deepcopy(candidate), node))


    def _parse_stubs_state(
            modules_paths: _t.Iterable[_catalog.Path]
    ) -> _t.Tuple[_t.Dict[_catalog.Path, _Scope],
                  _t.Dict[_catalog.Path, _ModuleAstNodesKinds],
                  _t.Dict[_catalog.Path, _ModuleRawAstNodes],
                  _t.Dict[_catalog.Path, _ModuleReferences],
                  _t.Dict[_catalog.Path, _ModuleSubmodules],
                  _t.Dict[_catalog.Path, _ModuleSuperclasses]]:
        modules_definitions: _t.Dict[_catalog.Path, _Scope] = {}
        modules_nodes_kinds: _t.Dict[_catalog.Path, _ModuleAstNodesKinds] = {}
        modules_ast_nodes: _t.Dict[_catalog.Path, _ModuleAstNodes] = {}
        modules_references: _t.Dict[_catalog.Path, _ModuleReferences] = {}
        modules_submodules: _t.Dict[_catalog.Path, _ModuleSubmodules] = {}
        modules_superclasses: _t.Dict[_catalog.Path, _ModuleSuperclasses] = {}
        classes_bases: _t.Dict[_catalog.QualifiedPath, _t.List[_ast.expr]] = {}
        generics_parameters_paths: _t.Dict[_catalog.QualifiedPath,
                                           _t.Tuple[_catalog.Path, ...]] = {}
        visited_modules_paths: _t.Set[_catalog.Path] = set()
        _parse_stub_scope(
                _catalog.module_path_from_module(_builtins), modules_ast_nodes,
                modules_nodes_kinds, modules_definitions, modules_references,
                modules_submodules, modules_superclasses,
                visited_modules_paths, classes_bases, generics_parameters_paths
        )
        for module_path in modules_paths:
            _parse_stub_scope(
                    module_path, modules_ast_nodes, modules_nodes_kinds,
                    modules_definitions, modules_references,
                    modules_submodules, modules_superclasses,
                    visited_modules_paths, classes_bases,
                    generics_parameters_paths
            )
        _process_classes_bases(
                classes_bases, generics_parameters_paths, modules_ast_nodes,
                modules_definitions, modules_nodes_kinds, modules_references,
                modules_submodules, modules_superclasses
        )
        modules_raw_ast_nodes = {
            module_path: {
                object_path: [_serialization.to_raw(ast_node)
                              for ast_node in ast_nodes]
                for object_path, ast_nodes in module_ast_nodes.items()
            }
            for module_path, module_ast_nodes in modules_ast_nodes.items()
        }
        return (
            modules_definitions, modules_nodes_kinds, modules_raw_ast_nodes,
            modules_references, modules_submodules, modules_superclasses
        )


    def _process_classes_bases(
            classes_bases: _t.Dict[_catalog.QualifiedPath, _t.List[_ast.expr]],
            generics_parameters_paths: _t.Dict[_catalog.QualifiedPath,
                                               _t.Tuple[_catalog.Path, ...]],
            modules_ast_nodes: _t.Dict[_catalog.Path, _ModuleAstNodes],
            modules_definitions: _t.Dict[_catalog.Path, _Scope],
            modules_nodes_kinds: _t.Dict[_catalog.Path, _ModuleAstNodesKinds],
            modules_references: _t.Dict[_catalog.Path, _ModuleReferences],
            modules_submodules: _t.Dict[_catalog.Path, _ModuleSubmodules],
            modules_superclasses: _t.Dict[_catalog.Path, _ModuleSuperclasses],
            *,
            specializations_module_path: _catalog.Path = ('__specializations',)
    ) -> None:
        assert specializations_module_path not in modules_ast_nodes
        specializations_ast_nodes = modules_ast_nodes[
            specializations_module_path
        ] = {}
        assert specializations_module_path not in modules_definitions
        specializations_module_scope = modules_definitions[
            specializations_module_path
        ] = {}
        assert specializations_module_path not in modules_nodes_kinds
        specializations_nodes_kinds = modules_nodes_kinds[
            specializations_module_path
        ] = {}
        assert specializations_module_path not in modules_references
        specializations_references = modules_references[
            specializations_module_path
        ] = {}
        for (class_module_path, class_object_path), class_bases in (
                classes_bases.items()
        ):
            for base in class_bases:
                base_module_path, base_object_path = _register_base_ast_node(
                        base, class_module_path, class_object_path,
                        classes_bases, generics_parameters_paths,
                        specializations_ast_nodes, specializations_module_path,
                        specializations_module_scope,
                        specializations_nodes_kinds,
                        specializations_references, modules_ast_nodes,
                        modules_definitions, modules_nodes_kinds,
                        modules_references, modules_submodules,
                        modules_superclasses
                )
                modules_superclasses.setdefault(
                        class_module_path, {}
                ).setdefault(class_object_path, []).append((base_module_path,
                                                            base_object_path))


    def _register_base_ast_node(
            base: _ast.expr,
            child_module_path: _catalog.Path,
            child_object_path: _catalog.Path,
            classes_bases: _t.Dict[_catalog.QualifiedPath, _t.List[_ast.expr]],
            generics_parameters_paths: _t.Dict[_catalog.QualifiedPath,
                                               _t.Tuple[_catalog.Path, ...]],
            specializations_ast_nodes: _ModuleAstNodes,
            specializations_module_path: _catalog.Path,
            specializations_module_scope: _Scope,
            specializations_nodes_kinds: _ModuleAstNodesKinds,
            specializations_references: _ModuleReferences,
            modules_ast_nodes: _t.Dict[_catalog.Path, _ModuleAstNodes],
            modules_definitions: _t.Dict[_catalog.Path, _Scope],
            modules_nodes_kinds: _t.Dict[_catalog.Path, _ModuleAstNodesKinds],
            modules_references: _t.Dict[_catalog.Path, _ModuleReferences],
            modules_submodules: _t.Dict[_catalog.Path, _ModuleSubmodules],
            modules_superclasses: _t.Dict[_catalog.Path, _ModuleSuperclasses]
    ) -> _catalog.QualifiedPath:
        if _is_generic_specialization(base):
            base_name = _serialization.to_identifier(base)
            base_object_path = (base_name,)
            if base_name not in specializations_module_scope:
                specialization_args = _unpack_ast_node(
                        _subscript_to_item(base)
                )
                generic_object_path = _conversion.to_path(base.value)
                generic_module_path, generic_object_path = (
                    _scoping.resolve_object_path(
                            child_module_path, child_object_path[:-1],
                            generic_object_path, modules_definitions,
                            modules_references, modules_submodules,
                            modules_superclasses
                    )
                )
                generic_parameters_paths = generics_parameters_paths[
                    (generic_module_path, generic_object_path)
                ]
                _register_generic_specialization(
                        generic_module_path, generic_object_path,
                        child_module_path, base_object_path,
                        generic_parameters_paths,
                        specialization_args, specializations_ast_nodes,
                        specializations_module_scope,
                        specializations_nodes_kinds,
                        specializations_references, modules_ast_nodes,
                        modules_definitions, modules_nodes_kinds,
                        modules_references, modules_submodules,
                        modules_superclasses
                )
                assert base_object_path not in modules_superclasses.get(
                        specializations_module_path, {}
                )
                specialization_table = dict(zip(generic_parameters_paths,
                                                specialization_args))
                specialize = _SpecializeGeneric(specialization_table).visit
                generic_bases = classes_bases[(generic_module_path,
                                               generic_object_path)]
                for generic_base in generic_bases:
                    base_base_module_path: _catalog.Path
                    base_base_object_path: _catalog.Path
                    if _is_generic_specialization(generic_base):
                        base_base_node = specialize(generic_base)
                        base_base_name = _serialization.to_identifier(
                                base_base_node
                        )
                        base_base_module_path, base_base_object_path = (
                            specializations_module_path, (base_base_name,)
                        )
                        if base_base_name not in specializations_module_scope:
                            generic_base_base_object_path = (
                                _conversion.to_path(generic_base.value)
                            )
                            (
                                generic_base_base_module_path,
                                generic_base_base_object_path
                            ) = _scoping.resolve_object_path(
                                    generic_module_path,
                                    generic_object_path[:-1],
                                    generic_base_base_object_path,
                                    modules_definitions, modules_references,
                                    modules_submodules, modules_superclasses
                            )
                            generic_base_base_parameters_paths = (
                                generics_parameters_paths[
                                    (generic_base_base_module_path,
                                     generic_base_base_object_path)
                                ]
                            )
                            base_base_specialization_args = _unpack_ast_node(
                                    _subscript_to_item(base_base_node)
                            )
                            _register_generic_specialization(
                                    generic_base_base_module_path,
                                    generic_base_base_object_path,
                                    child_module_path, base_base_object_path,
                                    generic_base_base_parameters_paths,
                                    base_base_specialization_args,
                                    specializations_ast_nodes,
                                    specializations_module_scope,
                                    specializations_nodes_kinds,
                                    specializations_references,
                                    modules_ast_nodes, modules_definitions,
                                    modules_nodes_kinds, modules_references,
                                    modules_submodules, modules_superclasses
                            )
                    else:
                        base_base_object_path = _conversion.to_path(
                                generic_base
                        )
                        base_base_module_path, base_base_object_path = (
                            _scoping.resolve_object_path(
                                    generic_module_path, (),
                                    base_base_object_path, modules_definitions,
                                    modules_references, modules_submodules,
                                    modules_superclasses
                            )
                        )
                    modules_superclasses.setdefault(
                            specializations_module_path, {}
                    ).setdefault(base_object_path, []).append(
                            (base_base_module_path, base_base_object_path)
                    )
            return specializations_module_path, base_object_path
        else:
            base_reference_path = _conversion.to_path(base)
            return _scoping.resolve_object_path(
                    child_module_path, child_object_path[:-1],
                    base_reference_path, modules_definitions,
                    modules_references, modules_submodules,
                    modules_superclasses
            )


    def _register_generic_specialization(
            generic_module_path: _catalog.Path,
            generic_object_path: _catalog.Path,
            specialization_module_path: _catalog.Path,
            specialization_object_path: _catalog.Path,
            generic_parameters_paths: _t.Sequence[_catalog.Path],
            specialization_args: _t.Sequence[_ast.expr],
            specializations_ast_nodes: _ModuleAstNodes,
            specializations_module_scope: _Scope,
            specializations_nodes_kinds: _ModuleAstNodesKinds,
            specializations_references: _ModuleReferences,
            modules_ast_nodes: _t.Dict[_catalog.Path, _ModuleAstNodes],
            modules_definitions: _t.Dict[_catalog.Path, _Scope],
            modules_nodes_kinds: _t.Dict[_catalog.Path, _ModuleAstNodesKinds],
            modules_references: _t.Dict[_catalog.Path, _ModuleReferences],
            modules_submodules: _t.Mapping[_catalog.Path, _ModuleSubmodules],
            modules_superclasses: _t.Mapping[_catalog.Path,
                                             _ModuleSuperclasses],
            builtins_module_path: _catalog.Path
            = _catalog.module_path_from_module(_builtins)
    ) -> None:
        base_scope = specializations_module_scope
        for part in specialization_object_path:
            base_scope = base_scope.setdefault(part, {})
        generic_scope = modules_definitions[generic_module_path]
        for part in generic_object_path:
            generic_scope = generic_scope[part]
        base_scope.update(generic_scope)
        generic_module_ast_nodes = modules_ast_nodes[generic_module_path]
        specializations_nodes_kinds[
            specialization_object_path
        ] = _NodeKind.CLASS
        specialize = _SpecializeGeneric(
                dict(zip(generic_parameters_paths, specialization_args))
        ).visit
        args_names = (
                {arg.id
                 for arg in specialization_args
                 if is_dependency_name(arg)}
                | {child.id
                   for ast_node in specialization_args
                   for child in _recursively_iterate_children(ast_node)
                   if is_dependency_name(child)}
        )
        for name in generic_scope.keys():
            generic_field_path = (*generic_object_path, name)
            generic_ast_nodes = generic_module_ast_nodes[generic_field_path]
            specialization_field_path = (*specialization_object_path, name)
            specialization_ast_nodes = specializations_ast_nodes[
                specialization_field_path
            ] = [specialize(_deepcopy(ast_node))
                 for ast_node in generic_ast_nodes]
            specialization_definitions_names = set(
                    chain.from_iterable(
                            _conversion.to_names(ast_node)
                            for ast_node in specialization_ast_nodes
                    )
            )
            for dependency_name in (
                    {child.id
                     for ast_node in specialization_ast_nodes
                     for child in _recursively_iterate_children(ast_node)
                     if is_dependency_name(child)}
                    - specialization_definitions_names
            ):
                dependency_path = (dependency_name,)
                dependency_module_path, dependency_object_path = (
                    _scoping.resolve_object_path(
                            (specialization_module_path
                             if dependency_name in args_names
                             else generic_module_path), (),
                            dependency_path, modules_definitions,
                            modules_references, modules_submodules,
                            modules_superclasses
                    )
                )
                if dependency_module_path != builtins_module_path:
                    specializations_references[dependency_path] = (
                        dependency_module_path, dependency_object_path
                    )
            specializations_nodes_kinds[specialization_field_path] = (
                modules_nodes_kinds[generic_module_path][generic_field_path]
            )


    if _execution.is_main_process():
        (
            definitions, nodes_kinds, raw_ast_nodes, references, submodules,
            superclasses
        ) = _execution.call_in_process(_parse_stubs_state,
                                       _stdlib_modules_paths)
        _exporting.save(_CACHE_PATH,
                        **{_DEFINITIONS_FIELD_NAME: definitions,
                           _NODES_KINDS_FIELD_NAME: nodes_kinds,
                           _RAW_AST_NODES_FIELD_NAME: raw_ast_nodes,
                           _REFERENCES_FIELD_NAME: references,
                           _SUBMODULES_FIELD_NAME: submodules,
                           _SUPERCLASSES_FIELD_NAME: superclasses,
                           _VERSION_FIELD_NAME: _version})
    else:
        (
            definitions, nodes_kinds, raw_ast_nodes, references, submodules,
            superclasses
        ) = {}, {}, {}, {}, {}, {}
