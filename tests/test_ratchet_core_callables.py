"""Ratchet D core_callables: parameters typed `Callable` in the layout core, which only falls.

A core function takes a fact as a value, never as a callback (Fable section 3 row 10).
Each parameter whose annotation names `Callable`, bare, dotted or quoted, counts once.
"""

import ast

import pytest
from gate_scan import ROOT, check_stock, stock

CORE = ROOT / "packages" / "fransys-layout" / "src" / "fransys_layout" / "core"
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _is_callable_mention(node: ast.AST) -> bool:
    """True for a `Callable` name, a `.Callable` attribute, or a string that quotes it."""
    if isinstance(node, ast.Name):
        return node.id == "Callable"
    if isinstance(node, ast.Attribute):
        return node.attr == "Callable"
    return (
        isinstance(node, ast.Constant) and isinstance(node.value, str) and "Callable" in node.value
    )


def _names_callable(annotation: ast.expr) -> bool:
    """True when some node of the annotation subtree names `Callable`."""
    return any(_is_callable_mention(node) for node in ast.walk(annotation))


def _parameters(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    """Every parameter of a function: positional, keyword-only, `*args` and `**kwargs`."""
    args = func.args
    named = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    return named + [arg for arg in (args.vararg, args.kwarg) if arg is not None]


def callable_params(source: str) -> list[tuple[int, str]]:
    """The (line, name) of each parameter whose annotation names `Callable`."""
    return [
        (arg.lineno, arg.arg)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, FUNCTIONS)
        for arg in _parameters(node)
        if arg.annotation is not None and _names_callable(arg.annotation)
    ]


def core_callable_count() -> int:
    """The callable-typed parameters over every module of the layout core."""
    paths = list(CORE.rglob("*.py"))
    return sum(len(callable_params(path.read_text(encoding="utf-8"))) for path in paths)


@pytest.mark.private_input  # a private-gate count (R462)
def test_core_callable_stock():
    check_stock("core_callables", core_callable_count(), stock("core_callables"))


def test_synthetic_bare_callable_annotation_counts_one():
    assert callable_params("def f(g: Callable[[int], int]): ...") == [(1, "g")]


def test_synthetic_quoted_callable_annotation_counts_one():
    assert callable_params('def f(g: "Callable[[int], int]"): ...') == [(1, "g")]


def test_synthetic_plain_annotation_counts_zero():
    assert callable_params("def f(a: int): ...") == []


def test_synthetic_keyword_only_and_dotted_callable_count_two():
    source = "def f(*, a: Callable[..., int] | None = None, b: collections.abc.Callable): ..."
    assert [name for _, name in callable_params(source)] == ["a", "b"]
