"""`fransys_el` keeps no side-to-step table: it reads `fransys_layout.core.SIDE_STEP` (R583).

The scan is the layout test's `step_tables`, loaded by path.
"""

import importlib.util
from pathlib import Path
from typing import Any

SCAN = Path(__file__).resolve().parents[2] / "fransys-layout/tests/test_one_port_exit.py"
SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "fransys_el"


def _step_tables(source: str) -> list[Any]:
    spec = importlib.util.spec_from_file_location("one_port_exit_by_path", SCAN)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.step_tables(source)


def test_the_scan_finds_a_side_and_a_facing_keyed_table_here():
    assert _step_tables('_STEP = {"N": (0, -1), "S": (0, 1)}') == [1]
    assert _step_tables("_STEP = {Facing.N: (0, -1), Facing.S: (0, 1)}") == [1]


def test_no_module_of_fransys_el_writes_a_step_table():
    found = {path.name: lines for path in sorted(SRC_ROOT.rglob("*.py")) if (lines := _step_tables(path.read_text(encoding="utf-8")))}
    assert not found, f"read fransys_layout.core.SIDE_STEP, not a table of your own: {found}"
