"""The loose-symbol ratchet of decision layout-0218.

A loose symbol is a placement of a function with nothing connected (`derive.function_is_loose`):
no conductor and no net of two or more ports at any port, nor at its mate's. The census of
NO-LOOSE-SYMBOLS found 318 over the gate's builds; the models below held them (a selector's
coil, a changeover's relay coil, the spare coils of the cabinet fixture's discovery variant).
The count may only be zero.
"""

import importlib.util
import sys
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
import pytest
from fransys_el import OPTIONS

from fransys_layout.engines import lay_out_schematic
from fransys_model.derive import function_is_loose
from fransys_model.kernel import freeze
from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions

ROOT = Path(__file__).resolve().parent.parent


def _load(path: Path, name: str) -> Any:
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


@cache
def _models() -> dict[str, Any]:
    cabinet = _load(ROOT / "packages/fransys-layout/tests/layout_cabinet.py", "cabinet_for_loose")
    selector = _load(ROOT / "packages/fransys/tests/test_series_selector.py", "selector_for_loose")
    changeover = _load(
        ROOT / "tests/field_cases/test_a_changeover_feeds_two_branches_in_series.py",
        "changeover_for_loose",
    )
    d = fr.design("demo_parts")
    selector._selector(d)
    return {
        "cabinet": lay_out_schematic(freeze(cabinet.build_cabinet(discovery=True)), OPTIONS)[0],
        "selector": lay_out_schematic(fr.build(d).model, OPTIONS)[0],
        "changeover": lay_out_schematic(fr.build(changeover.changeover_design()).model, OPTIONS)[0],
    }


def _loose_placements(model: Any) -> list[Any]:
    """Each placement of a loose function; inside an item box (a `view`), of a wholly loose item."""
    table = functions(model)
    loose_items = {
        item
        for item in {f.item for f in table.values()}
        if all(function_is_loose(model, f) for f, one in table.items() if one.item == item)
    }
    return [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if function_is_loose(model, p.function)
        and (p.key[-1] != "view" or table[p.function].item in loose_items)
    ]


@pytest.mark.parametrize("name", ["cabinet", "selector", "changeover"])
def test_no_symbol_with_nothing_connected_is_placed(name: str) -> None:
    """Each model draws its circuit, and none of its placements has nothing connected.

    # UNDO: engines/schematic/read/loose.py, `without_loose` returns `inputs` unchanged
    """
    model = _models()[name]
    assert layout_of(model, SymbolPlacement), "the model draws its circuit"
    assert _loose_placements(model) == []


def test_each_model_holds_a_loose_function() -> None:
    """The ratchet measures something: every model has a function with nothing connected."""
    for name, model in _models().items():
        assert any(function_is_loose(model, f) for f in functions(model)), name
