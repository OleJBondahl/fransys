"""Ratchet: typed setting literals in `packages/*/src`, which only fall.

A setting lives in a package TOML file (SETTINGS ST1), so a number typed in code under a unit
suffix (`*_mm`, `*_pct`, ...) is a stray copy. Module-level and dataclass-field assignments count.
"""

import ast
from typing import TYPE_CHECKING

import pytest
from gate_scan import check_stock, src_modules, stock

if TYPE_CHECKING:
    from pathlib import Path

SUFFIXES = (
    "_mm",
    "_pct",
    "_g",
    "_pt",
    "_gap",
    "_pitch",
    "_margin",
    "_height",
    "_penalty",
    "_width",
)
NUMBER_CALLS = frozenset({"Decimal", "float", "int"})


def _numeric(node: ast.expr) -> bool:
    """A numeric Constant, a bool not counted."""
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int | float)
        and not isinstance(node.value, bool)
    )


def _literal(node: ast.expr) -> bool:
    """A numeric constant, its unary minus, or Decimal/float/int of a numeric or str constant."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _numeric(node.operand)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in NUMBER_CALLS and len(node.args) == 1:
            arg = node.args[0]
            return isinstance(arg, ast.Constant) and (_numeric(arg) or isinstance(arg.value, str))
        return False
    return _numeric(node)


def _targets(stmt: ast.stmt) -> list[str]:
    """The plain names a statement binds to a literal value, else none."""
    if isinstance(stmt, ast.AnnAssign):
        if stmt.value is not None and isinstance(stmt.target, ast.Name) and _literal(stmt.value):
            return [stmt.target.id]
        return []
    if isinstance(stmt, ast.Assign) and _literal(stmt.value):
        return [target.id for target in stmt.targets if isinstance(target, ast.Name)]
    return []


def _hits(body: list[ast.stmt], *, upper: bool) -> list[tuple[int, str]]:
    """`(line, name)` per suffixed literal in `body`; `upper` keeps UPPER_CASE names only."""
    return [
        (stmt.lineno, name)
        for stmt in body
        for name in _targets(stmt)
        if name.lower().endswith(SUFFIXES) and (not upper or name.isupper())
    ]


def setting_literals(source: str) -> list[tuple[int, str]]:
    """Each `(line, name)` typed setting literal, module-level or in a class body, by line."""
    tree = ast.parse(source)
    sites = _hits(tree.body, upper=True)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            sites += _hits(node.body, upper=False)
    return sorted(sites)


def _all_sites() -> list[tuple[Path, int, str]]:
    """`(path, line, name)` over every `packages/*/src` file except `_vendor_*`."""
    return [
        (path, line, name)
        for _module, path in src_modules()
        if not path.name.startswith("_vendor_")
        for line, name in setting_literals(path.read_text(encoding="utf-8"))
    ]


def found_count() -> int:
    """The number of typed setting literals over `packages/*/src`."""
    return len(_all_sites())


@pytest.mark.private_input  # a private-gate count (R462)
def test_settings_literal_stock():
    check_stock("settings_literals", found_count(), stock("settings_literals"))


def test_synthetic_module_constant_with_suffix_counts():
    assert setting_literals("FOO_MM = 1.8\n") == [(1, "FOO_MM")]


def test_synthetic_dataclass_field_with_suffix_counts():
    source = 'from decimal import Decimal\n\n\nclass A:\n    gap_mm: Decimal = Decimal("1.8")\n'
    assert setting_literals(source) == [(5, "gap_mm")]


def test_synthetic_no_suffix_str_or_function_local_counts_zero():
    source = 'FOO = 1.8\nNAME_MM = "x"\n\n\ndef f():\n    a_mm = 1.0\n'
    assert setting_literals(source) == []


def test_synthetic_two_sites_count_two():
    source = "A_PCT = -2\n\n\nclass B:\n    w_width = 3.5\n"
    assert len(setting_literals(source)) == 2
