"""The grid search has one home: `stages/grid_path.py` (decision layout-0144).

A second definition of `grid_path` in the package is a copy of the search that drifts.
"""

import ast
import importlib
from pathlib import Path

from fransys_layout.stages import grid_path as home

SRC = Path(home.__file__).parents[1]


def _defining_modules(name: str) -> list[str]:
    found = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(isinstance(n, ast.FunctionDef) and n.name == name for n in ast.walk(tree)):
            found.append(path.relative_to(SRC).as_posix())
    return found


def test_the_router_calls_the_one_grid_path_function() -> None:
    router = importlib.import_module("fransys_layout.stages.route")
    assert router.grid_path is home.grid_path


def test_only_the_grid_path_module_defines_it() -> None:
    assert _defining_modules("grid_path") == ["stages/grid_path.py"]
