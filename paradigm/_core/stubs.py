import sys as _sys
import typing as _t
from importlib import import_module as _import_module
from operator import attrgetter as _attrgetter
from pathlib import Path as _Path

import mypy as _mypy
from mypy.version import __version__ as _mypy_version

from . import (catalog as _catalog,
               scoping as _scoping)

_CACHE_PATH = _Path(__file__).with_name(
        '_' + _mypy.__name__ + '_' + _mypy_version.replace('.', '_')
        + '_' + _sys.platform
        + '_' + _sys.implementation.name
        + '_' + '_'.join(map(str, _sys.version_info))
        + '_' + _Path(__file__).name
)
_DEFINITIONS_FIELD_NAME = 'definitions'
_REFERENCES_FIELD_NAME = 'references'
_SUB_SCOPES_FIELD_NAME = 'sub_scopes'

definitions: _t.Dict[_catalog.Path, _scoping.Scope]
references: _t.Dict[_catalog.Path, _scoping.ModuleReferences]
sub_scopes: _t.Dict[_catalog.Path, _scoping.ModuleSubScopes]

try:
    definitions, references, sub_scopes = _attrgetter(
            _DEFINITIONS_FIELD_NAME, _REFERENCES_FIELD_NAME,
            _SUB_SCOPES_FIELD_NAME
    )(_import_module((''
                      if __name__ in ('__main__', '__mp_main__')
                      else __name__.rsplit('.', maxsplit=1)[0] + '.')
                     + _CACHE_PATH.stem))
except Exception:
    import ast as _ast
    import builtins as _builtins
    import warnings as _warnings
    from functools import (partial as _partial,
                           singledispatch as _singledispatch)

    from . import (execution as _execution,
                   exporting as _exporting,
                   namespacing as _namespacing,
                   pretty as _pretty,
                   sources as _sources)
    from .arboreal.importing import (
        evaluate_expression, left_search_within_children,
        recursively_iterate_children,
        to_parent_module_path as _to_parent_module_path
    )
    from .arboreal import construction as _construction
    from .sources import stubs_stdlib_modules_paths as _stdlib_modules_paths


    @_singledispatch
    def _ast_node_to_path(ast_node: _ast.AST) -> _catalog.Path:
        raise TypeError(type(ast_node))


    @_ast_node_to_path.register(_ast.Name)
    def _(ast_node: _ast.Name) -> _catalog.Path:
        return (ast_node.id,)


    @_ast_node_to_path.register(_ast.Subscript)
    def _(ast_node: _ast.Subscript) -> _catalog.Path:
        return _ast_node_to_path(ast_node.value)


    @_ast_node_to_path.register(_ast.Attribute)
    def _(ast_node: _ast.Attribute) -> _catalog.Path:
        return (*_ast_node_to_path(ast_node.value), ast_node.attr)


    @_singledispatch
    def _ast_node_to_maybe_path(
            ast_node: _ast.AST
    ) -> _t.Optional[_catalog.Path]:
        return None


    @_ast_node_to_maybe_path.register(_ast.Name)
    def _(ast_node: _ast.Name) -> _catalog.Path:
        return (ast_node.id,)


    @_ast_node_to_maybe_path.register(_ast.Subscript)
    def _(ast_node: _ast.Subscript) -> _catalog.Path:
        return _ast_node_to_path(ast_node.value)


    @_ast_node_to_maybe_path.register(_ast.Attribute)
    def _(ast_node: _ast.Attribute) -> _catalog.Path:
        return (*_ast_node_to_path(ast_node.value), ast_node.attr)


    class _StateParser(_ast.NodeVisitor):
        def __init__(
                self,
                module_path: _catalog.Path,
                parent_path: _catalog.Path,
                source_path: _Path,
                scope_definitions: _scoping.Scope,
                module_references: _scoping.ModuleReferences,
                module_sub_scopes: _scoping.ModuleSubScopes,
                modules_definitions: _t.Dict[_catalog.Path, dict],
                modules_references: _t.Dict[_catalog.Path,
                                            _scoping.ModuleReferences],
                modules_sub_scopes: _t.Dict[_catalog.Path,
                                            _scoping.ModuleSubScopes],
                visited_modules_paths: _t.Set[_catalog.Path]
        ) -> None:
            (
                self.module_path, self.module_references,
                self.module_sub_scopes, self.modules_definitions,
                self.modules_references, self.modules_sub_scopes,
                self.parent_path, self.scope_definitions, self.source_path,
                self.visited_modules_paths
            ) = (
                module_path, module_references, module_sub_scopes,
                modules_definitions, modules_references, modules_sub_scopes,
                parent_path, scope_definitions, source_path,
                visited_modules_paths
            )

        def visit_AnnAssign(self, node: _ast.AnnAssign) -> None:
            target_path = _ast_node_to_path(node.target)
            value_ast_node = node.value
            value_path = (None
                          if value_ast_node is None
                          else _ast_node_to_maybe_path(value_ast_node))
            if value_path is None:
                self._add_path_definition(target_path)
            else:
                value_module_path, value_object_path = self._to_qualified_path(
                        value_path
                )
                self._add_reference(target_path, value_module_path,
                                    value_object_path)

        def visit_Assign(self, node: _ast.Assign) -> None:
            try:
                value_path = _ast_node_to_path(node.value)
            except TypeError:
                for target in node.targets:
                    target_path = _ast_node_to_path(target)
                    self._add_path_definition(target_path)
            else:
                value_module_path, value_object_path = self._to_qualified_path(
                        value_path
                )
                for target in node.targets:
                    target_path = _ast_node_to_path(target)
                    self._add_reference(target_path, value_module_path,
                                        value_object_path)

        def visit_AsyncFunctionDef(self, node: _ast.AsyncFunctionDef) -> None:
            self._add_name_definition(node.name)

        def visit_ClassDef(self, node: _ast.ClassDef) -> None:
            class_name = node.name
            self._add_name_definition(class_name)
            class_path = self.parent_path + (class_name,)
            for base in node.bases:
                base_reference_path = _ast_node_to_path(base)
                assert base_reference_path is not None
                base_module_path, base_object_path = self._to_qualified_path(
                        base_reference_path
                )
                self._add_sub_scope(class_path, base_module_path,
                                    base_object_path)
            parse_child = _StateParser(
                    self.module_path, class_path, self.source_path,
                    self.scope_definitions[class_name], self.module_references,
                    self.module_sub_scopes, self.modules_definitions,
                    self.modules_references, self.modules_sub_scopes,
                    self.visited_modules_paths
            ).visit
            for child in node.body:
                parse_child(child)

        def visit_If(self, node: _ast.If) -> None:
            namespace = {}
            for dependency_name in {
                child.id
                for child in recursively_iterate_children(node.test)
                if (isinstance(child, _ast.Name)
                    and isinstance(child.ctx, _ast.Load))
            }:
                module_path, object_path = _resolve_object_path(
                        self.module_path, self.parent_path, (dependency_name,),
                        self.modules_definitions, self.modules_references,
                        self.modules_sub_scopes, self.visited_modules_paths
                )
                module = _import_module(_catalog.path_to_string(module_path))
                namespace[dependency_name] = (_namespacing.search(vars(module),
                                                                  object_path)
                                              if object_path
                                              else module)
            condition = evaluate_expression(node.test,
                                            source_path=self.source_path,
                                            namespace=namespace)
            for child in (node.body if condition else node.orelse):
                self.visit(child)

        def visit_FunctionDef(self, node: _ast.FunctionDef) -> None:
            self._add_name_definition(node.name)

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
                    self._add_sub_scope((), parent_module_path, ())
                else:
                    actual_path = _catalog.path_from_string(alias.name)
                    self._add_reference(actual_path
                                        if alias.asname is None
                                        else (alias.asname,),
                                        parent_module_path, actual_path)

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
            assert isinstance(referent_module_path,
                              tuple), referent_module_path
            self.module_references[reference_path] = (referent_module_path,
                                                      referent_object_path)

        def _add_sub_scope(self,
                           reference_path: _catalog.Path,
                           referent_module_path: _catalog.Path,
                           referent_object_path: _catalog.Path) -> None:
            self.module_sub_scopes.setdefault(
                    reference_path, set()
            ).add((referent_module_path, referent_object_path))

        def _to_qualified_path(
                self, object_path: _catalog.Path
        ) -> _catalog.QualifiedPath:
            try:
                return _resolve_object_path(
                        self.module_path, self.parent_path, object_path,
                        self.modules_definitions, self.modules_references,
                        self.modules_sub_scopes, self.visited_modules_paths
                )
            except _ObjectNotFound:
                self._add_path_definition(object_path)
                return (self.module_path, object_path)


    class _ObjectNotFound(Exception):
        pass


    def _resolve_object_path(
            module_path: _catalog.Path,
            parent_path: _catalog.Path,
            object_path: _catalog.Path,
            modules_definitions: _t.Dict[_catalog.Path, _scoping.Scope],
            modules_references: _t.Dict[_catalog.Path,
                                        _scoping.ModuleReferences],
            modules_sub_scopes: _t.Dict[_catalog.Path,
                                        _scoping.ModuleSubScopes],
            visited_modules_paths: _t.Set[_catalog.Path],
            *,
            _builtins_module_path: _catalog.Path
            = _catalog.module_path_from_module(_builtins)
    ) -> _catalog.QualifiedPath:
        first_name = object_path[0]
        module_definitions = _parse_stub_scope(
                module_path, modules_definitions, modules_references,
                modules_sub_scopes, visited_modules_paths
        )
        if (_scoping.scope_contains_path(module_definitions,
                                         parent_path + (first_name,))
                or first_name in module_definitions):
            return module_path, object_path
        elif () in modules_sub_scopes[module_path]:
            for sub_module_path, _ in modules_sub_scopes[module_path][()]:
                try:
                    return _resolve_object_path(
                            sub_module_path, (), object_path,
                            modules_definitions, modules_references,
                            modules_sub_scopes, visited_modules_paths
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
        if (_builtins_module_path in modules_definitions
                and _scoping.scope_contains_path(
                        modules_definitions[_builtins_module_path], object_path
                )):
            return _builtins_module_path, object_path
        raise _ObjectNotFound(object_path)


    def _parse_stub_scope(
            module_path: _catalog.Path,
            modules_definitions: _t.Dict[_catalog.Path, _scoping.Scope],
            modules_references: _t.Dict[_catalog.Path,
                                        _scoping.ModuleReferences],
            modules_sub_scopes: _t.Dict[_catalog.Path,
                                        _scoping.ModuleSubScopes],
            visited_modules_paths: _t.Set[_catalog.Path],
    ) -> _scoping.Scope:
        if module_path in visited_modules_paths:
            return modules_definitions[module_path]
        visited_modules_paths.add(module_path)
        source_path = _sources.from_module_path(module_path)
        module_definitions = modules_definitions[module_path] = {}
        module_references = modules_references[module_path] = {}
        module_sub_scopes = modules_sub_scopes[module_path] = {}
        ast_node = _construction.from_source_path(source_path)
        _StateParser(
                module_path, (), source_path, module_definitions,
                module_references, module_sub_scopes, modules_definitions,
                modules_references, modules_sub_scopes,
                visited_modules_paths
        ).generic_visit(ast_node)
        return module_definitions


    def _parse_stubs_state(
            modules_paths: _t.Iterable[_catalog.Path]
    ) -> _t.Tuple[_t.Dict[_catalog.Path, _scoping.Scope],
                  _t.Dict[_catalog.Path, _scoping.ModuleReferences],
                  _t.Dict[_catalog.Path, _scoping.ModuleSubScopes]]:
        modules_definitions: _t.Dict[_catalog.Path, _scoping.Scope] = {}
        visited_modules_paths: _t.Set[_catalog.Path] = set()
        modules_references: _t.Dict[_catalog.Path,
                                    _scoping.ModuleReferences] = {}
        modules_sub_scopes: _t.Dict[_catalog.Path,
                                    _scoping.ModuleSubScopes] = {}
        _parse_stub_scope(_catalog.module_path_from_module(_builtins),
                          modules_definitions, modules_references,
                          modules_sub_scopes, visited_modules_paths)
        for module_path in modules_paths:
            _parse_stub_scope(module_path, modules_definitions,
                              modules_references, modules_sub_scopes,
                              visited_modules_paths)
        return modules_definitions, modules_references, modules_sub_scopes


    if _execution.is_main_process():
        definitions, references, sub_scopes = _execution.call_in_process(
                _parse_stubs_state, _stdlib_modules_paths
        )
        _exporting.save(_CACHE_PATH, **{_DEFINITIONS_FIELD_NAME: definitions,
                                        _REFERENCES_FIELD_NAME: references,
                                        _SUB_SCOPES_FIELD_NAME: sub_scopes})
    else:
        definitions, references, sub_scopes = {}, {}, {}
