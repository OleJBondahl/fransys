"""The layout tests' `turn_fixtures.py` by path: symdef's `orient` turns the old flat values."""

import importlib.util
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

TURNS = Path(__file__).resolve().parents[2] / "fransys-layout/tests/core/turn_fixtures.py"


@cache
def turn_fixtures() -> ModuleType:
    """The helper module, loaded once."""
    spec = importlib.util.spec_from_file_location("turn_fixtures_by_path", TURNS)
    if spec is None or spec.loader is None:
        msg = f"cannot load {TURNS}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
