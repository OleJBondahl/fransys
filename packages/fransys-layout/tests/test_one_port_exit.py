"""No module keeps its own side-to-step table: `core.sides.SIDE_STEP` is the one.

A step table is a dict literal whose keys are `Facing.<name>` reads or the side letters "N" "E"
"S" "W" and whose values are tuples. This scans `src/fransys_layout` (and, from
"""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "fransys_layout"
HOMES = ("geometry/exits.py", "core/sides.py")


def _is_facing(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "Facing"


def _is_side(node: ast.expr | None) -> bool:
    return _is_facing(node) or (isinstance(node, ast.Constant) and node.value in ("N", "E", "S", "W"))


def step_tables(source: str) -> list[int]:
    """The line of every dict of `Facing.<x>` keys with tuple values in `source`."""
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Dict)
        and node.keys
        and all(_is_side(key) for key in node.keys)
        and all(isinstance(value, ast.Tuple) for value in node.values)
    ]


def test_the_scan_finds_the_shape_it_looks_for() -> None:
    """It can fail: a step table is found; a map to facings or points is not."""
    assert step_tables("S = {Facing.N: (0, -1), Facing.S: (0, 1)}") == [1]
    assert step_tables("B = {Facing.N: Facing.S, Facing.S: Facing.N}") == []
    assert step_tables("F = {Facing.N: Point(x=1, y=2)}") == []
    assert step_tables("S = {Facing.N: (0, -1), other: (0, 1)}") == []
    assert step_tables('S = {"N": (0, -1), "S": (0, 1)}') == [1]
    assert step_tables('S = {"N": "S", "S": "N"}') == []


def test_no_module_but_the_home_writes_a_facing_step_table() -> None:
    """Every module reads `FACING_STEP` or calls `port_exit`; none writes the four steps again."""
    found = {}
    for path in sorted(SRC_ROOT.rglob("*.py")):
        name = path.relative_to(SRC_ROOT).as_posix()
        if name not in HOMES and (lines := step_tables(path.read_text(encoding="utf-8"))):
            found[name] = lines
    assert not found, f"use core.SIDE_STEP, geometry.FACING_STEP or port_exit, not a table of your own: {found}"
