"""`surface.toml`: the snapshot of each surface module and its sorted `__all__` names.

Fails on any difference from `scripts/lean_surface.py`; an order names the surface move.
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fransys_lean_surface", ROOT / "scripts" / "lean_surface.py"
)
if _spec is None or _spec.loader is None:
    msg = "could not load scripts/lean_surface.py"
    raise ImportError(msg)
lean_surface = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lean_surface
_spec.loader.exec_module(lean_surface)

ORDER = "an order names the surface move"


def _snapshot() -> dict[str, list[str]]:
    data = tomllib.loads((ROOT / "surface.toml").read_text(encoding="utf-8"))
    modules: dict[str, list[str]] = data["modules"]
    return modules


def test_module_set_equals_the_snapshot() -> None:
    code = set(lean_surface.surface_modules())
    snap = set(_snapshot())
    added = sorted(code - snap)
    removed = sorted(snap - code)
    assert code == snap, (
        f"surface modules differ from surface.toml; added in code: {added}; "
        f"removed from code: {removed}; {ORDER}"
    )


def test_each_modules_names_equal_the_snapshot() -> None:
    snap = _snapshot()
    names = lean_surface.surface_names()
    added: list[str] = []
    removed: list[str] = []
    for module in sorted(set(names) & set(snap)):
        code_names = set(names[module])
        snap_names = set(snap[module])
        added += [f"{module}.{name}" for name in code_names - snap_names]
        removed += [f"{module}.{name}" for name in snap_names - code_names]
    assert not [*added, *removed], (
        f"surface names differ from surface.toml; added in code: {sorted(added)}; "
        f"removed from code: {sorted(removed)}; {ORDER}"
    )


def test_model_modules_never_grow() -> None:
    count = len(lean_surface._MODEL_MODULES)
    assert count <= 19, (
        f"_MODEL_MODULES has {count} modules; the number only falls "
        "(EL-MODEL M1 amendment 3), so the limit stays at 19 (LIB-ADOPT R1: two family doors)"
    )
