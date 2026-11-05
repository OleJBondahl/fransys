"""The new engine reads the build's `Library` as a value, never module `LIBRARY` (SETTINGS ST4)."""
# NET_POTENTIAL_CONFLICT 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# NET_SHORTED 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.

import ast
from pathlib import Path
from typing import Any

import fransys_el
import pytest
import symdef
from conventions_fixtures import house
from fransys_el import style, symbol_kit, unknown_symbols
from placement_fixtures import planted_model

from electrical_symbols import LIBRARY

_SRC = Path(fransys_el.__file__).parent
_SYMBOLS = Path(fransys_el.__file__).parents[2].parent / "fransys-layout/src/fransys_layout/symbols"


def reads_library(source: str) -> bool:
    """Whether `source` names `LIBRARY`: an import, a load or an attribute of it."""
    return any(
        (isinstance(n, ast.Name) and n.id == "LIBRARY") or (isinstance(n, ast.alias) and n.name.split(".")[-1] == "LIBRARY")
        for n in ast.walk(ast.parse(source))
    )


@pytest.mark.parametrize("source", ["from electrical_symbols import LIBRARY", "x = LIBRARY.get('a')", "import a.LIBRARY"])
def test_the_scan_can_fail(source: str) -> None:
    assert reads_library(source)
    assert not reads_library("library.get('a')")


def test_no_new_engine_file_reads_module_library() -> None:
    files = [*_SRC.glob("*.py"), *_SYMBOLS.glob("*.py")]
    assert len(files) > 20
    assert [f.name for f in files if reads_library(f.read_text())] == []


def test_the_style_follows_the_library_module() -> None:
    moved = LIBRARY.with_settings(module_mm=2.0)
    assert style(moved).module_mm == 2.0
    assert style(LIBRARY).module_mm == 2.5
    assert style(moved) != style(LIBRARY)


def test_the_style_follows_the_library_divisions() -> None:
    assert style(LIBRARY).g_per_module == LIBRARY.grid.divisions_per_module


class _Empty:
    """A library with no symbol: `symbol_kit` reaching it proves it reads its argument."""

    def get(self, key: str) -> None:
        raise symdef.UnknownSymbolError(key)


def test_symbol_kit_binds_through_the_library_it_is_given() -> None:
    model = planted_model()
    assert symbol_kit(model, LIBRARY) == symbol_kit(model, LIBRARY.with_settings(module_mm=2.0))
    empty: Any = _Empty()  # reached, it lacks every key: all are unknown and each is a box (R242)
    assert not unknown_symbols(model, LIBRARY)
    assert unknown_symbols(model, empty)
    boxes = symbol_kit(model, empty)
    assert {pick.key for pick in boxes.values()} == {"generic-box"}


def test_house_conventions_need_no_library() -> None:
    assert house() == house()
