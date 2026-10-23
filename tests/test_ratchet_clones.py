"""Ratchet E9 of SURFACE-COHERENCE: exact clones among the function bodies of `packages/*/src`.

A body of 25 or more AST nodes (docstring excluded) whose dump is equal to another's once its
arguments and local names are renamed forms a group. The count of groups only falls.
"""

import ast
from typing import override

import pytest
from gate_scan import PACKAGES_ROOT, ROOT, check_stock, src_modules, stock

MIN_NODES = 25


class _Norm(ast.NodeTransformer):
    """Rename the given local names, and every argument, to `_`; drop argument annotations."""

    def __init__(self, local: frozenset[str]) -> None:
        self.local = local

    @override
    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id not in self.local:
            return node
        return ast.copy_location(ast.Name(id="_", ctx=node.ctx), node)

    @override
    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = "_"
        node.annotation = None
        return node


def _is_docstring(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)


def _locals(func: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    args = {a.arg for a in ast.walk(func.args) if isinstance(a, ast.arg)}
    stored = {
        n.id for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
    }
    return frozenset(args | stored)


def _dump(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """The normalised dump of a body of `MIN_NODES` nodes or more, else None."""
    body = [s for s in func.body if not _is_docstring(s)]
    module = ast.Module(body=body, type_ignores=[])
    if sum(1 for _ in ast.walk(module)) < MIN_NODES:
        return None
    return ast.dump(_Norm(_locals(func)).visit(ast.parse(ast.unparse(module))))


def clone_groups(sources: dict[str, str]) -> list[list[str]]:
    """Groups of two or more `module:line name` sites with equal normalised bodies."""
    seen: dict[str, list[str]] = {}
    for module, source in sources.items():
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                key = _dump(node)
                if key is not None:
                    seen.setdefault(key, []).append(f"{module}:{node.lineno} {node.name}")
    return [sites for sites in seen.values() if len(sites) > 1]


def _test_sources() -> dict[str, str]:
    """Source of every `tests/**/*.py` and `packages/*/tests/**/*.py`, keyed by repo path."""
    paths = [*ROOT.glob("tests/**/*.py"), *PACKAGES_ROOT.glob("*/tests/**/*.py")]
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(paths)
    }


@pytest.fixture(scope="module")
def groups() -> list[list[str]]:
    return clone_groups(
        {module: path.read_text(encoding="utf-8") for module, path in src_modules()}
    )


@pytest.mark.private_input  # a private-gate count (R462)
def test_clone_groups_stay_at_their_stock(groups: list[list[str]]) -> None:
    listing = "\n".join("  " + " == ".join(sites) for sites in groups)
    found = len(groups)
    assert found <= stock("clones"), f"exact clone groups:\n{listing}"
    check_stock("clones", found, stock("clones"))


@pytest.fixture(scope="module")
def test_groups() -> list[list[str]]:
    return clone_groups(_test_sources())


@pytest.mark.private_input  # a private-gate count (R462)
def test_test_clone_groups_stay_at_their_stock(test_groups: list[list[str]]) -> None:
    listing = "\n".join("  " + " == ".join(sites) for sites in test_groups)
    found = len(test_groups)
    assert found <= stock("clones_tests"), f"exact clone groups among tests:\n{listing}"
    check_stock("clones_tests", found, stock("clones_tests"))


BODY = """
def {name}({arg}):
    {loc} = []
    for item in {arg}:
        if item.ok and item.size > 3:
            {loc}.append(item.name.strip().lower())
        else:
            {loc}.extend([item.a, item.b, item.c])
    return tuple(sorted({loc}))
"""


def test_equal_bodies_under_other_names_form_one_group() -> None:
    one = BODY.format(name="f", arg="xs", loc="out")
    two = BODY.format(name="g", arg="ys", loc="acc")
    assert clone_groups({"m1": one, "m2": two}) == [["m1:2 f", "m2:2 g"]]


def test_a_short_body_forms_no_group() -> None:
    short = "def f(a):\n    return a + 1\n"
    assert clone_groups({"m1": short, "m2": short}) == []


def test_a_differing_body_forms_no_group() -> None:
    one = BODY.format(name="f", arg="xs", loc="out")
    two = BODY.format(name="g", arg="ys", loc="acc").replace("> 3", "> 4")
    assert clone_groups({"m1": one, "m2": two}) == []
