"""Resolve semantic method contracts and executable dependency fingerprints.

Canonical declarations name substantive algorithms and data resources. Source
AST resolution follows their internal helpers without importing handlers or
optional scientific engines. Only referenced symbols participate; editorial
changes and unrelated functions leave the method fingerprint unchanged.
"""

from __future__ import annotations

import ast
from functools import lru_cache
from importlib.resources import files
from importlib.util import resolve_name
import inspect
import textwrap
from types import CodeType

from stratbox.shared.data.methods import MethodDescriptor
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

_INFRASTRUCTURE = (
    "stratbox.core.execution", "stratbox.operations",
    "stratbox.core.resources", "stratbox.domains.registry",
    "stratbox.core.runtime", "stratbox.core.limits",
    "stratbox.core.storage", "stratbox.core.network", "stratbox.shared.identity",
    "stratbox.shared.identifiers", "stratbox.shared.evidence", "stratbox.shared.data.datasets",
    "stratbox.shared.data.methods",
)
_SEMANTIC_ROLES = frozenset({"input", "parameter", "method", "dependency"})


class MethodError(ValueError):
    @property
    def code(self):
        return self.args[0]


def _meaningful(module):
    return (module == "stratbox" or module.startswith("stratbox.")) and not any(
        module == prefix or module.startswith(prefix + ".") for prefix in _INFRASTRUCTURE)


class _WithoutDocumentation(ast.NodeTransformer):
    def generic_visit(self, node):
        node = super().generic_visit(node)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
        return node


@lru_cache(maxsize=16384)
def _normalized(node):
    # Parsing the copied tree prevents normalization from mutating cached ASTs.
    copied = ast.parse(ast.unparse(node))
    return ast.dump(_WithoutDocumentation().visit(copied), include_attributes=False).encode("utf-8")


@lru_cache(maxsize=4096)
def _source_path(module):
    if module != "stratbox" and not module.startswith("stratbox."):
        raise MethodError("method.reference_outside_package")
    path = files("stratbox").joinpath(*module.split(".")[1:])
    for candidate, package in ((path.with_suffix(".py") if hasattr(path, "with_suffix") else None, False),
                               (path.joinpath("__init__.py"), True)):
        if candidate is not None and candidate.is_file():
            return candidate, package
    # Traversable resources also support zipped wheels and need no Path API.
    parent = files("stratbox").joinpath(*module.split(".")[1:-1])
    candidate = parent.joinpath(module.rsplit(".", 1)[-1] + ".py")
    if candidate.is_file():
        return candidate, False
    raise MethodError("method.reference_unavailable")


@lru_cache(maxsize=4096)
def _source_bytes(module, stamp):
    candidate, package = _source_path(module)
    return candidate.read_bytes(), package


def _source(module):
    candidate, package = _source_path(module)
    if hasattr(candidate, "stat"):
        state = candidate.stat()
        return _source_bytes(module, (state.st_mtime_ns, state.st_ctime_ns, state.st_size))
    return candidate.read_bytes(), package


@lru_cache(maxsize=4096)
def _parsed(module, contents, package):
    try:
        tree = ast.parse(contents.decode("utf-8"))
    except (UnicodeError, SyntaxError):
        raise MethodError("method.source_invalid") from None
    symbols = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols[node.name] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            for target in targets:
                if isinstance(target, ast.Name):
                    symbols[target.id] = node
    return tree, symbols, package


def _imports(nodes, module, package):
    result = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                result[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0], "")
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:
                base = module if package else module.rpartition(".")[0]
                target = resolve_name("." * node.level + target, base)
            for alias in node.names:
                if alias.name != "*":
                    result[alias.asname or alias.name] = (target, alias.name)
    return result


def _select(symbols, symbol):
    head, _, tail = symbol.partition(".")
    node = symbols.get(head)
    if node is None:
        return None
    for part in tail.split(".") if tail else ():
        node = next((item for item in getattr(node, "body", ())
                     if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and item.name == part), None)
        if node is None:
            return None
    return node


def _chain(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    return (node.id, *reversed(parts)) if isinstance(node, ast.Name) else ()


def _references(node, module, symbol, tree, symbols, package):
    imports = _imports(tree.body, module, package)
    imports.update(_imports(ast.walk(node), module, package))
    bound = {item.arg for item in ast.walk(node) if isinstance(item, ast.arg)}
    bound.update(item.id for item in ast.walk(node) if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store))
    bound -= imports.keys()
    references = set()
    parent_class = symbol.rpartition(".")[0]
    for item in ast.walk(node):
        if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Load) and item.id not in bound:
            if item.id in symbols and item.id != symbol.split(".")[0]:
                references.add((module, item.id))
            elif item.id in imports:
                target, imported = imports[item.id]
                if imported:
                    references.add((target, imported))
        elif isinstance(item, ast.Attribute):
            chain = _chain(item)
            if not chain:
                continue
            if parent_class and chain[0] in {"self", "cls"} and len(chain) == 2:
                references.add((module, parent_class + "." + chain[1]))
            elif chain[0] in imports:
                target, imported = imports[chain[0]]
                parts = (*([imported] if imported else []), *chain[1:])
                if parts:
                    references.add((target, ".".join(parts)))
    return references


@lru_cache(maxsize=16384)
def _symbol_info(node, module, symbol, tree, package):
    symbols = {}
    for candidate in tree.body:
        if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols[candidate.name] = candidate
        elif isinstance(candidate, (ast.Assign, ast.AnnAssign)):
            targets = candidate.targets if isinstance(candidate, ast.Assign) else (candidate.target,)
            for target in targets:
                if isinstance(target, ast.Name):
                    symbols[target.id] = candidate
    return ByteIdentity.of(_normalized(node)), tuple(sorted(_references(node, module, symbol, tree, symbols, package)))


def algorithm_fingerprints(references):
    """Fingerprint only reachable substantive symbol definitions and constants."""
    found = {}
    visiting = set()
    roots = set(references)

    def visit(module, symbol, explicit=False):
        reference = module + ":" + symbol
        if reference in found or reference in visiting:
            return
        if not explicit and not _meaningful(module):
            return
        visiting.add(reference)
        contents, package = _source(module)
        tree, symbols, package = _parsed(module, contents, package)
        node = _select(symbols, symbol)
        if node is None:
            # Package re-exports retain the defining symbol as their owner.
            imports = _imports(tree.body, module, package)
            head, separator, tail = symbol.partition(".")
            if head in imports:
                target, imported = imports[head]
                selected = ".".join(part for part in (imported, tail) if part)
                if selected:
                    visit(target, selected, explicit=explicit)
                    visiting.remove(reference)
                    return
            if separator:
                try:
                    _source(module + "." + head)
                except (MethodError, OSError, KeyError):
                    pass
                else:
                    visit(module + "." + head, tail, explicit=explicit)
                    visiting.remove(reference)
                    return
            # Attribute methods on runtime objects are encoded by their owner
            # function; an unresolved explicitly named algorithm is an error.
            if explicit:
                raise MethodError("method.reference_unavailable")
            visiting.remove(reference)
            return
        found[reference], dependencies = _symbol_info(node, module, symbol, tree, package)
        for target, imported in dependencies:
            visit(target, imported)
        visiting.remove(reference)

    for reference in sorted(roots):
        if not isinstance(reference, str) or reference.count(":") != 1 or not all(reference.split(":")):
            raise MethodError("method.reference_invalid")
        visit(*reference.split(":"), explicit=True)
    return found


def resource_fingerprints(references):
    result = {}
    for reference in references:
        if not isinstance(reference, str) or reference.count(":") != 1:
            raise MethodError("method.resource_invalid")
        package, relative = reference.split(":")
        parts = relative.split("/")
        if not package.startswith("stratbox.") or not relative or any(part in {"", ".", ".."} for part in parts) or "\\" in relative:
            raise MethodError("method.resource_invalid")
        path = files("stratbox").joinpath(*package.split(".")[1:], *parts)
        if not path.is_file():
            raise MethodError("method.resource_unavailable")
        result[reference] = ByteIdentity.of(path.read_bytes())
    return result


def _code_value(code):
    """Fallback for trusted in-memory callables without a source resource."""
    constants = []
    for value in code.co_consts:
        if isinstance(value, CodeType):
            constants.append(_code_value(value))
        elif value is None or type(value) in {bool, int, str, bytes, float, complex}:
            constants.append(repr(value))
        else:
            constants.append(type(value).__qualname__)
    return {"bytecode": code.co_code.hex(), "constants": constants, "names": code.co_names,
            "variables": code.co_varnames, "arguments": (code.co_argcount, code.co_kwonlyargcount)}


def callable_fingerprint(work):
    if not callable(work):
        raise MethodError("method.algorithm_required")
    try:
        source = textwrap.dedent(inspect.getsource(work))
        tree = ast.parse(source)
        if getattr(work, "__name__", None) == "<lambda>":
            node = next(item for item in ast.walk(tree) if isinstance(item, ast.Lambda))
        else:
            node = next((item for item in ast.walk(tree)
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == work.__name__), tree)
        identity = ByteIdentity.of(_normalized(node))
    except (OSError, TypeError, SyntaxError, IndentationError):
        code = getattr(work, "__code__", None)
        if not isinstance(code, CodeType):
            raise MethodError("method.algorithm_unavailable") from None
        identity = ByteIdentity.of(canonical_manifest_bytes(_code_value(code)))
    return identity


def semantic_contract(definition):
    from stratbox.core.execution.values import argument_value
    semantics = definition.processing
    policies = tuple(getattr(definition, "request_fields", ()))
    roles = {item.path: item.role for item in policies}
    def semantic(path):
        return roles.get(path, "parameter") in _SEMANTIC_ROLES
    if semantics is None:
        return {"request": definition.request_type.__qualname__, "fields": [
            {"path": item.path, "role": item.role} for item in policies if item.role in _SEMANTIC_ROLES]}
    return {"inputs": [argument_value(port) for port in semantics.inputs if semantic(port.path)],
            "parameters": [name for name in semantics.parameters if semantic(name)],
            "outputs": [argument_value(port) for port in semantics.outputs],
            "fields": [{"path": item.path, "role": item.role} for item in policies if item.role in _SEMANTIC_ROLES],
            "function": semantics.function.value}


def _external_algorithm_fingerprints(references):
    """Fingerprint explicit trusted contributions, never import plan-supplied code.

    The runtime catalog admits implementation references before this function is
    called. A serialized execution plan contains only selected catalog IDs and
    fingerprints; it cannot introduce a new reference through this path.
    """
    from importlib import import_module
    from stratbox.core.execution.values import argument_identity
    algorithms = {}
    seen = set()

    def visit(reference, value):
        if id(value) in seen:
            return
        seen.add(id(value))
        algorithms[reference] = callable_fingerprint(value)
        if not inspect.isfunction(value):
            return
        closure = inspect.getclosurevars(value)
        for name, item in {**closure.globals, **closure.nonlocals}.items():
            if inspect.isfunction(item) and item.__module__ == value.__module__:
                visit(reference + "." + name,item)
            elif not inspect.ismodule(item) and not callable(item):
                try:
                    algorithms[reference + ".binding." + name] = argument_identity(item)
                except (TypeError,ValueError):
                    raise MethodError("method.external_binding_not_identifiable") from None

    for reference in references:
        module,name = reference.split(":",1)
        try:
            value = import_module(module)
            for part in name.split("."):
                value = getattr(value,part)
        except (ImportError,AttributeError):
            raise MethodError("method.external_algorithm_unavailable") from None
        visit(reference,value)
    return algorithms


def method_descriptor(definition, *, work=None):
    """Resolve one admitted, content-addressed method without API revisions."""
    references = tuple(getattr(definition, "method_refs", ()))
    internal = tuple(reference for reference in references if reference.split(":",1)[0] == "stratbox" or reference.startswith("stratbox."))
    external = tuple(reference for reference in references if reference not in internal)
    algorithms = algorithm_fingerprints(internal)
    algorithms.update(_external_algorithm_fingerprints(external))
    if not algorithms:
        algorithms["callable"] = callable_fingerprint(work)
    resources = resource_fingerprints(tuple(getattr(definition, "method_resources", ())))
    return MethodDescriptor.build(definition.method_id, semantic_contract(definition),
                                  algorithms=algorithms, resources=resources)
