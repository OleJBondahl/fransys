"""The scanner of the TEXT-JOINS gate (spec NUMBER-SORT K16, order NS-8, record 0236).

A site is an f-string, a `+` chain of strings or a `.join` of a tuple or list that combines two
operands, one at least a row field, in an output package, render, the facade or author. A row field
is `x.field` (or `x.a.b`) where `x` is a parameter or a loop or comprehension variable of the
enclosing scopes, not `self`, `cls` or an imported module name. The other operand is a second row
field or a string literal. A direct argument of a `raise` is not a site, nor is a join assigned
to a local name that a `raise` in the same function passes as its exception's message (the house
form `msg = f"..."; raise X(msg)`, designer 2026-10-18); a `Finding(...)` message is.
"""

import ast
from typing import NamedTuple

SCOPE = frozenset(
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
NOT_ROWS = frozenset(["self", "cls"])


class Site(NamedTuple):
    """One join: the enclosing function, the line, whether it is a direct `raise` argument and the
    name of the call it is a direct argument of (`""` if none)."""

    name: str
    line: int
    in_raise: bool
    call: str


def _targets(node: ast.AST) -> set[str]:
    return {
        n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
    }


def _bound(scope: ast.AST) -> set[str]:
    """Parameters of `scope` plus every loop and comprehension variable inside it."""
    names: set[str] = set()
    if isinstance(scope, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
        args = scope.args
        every = [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]
        names |= {a.arg for a in every if a is not None}
    for sub in ast.walk(scope):
        if isinstance(sub, ast.For | ast.AsyncFor | ast.comprehension):
            names |= _targets(sub.target)
    return names - NOT_ROWS


def _root(node: ast.expr) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _has_field(node: ast.AST, rows: set[str]) -> bool:
    return any(isinstance(n, ast.Attribute) and _root(n) in rows for n in ast.walk(node))


def _is_str(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _chain(node: ast.expr) -> list[ast.expr]:
    """The operands of a `+` chain, left to right."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return [*_chain(node.left), *_chain(node.right)]
    return [node]


def _operands(node: ast.AST) -> list[ast.expr] | None:
    """The operands a join combines, or None when `node` is not a join."""
    if isinstance(node, ast.JoinedStr):
        return [v.value if isinstance(v, ast.FormattedValue) else v for v in node.values]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        parts = _chain(node)
        return parts if any(_is_str(p) or isinstance(p, ast.JoinedStr) for p in parts) else None
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "join"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Tuple | ast.List)
    ):
        return list(node.args[0].elts)
    return None


def _is_site(node: ast.AST, rows: set[str]) -> bool:
    parts = _operands(node)
    if parts is None or len(parts) < 2:
        return False
    fields = sum(1 for p in parts if _has_field(p, rows))
    literals = sum(1 for p in parts if _is_str(p))
    return fields >= 1 and fields + literals >= 2


def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else ""


def _inner_ids(node: ast.AST) -> set[int]:
    """Ids of the joins nested inside a join's own chain or format spec: not sites themselves."""
    inner: set[int] = set()
    if isinstance(node, ast.BinOp):
        for sub in ast.walk(node):
            if sub is not node and isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Add):
                inner.add(id(sub))
    elif isinstance(node, ast.JoinedStr):
        inner |= {
            id(v.format_spec)
            for v in node.values
            if isinstance(v, ast.FormattedValue) and v.format_spec
        }
    return inner


def _direct_args(tree: ast.AST) -> dict[int, tuple[bool, str]]:
    """Id of each direct call argument -> (is a raise's argument, the call's name)."""
    found: dict[int, tuple[bool, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            for arg in [*node.exc.args, *(k.value for k in node.exc.keywords)]:
                found[id(arg)] = (True, _call_name(node.exc))
            found[id(node.exc)] = (True, "")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for arg in [*node.args, *(k.value for k in node.keywords)]:
                found.setdefault(id(arg), (False, _call_name(node)))
    return found


def _raise_messages(func: ast.AST) -> set[int]:
    """Ids of values assigned to a local name that a `raise` in `func` passes as its message."""
    named: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            named |= {a.id for a in node.exc.args if isinstance(a, ast.Name)}
    return {
        id(n.value)
        for n in ast.walk(func)
        if isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id in named
    }


def sites(tree: ast.AST, module: str) -> list[Site]:
    """Every join site in `tree`, raise arguments included, flagged as such."""
    if module.split(".", maxsplit=1)[0] not in SCOPE:
        return []
    direct = _direct_args(tree)
    skip: set[int] = set()
    messages: set[int] = set()
    found: list[Site] = []

    def visit(node: ast.AST, name: str, rows: set[str]) -> None:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            rows = rows | _bound(node)
            name = node.name if not isinstance(node, ast.Lambda) else name
            if not isinstance(node, ast.Lambda):
                messages.update(_raise_messages(node))
        if isinstance(node, ast.expr) and id(node) not in skip and _is_site(node, rows):
            in_raise, call = direct.get(id(node), (False, ""))
            if id(node) not in messages:
                found.append(Site(name, node.lineno, in_raise, call))
            skip.update(_inner_ids(node))
        for child in ast.iter_child_nodes(node):
            visit(child, name, rows)

    visit(tree, "<module>", _bound(tree))
    return found


def text_joins(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """`(function, line)` of each join of row fields or a row field and a literal, bar `raise`."""
    return [(s.name, s.line) for s in sites(tree, module) if not s.in_raise]
