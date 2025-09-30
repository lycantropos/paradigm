from __future__ import annotations

import ast as _ast
import builtins as _builtins
import inspect as _inspect
import sys as _sys
import types as _types
import typing as _t
from collections.abc import Callable, Iterable, Sequence
from functools import partial as _partial, singledispatch as _singledispatch
from itertools import starmap, zip_longest as _zip_longest
from typing import Any, Final, TypeVar

from typing_extensions import Self as _Self

from . import catalog as _catalog, scoping as _scoping, stubs as _stubs
from .arboreal import conversion as _conversion
from .arboreal.evaluation import (
    evaluate_expression_node as _evaluate_expression_node,
)
from .arboreal.kind import StatementNodeKind as _NodeKind
from .arboreal.utils import subscript_to_item as _subscript_to_item
from .models import (
    OptionalParameter as _OptionalParameter,
    Parameter as _Parameter,
    ParameterKind as _ParameterKind,
    PlainSignature as _PlainSignature,
    RequiredParameter as _RequiredParameter,
    Signature as _Signature,
    from_signatures as _from_signatures,
)
from .modules import supported_stdlib_qualified_paths as _qualified_paths
from .utils import decorate_if as _decorate_if


@_singledispatch
def from_callable(callable_: Callable[..., Any], /) -> _Signature:
    raise TypeError(type(callable_))


@from_callable.register(_types.BuiltinFunctionType)
@_decorate_if(
    from_callable.register(_types.BuiltinMethodType),
    _sys.implementation.name != 'pypy',
)
def _(
    callable_: _types.BuiltinFunctionType | _types.BuiltinMethodType, /
) -> _Signature:
    try:
        return (
            (
                _from_callable(callable_)
                if isinstance(callable_.__self__, type)
                else (
                    _from_callable(
                        getattr(type(callable_.__self__), callable_.__name__)
                    ).bind(callable_.__self__)
                )
            )
            if (
                callable_.__self__ is not None
                and not isinstance(callable_.__self__, _types.ModuleType)
            )
            else _from_callable(callable_)
        )
    except _SignatureNotFound:
        return _from_raw_signature(_to_raw_signature(callable_))


@from_callable.register(_types.FunctionType)
def _(callable_: _types.FunctionType, /) -> _Signature:
    try:
        return _from_callable(callable_)
    except _SignatureNotFound:
        return _from_raw_signature(_to_raw_signature(callable_))


@from_callable.register(_types.MethodType)
def _(callable_: _types.MethodType, /) -> _Signature:
    try:
        return (
            _from_callable(callable_)
            if isinstance(callable_.__self__, type)
            else (
                _from_callable(
                    getattr(type(callable_.__self__), callable_.__name__)
                ).bind(callable_.__self__)
            )
        )
    except _SignatureNotFound:
        return _from_raw_signature(_to_raw_signature(callable_))


@_decorate_if(
    from_callable.register(_types.MethodWrapperType),
    _sys.implementation.name != 'pypy',
)
def _(callable_: _types.MethodWrapperType, /) -> _Signature:
    self = callable_.__self__
    assert not isinstance(self, type), callable_
    try:
        return _from_callable(getattr(type(self), callable_.__name__)).bind(
            self
        )
    except _SignatureNotFound:
        return _from_raw_signature(_to_raw_signature(callable_))


@_decorate_if(
    from_callable.register(_types.MethodDescriptorType),
    _sys.implementation.name != 'pypy',
)
@_decorate_if(
    from_callable.register(_types.WrapperDescriptorType),
    _sys.implementation.name != 'pypy',
)
def _(
    callable_: _types.MethodDescriptorType | _types.WrapperDescriptorType, /
) -> _Signature:
    cls = callable_.__objclass__
    assert isinstance(cls, type), callable_
    try:
        return _from_callable(callable_)
    except _SignatureNotFound:
        return _from_raw_signature(_to_raw_signature(callable_))


@from_callable.register(type)
def _(_callable: Callable[..., Any], /) -> _Signature:
    try:
        qualified_paths = resolve_qualified_paths(_callable)
        if not qualified_paths:
            raise _SignatureNotFound
        module_path, object_path = _resolve_builder_qualified_path(
            qualified_paths
        )
        ast_nodes = _load_statements_nodes(module_path, object_path)
        class_path, _builder_name = object_path[:-1], object_path[-1]
        return _from_signatures(
            *[
                _from_statement_node(
                    ast_node, _callable, module_path, class_path
                )
                for ast_node in ast_nodes
            ]
        )
    except _SignatureNotFound:
        return _from_raw_signature(
            _to_raw_signature(_callable).replace(return_annotation=_Self)
        )


@from_callable.register(_partial)
def _(_callable: _partial[Any], /) -> _Signature:
    return from_callable(_callable.func).bind(
        *_callable.args, **_callable.keywords
    )


@_singledispatch
def _from_expression_node(
    ast_node: _ast.expr,
    _callable: Callable[..., Any],
    _module_path: _catalog.Path,
    _parent_path: _catalog.Path,
    /,
) -> _Signature:
    raise TypeError(ast_node)


@_from_expression_node.register(_ast.Attribute)
@_from_expression_node.register(_ast.Name)
def _(
    ast_node: _ast.Attribute | _ast.Name,
    callable_: Callable[..., Any],
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    /,
    *,
    call_name: str = object.__call__.__name__,
) -> _Signature:
    object_path = _conversion.to_path(ast_node)
    module_path, object_path = _scoping.resolve_object_path(
        module_path,
        parent_path,
        object_path,
        _stubs.definitions,
        _stubs.references,
        _stubs.submodules,
        _stubs.superclasses,
    )
    node_kind = _stubs.statements_nodes_kinds[module_path][object_path]
    if node_kind is _NodeKind.CLASS:
        call_ast_nodes = _load_statements_nodes(
            module_path, (*object_path, call_name)
        )
        call_signatures = [
            _from_statement_node(ast_node, callable_, module_path, ())
            for ast_node in call_ast_nodes
        ]
        return _from_signatures(
            *[signature.bind(callable_) for signature in call_signatures]
        )
    annotation_nodes = _stubs.statements_nodes[module_path][object_path]
    if len(annotation_nodes) == 1:
        (annotation_node,) = annotation_nodes
        assert isinstance(annotation_node, _ast.stmt), (
            module_path,
            object_path,
        )
        return _from_statement_node(
            annotation_node, callable_, module_path, ()
        )
    raise _SignatureNotFound


@_from_expression_node.register(_ast.Call)
def _(
    ast_node: _ast.Call,
    callable_: Callable[..., Any],
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    /,
    *,
    type_var_object_path: _catalog.Path = _catalog.path_from_string(  # noqa: B008
        TypeVar.__qualname__
    ),
    typing_module_path: _catalog.Path = _catalog.module_path_from_module(_t),  # noqa: B008
) -> _Signature:
    callable_object_path = _conversion.to_path(ast_node.func)
    callable_module_path, callable_object_path = _scoping.resolve_object_path(
        module_path,
        parent_path,
        callable_object_path,
        _stubs.definitions,
        _stubs.references,
        _stubs.submodules,
        _stubs.superclasses,
    )
    if (
        callable_module_path == typing_module_path
        and callable_object_path == type_var_object_path
    ):
        maybe_bound_type_node = next(
            (
                keyword.value
                for keyword in ast_node.keywords
                if keyword.arg == 'bound'
            ),
            None,
        )
        return (
            _from_signatures(
                *[
                    _from_expression_node(
                        argument, callable_, module_path, parent_path
                    )
                    for argument in ast_node.args[1:]
                ]
            )
            if maybe_bound_type_node is None
            else _from_expression_node(
                maybe_bound_type_node, callable_, module_path, parent_path
            )
        )
    raise _SignatureNotFound


@_from_expression_node.register(_ast.Subscript)
def _(
    ast_node: _ast.Subscript,
    _callable: Callable[..., Any],
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    /,
    *,
    callable_object_path: _catalog.Path = ('Callable',),
    typing_module_path: _catalog.Path = _catalog.module_path_from_module(_t),  # noqa: B008
) -> _Signature:
    value_path = _conversion.to_path(ast_node.value)
    value_module_path, value_object_path = _scoping.resolve_object_path(
        module_path,
        parent_path,
        value_path,
        _stubs.definitions,
        _stubs.references,
        _stubs.submodules,
        _stubs.superclasses,
    )
    if (
        value_module_path == typing_module_path
        and value_object_path == callable_object_path
    ):
        callable_arguments = _subscript_to_item(ast_node)
        assert isinstance(callable_arguments, _ast.Tuple)
        arguments_annotations, returns_annotation = callable_arguments.elts
        return (
            _PlainSignature(
                *[
                    _RequiredParameter(
                        annotation=_evaluate_expression_node(
                            annotation, module_path, parent_path, {}
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
                ),
            )
            if isinstance(arguments_annotations, _ast.List)
            # unspecified parameters case
            else _PlainSignature(
                _OptionalParameter(
                    annotation=Any,
                    kind=_ParameterKind.VARIADIC_POSITIONAL,
                    name='args',
                ),
                _OptionalParameter(
                    annotation=Any,
                    kind=_ParameterKind.VARIADIC_KEYWORD,
                    name='kwargs',
                ),
                returns=_evaluate_expression_node(
                    returns_annotation, module_path, parent_path, {}
                ),
            )
        )
    raise _SignatureNotFound


@_singledispatch
def _from_statement_node(
    ast_node: _ast.stmt,
    _callable: Callable[..., Any],
    _module_path: _catalog.Path,
    _parent_path: _catalog.Path,
    /,
) -> _Signature:
    raise TypeError(ast_node)


@_from_statement_node.register(_ast.AnnAssign)
def _(
    ast_node: _ast.AnnAssign,
    callable_: Callable[..., Any],
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    /,
) -> _Signature:
    return _from_expression_node(
        (ast_node.annotation if ast_node.value is None else ast_node.value),
        callable_,
        module_path,
        parent_path,
    )


@_from_statement_node.register(_ast.Assign)
def _(
    ast_node: _ast.Assign,
    callable_: Callable[..., Any],
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    /,
) -> _Signature:
    return _from_expression_node(
        ast_node.value, callable_, module_path, parent_path
    )


@_from_statement_node.register(_ast.AsyncFunctionDef)
@_from_statement_node.register(_ast.FunctionDef)
def _(
    ast_node: _ast.AsyncFunctionDef | _ast.FunctionDef,
    callable_: Callable[..., Any],
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    /,
) -> _Signature:
    parameters = _parameters_from(
        ast_node, callable_, module_path, parent_path
    )
    returns = _returns_annotation_from(
        ast_node, callable_, module_path, parent_path
    )
    return _PlainSignature(*parameters, returns=returns)


def _parameters_from(
    ast_node: _ast.AsyncFunctionDef | _ast.FunctionDef,
    callable_: Callable[..., Any],
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    /,
) -> list[_Parameter]:
    signature_ast = ast_node.args
    result: list[_Parameter] = list(
        filter(
            None,
            (
                *_to_positional_parameters(
                    signature_ast, module_path, parent_path
                ),
                _to_variadic_positional_parameter(
                    signature_ast, module_path, parent_path
                ),
                *_to_keyword_parameters(
                    signature_ast, module_path, parent_path
                ),
                _to_variadic_keyword_parameter(
                    signature_ast, module_path, parent_path
                ),
            ),
        )
    )
    if isinstance(callable_, type):
        del result[0]
    elif any(
        _is_classmethod(decorator_node, module_path, parent_path)
        for decorator_node in ast_node.decorator_list
    ):
        result[0] = _RequiredParameter(
            annotation=type[_Self],  # pyright: ignore[reportGeneralTypeIssues]
            kind=_ParameterKind.POSITIONAL_ONLY,
            name=result[0].name,
        )
    elif (
        _stubs.statements_nodes_kinds[module_path].get(parent_path)
        is _NodeKind.CLASS
    ):
        result[0] = _RequiredParameter(
            annotation=_Self,
            kind=_ParameterKind.POSITIONAL_ONLY,
            name=result[0].name,
        )
    return result


def _returns_annotation_from(
    ast_node: _ast.AsyncFunctionDef | _ast.FunctionDef,
    callable_: Callable[..., Any],
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    /,
    *,
    initializer_name: str = object.__init__.__name__,
) -> Any:
    returns_node = ast_node.returns
    return (
        _Self
        if (isinstance(callable_, type) and ast_node.name == initializer_name)
        else (
            Any
            if returns_node is None
            else _evaluate_expression_node(
                returns_node, module_path, parent_path, {}
            )
        )
    )


def _is_classmethod(
    expression_node: _ast.expr,
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    /,
    *,
    classmethod_qualified_path: _catalog.QualifiedPath = (
        _catalog.module_path_from_module(_builtins),  # noqa: B008
        _catalog.path_from_string(classmethod.__qualname__),  # noqa: B008
    ),
) -> bool:
    maybe_path = _conversion.to_maybe_path(expression_node)
    return (
        maybe_path is not None
        and _scoping.resolve_object_path(
            module_path,
            parent_path,
            maybe_path,
            _stubs.definitions,
            _stubs.references,
            _stubs.submodules,
            _stubs.superclasses,
        )
        == classmethod_qualified_path
    )


class _SignatureNotFound(Exception):
    pass


def _try_resolve_object_path(
    module_path: _catalog.Path, object_path: _catalog.Path
) -> _catalog.QualifiedPath:
    try:
        return _scoping.resolve_object_path(
            module_path,
            (),
            object_path,
            _stubs.definitions,
            _stubs.references,
            _stubs.submodules,
            _stubs.superclasses,
        )
    except _scoping.ObjectNotFound:
        return (), ()


def _from_callable(value: Callable[..., Any]) -> _Signature:
    for module_path, object_path in _to_qualified_paths(value):
        nodes = _load_statements_nodes(module_path, object_path)
        parent_path = object_path[:-1]
        try:
            signatures = [
                _from_statement_node(node, value, module_path, parent_path)
                for node in nodes
            ]
        except _SignatureNotFound:
            continue
        else:
            return _from_signatures(*signatures)
    raise _SignatureNotFound


def _to_qualified_paths(
    value: Callable[..., Any],
) -> Iterable[_catalog.QualifiedPath]:
    qualified_paths = resolve_qualified_paths(value)
    if qualified_paths:
        module_path, object_path = qualified_paths[0]
        if (
            _stubs.statements_nodes_kinds[module_path][object_path]
            is _NodeKind.CLASS
        ):
            yield _resolve_builder_qualified_path(qualified_paths)
        else:
            yield from qualified_paths


_OBJECT_BUILDER_QUALIFIED_PATH: Final[_catalog.QualifiedPath] = (
    _catalog.module_path_from_module(_builtins),
    _catalog.path_from_string(object.__qualname__)
    + _catalog.path_from_string(object.__new__.__name__),
)


def _resolve_builder_qualified_path(
    qualified_paths: Sequence[_catalog.QualifiedPath],
    *,
    object_builder_qualified_path: _catalog.QualifiedPath = (
        _OBJECT_BUILDER_QUALIFIED_PATH
    ),
) -> _catalog.QualifiedPath:
    candidates = set(
        starmap(_to_class_builder_qualified_path, qualified_paths)
    )
    try:
        ((module_path, object_path),) = candidates
    except ValueError:
        try:
            candidates.remove(object_builder_qualified_path)
            ((module_path, object_path),) = candidates
        except (KeyError, ValueError):
            raise _SignatureNotFound from None
    return module_path, object_path


def _load_statements_nodes(
    module_path: _catalog.Path, object_path: _catalog.Path
) -> Sequence[_ast.stmt]:
    try:
        nodes = _stubs.statements_nodes[module_path][object_path]
    except KeyError:
        raise _SignatureNotFound from None
    else:
        assert len(nodes) > 0, (module_path, object_path)
        return nodes


def resolve_qualified_paths(
    value: Callable[..., Any],
) -> list[_catalog.QualifiedPath]:
    module_path, object_path = _catalog.qualified_path_from(value)
    try:
        candidates_paths = _qualified_paths[module_path][object_path]
    except KeyError:
        assert not module_path or object_path, value
        qualified_paths = [(module_path, object_path)] if module_path else []
    else:
        qualified_paths = [
            path
            for path in candidates_paths
            if _value_has_qualified_path(value, path)
        ]
    return sorted(
        {
            (module_path, object_path)
            for module_path, object_path in list(
                starmap(_try_resolve_object_path, qualified_paths)
            )
            if module_path and object_path
        }
    )


def _to_class_builder_qualified_path(
    module_path: _catalog.Path,
    object_path: _catalog.Path,
    *,
    object_builder_qualified_path: _catalog.QualifiedPath = (
        _OBJECT_BUILDER_QUALIFIED_PATH
    ),
    constructor_name: str = object.__new__.__name__,
    initializer_name: str = object.__init__.__name__,
) -> _catalog.QualifiedPath:
    for base_module_path, _base_object_path in _to_mro(
        module_path, object_path
    ):
        base_module_annotations = _stubs.statements_nodes[base_module_path]
        constructor_path = (*object_path, constructor_name)
        initializer_path = (*object_path, initializer_name)
        if initializer_path in base_module_annotations:
            return (base_module_path, initializer_path)
        if constructor_path in base_module_annotations:
            return (base_module_path, constructor_path)
    return object_builder_qualified_path


def _to_mro(
    module_path: _catalog.Path, object_path: _catalog.Path, /
) -> Iterable[_catalog.QualifiedPath]:
    yield (module_path, object_path)
    try:
        bases = _stubs.superclasses[module_path][object_path]
    except KeyError:
        return
    else:
        for base_module_path, base_object_path in bases:
            yield from _to_mro(base_module_path, base_object_path)


def _value_has_qualified_path(
    value: Any, path: _catalog.QualifiedPath, /
) -> bool:
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


def _parameter_from_raw(raw: _inspect.Parameter, /) -> _Parameter:
    annotation, kind, name = (
        Any if raw.annotation is _inspect.Parameter.empty else raw.annotation,
        _ParameterKind(raw.kind),
        raw.name,
    )
    return (
        (
            _OptionalParameter(annotation=annotation, kind=kind, name=name)
            if (
                kind is _ParameterKind.VARIADIC_POSITIONAL
                or kind is _ParameterKind.VARIADIC_KEYWORD
            )
            else _RequiredParameter(
                annotation=annotation, kind=kind, name=name
            )
        )
        if raw.default is _inspect.Parameter.empty
        else _OptionalParameter(
            annotation=annotation, default=raw.default, kind=kind, name=name
        )
    )


def _from_raw_signature(value: _inspect.Signature) -> _Signature:
    return _PlainSignature(
        *[_parameter_from_raw(raw) for raw in value.parameters.values()],
        returns=(
            Any
            if value.return_annotation is _inspect.Parameter.empty
            else value.return_annotation
        ),
    )


def _parameter_from_ast_node(
    ast_node: _ast.arg,
    default_ast: _ast.expr | None,
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    kind: _ParameterKind,
) -> _Parameter:
    annotation = (
        Any
        if ast_node.annotation is None
        else _evaluate_expression_node(
            ast_node.annotation, module_path, parent_path, {}
        )
    )
    name = ast_node.arg
    if default_ast is not None:
        default = _evaluate_expression_node(
            default_ast, module_path, parent_path, {}
        )
        return _OptionalParameter(
            annotation=annotation,
            **({} if default is Ellipsis else {'default': default}),
            kind=kind,
            name=name,
        )
    if (
        kind is _ParameterKind.VARIADIC_POSITIONAL
        or kind is _ParameterKind.VARIADIC_KEYWORD
    ):
        return _OptionalParameter(annotation=annotation, kind=kind, name=name)
    return _RequiredParameter(annotation=annotation, kind=kind, name=name)


def _to_keyword_parameters(
    signature_ast: _ast.arguments,
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    *,
    kind: _ParameterKind = _ParameterKind.KEYWORD_ONLY,
) -> list[_Parameter]:
    return [
        _parameter_from_ast_node(
            parameter_ast, default_ast, module_path, parent_path, kind
        )
        for parameter_ast, default_ast in zip(
            signature_ast.kwonlyargs, signature_ast.kw_defaults, strict=False
        )
    ]


def _to_positional_parameters(
    signature_ast: _ast.arguments,
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
) -> list[_Parameter]:
    # double-reversing since parameters with default arguments go last
    parameters_with_defaults_ast: list[tuple[_ast.arg, _ast.expr | None]] = (
        list(
            _zip_longest(
                reversed(signature_ast.posonlyargs + signature_ast.args),
                signature_ast.defaults[::-1],
            )
        )[::-1]
    )
    kind = _ParameterKind.POSITIONAL_ONLY
    return [
        _parameter_from_ast_node(
            parameter_ast, default_ast, module_path, parent_path, kind
        )
        for parameter_ast, default_ast in parameters_with_defaults_ast
    ]


def _to_raw_signature(callable_: Callable[..., Any], /) -> _inspect.Signature:
    return _inspect.signature(callable_, eval_str=True)


def _to_variadic_keyword_parameter(
    signature_ast: _ast.arguments,
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    *,
    kind: _ParameterKind = _ParameterKind.VARIADIC_KEYWORD,
) -> _Parameter | None:
    ast_node = signature_ast.kwarg
    return (
        None
        if ast_node is None
        else _parameter_from_ast_node(
            ast_node, None, module_path, parent_path, kind
        )
    )


def _to_variadic_positional_parameter(
    signature_ast: _ast.arguments,
    module_path: _catalog.Path,
    parent_path: _catalog.Path,
    *,
    kind: _ParameterKind = _ParameterKind.VARIADIC_POSITIONAL,
) -> _Parameter | None:
    ast_node = signature_ast.vararg
    return (
        None
        if ast_node is None
        else _parameter_from_ast_node(
            ast_node, None, module_path, parent_path, kind
        )
    )
