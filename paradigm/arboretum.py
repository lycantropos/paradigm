import builtins
import copy
import importlib
import typing
from contextlib import suppress
from functools import (reduce,
                       singledispatch)
from itertools import (chain,
                       starmap,
                       zip_longest)
from pathlib import Path
from typing import (Any,
                    FrozenSet,
                    Iterable,
                    List,
                    MutableMapping,
                    Union)

from typed_ast import ast3

from . import (catalog,
               namespaces,
               sources)
from .conversion import TypedToPlain
from .hints import Namespace

Node = Union[ast3.AST, catalog.Path, List[ast3.AST]]
Nodes = MutableMapping[catalog.Path, Node]

TYPING_MODULE_PATH = catalog.factory(typing)
OVERLOAD_DECORATORS_PATHS = frozenset(next(
        (TYPING_MODULE_PATH.join(path), path)
        for path in catalog.paths_factory(typing.overload)))
NAMED_TUPLE_CLASSES_PATHS = frozenset(next(
        (TYPING_MODULE_PATH.join(path), path)
        for path in catalog.paths_factory(typing.NamedTuple)))


@singledispatch
def are_similar(left_object: Any, right_object: Any) -> bool:
    return left_object == right_object


@are_similar.register(ast3.AST)
def are_nodes_similar(left_object: ast3.AST, right_object: Node) -> bool:
    if type(left_object) is not type(right_object):
        return False
    for property_name in chain(left_object._attributes, left_object._fields):
        try:
            left_property = getattr(left_object, property_name)
        except AttributeError:
            continue
        try:
            right_property = getattr(right_object, property_name)
        except AttributeError:
            return False
        if not are_similar(left_property, right_property):
            return False
    return True


def to_nodes(object_path: catalog.Path,
             module_path: catalog.Path) -> List[ast3.AST]:
    nodes = module_path_to_nodes(module_path,
                                 base=built_ins_nodes)
    reduce_node = Reducer(nodes=nodes,
                          parent_path=catalog.Path()).visit
    root = nodes[catalog.Path()]
    reduce_node(root)
    while True:
        try:
            result = search_node(object_path,
                                 nodes=nodes)
        except KeyError:
            parent_path = object_path.parent
            parent_node = search_node(parent_path,
                                      nodes=nodes)
            while True:
                children = list(root.body)
                reduce_node(parent_node)
                children_remained_intact = all(starmap(are_similar,
                                                       zip_longest(children,
                                                                   root.body)))
                if children_remained_intact:
                    raise
                try:
                    result = search_node(object_path,
                                         nodes=nodes)
                except KeyError:
                    continue
                else:
                    break
        if not isinstance(result, list):
            result = [result]
        return result


def search_node(path: catalog.Path,
                *,
                nodes: Nodes) -> ast3.AST:
    while True:
        result = nodes[path]
        if is_link(result):
            path = result
            continue
        break
    return result


is_link = catalog.Path.__instancecheck__


def module_path_to_nodes(module_path: catalog.Path,
                         *,
                         base: Nodes = None) -> Nodes:
    root = to_flat_root(module_path)
    if base is None:
        base = {}
    result = copy.copy(base)
    Registry(nodes=result,
             module_path=module_path,
             parent_path=catalog.Path()).visit(root)
    return result


def to_flat_root(module_path: catalog.Path) -> ast3.Module:
    source_path = sources.factory(module_path)
    result = factory(source_path)
    namespace = namespaces.factory(module_path)
    namespace = namespaces.merge([built_ins_namespace, namespace])
    Flattener(namespace=namespace,
              module_path=module_path,
              parent_path=catalog.Path()).visit(result)
    return result


@singledispatch
def factory(object_: Any) -> ast3.Module:
    raise TypeError('Unsupported object type: {type}.'
                    .format(type=type(object_)))


@factory.register(Path)
def from_source_path(object_: Path) -> ast3.Module:
    return ast3.parse(object_.read_text())


@factory.register(catalog.Path)
def from_module_path(object_: catalog.Path) -> ast3.Module:
    return factory(sources.factory(object_))


@factory.register(ast3.Module)
def from_root(object_: ast3.Module) -> ast3.Module:
    return object_


@factory.register(ast3.AST)
def from_node(object_: ast3.AST) -> ast3.Module:
    return ast3.Module([object_], [])


class Base(ast3.NodeTransformer):
    def __init__(self,
                 *,
                 parent_path: catalog.Path,
                 is_nested: bool) -> None:
        self.parent_path = parent_path
        self.is_nested = is_nested

    def resolve_path(self, path: catalog.Path) -> catalog.Path:
        if self.is_nested:
            return self.parent_path.join(path)
        return path


class Flattener(Base):
    def __init__(self,
                 *,
                 namespace: Namespace,
                 module_path: catalog.Path,
                 parent_path: catalog.Path,
                 is_nested: bool = False) -> None:
        super().__init__(parent_path=parent_path,
                         is_nested=is_nested)
        self.namespace = namespace
        self.module_path = module_path

    def visit_Import(self, node: ast3.Import) -> Iterable[ast3.Import]:
        for name_alias in node.names:
            alias_path = self.resolve_path(to_alias_path(name_alias))
            actual_path = to_actual_path(name_alias)
            if not namespace_contains(self.namespace, alias_path):
                parent_module_name = actual_path.parts[0]
                module = importlib.import_module(parent_module_name)
                self.namespace[parent_module_name] = module
            yield ast3.Import([name_alias])

    def visit_ImportFrom(self, node: ast3.ImportFrom
                         ) -> Iterable[ast3.ImportFrom]:
        parent_module_path = to_parent_module_path(
                node,
                parent_module_path=self.module_path)
        for name_alias in node.names:
            alias_path = self.resolve_path(to_alias_path(name_alias))
            actual_path = to_actual_path(name_alias)
            if actual_path == catalog.WILDCARD_IMPORT:
                self.namespace.update(namespaces.factory(parent_module_path))
                yield from to_flat_root(parent_module_path).body
                continue
            elif not namespace_contains(self.namespace, alias_path):
                namespace = namespaces.factory(parent_module_path)
                try:
                    self.namespace[str(alias_path)] = search_by_path(
                            namespace,
                            actual_path)
                except KeyError:
                    module_path = parent_module_path.join(actual_path)
                    with suppress(ImportError):
                        self.namespace[str(alias_path)] = (
                            importlib.import_module(str(module_path)))
            yield ast3.ImportFrom(str(parent_module_path), [name_alias], 0)

    def visit_ClassDef(self, node: ast3.ClassDef) -> ast3.ClassDef:
        path = self.resolve_path(catalog.factory(node.name))
        transformer = type(self)(namespace=self.namespace,
                                 parent_path=path,
                                 module_path=self.module_path,
                                 is_nested=True)
        for child in node.body:
            transformer.visit(child)
        return node

    def visit_If(self, node: ast3.If) -> Iterable[ast3.AST]:
        if self.visit(node.test):
            children = node.body
        else:
            children = node.orelse
        for child in children:
            self.visit(child)
        yield from children

    def visit_BoolOp(self, node: ast3.BoolOp) -> bool:
        return self.evaluate_expression(node)

    def visit_Compare(self, node: ast3.Compare) -> bool:
        return self.evaluate_expression(node)

    def evaluate_expression(self, node: ast3.expr) -> Any:
        # to avoid name conflicts
        # we're using name that won't be present
        # because it'll lead to ``SyntaxError`` otherwise
        # and no AST will be generated
        temporary_name = '@tmp'
        assignment = expression_to_assignment(node,
                                              name=temporary_name)
        execute(assignment,
                namespace=self.namespace)
        return self.namespace.pop(temporary_name)


class Registry(Base):
    def __init__(self,
                 *,
                 nodes: Nodes,
                 module_path: catalog.Path,
                 parent_path: catalog.Path,
                 is_nested: bool = False) -> None:
        super().__init__(parent_path=parent_path,
                         is_nested=is_nested)
        self.nodes = nodes
        self.module_path = module_path

    def visit_Module(self, node: ast3.Module) -> ast3.Module:
        self.nodes[catalog.Path()] = node
        for child in node.body:
            self.visit(child)
        return node

    def visit_ClassDef(self, node: ast3.ClassDef) -> ast3.ClassDef:
        path = self.resolve_path(catalog.factory(node.name))
        try:
            self.nodes[path]
        except KeyError:
            pass
        else:
            inherits_itself = any(path == base_path
                                  for base_path in map(self.visit, node.bases))
            if not inherits_itself:
                nodes = {object_path: object_node
                         for object_path, object_node in self.nodes.items()
                         if not object_path.is_child_of(path)}
                self.nodes.clear()
                self.nodes.update(nodes)
        self.nodes[path] = node
        transformer = type(self)(nodes=self.nodes,
                                 module_path=self.module_path,
                                 parent_path=path,
                                 is_nested=True)
        for child in node.body:
            transformer.visit(child)
        return node

    def visit_FunctionDef(self, node: ast3.FunctionDef) -> ast3.FunctionDef:
        path = self.resolve_path(catalog.factory(node.name))
        if self.is_overloaded(node):
            try:
                self.nodes.setdefault(path, []).append(node)
            except AttributeError:
                self.nodes[path] = [node]
        else:
            self.nodes[path] = node
        return node

    def visit_Import(self, node: ast3.Import) -> ast3.Import:
        for child in node.names:
            alias_path = self.resolve_path(to_alias_path(child))
            self.nodes[alias_path] = node
        return node

    def visit_ImportFrom(self, node: ast3.ImportFrom) -> ast3.ImportFrom:
        for child in node.names:
            alias_path = self.resolve_path(to_alias_path(child))
            self.nodes[alias_path] = node
        return node

    def visit_AnnAssign(self, node: ast3.AnnAssign) -> ast3.AnnAssign:
        path = self.visit(node.target)
        value_node = self.visit(node.value or node.annotation)
        self.nodes[path] = value_node
        return node

    def visit_Assign(self, node: ast3.Assign) -> ast3.Assign:
        paths = map(self.visit, node.targets)
        value_node = self.visit(node.value)
        for path in paths:
            self.nodes[path] = value_node
        return node

    def visit_Attribute(self, node: ast3.Attribute) -> catalog.Path:
        parent_path = self.visit(node.value)
        attribute_path = catalog.factory(node.attr)
        return parent_path.join(attribute_path)

    def visit_Call(self, node: ast3.Call) -> ast3.AST:
        if not self.is_named_tuple_definition(node):
            return node
        class_name_node, fields_node = node.args

        def field_to_parameter(field_node: ast3.expr) -> ast3.arg:
            name_node, annotation_node = field_node.elts
            return ast3.arg(ast3.literal_eval(name_node), annotation_node)

        initializer_node = ast3.FunctionDef(
                '__init__',
                ast3.arguments([ast3.arg('self', None)]
                               + list(map(field_to_parameter,
                                          fields_node.elts)),
                               None, [], [], None, []),
                [ast3.Pass()], [], None)
        return self.visit(ast3.ClassDef(ast3.literal_eval(class_name_node),
                                        [ast3.Name(tuple.__name__,
                                                   ast3.Load())],
                                        [], [initializer_node], []))

    def visit_Name(self, node: ast3.Name) -> catalog.Path:
        name_path = catalog.factory(node.id)
        context = node.ctx
        if isinstance(context, ast3.Load):
            return name_path
        elif isinstance(context, ast3.Store):
            return self.resolve_path(name_path)
        else:
            raise TypeError('Unsupported context type: {type}.'
                            .format(type=type(context)))

    def visit_Subscript(self, node: ast3.Subscript) -> catalog.Path:
        context = node.ctx
        if not isinstance(context, ast3.Load):
            raise TypeError('Unsupported context type: {type}.'
                            .format(type=type(context)))
        return self.visit(node.value)

    def is_named_tuple_definition(self, node: ast3.Call) -> bool:
        function_path = self.visit(node.func)
        return self.intersect_with_target_paths(
                function_path,
                target_module_path=TYPING_MODULE_PATH,
                target_paths=NAMED_TUPLE_CLASSES_PATHS)

    def is_overloaded(self, node: ast3.FunctionDef) -> bool:
        decorators_paths = map(self.visit, node.decorator_list)
        return self.intersect_with_target_paths(
                *decorators_paths,
                target_module_path=TYPING_MODULE_PATH,
                target_paths=OVERLOAD_DECORATORS_PATHS)

    def intersect_with_target_paths(self,
                                    *paths: catalog.Path,
                                    target_module_path: catalog.Path,
                                    target_paths: FrozenSet[catalog.Path]
                                    ) -> bool:
        candidate_paths = target_paths & set(paths)
        try:
            candidate_path, = candidate_paths
        except ValueError:
            pass
        else:
            if self.module_path == target_module_path:
                return True
            root_path = catalog.factory(candidate_path.parts[0])
            root_node = self.nodes[root_path]
            if isinstance(root_node, ast3.Import):
                imported_modules_paths = map(to_actual_path, root_node.names)
                if any(module_path == target_module_path
                       for module_path in imported_modules_paths):
                    return True
            elif isinstance(root_node, ast3.ImportFrom):
                imported_from_module_path = catalog.factory(root_node.module)
                if imported_from_module_path == target_module_path:
                    return True
        return False


def complete_new_style_class_bases(bases: List[ast3.expr]) -> List[ast3.Expr]:
    return [*bases, ast3.Name('object', ast3.Load())]


class Reducer(Base):
    def __init__(self,
                 *,
                 nodes: Nodes,
                 parent_path: catalog.Path,
                 is_nested: bool = False) -> None:
        super().__init__(parent_path=parent_path,
                         is_nested=is_nested)
        self.nodes = nodes

    def visit_Import(self, node: ast3.Import) -> ast3.Import:
        for child in node.names:
            alias_path = to_alias_path(child)
            actual_path = to_actual_path(child)
            nodes = module_path_to_nodes(actual_path)
            self.nodes.update(dict(zip(map(alias_path.join, nodes.keys()),
                                       nodes.values())))
        return node

    def visit_ImportFrom(self, node: ast3.ImportFrom) -> ast3.ImportFrom:
        parent_module_path = catalog.factory(node.module)
        for name_alias in node.names:
            alias_path = self.resolve_path(to_alias_path(name_alias))
            actual_path = to_actual_path(name_alias)
            if actual_path == catalog.WILDCARD_IMPORT:
                nodes = module_path_to_nodes(parent_module_path)
                self.nodes.update(nodes)
                continue
            object_path = parent_module_path.join(actual_path)
            if is_module_path(object_path):
                module_root = factory(object_path)
                self.nodes[alias_path] = module_root
            else:
                nodes = module_path_to_nodes(parent_module_path)
                target_node = nodes.pop(actual_path)
                if isinstance(target_node, (ast3.Import, ast3.ImportFrom)):
                    # handle chained imports
                    nodes = {}
                    transformer = type(self)(nodes=nodes,
                                             parent_path=parent_module_path)
                    transformer.visit(target_node)
                    target_node = nodes.pop(actual_path)
                self.nodes[alias_path] = target_node
                # hack to be able to visit "imported" nodes
                self.nodes.update(nodes)
        return node

    def visit_ClassDef(self, node: ast3.ClassDef) -> ast3.ClassDef:
        path = self.resolve_path(catalog.factory(node.name))
        bases = complete_new_style_class_bases(node.bases)
        for base_path in map(self.visit, bases):
            base_nodes = {object_path: node
                          for object_path, node in self.nodes.items()
                          if object_path.is_child_of(base_path)
                          and object_path != base_path}
            for base_object_path, base_object_node in base_nodes.items():
                self.nodes.setdefault(base_object_path.with_parent(path),
                                      base_object_node)
        transformer = type(self)(nodes=self.nodes,
                                 parent_path=path,
                                 is_nested=True)
        for child in node.body:
            transformer.visit(child)
        return node

    def visit_FunctionDef(self, node: ast3.FunctionDef) -> ast3.FunctionDef:
        return node

    def visit_Assign(self, node: ast3.Assign) -> ast3.Assign:
        return node

    def visit_AnnAssign(self, node: ast3.AnnAssign) -> ast3.AnnAssign:
        return node

    def visit_Call(self, node: ast3.Call) -> catalog.Path:
        return self.visit(node.func)

    def visit_Attribute(self, node: ast3.Attribute) -> catalog.Path:
        parent_path = self.visit(node.value)
        attribute_path = catalog.factory(node.attr)
        object_path = parent_path.join(attribute_path)
        self.nodes[attribute_path] = self.nodes[object_path]
        return object_path

    def visit_Name(self, node: ast3.Name) -> catalog.Path:
        return self.resolve_path(catalog.factory(node.id))

    def visit_Subscript(self, node: ast3.Subscript) -> catalog.Path:
        context = node.ctx
        if not isinstance(context, ast3.Load):
            raise TypeError('Unsupported context type: {type}.'
                            .format(type=type(context)))
        return self.visit(node.value)


def search_by_path(namespace: Namespace, path: catalog.Path) -> Any:
    return reduce(getattr, path.parts[1:], namespace[path.parts[0]])


def namespace_contains(namespace: Namespace, path: catalog.Path) -> bool:
    try:
        search_by_path(namespace, path)
    except (KeyError, AttributeError):
        return False
    else:
        return True


def is_module_path(object_path: catalog.Path) -> bool:
    try:
        importlib.import_module(str(object_path))
    except ImportError:
        return False
    else:
        return True


def to_parent_module_path(object_: ast3.ImportFrom,
                          *,
                          parent_module_path: catalog.Path) -> catalog.Path:
    level = object_.level
    import_is_relative = level > 0
    if not import_is_relative:
        return catalog.factory(object_.module)
    depth = (len(parent_module_path.parts)
             + is_package(parent_module_path)
             - level) or None
    module_path_parts = filter(None,
                               chain(parent_module_path.parts[:depth],
                                     (object_.module,)))
    return catalog.Path(*module_path_parts)


def is_package(module_path: catalog.Path) -> bool:
    return hasattr(importlib.import_module(str(module_path)), '__path__')


def to_alias_path(node: ast3.alias) -> catalog.Path:
    result = node.asname
    if result is None:
        result = node.name
    return catalog.factory(result)


def to_actual_path(node: ast3.alias) -> catalog.Path:
    return catalog.factory(node.name)


def expression_to_assignment(node: ast3.expr,
                             *,
                             name: str) -> ast3.Assign:
    name_node = ast3.Name(name, ast3.Store())
    result = ast3.Assign([name_node], node, None)
    return ast3.fix_missing_locations(result)


@singledispatch
def execute(node: ast3.AST,
            *,
            namespace: Namespace) -> None:
    raise TypeError('Unsupported node type: {type}.'
                    .format(type=type(node)))


@execute.register(ast3.stmt)
def execute_statement(node: ast3.stmt,
                      *,
                      namespace: Namespace) -> None:
    execute_tree(factory(node),
                 namespace=namespace)


@execute.register(ast3.Module)
def execute_tree(node: ast3.Module,
                 *,
                 namespace: Namespace) -> None:
    node = TypedToPlain().visit(node)
    code = compile(node, '<unknown>', 'exec')
    exec(code, namespace)


built_ins_namespace = namespaces.factory(builtins)
built_ins_nodes = module_path_to_nodes(catalog.factory(builtins))
