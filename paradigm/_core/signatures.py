import ast as _ast
import builtins as _builtins
import inspect as _inspect
import sys as _sys
import types as _types
import typing as _t
from functools import (partial as _partial,
                       singledispatch as _singledispatch)
from itertools import zip_longest as _zip_longest

from . import (catalog as _catalog,
               scoping as _scoping,
               stubs as _stubs)
from .arboreal import (construction as _construction,
                       conversion as _conversion)
from .arboreal.evaluation import evaluate_ast_node as _evaluate_ast_node
from .arboreal.kind import NodeKind as _NodeKind
from .arboreal.utils import subscript_to_item as _subscript_to_item
from .models import (Parameter as _Parameter,
                     PlainSignature as _PlainSignature,
                     Signature as _Signature,
                     from_signatures as _from_signatures)
from .modules import supported_stdlib_qualified_paths as _qualified_paths


@_singledispatch
def from_callable(_callable: _t.Callable[..., _t.Any]) -> _Signature:
    raise TypeError(f'Unsupported object type: {type(_callable)}.')


@from_callable.register(_types.BuiltinFunctionType)
@from_callable.register(_types.BuiltinMethodType)
@from_callable.register(_types.FunctionType)
@from_callable.register(_types.MethodType)
@from_callable.register(_types.MethodDescriptorType)
@from_callable.register(_types.MethodWrapperType)
@from_callable.register(_types.WrapperDescriptorType)
@from_callable.register(type)
def _(_callable: _t.Callable[..., _t.Any]) -> _Signature:
    try:
        return ((_from_callable(_callable)
                 if isinstance(_callable.__self__, type)
                 else (_from_callable(getattr(type(_callable.__self__),
                                              _callable.__name__))
                       .bind(_callable.__self__)))
                if (isinstance(_callable, _types.BuiltinMethodType)
                    and _callable.__self__ is not None
                    and not isinstance(_callable.__self__, _types.ModuleType)
                    or isinstance(_callable, (_types.MethodType,
                                              _types.MethodWrapperType)))
                else (_from_callable(_callable).bind(_callable)
                      if isinstance(_callable, type)
                      else _from_callable(_callable)))
    except _SignatureNotFound:
        return _from_raw_signature(_inspect.signature(_callable))


@from_callable.register(_partial)
def _(_callable: _partial) -> _Signature:
    return from_callable(_callable.func).bind(*_callable.args,
                                              **_callable.keywords)


@_singledispatch
def _from_ast(ast_node: _ast.AST, module_path: _catalog.Path) -> _Signature:
    raise TypeError(ast_node)


@_from_ast.register(_ast.AnnAssign)
def _(ast_node: _ast.AnnAssign, module_path: _catalog.Path) -> _Signature:
    annotation_node = ast_node.annotation
    if ast_node.value is None:
        return _from_ast(annotation_node, module_path)
    else:
        raise ValueError(ast_node)


@_from_ast.register(_ast.Subscript)
def _(ast_node: _ast.Subscript,
      module_path: _catalog.Path,
      *,
      callable_object_path: _catalog.Path = ('Callable',),
      typing_module_path: _catalog.Path
      = _catalog.module_path_from_module(_t)) -> _Signature:
    value_path = _conversion.to_path(ast_node.value)
    value_module_path, value_object_path = _scoping.resolve_object_path(
            module_path, (), value_path, _stubs.definitions,
            _stubs.references, _stubs.sub_scopes
    )
    if (value_module_path == typing_module_path
            and value_object_path == callable_object_path):
        callable_arguments = _subscript_to_item(ast_node)
        assert isinstance(callable_arguments, _ast.Tuple)
        arguments_annotations = callable_arguments.elts[0]
        return (
            _PlainSignature(
                    *[
                        _Parameter(
                                annotation=_evaluate_ast_node(annotation,
                                                              module_path, {}),
                                name='_' + str(index),
                                kind=_Parameter.Kind.POSITIONAL_ONLY,
                                has_default=False
                        )
                        for index, annotation in enumerate(
                                arguments_annotations.elts
                        )
                    ]
            )
            if isinstance(arguments_annotations, _ast.List)
            # unspecified parameters case
            else _PlainSignature(
                    _Parameter(annotation=_t.Any,
                               name='args',
                               kind=_Parameter.Kind.VARIADIC_POSITIONAL,
                               has_default=False),
                    _Parameter(annotation=_t.Any,
                               name='kwargs',
                               kind=_Parameter.Kind.VARIADIC_KEYWORD,
                               has_default=False),
            )
        )
    raise _SignatureNotFound


@_from_ast.register(_ast.Attribute)
@_from_ast.register(_ast.Name)
def _(ast_node: _t.Union[_ast.Attribute, _ast.Name],
      module_path: _catalog.Path) -> _Signature:
    object_path = _conversion.to_path(ast_node)
    module_path, object_path = _scoping.resolve_object_path(
            module_path, (), object_path, _stubs.definitions,
            _stubs.references, _stubs.sub_scopes
    )
    node_kind = _NodeKind(_stubs.nodes_kinds[module_path][object_path])
    if node_kind is _NodeKind.CLASS:
        try:
            raw_ast_nodes = _stubs.raw_ast_nodes[module_path][
                (*object_path, object.__call__.__name__)
            ]
        except KeyError:
            raise _SignatureNotFound
        call_ast_nodes = [_construction.from_raw(raw)
                          for raw in raw_ast_nodes]
        call_signatures = [_from_ast(ast_node, module_path)
                           for ast_node in call_ast_nodes]
        return _from_signatures(*[signature.bind('self')
                                  for signature in call_signatures])
    else:
        annotation_nodes = [
            _construction.from_raw(raw)
            for raw in _stubs.raw_ast_nodes[module_path][object_path]
        ]
        if len(annotation_nodes) == 1:
            annotation_node, = annotation_nodes
            if isinstance(annotation_node, _ast.Assign):
                return _from_ast(annotation_node.value, module_path)
    raise _SignatureNotFound


@_from_ast.register(_ast.Call)
@_from_ast.register(_ast.Attribute)
def _(ast_node: _ast.Subscript,
      module_path: _catalog.Path,
      *,
      type_var_object_path: _catalog.Path
      = _catalog.path_from_string(_t.TypeVar.__qualname__),
      typing_module_path: _catalog.Path
      = _catalog.module_path_from_module(_t)) -> _Signature:
    assert isinstance(ast_node, _ast.Call), ast_node
    callable_object_path = _conversion.to_path(ast_node.func)
    callable_module_path, callable_object_path = (
        _scoping.resolve_object_path(
                module_path, (), callable_object_path,
                _stubs.definitions, _stubs.references,
                _stubs.sub_scopes
        )
    )
    if (callable_module_path == typing_module_path
            and callable_object_path == type_var_object_path):
        maybe_bound_type_node = next((keyword.value
                                      for keyword in ast_node.keywords
                                      if keyword.arg == 'bound'),
                                     None)
        if maybe_bound_type_node is None:
            return _from_signatures(*[_from_ast(argument, module_path)
                                      for argument in ast_node.args[1:]])
        else:
            return _from_ast(maybe_bound_type_node, module_path)
    raise _SignatureNotFound


@_from_ast.register(_ast.AsyncFunctionDef)
@_from_ast.register(_ast.FunctionDef)
def _(ast_node: _ast.FunctionDef, module_path: _catalog.Path) -> _Signature:
    signature_ast = ast_node.args
    parameters = filter(
            None,
            (*_to_positional_parameters(signature_ast, module_path),
             _to_variadic_positional_parameter(signature_ast, module_path),
             *_to_keyword_parameters(signature_ast, module_path),
             _to_variadic_keyword_parameter(signature_ast, module_path))
    )
    return _PlainSignature(*parameters)


class _SignatureNotFound(Exception):
    pass


def _try_resolve_object_path(
        module_path: _catalog.Path, object_path: _catalog.Path
) -> _catalog.QualifiedPath:
    try:
        return _scoping.resolve_object_path(
                module_path, (), object_path, _stubs.definitions,
                _stubs.references, _stubs.sub_scopes
        )
    except _scoping.ObjectNotFound:
        return (), ()


def _from_callable(
        value: _t.Callable[..., _t.Any],
        *,
        object_builder_qualified_path: _catalog.QualifiedPath
        = (_catalog.module_path_from_module(_builtins),
           _catalog.path_from_string(object.__qualname__)
           + _catalog.path_from_string(object.__new__.__name__))
) -> _Signature:
    qualified_paths = resolve_qualified_paths(value)
    if not qualified_paths:
        raise _SignatureNotFound
    module_path, object_path = qualified_paths[0]
    if (isinstance(value, type)
            or (_stubs.nodes_kinds[module_path][object_path]
                == _NodeKind.CLASS)):
        builders_qualified_paths = {
            _to_class_builder_qualified_path(module_path, object_path)
            for module_path, object_path in qualified_paths
        }
        try:
            (module_path, object_path), = builders_qualified_paths
        except ValueError:
            try:
                builders_qualified_paths.remove(object_builder_qualified_path)
                (module_path, object_path), = builders_qualified_paths
            except (KeyError, ValueError):
                raise _SignatureNotFound
    try:
        raw_ast_nodes = _stubs.raw_ast_nodes[module_path][object_path]
    except KeyError:
        raise _SignatureNotFound
    assert raw_ast_nodes, (module_path, object_path)
    ast_nodes = [_construction.from_raw(raw_ast_node)
                 for raw_ast_node in raw_ast_nodes]
    return _from_signatures(*[_from_ast(ast_node, module_path)
                              for ast_node in ast_nodes])


def resolve_qualified_paths(
        value: _t.Callable[..., _t.Any]
) -> _t.List[_catalog.QualifiedPath]:
    module_path, object_path = _catalog.qualified_path_from(value)
    try:
        candidates_paths = _qualified_paths[module_path][object_path]
    except KeyError:
        if module_path:
            assert object_path, value
            qualified_paths = [(module_path, object_path)]
        else:
            qualified_paths = []
    else:
        qualified_paths = [path
                           for path in candidates_paths
                           if _value_has_qualified_path(value, path)]
    return sorted({
        (module_path, object_path)
        for module_path, object_path in [
            _try_resolve_object_path(module_path, object_path)
            for module_path, object_path in qualified_paths
        ]
        if module_path and object_path
    })


def _to_class_builder_qualified_path(
        module_path: _catalog.Path,
        object_path: _catalog.Path,
        *,
        object_builder_qualified_path: _catalog.QualifiedPath
        = (_catalog.module_path_from_module(_builtins),
           _catalog.path_from_string(object.__qualname__)
           + _catalog.path_from_string(object.__new__.__name__)),
        constructor_name: str = object.__new__.__name__,
        initializer_name: str = object.__init__.__name__
) -> _catalog.QualifiedPath:
    for base_module_path, base_object_path in _to_mro(module_path,
                                                      object_path):
        base_module_annotations = _stubs.raw_ast_nodes[base_module_path]
        constructor_path = object_path + (constructor_name,)
        initializer_path = object_path + (initializer_name,)
        if initializer_path in base_module_annotations:
            return (base_module_path, initializer_path)
        elif constructor_path in base_module_annotations:
            return (base_module_path, constructor_path)
    return object_builder_qualified_path


def _to_mro(module_path: _catalog.Path,
            object_path: _catalog.Path) -> _t.Iterable[_catalog.QualifiedPath]:
    yield (module_path, object_path)
    try:
        bases = _stubs.sub_scopes[module_path][object_path]
    except KeyError:
        return
    else:
        for base_module_path, base_object_path in bases:
            yield from _to_mro(base_module_path, base_object_path)


def _value_has_qualified_path(value: _t.Any,
                              path: _catalog.QualifiedPath) -> bool:
    module_path, object_path = path
    module_name = _catalog.path_to_string(module_path)
    candidate = _sys.modules.get(module_name)
    if candidate is None:
        # undecidable, let's keep it
        return True
    for part in object_path:
        try:
            candidate = getattr(candidate, part)
        except AttributeError:
            return False
    return candidate is value


def _from_raw_signature(object_: _inspect.Signature) -> _Signature:
    return _PlainSignature(*[
        _Parameter(annotation=(_t.Any
                               if raw.annotation is _inspect._empty
                               else raw.annotation),
                   name=raw.name,
                   kind=_Parameter.Kind(raw.kind),
                   has_default=raw.default is not _inspect._empty)
        for raw in object_.parameters.values()
    ])


def _parameter_from_ast_node(ast_node: _ast.arg,
                             default_ast: _t.Optional[_ast.expr],
                             module_path: _catalog.Path,
                             *,
                             kind: _Parameter.Kind) -> _Parameter:
    return _Parameter(annotation=(_t.Any
                                  if ast_node.annotation is None
                                  else _evaluate_ast_node(ast_node.annotation,
                                                          module_path, {})),
                      has_default=default_ast is not None,
                      kind=kind,
                      name=ast_node.arg)


def _to_keyword_parameters(
        signature_ast: _ast.arguments,
        module_path: _catalog.Path
) -> _t.Iterable[_Parameter]:
    kind = _Parameter.Kind.KEYWORD_ONLY
    return [_parameter_from_ast_node(parameter_ast, default_ast, module_path,
                                     kind=kind)
            for parameter_ast, default_ast in zip(signature_ast.kwonlyargs,
                                                  signature_ast.kw_defaults)]


def _to_positional_parameters(
        signature_ast: _ast.arguments,
        module_path: _catalog.Path
) -> _t.Iterable[_Parameter]:
    # double-reversing since parameters with default arguments go last
    parameters_with_defaults_ast: _t.List[
        _t.Tuple[_ast.arg, _t.Optional[_ast.expr]]
    ] = list(_zip_longest(reversed(signature_ast.args),
                          signature_ast.defaults))[::-1]
    kind = _Parameter.Kind.POSITIONAL_ONLY
    return [_parameter_from_ast_node(parameter_ast, default_ast, module_path,
                                     kind=kind)
            for parameter_ast, default_ast in parameters_with_defaults_ast]


def _to_variadic_keyword_parameter(
        signature_ast: _ast.arguments,
        module_path: _catalog.Path
) -> _t.Optional[_Parameter]:
    ast_node = signature_ast.kwarg
    return (
        None
        if ast_node is None
        else _parameter_from_ast_node(ast_node, None, module_path,
                                      kind=_Parameter.Kind.VARIADIC_KEYWORD)
    )


def _to_variadic_positional_parameter(
        signature_ast: _ast.arguments,
        module_path: _catalog.Path
) -> _t.Optional[_Parameter]:
    ast_node = signature_ast.vararg
    return (
        None
        if ast_node is None
        else _parameter_from_ast_node(ast_node, None, module_path,
                                      kind=_Parameter.Kind.VARIADIC_POSITIONAL)
    )
