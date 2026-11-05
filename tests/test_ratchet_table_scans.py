"""Ratchet table_scans: a keyed lookup done by filtering a table walk (model-0374).

`ports.function`, `items.unit` and `units.parent` each have an index (`Indexes.ports_by_function`,
`UnitIndex.own_items`, `UnitIndex.child_units`), so `if p.function == f` over
"""

import ast

import pytest
from gate_scan import check_stock, src_modules, stock

FIELD_OF = {"ports": "function", "items": "unit", "units": "parent", "units_table": "parent"}


def _walked_table(iterable: ast.expr) -> str | None:
    """The accessor name of `<accessor>(model).values()`, else `None`."""
    if (
        isinstance(iterable, ast.Call)
        and isinstance(iterable.func, ast.Attribute)
        and iterable.func.attr == "values"
        and isinstance(iterable.func.value, ast.Call)
        and isinstance(iterable.func.value.func, ast.Name)
    ):
        return iterable.func.value.func.id
    return None


def _filters_on_key(tests: list[ast.expr], var: str, field: str) -> bool:
    """True when a test holds `var.field == <non-constant>` (either side)."""
    for test in tests:
        for node in ast.walk(test):
            if not (isinstance(node, ast.Compare) and isinstance(node.ops[0], ast.Eq)):
                continue
            left, right = node.left, node.comparators[0]
            for side, other in ((left, right), (right, left)):
                if (
                    isinstance(side, ast.Attribute)
                    and side.attr == field
                    and isinstance(side.value, ast.Name)
                    and side.value.id == var
                    and not isinstance(other, ast.Constant)
                ):
                    return True
    return False


def _body_tests(body: list[ast.stmt]) -> list[ast.expr]:
    """The `if` tests anywhere in a loop body."""
    return [n.test for stmt in body for n in ast.walk(stmt) if isinstance(n, ast.If)]


def table_scans(source: str) -> list[int]:
    """The line of each comprehension or `for` that filters a walked table on its indexed key."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.comprehension):
            tests, iterable, target = node.ifs, node.iter, node.target
        elif isinstance(node, ast.For):
            tests, iterable, target = _body_tests(node.body), node.iter, node.target
        else:
            continue
        table = _walked_table(iterable)
        if table in FIELD_OF and isinstance(target, ast.Name) and _filters_on_key(tests, target.id, FIELD_OF[table]):
            found.append(iterable.lineno)
    return found


@pytest.mark.private_input  # a private-gate count (R462)
def test_table_scans_stock():
    found = sum(len(table_scans(path.read_text(encoding="utf-8"))) for _, path in src_modules())
    check_stock("table_scans", found, stock("table_scans"))


def test_synthetic_comprehension_filtering_ports_on_function_counts_one():
    assert table_scans("x = [p.id for p in ports(m).values() if p.function == f]\n") == [1]


def test_synthetic_for_loop_filtering_units_on_parent_counts_one():
    source = "for u in units_table(m).values():\n    if u.parent == unit:\n        pass\n"
    assert table_scans(source) == [1]


def test_synthetic_index_read_counts_zero():
    assert table_scans("x = [ports(m)[p] for p in idx.ports_by_function.get(f, ())]\n") == []


def test_synthetic_constant_comparand_counts_zero():
    assert table_scans("x = [i for i in items(m).values() if i.unit == 'a']\n") == []
