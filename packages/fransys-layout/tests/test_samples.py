"""The hand-made fixtures obey the wiring-grid contract the engine relies on (geometry.md 5.1,
geometry.md 5.2).

A skipped skeleton with an off-grid origin would fail once implemented for a reason
that is a fixture bug, so this check runs today: it needs no stub.
"""

import ast
from pathlib import Path

from fransys_layout.geometry import WIRING_GRID

TESTS_ROOT = Path(__file__).resolve().parent


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
    """An origin at y = 100 is caught."""
    assert _off_grid_origins("placed(1, x=104, y=100)\n", "synthetic") == ["synthetic:1: y=100"]
