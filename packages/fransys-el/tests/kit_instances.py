"""The study instances the kit must draw, rebuilt from the tests that name them (Ruling 43.2).

Each model comes from the builder of the field-case test its dump names, loaded by path. The
same builders live in P7.6's `input_card_designs.py` (w03, w09, p02) and P7.4's rebuilds
(w06, w07); this branch holds its own loader until they land, and retypes no model.
"""

import importlib.util
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys as fr

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Model

__all__ = ["INSTANCES"]

ROOT = Path(__file__).resolve().parents[3]
W06 = "test_a_wide_controller_row_leaves_no_column_past_the_content_box"
W07 = "test_a_nested_units_pages_take_the_units_title"
W09 = "test_an_input_card_prints_its_pins_in_marking_order_whatever_its_partners_order"
W03 = "test_plc_list_pin_of_a_later_channel"
P02 = "test_a_strip_wired_outside_routes_every_wire_to_a_plc_module_under_it"


def _case(name: str) -> Any:
    """A field-case module, loaded by path (it imports its helpers from `tests/`)."""
    sys.path.insert(0, str(ROOT / "tests"))
    path = ROOT / "tests" / "field_cases" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _documented(d: Any, unit: str) -> Model:
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# c\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(preset, unit, cover=cover)).model


def w06() -> Model:
    """A wide controller: connector pins to terminals, relay groups, chains (`d.add(_control)`)."""
    d = fr.design("demo_parts")
    d.add(_case(W06)._control, "U1")
    return _documented(d, "demo-control")


def w07() -> Model:
    """A cabinet of lamps on a board's connectors, nested units (`_cabinet` added as C1)."""
    d = fr.design("demo_parts")
    d.add(_case(W07)._cabinet("Board I/O"), "C1", place=None)
    return _documented(d, "demo-cab")


def w09() -> Model:
    """The connector fan: six contacts, each fed from its own pin and wired to a channel."""
    return _case(W09)._built("fan")


def w03() -> Model:
    """A 4-channel analog card, each channel wired to a connector header."""
    return _case(W03).built.__wrapped__().model


def p02() -> Model:
    """A unit strip wired to a module inside the unit and on to a field strip."""
    return _case(P02)._built().model


INSTANCES: dict[str, Callable[[], Model]] = {
    "p02": p02,
    "w06": w06,
    "w07": w07,
    "w03": w03,
    "w09": w09,
}
