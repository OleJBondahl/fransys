"""The hand-made fixtures obey the wiring-grid contract the engine relies on (geometry.md 5.1,
geometry.md 5.2).

A skipped skeleton with an off-grid origin would fail once implemented for a reason
that is a fixture bug, so this check runs today: it needs no stub.
"""

import ast
from pathlib import Path

from samples import through_geometry

from fransys_layout.geometry import WIRING_GRID, Facing, SymbolGeometry

TESTS_ROOT = Path(__file__).resolve().parent


def _geometry_problems(geometry: SymbolGeometry) -> list[str]:
    """Ports off the wiring grid, or not on the body-box side their facing names."""
    body = geometry.body
    side = {
        Facing.N: lambda p: p.y == body.y,
        Facing.S: lambda p: p.y == body.y + body.height,
        Facing.W: lambda p: p.x == body.x,
        Facing.E: lambda p: p.x == body.x + body.width,
    }
    problems = []
    for port in geometry.ports:
        if port.at.x % WIRING_GRID or port.at.y % WIRING_GRID:
            problems.append(f"{geometry.key}.{port.name}: off the wiring grid")
        if not side[port.facing](port.at):
            problems.append(f"{geometry.key}.{port.name}: not on its {port.facing.name} side")
    return problems


def _off_grid_origins(source: str, name: str) -> list[str]:
    """Every `placed(..., x=<int>, y=<int>)` call in `source` with an off-grid literal."""
    problems = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "placed"):
            continue
        for keyword in node.keywords:
            literal = getattr(keyword.value, "value", None)
            on_axis = keyword.arg in {"x", "y"} and isinstance(literal, int)
            if on_axis and literal % WIRING_GRID:
                problems.append(f"{name}:{node.lineno}: {keyword.arg}={literal}")
    return problems


def test_sample_geometries_keep_the_library_wiring_contract() -> None:
    """Ports of every sample geometry are on the wiring grid and on the matching body side."""
    assert _geometry_problems(through_geometry()) == []
    assert _geometry_problems(through_geometry(half_height=24)) == []


def test_every_placed_origin_in_the_tests_is_on_the_wiring_grid() -> None:
    """Origin plus on-grid port offset stays on the grid only if the origin is on it."""
    problems = []
    for path in sorted(TESTS_ROOT.rglob("test_*.py")):
        if path.name == "test_samples.py":
            continue
        source = path.read_text(encoding="utf-8")
        problems.extend(_off_grid_origins(source, str(path.relative_to(TESTS_ROOT))))
    assert problems == []


def test_the_checks_fail_on_synthetic_off_grid_input() -> None:
    """An origin at y = 100 and a port at y = 12 are both caught."""
    assert _off_grid_origins("placed(1, x=104, y=100)\n", "synthetic") == ["synthetic:1: y=100"]
    assert _geometry_problems(through_geometry(half_height=12)) == [
        "make-contact.in: off the wiring grid",
        "make-contact.out: off the wiring grid",
    ]
