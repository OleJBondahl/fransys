"""LEAN-GATES P7 (MS7): the typed-surface signature check.

Every surface function, method and property must be fully annotated on every parameter and its
return, with no `Any`, `object`, or unparameterised `dict`/`list`/`tuple` anywhere in an
annotation expression (top level or nested inside a subscript's type arguments). A string
forward-reference annotation is re-parsed and classified the same way. `ast.parse` sees the real
expression node for a source annotation like `list[int]` whether or not the module has `from
__future__ import annotations` -- that future import only changes runtime `__annotations__`
stringification, never what the parser sees in the source text -- so no consumer here needs
`typing.get_type_hints` (which would raise on this codebase's many `if TYPE_CHECKING:`-only
names) at all.

Two measurements, kept separate: `measure_surface_types` (MS7's own "function, method and
property" wording) and `measure_record_field_types` (a `@value`/`@record` class's own field
annotations, a different thing worth tracking on its own rather than folded into the first).
Both read the surface from `lean_surface.resolve_surface_names`, deduped by `(defining_file,
qualname)` -- the same dedup `lean_docstrings._surface_sites` uses, reimplemented here rather
than imported, since these are independent scripts that must still agree on "the surface".

Not a package module (loaded by file path, never imported): lives under root `scripts/`, loaded by
its own tests via `importlib.util.spec_from_file_location`, and imports `scripts/lean_surface.py`
the same way (there is no scripts package to import from).
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import types
    from collections.abc import Iterable

_SCRIPTS_DIR = Path(__file__).resolve().parent
_LEAN_SURFACE_NAME = "fransys_lean_surface"


def _load_lean_surface() -> types.ModuleType:
    """Load `scripts/lean_surface.py` the way its own tests do, reusing a prior load."""
    if _LEAN_SURFACE_NAME in sys.modules:
        return sys.modules[_LEAN_SURFACE_NAME]
    spec = importlib.util.spec_from_file_location(
        _LEAN_SURFACE_NAME, _SCRIPTS_DIR / "lean_surface.py"
    )
    if spec is None or spec.loader is None:
        msg = "could not load scripts/lean_surface.py"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_LEAN_SURFACE_NAME] = module
    spec.loader.exec_module(module)
    return module


lean_surface = _load_lean_surface()

_DEF_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)
_BANNED_NAMES = frozenset({"Any", "object", "dict", "list", "tuple"})
_RECORD_DECORATORS = frozenset({"value", "record"})


def _contains_banned(node: ast.AST) -> bool:
    """`True` if `node`'s expression tree names a banned annotation shape anywhere in it.

    A string-literal annotation is re-parsed as an expression and classified the same way. A
    `Subscript`'s own `.value` (e.g. the `dict` in `dict[str, int]`) is already parameterised
    and is skipped; only `.slice` is walked, so a nested bare name (`list[dict]`'s inner `dict`)
    is still caught while a fully parameterised one is not.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            reparsed = ast.parse(node.value, mode="eval").body
        except SyntaxError:
            return False
        return _contains_banned(reparsed)
    if isinstance(node, ast.Name):
        return node.id in _BANNED_NAMES
    if isinstance(node, ast.Attribute):
        return node.attr in _BANNED_NAMES
    if isinstance(node, ast.Subscript):
        return _contains_banned(node.slice)
    return any(_contains_banned(child) for child in ast.iter_child_nodes(node))


def _surface_params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    """`fn`'s own positional and keyword-only parameters, `self`/`cls` dropped by name.

    Only the first positional parameter is ever dropped, and only when named `self` or `cls`
    (MS7's own scope: a method's real first argument, never a later same-named parameter).
    """
    positional = [*fn.args.posonlyargs, *fn.args.args]
    if positional and positional[0].arg in ("self", "cls"):
        positional = positional[1:]
    return [*positional, *fn.args.kwonlyargs]


def _count_violations(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Every offending parameter or return annotation in `fn`'s own signature."""
    count = 0
    for param in _surface_params(fn):
        if param.annotation is None or _contains_banned(param.annotation):
            count += 1
    if fn.returns is None or _contains_banned(fn.returns):
        count += 1
    return count


def _public_methods(class_node: ast.ClassDef) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    """`class_node`'s own public methods, properties and `__init__`, direct children only.

    `__init__` is the one dunder read: it is the signature a caller builds the class by.
    """
    return tuple(
        child
        for child in class_node.body
        if isinstance(child, _DEF_TYPES)
        and (child.name == "__init__" or not child.name.startswith("_"))
    )


def _is_record_decorated(class_node: ast.ClassDef) -> bool:
    """`True` if `class_node` carries a `@value` or `@record` decorator, bare or dotted."""
    for decorator in class_node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id in _RECORD_DECORATORS:
            return True
        if isinstance(target, ast.Attribute) and target.attr in _RECORD_DECORATORS:
            return True
    return False


def _resolved_surface_defs(
    modules: Iterable[str] | None,
    entries: tuple[Any, ...] | None = None,
) -> list[tuple[str, str, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef]]:
    """One `(root-relative path, qualname, def node)` per distinct `(defining_file, qualname)`.

    Same dedup `lean_docstrings._surface_sites` uses (a name reachable through two surface
    modules yields one entry), reimplemented here rather than imported so the two independent
    scripts still agree on "the surface" by matching logic, not by sharing code. `entries`, when
    given, is used instead of a fresh `lean_surface.resolve_surface_names(modules)` call -- a
    caller that already resolved the surface once (e.g. `lean_check.py`, wiring several checks
    together) passes it through instead of paying the resolve cost again.
    """
    if entries is None:
        entries = lean_surface.resolve_surface_names(modules)
    trees: dict[Path, ast.Module] = {}
    seen: set[tuple[Path, str]] = set()
    resolved: list[tuple[str, str, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for entry in entries:
        key = (entry.defining_file, entry.qualname)
        if key in seen:
            continue
        seen.add(key)
        tree = trees.setdefault(entry.defining_file, lean_surface.module_tree(entry.defining_file))
        node = lean_surface.find_def(tree, entry.qualname)
        if node is None:
            continue
        rel = entry.defining_file.relative_to(lean_surface.ROOT).as_posix()
        resolved.append((rel, entry.qualname, node))
    return resolved


def measure_surface_types(
    modules: Iterable[str] | None = None, entries: tuple[Any, ...] | None = None
) -> dict[str, int]:
    """Every offending surface function/method/property signature, keyed `path::qualname`.

    Valued by the COUNT of `Any`/`object`/unparameterised `dict`/`list`/`tuple`/missing
    annotations in that one signature's parameters or return (>=1). Surface from
    `lean_surface.resolve_surface_names()`, deduped by `(defining_file, qualname)` the same way
    `lean_docstrings._surface_sites()` does. `entries` overrides that resolve call (see
    `_resolved_surface_defs`).
    """
    measured: dict[str, int] = {}
    for rel, qualname, node in _resolved_surface_defs(modules, entries):
        if isinstance(node, ast.ClassDef):
            for method in _public_methods(node):
                count = _count_violations(method)
                if count:
                    measured[f"{rel}::{qualname}.{method.name}"] = count
        else:
            count = _count_violations(node)
            if count:
                measured[f"{rel}::{qualname}"] = count
    return measured


def measure_record_field_types(
    modules: Iterable[str] | None = None, entries: tuple[Any, ...] | None = None
) -> dict[str, int]:
    """Every offending `@value`/`@record` surface class's field annotations, keyed `path::Class`.

    One count per class, summed over its own fields (the same four violation kinds, `Any`/
    `object`/unparameterised `dict`/`list`/`tuple` -- a dataclass field always has some
    annotation syntactically, so "missing" never applies here). A dataclass's auto-generated
    `__init__` has no AST node of its own to check per-parameter, so this reads the class's
    `AnnAssign` field declarations directly instead. Reported separately from
    `measure_surface_types`. `entries` overrides the resolve call (see `_resolved_surface_defs`).
    """
    measured: dict[str, int] = {}
    for rel, qualname, node in _resolved_surface_defs(modules, entries):
        if not isinstance(node, ast.ClassDef) or not _is_record_decorated(node):
            continue
        count = sum(
            1
            for field in node.body
            if isinstance(field, ast.AnnAssign) and _contains_banned(field.annotation)
        )
        if count:
            measured[f"{rel}::{qualname}"] = count
    return measured
