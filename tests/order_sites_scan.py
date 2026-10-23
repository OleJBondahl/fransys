"""The order gate's scanners (spec NUMBER-SORT K13): every sort, `reversed`, keyed `min` or `max`
and reverse slice outside the order homes is a site.

Four scanners of `test_one_home.Scanner` shape, each returning `(enclosing function, line)`:
`order_sites`, `core_order_sites`, `core_text_keys` and `order_id_reads`. The allowance is by
name: inside `fransys_model` a `key=` that resolves through the module's imports to a name in the
`__all__` of `fransys_model.derive.order` or `order_*`, or to `kernel.natural_key`, is no site.
"""

import ast
import importlib
import pkgutil
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

MODEL = "fransys_model"
DERIVE = "fransys_model.derive"
HOME_MODULES = frozenset(
    [
        "fransys_kernel.canonical_forms",
        "fransys_kernel.diff",
        "fransys_kernel.findings",
        "fransys_kernel.naturals",
    ]
)
CORE = "fransys_layout.core"
NATURAL_KEY = "fransys_model.kernel.natural_key"
SET_ITERATING = frozenset(
    [
        "fransys_reports",
        "fransys_pdf",
        "fransys_kicad",
        "fransys_wago",
        "fransys_overview",
        "fransys_render",
        "fransys",
        "fransys_author",
    ]
)
SORT_NAMES = frozenset(["sorted", "reversed", "nsmallest", "nlargest"])
PICK_NAMES = frozenset(["min", "max"])
SORT_METHODS = frozenset(["sort", "reverse", "nsmallest", "nlargest"])
STR_METHODS = frozenset(dir(str)) - frozenset(dir(object))
Hit = tuple[str, int]


def _is_order_module(module: str) -> bool:
    """True for `fransys_model.derive.order` and its `order_*` siblings."""
    return module == f"{DERIVE}.order" or module.startswith(f"{DERIVE}.order_")


def is_home(module: str) -> bool:
    """True for the three homes the gate does not scan (the core has its own tables)."""
    return _is_order_module(module) or module in HOME_MODULES


def in_core(module: str) -> bool:
    """True for `fransys_layout.core` and its submodules."""
    return module == CORE or module.startswith(CORE + ".")


@cache
def home_names() -> frozenset[str]:
    """Each `module.name` in the `__all__` of `order` and its `order_*` siblings, read by import."""
    derive = importlib.import_module(DERIVE)
    names = set()
    for info in pkgutil.iter_modules(derive.__path__):
        module = f"{DERIVE}.{info.name}"
        if _is_order_module(module):
            names.update(f"{module}.{n}" for n in importlib.import_module(module).__all__)
    return frozenset(names) | {NATURAL_KEY}


def _absolute(node: ast.ImportFrom, module: str) -> str:
    """The dotted module an `ImportFrom` names, a relative one resolved against `module`."""
    if not node.level:
        return node.module or ""
    base = module.split(".")[: -node.level]
    return ".".join([*base, *([node.module] if node.module else [])])


def import_aliases(tree: ast.AST, module: str) -> dict[str, str]:
    """Local name -> the dotted name it stands for, from the module's imports."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            source = _absolute(node, module)
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{source}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
    return aliases


def _dotted(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id)
    if isinstance(node, ast.Attribute) and (base := _dotted(node.value, aliases)):
        return f"{base}.{node.attr}"
    return None


def is_home_key(key: ast.expr | None, aliases: dict[str, str]) -> bool:
    """True when `key` is a name that resolves to a home key; a lambda, call or tuple is not."""
    if not isinstance(key, ast.Name | ast.Attribute):
        return False
    return _dotted(key, aliases) in home_names()


def _has_text(args: list[ast.expr]) -> bool:
    for arg in args:
        for node in ast.walk(arg):
            if isinstance(node, ast.JoinedStr) or (
                isinstance(node, ast.Constant) and isinstance(node.value, str)
            ):
                return True
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "str"
            ):
                return True
    return False


def _is_reverse_slice(node: ast.Subscript) -> bool:
    step = node.slice.step if isinstance(node.slice, ast.Slice) else None
    return (
        isinstance(step, ast.UnaryOp)
        and isinstance(step.op, ast.USub)
        and isinstance(step.operand, ast.Constant)
        and step.operand.value == 1
    )


def _set_source(node: ast.expr) -> bool:
    if isinstance(node, ast.Set):
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"set", "frozenset"}
    )


def _walk_named(node: ast.AST, name: str = "<module>") -> Iterator[tuple[ast.AST, str]]:
    """Every node with the name of its enclosing function (`<module>` at top level)."""
    for child in ast.iter_child_nodes(node):
        inner = child.name if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) else name
        yield child, inner
        yield from _walk_named(child, inner)


def _key_of(node: ast.Call) -> ast.expr | None:
    return next((k.value for k in node.keywords if k.arg == "key"), None)


def _call_is_site(node: ast.Call, allow: dict[str, str] | None) -> bool:
    fn = node.func
    key = _key_of(node)
    if isinstance(fn, ast.Attribute) and fn.attr in SORT_METHODS:
        name = fn.attr
    elif isinstance(fn, ast.Name) and fn.id in SORT_NAMES | PICK_NAMES:
        name = fn.id
    else:
        return False
    if name in PICK_NAMES and key is None and not _has_text(node.args):
        return False
    return not (allow is not None and is_home_key(key, allow))


def _sites(tree: ast.AST, module: str, *, allow: bool, sets: bool) -> list[Hit]:
    aliases = import_aliases(tree, module) if allow else None
    found: list[Hit] = []
    for node, name in _walk_named(tree):
        if (isinstance(node, ast.Subscript) and _is_reverse_slice(node)) or (
            isinstance(node, ast.Call) and _call_is_site(node, aliases)
        ):
            found.append((name, node.lineno))
        elif sets and isinstance(node, ast.For | ast.comprehension) and _set_source(node.iter):
            found.append((name, node.iter.lineno))
    return found


def order_sites(tree: ast.AST, module: str) -> list[Hit]:
    """Sort sites outside the homes and outside the layout core."""
    if is_home(module) or in_core(module):
        return []
    top = module.split(".", maxsplit=1)[0]
    return _sites(tree, module, allow=top == MODEL, sets=top in SET_ITERATING)


def core_order_sites(tree: ast.AST, module: str) -> list[Hit]:
    """The same site kinds inside `fransys_layout.core`, which only refuses a rise."""
    return _sites(tree, module, allow=False, sets=False) if in_core(module) else []


def _key_exprs(tree: ast.AST) -> Iterator[tuple[ast.expr, str]]:
    for node, name in _walk_named(tree):
        if isinstance(node, ast.Call) and (key := _key_of(node)) is not None:
            yield key, name


def _text_uses(expr: ast.AST) -> Iterator[ast.expr]:
    for node in ast.walk(expr):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node
        elif isinstance(node, ast.Name | ast.Attribute):
            attr = node.id if isinstance(node, ast.Name) else node.attr
            if attr == "natural_key" or (
                isinstance(node, ast.Attribute)
                and (
                    attr in STR_METHODS
                    or (isinstance(node.value, ast.Name) and node.value.id == "re")
                )
            ):
                yield node


def core_text_keys(tree: ast.AST, module: str) -> list[Hit]:
    """`natural_key`, a `str` method, a `re` call or a string literal inside a core sort key.

    A key given by the name of a function of the same module counts the uses in that function.
    """
    if not in_core(module):
        return []
    defs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    found = []
    for key, name in _key_exprs(tree):
        bodies = [defs[key.id]] if isinstance(key, ast.Name) and key.id in defs else [key]
        found += [(name, use.lineno) for body in bodies for use in _text_uses(body)]
    return found


def _id_params(fn: ast.FunctionDef | ast.Lambda) -> set[str]:
    if isinstance(fn, ast.Lambda):
        return {a.arg for a in fn.args.args}
    return {a.arg for a in fn.args.args if a.annotation and "Id" in ast.unparse(a.annotation)}


def _key_bodies(tree: ast.AST) -> Iterator[tuple[ast.AST, set[str], str]]:
    """Functions named `*_key` or `*_tie` and lambdas given as `key=`, with their Id parameters."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.endswith(("_key", "_tie")):
            yield node, _id_params(node), node.name
    for key, name in _key_exprs(tree):
        if isinstance(key, ast.Lambda):
            yield key, _id_params(key), name


def _tuple_elements(body: ast.AST) -> Iterator[ast.expr]:
    for node in ast.walk(body):
        if isinstance(node, ast.Tuple):
            yield from node.elts


def order_id_reads(tree: ast.AST, module: str) -> list[Hit]:
    """A read of `.id`, or a bare `Id` value as a tuple element, in a key body of the home."""
    if not _is_order_module(module):
        return []
    found: list[Hit] = []
    for body, ids, name in _key_bodies(tree):
        found += [
            (name, n.lineno)
            for n in ast.walk(body)
            if isinstance(n, ast.Attribute) and n.attr == "id" and isinstance(n.ctx, ast.Load)
        ]
        found += [
            (name, e.lineno)
            for e in _tuple_elements(body)
            if isinstance(e, ast.Name) and e.id in ids
        ]
    return found


def callable_param_orders(tree: ast.AST, module: str) -> list[Hit]:
    """Functions of an `order*` module that take a callable (a key or rank) as a parameter.

    A home takes plain values and returns an order; a callable parameter would let any caller
    sort through a lambda uncounted (spec NUMBER-SORT, ruling KIT-FACTS order_kit).
    """
    if not _is_order_module(module):
        return []
    return [
        (node.name, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        if arg.annotation is not None and "Callable" in ast.unparse(arg.annotation)
    ]
