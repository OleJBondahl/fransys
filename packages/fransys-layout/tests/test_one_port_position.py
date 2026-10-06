"""No module recomputes a port's page position: `geometry.port_page_at` is its one home.

A port's page position is a placed function's origin plus the port's own offset, written
`placed.at.x + port.at.x`. This scans `src/fransys_layout` with stdlib `ast` for a sum of two
`.at.x` (or two `.at.y`) reads on different bases, which is that shape.
"""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "fransys_layout"

# Files where such a sum is not a port's page position, each with its reason.
EXCLUDED = {
    "stages/texts/markers.py": (
        "mid-point of a C21 run's two end stubs: `(first.at.x + last.at.x) // 2`"
    ),
}


def _at_read(node: ast.expr) -> tuple[str, str] | None:
    """`(base, axis)` for `<base>.at.x` or `<base>.at.y`, else `None`."""
    if (
        isinstance(node, ast.Attribute)
        and node.attr in {"x", "y"}
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "at"
    ):
        return ast.unparse(node.value.value), node.attr
    return None


def recomputed_positions(source: str) -> list[int]:
    """The line of every `<a>.at.x + <b>.at.x` (or `y`) with two different bases in `source`."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = _at_read(node.left), _at_read(node.right)
            if left and right and left[1] == right[1] and left[0] != right[0]:
                lines.append(node.lineno)
    return lines


def test_the_scan_finds_the_shape_it_looks_for() -> None:
    """It can fail: the shape is found, and the sums that are not that shape are not."""
    assert recomputed_positions("y = placed.at.y + port.at.y") == [1]
    assert recomputed_positions("x = (row[0].at.x + row[-1].at.x) // 2") == [1]
    assert recomputed_positions("x = placed.at.x + port.at.y") == []  # x with y
    assert recomputed_positions("x = one.at.x + one.at.x") == []  # one base
    assert recomputed_positions("x = one.at.x + dx") == []  # an offset, not a port


def test_no_module_recomputes_a_port_page_position() -> None:
    """Every module calls `port_page_at`; none adds a placed origin to a port offset itself."""
    found = {}
    for path in sorted(SRC_ROOT.rglob("*.py")):
        name = path.relative_to(SRC_ROOT).as_posix()
        if name in EXCLUDED:
            continue
        if lines := recomputed_positions(path.read_text(encoding="utf-8")):
            found[name] = lines
    assert not found, f"use geometry.port_page_at instead of adding .at.x/.at.y: {found}"
