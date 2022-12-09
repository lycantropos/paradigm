import ast as _ast
import builtins as _builtins
import inspect as _inspect
import sys as _sys
import types as _types
import typing as _t
from functools import (partial as _partial,
                       singledispatch as _singledispatch)
from itertools import zip_longest as _zip_longest

from typing_extensions import Self as _Self

from . import (catalog as _catalog,
               scoping as _scoping,
               stubs as _stubs)
from .arboreal import (construction as _construction,
                       conversion as _conversion)
from .arboreal.evaluation import (
    evaluate_expression_node as _evaluate_expression_node
)
from .arboreal.kind import NodeKind as _NodeKind
from .arboreal.utils import subscript_to_item as _subscript_to_item
from .models import (OptionalParameter as _OptionalParameter,
                     Parameter as _Parameter,
                     ParameterKind as _ParameterKind,
                     PlainSignature as _PlainSignature,
                     RequiredParameter as _RequiredParameter,
                     Signature as _Signature,
                     from_signatures as _from_signatures)
from .modules import supported_stdlib_qualified_paths as _qualified_paths
from .utils import decorate_if as _decorate_if


@_singledispatch
def from_callable(_callable: _t.Callable[..., _t.Any]) -> _Signature:
    raise TypeError(type(_callable))


@from_callable.register(_types.BuiltinFunctionType)
@_decorate_if(from_callable.register(_types.BuiltinMethodType),
              _sys.implementation.name != 'pypy')
def _(
        _callable: _t.Union[_types.BuiltinFunctionType,
                            _types.BuiltinMethodType]
) -> _Signature:
    try:
        return ((_from_callable(_callable)
                 if isinstance(_callable.__self__, type)
                 else (_from_callable(getattr(type(_callable.__self__),
                                              _callable.__name__))
                       .bind(_callable.__self__)))
                if (_callable.__self__ is not None
                    and not isinstance(_callable.__self__, _types.ModuleType))
                else _from_callable(_callable))
    except _SignatureNotFound:
        return _from_raw_signature(_inspect.signature(_callable))


@from_callable.register(_types.FunctionType)
def _(_callable: _types.FunctionType) -> _Signature:
    try:
        return _from_callable(_callable)
    except _SignatureNotFound:
        return _from_raw_signature(_inspect.signature(_callable))


@from_callable.register(_types.MethodType)
def _(_callable: _types.MethodType) -> _Signature:
    try:
        return (_from_callable(_callable)
                if isinstance(_callable.__self__, type)
                else (_from_callable(getattr(type(_callable.__self__),
                                             _callable.__name__))
                      .bind(_callable.__self__)))
    except _SignatureNotFound:
        return _from_raw_signature(_inspect.signature(_callable))


@_decorate_if(from_callable.register(_types.MethodWrapperType),
              _sys.implementation.name != 'pypy')
def _(_callable: _types.MethodWrapperType) -> _Signature:
    self = _callable.__self__
    assert not isinstance(self, type), _callable
    try:
        return (_from_callable(getattr(type(self), _callable.__name__))
                .bind(self))
    except _SignatureNotFound:
        return _from_raw_signature(_inspect.signature(_callable))


@_decorate_if(from_callable.register(_types.MethodDescriptorType),
              _sys.implementation.name != 'pypy')
@_decorate_if(from_callable.register(_types.WrapperDescriptorType),
              _sys.implementation.name != 'pypy')
def _(_callable: _t.Union[_types.MethodDescriptorType,
                          _types.WrapperDescriptorType]) -> _Signature:
    cls = _callable.__objclass__
    assert isinstance(cls, type), _callable
    try:
        return _from_callable(_callable)
    except _SignatureNotFound:
        return _from_raw_signature(_inspect.signature(_callable))


@from_callable.register(type)
def _(_callable: _t.Callable[..., _t.Any]) -> _Signature:
    try:
        qualified_paths = resolve_qualified_paths(_callable)
        if not qualified_paths:
            raise _SignatureNotFound
        module_path, object_path = _resolve_builder_qualified_path(
                qualified_paths
        )
        ast_nodes = _load_ast_nodes(module_path, object_path)
        class_path, builder_name = object_path[:-1], object_path[-1]
        return _from_signatures(*[_from_statement_node(ast_node, _callable,
                                                       module_path, class_path)
                                  for ast_node in ast_nodes])
    except _SignatureNotFound:
        raw_signature = _inspect.signature(_callable)
        return _from_raw_signature(
                raw_signature.replace(return_annotation=_Self)
        )


@from_callable.register(_partial)
def _(_callable: _partial) -> _Signature:
    return from_callable(_callable.func).bind(*_callable.args,
                                              **_callable.keywords)


@_singledispatch
def _from_expression_node(ast_node: _ast.expr,
                          callable_: _t.Callable[..., _t.Any],
                          module_path: _catalog.Path,
                          parent_path: _catalog.Path) -> _Signature:
    raise TypeError(ast_node)


@_from_expression_node.register(_ast.Attribute)
@_from_expression_node.register(_ast.Name)
def _(ast_node: _t.Union[_ast.Attribute, _ast.Name],
      callable_: _t.Callable[..., _t.Any],
      module_path: _catalog.Path,
      parent_path: _catalog.Path,
      *,
      call_name: str = object.__call__.__name__) -> _Signature:
    object_path = _conversion.to_path(ast_node)
    module_path, object_path = _scoping.resolve_object_path(
            module_path, parent_path, object_path, _stubs.definitions,
            _stubs.references, _stubs.submodules, _stubs.superclasses
    )
    node_kind = _stubs.nodes_kinds[module_path][object_path]
    if node_kind is _NodeKind.CLASS:
        call_ast_nodes = _load_ast_nodes(module_path,
                                         (*object_path, call_name))
        call_signatures = [_from_statement_node(ast_node, callable_,
                                                module_path, ())
                           for ast_node in call_ast_nodes]
        return _from_signatures(*[signature.bind(callable_)
                                  for signature in call_signatures])
    else:
        annotation_nodes = [
            _construction.from_raw(raw)
            for raw in _stubs.raw_ast_nodes[module_path][object_path]
        ]
        if len(annotation_nodes) == 1:
            annotation_node, = annotation_nodes
            assert isinstance(annotation_node, _ast.stmt), (module_path,
                                                            object_path)
            return _from_statement_node(annotation_node, callable_,
                                        module_path, ())
    raise _SignatureNotFound


@_from_expression_node.register(_ast.Call)
def _(ast_node: _ast.Call,
      callable_: _t.Callable[..., _t.Any],
      module_path: _catalog.Path,
      parent_path: _catalog.Path,
      *,
      type_var_object_path: _catalog.Path
      = _catalog.path_from_string(_t.TypeVar.__qualname__),
      typing_module_path: _catalog.Path
      = _catalog.module_path_from_module(_t)) -> _Signature:
    callable_object_path = _conversion.to_path(ast_node.func)
    callable_module_path, callable_object_path = _scoping.resolve_object_path(
            module_path, parent_path, callable_object_path, _stubs.definitions,
            _stubs.references, _stubs.submodules, _stubs.superclasses
    )
    if (callable_module_path == typing_module_path
            and callable_object_path == type_var_object_path):
        maybe_bound_type_node = next((keyword.value
                                      for keyword in ast_node.keywords
                                      if keyword.arg == 'bound'),
                                     None)
        return (
            _from_signatures(
                    *[_from_expression_node(argument, callable_, module_path,
                                            parent_path)
                      for argument in ast_node.args[1:]]
            )
            if maybe_bound_type_node is None
            else _from_expression_node(maybe_bound_type_node, callable_,
                                       module_path, parent_path)
        )
    raise _SignatureNotFound


@_from_expression_node.register(_ast.Subscript)
def _(ast_node: _ast.Subscript,
      callable_: _t.Callable[..., _t.Any],
      module_path: _catalog.Path,
      parent_path: _catalog.Path,
      *,
      callable_object_path: _catalog.Path = ('Callable',),
      typing_module_path: _catalog.Path
      = _catalog.module_path_from_module(_t)) -> _Signature:
    value_path = _conversion.to_path(ast_node.value)
    value_module_path, value_object_path = _scoping.resolve_object_path(
            module_path, parent_path, value_path, _stubs.definitions,
            _stubs.references, _stubs.submodules, _stubs.superclasses
    )
    if (value_module_path == typing_module_path
            and value_object_path == callable_object_path):
        callable_arguments = _subscript_to_item(ast_node)
        assert isinstance(callable_arguments, _ast.Tuple)
        arguments_annotations, returns_annotation = callable_arguments.elts
        return (
            _PlainSignature(
                    *[
                        _RequiredParameter(
                                annotation=_evaluate_expression_node(
                                        annotation, module_path, parent_path,
                                        {}
                                ),
                                kind=_ParameterKind.POSITIONAL_ONLY,
                                name='_' + str(index),
                        )
                        for index, annotation in enumerate(
                                arguments_annotations.elts
                        )
                    ],
                    returns=_evaluate_expression_node(
                            returns_annotation, module_path, parent_path, {}
                    )
            )
            if isinstance(arguments_annotations, _ast.List)
            # unspecified parameters case
            else _PlainSignature(
                    _OptionalParameter(annotation=_t.Any,
                                       kind=_ParameterKind.VARIADIC_POSITIONAL,
                                       name='args'),
                    _OptionalParameter(annotation=_t.Any,
                                       kind=_ParameterKind.VARIADIC_KEYWORD,
                                       name='kwargs'),
                    returns=_evaluate_expression_node(
                            returns_annotation, module_path, parent_path, {}
                    )
            )
        )
    raise _SignatureNotFound


@_singledispatch
def _from_statement_node(ast_node: _ast.stmt,
                         callable_: _t.Callable[..., _t.Any],
                         module_path: _catalog.Path,
                         parent_path: _catalog.Path) -> _Signature:
    raise TypeError(ast_node)


@_from_statement_node.register(_ast.AnnAssign)
def _(ast_node: _ast.AnnAssign,
      callable_: _t.Callable[..., _t.Any],
      module_path: _catalog.Path,
      parent_path: _catalog.Path) -> _Signature:
    return _from_expression_node((ast_node.annotation
                                  if ast_node.value is None
                                  else ast_node.value), callable_, module_path,
                                 parent_path)


@_from_statement_node.register(_ast.Assign)
def _(ast_node: _ast.Assign,
      callable_: _t.Callable[..., _t.Any],
      module_path: _catalog.Path,
      parent_path: _catalog.Path) -> _Signature:
    return _from_expression_node(ast_node.value, callable_, module_path,
                                 parent_path)


@_from_statement_node.register(_ast.AsyncFunctionDef)
@_from_statement_node.register(_ast.FunctionDef)
def _(
        ast_node: _t.Union[_ast.AsyncFunctionDef, _ast.FunctionDef],
        callable_: _t.Callable[..., _t.Any],
        module_path: _catalog.Path,
        parent_path: _catalog.Path
) -> _Signature:
    parameters = _parameters_from(ast_node, callable_, module_path,
                                  parent_path)
    returns = _returns_annotation_from(ast_node, callable_, module_path,
                                       parent_path)
    return _PlainSignature(*parameters,
                           returns=returns)


def _parameters_from(
        ast_node: _t.Union[_ast.AsyncFunctionDef, _ast.FunctionDef],
        callable_: _t.Callable[..., _t.Any],
        module_path: _catalog.Path,
        parent_path: _catalog.Path
) -> _t.List[_Parameter]:
    signature_ast = ast_node.args
    result: _t.List[_Parameter] = list(filter(
            None,
            (*_to_positional_parameters(signature_ast, module_path,
                                        parent_path),
             _to_variadic_positional_parameter(signature_ast, module_path,
                                               parent_path),
             *_to_keyword_parameters(signature_ast, module_path, parent_path),
             _to_variadic_keyword_parameter(signature_ast, module_path,
                                            parent_path))
    ))
    if isinstance(callable_, type):
        del result[0]
    elif any(_is_classmethod(decorator_node, module_path, parent_path)
             for decorator_node in ast_node.decorator_list):
        result[0] = _RequiredParameter(annotation=_t.Type[_Self],
                                       kind=_ParameterKind.POSITIONAL_ONLY,
                                       name=result[0].name)
    elif _stubs.nodes_kinds[module_path].get(parent_path) is _NodeKind.CLASS:
        result[0] = _RequiredParameter(annotation=_Self,
                                       kind=_ParameterKind.POSITIONAL_ONLY,
                                       name=result[0].name)
    return result


def _returns_annotation_from(
        ast_node: _t.Union[_ast.AsyncFunctionDef, _ast.FunctionDef],
        callable_: _t.Callable[..., _t.Any],
        module_path: _catalog.Path,
        parent_path: _catalog.Path,
        *,
        initializer_name: str = object.__init__.__name__
) -> _t.Any:
    returns_node = ast_node.returns
    return (_Self
            if (isinstance(callable_, type)
                and ast_node.name == initializer_name)
            else (_t.Any
                  if returns_node is None
                  else _evaluate_expression_node(returns_node, module_path,
                                                 parent_path, {})))


def _is_classmethod(
        expression_node: _ast.expr,
        module_path: _catalog.Path,
        parent_path: _catalog.Path,
        *,
        classmethod_qualified_path: _catalog.QualifiedPath
        = (_catalog.module_path_from_module(_builtins),
           _catalog.path_from_string(classmethod.__qualname__)),
) -> bool:
    maybe_path = _conversion.to_maybe_path(expression_node)
    return (maybe_path is not None
            and _scoping.resolve_object_path(
                    module_path, parent_path, maybe_path, _stubs.definitions,
                    _stubs.references, _stubs.submodules, _stubs.superclasses
            ) == classmethod_qualified_path)


class _SignatureNotFound(Exception):
    pass


def _try_resolve_object_path(
        module_path: _catalog.Path, object_path: _catalog.Path
) -> _catalog.QualifiedPath:
    try:
        return _scoping.resolve_object_path(
                module_path, (), object_path, _stubs.definitions,
                _stubs.references, _stubs.submodules, _stubs.superclasses
        )
    except _scoping.ObjectNotFound:
        return (), ()


def _from_callable(value: _t.Callable[..., _t.Any]) -> _Signature:
    for module_path, object_path in _to_qualified_paths(value):
        ast_nodes = _load_ast_nodes(module_path, object_path)
        parent_path = object_path[:-1]
        try:
            signatures = [
                _from_statement_node(ast_node, value, module_path, parent_path)
                for ast_node in ast_nodes
            ]
        except _SignatureNotFound:
            continue
        else:
            return _from_signatures(*signatures)
    raise _SignatureNotFound


def _to_qualified_paths(
        value: _t.Callable[..., _t.Any]
) -> _t.Iterable[_catalog.QualifiedPath]:
    qualified_paths = resolve_qualified_paths(value)
    if qualified_paths:
        module_path, object_path = qualified_paths[0]
        if _stubs.nodes_kinds[module_path][object_path] is _NodeKind.CLASS:
            yield _resolve_builder_qualified_path(qualified_paths)
        else:
            yield from qualified_paths


def _resolve_builder_qualified_path(
        qualified_paths: _t.Sequence[_catalog.QualifiedPath],
        *,
        object_builder_qualified_path: _catalog.QualifiedPath
        = (_catalog.module_path_from_module(_builtins),
           _catalog.path_from_string(object.__qualname__)
           + _catalog.path_from_string(object.__new__.__name__))
) -> _catalog.QualifiedPath:
    candidates = {_to_class_builder_qualified_path(module_path, object_path)
                  for module_path, object_path in qualified_paths}
    try:
        (module_path, object_path), = candidates
    except ValueError:
        try:
            candidates.remove(object_builder_qualified_path)
            (module_path, object_path), = candidates
        except (KeyError, ValueError):
            raise _SignatureNotFound
    return module_path, object_path


def _load_ast_nodes(module_path: _catalog.Path,
                    object_path: _catalog.Path) -> _t.List[_ast.stmt]:
    try:
        raw_ast_nodes = _stubs.raw_ast_nodes[module_path][object_path]
    except KeyError:
        raise _SignatureNotFound
    else:
        assert raw_ast_nodes, (module_path, object_path)
        return [_statement_node_from_raw(raw_ast_node)
                for raw_ast_node in raw_ast_nodes]


def _statement_node_from_raw(raw: _conversion.RawAstNode) -> _ast.stmt:
    result = _construction.from_raw(raw)
    assert isinstance(result, _ast.stmt), raw
    return result


def resolve_qualified_paths(
        value: _t.Callable[..., _t.Any]
) -> _t.List[_catalog.QualifiedPath]:
    module_path, object_path = _catalog.qualified_path_from(value)
    try:
        candidates_paths = _qualified_paths[module_path][object_path]
    except KeyError:
        assert not module_path or object_path, value
        qualified_paths = ([(module_path, object_path)]
                           if module_path
                           else [])
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
        constructor_path = (*object_path, constructor_name)
        initializer_path = (*object_path, initializer_name)
        if initializer_path in base_module_annotations:
            return (base_module_path, initializer_path)
        elif constructor_path in base_module_annotations:
            return (base_module_path, constructor_path)
    return object_builder_qualified_path


def _to_mro(module_path: _catalog.Path,
            object_path: _catalog.Path) -> _t.Iterable[_catalog.QualifiedPath]:
    yield (module_path, object_path)
    try:
        bases = _stubs.superclasses[module_path][object_path]
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


def _parameter_from_raw(raw: _inspect.Parameter) -> _Parameter:
    annotation, kind, name = (
        _t.Any if raw.annotation is _inspect._empty else raw.annotation,
        _ParameterKind(raw.kind), raw.name
    )
    return ((_OptionalParameter(annotation=annotation,
                                kind=kind,
                                name=name)
             if (kind is _ParameterKind.VARIADIC_POSITIONAL
                 or kind is _ParameterKind.VARIADIC_KEYWORD)
             else _RequiredParameter(annotation=annotation,
                                     kind=kind,
                                     name=name))
            if raw.default is _inspect._empty
            else _OptionalParameter(annotation=annotation,
                                    default=raw.default,
                                    kind=kind,
                                    name=name))


def _from_raw_signature(value: _inspect.Signature) -> _Signature:
    return _PlainSignature(
            *[_parameter_from_raw(raw) for raw in value.parameters.values()],
            returns=(_t.Any
                     if value.return_annotation is _inspect._empty
                     else value.return_annotation)
    )


def _parameter_from_ast_node(ast_node: _ast.arg,
                             default_ast: _t.Optional[_ast.expr],
                             module_path: _catalog.Path,
                             parent_path: _catalog.Path,
                             kind: _ParameterKind) -> _Parameter:
    annotation = (_t.Any
                  if ast_node.annotation is None
                  else _evaluate_expression_node(ast_node.annotation,
                                                 module_path, parent_path, {}))
    name = ast_node.arg
    if default_ast is not None:
        default = _evaluate_expression_node(default_ast, module_path,
                                            parent_path, {})
        return _OptionalParameter(annotation=annotation,
                                  **({}
                                     if default is Ellipsis
                                     else {'default': default}),
                                  kind=kind,
                                  name=name)
    else:
        return (_OptionalParameter
                if (kind is _ParameterKind.VARIADIC_POSITIONAL
                    or kind is _ParameterKind.VARIADIC_KEYWORD)
                else _RequiredParameter)(annotation=annotation,
                                         kind=kind,
                                         name=name)


def _to_keyword_parameters(
        signature_ast: _ast.arguments,
        module_path: _catalog.Path,
        parent_path: _catalog.Path,
        *,
        kind: _ParameterKind = _ParameterKind.KEYWORD_ONLY
) -> _t.List[_Parameter]:
    return [_parameter_from_ast_node(parameter_ast, default_ast, module_path,
                                     parent_path, kind)
            for parameter_ast, default_ast in zip(signature_ast.kwonlyargs,
                                                  signature_ast.kw_defaults)]


def _to_positional_parameters(
        signature_ast: _ast.arguments,
        module_path: _catalog.Path,
        parent_path: _catalog.Path
) -> _t.List[_Parameter]:
    # double-reversing since parameters with default arguments go last
    parameters_with_defaults_ast: _t.List[
        _t.Tuple[_ast.arg, _t.Optional[_ast.expr]]
    ] = list(_zip_longest(reversed(signature_ast.args),
                          signature_ast.defaults))[::-1]
    kind = _ParameterKind.POSITIONAL_ONLY
    return [_parameter_from_ast_node(parameter_ast, default_ast, module_path,
                                     parent_path, kind)
            for parameter_ast, default_ast in parameters_with_defaults_ast]


def _to_variadic_keyword_parameter(
        signature_ast: _ast.arguments,
        module_path: _catalog.Path,
        parent_path: _catalog.Path,
        *,
        kind: _ParameterKind = _ParameterKind.VARIADIC_KEYWORD
) -> _t.Optional[_Parameter]:
    ast_node = signature_ast.kwarg
    return (None
            if ast_node is None
            else _parameter_from_ast_node(ast_node, None, module_path,
                                          parent_path, kind))


def _to_variadic_positional_parameter(
        signature_ast: _ast.arguments,
        module_path: _catalog.Path,
        parent_path: _catalog.Path,
        *,
        kind: _ParameterKind = _ParameterKind.VARIADIC_POSITIONAL
) -> _t.Optional[_Parameter]:
    ast_node = signature_ast.vararg
    return (None
            if ast_node is None
            else _parameter_from_ast_node(ast_node, None, module_path,
                                          parent_path, kind))
