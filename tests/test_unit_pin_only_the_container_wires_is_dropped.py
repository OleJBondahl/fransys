"""A nested unit's own document drops a boundary pin only its container wires (layout-0295).

The board of `tests/field_cases/test_a_unit_own_document_ignores_the_mates_its_container_wires.py`
is built alone and inside a cabinet whose harness plugs mate its headers. Pin 2 of header J1
carries a wire only in the cabinet, through its plug: the board's own document does not place it.
"""

import importlib.util
import tempfile
from pathlib import Path

import fransys as fr
from fransys_el import OPTIONS

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items, ports

_CASE = Path(__file__).resolve().parent / "field_cases"
_CASE /= "test_a_unit_own_document_ignores_the_mates_its_container_wires.py"
_spec = importlib.util.spec_from_file_location("_unit_mate_case", _CASE)
assert _spec is not None
assert _spec.loader is not None
_case = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_case)
_board, _cabinet = _case._board, _case._cabinet


def _board_pins(*, container: bool) -> set[tuple[str | None, str]]:
    """The (header tag, pin name) of every pin view of the board's items that is placed."""
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cover\n", encoding="utf-8")
    d = fr.design("demo_parts")
    docs = []
    if container:
        d.add(_cabinet, "U1")
        docs.append(fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cabinet", cover=cover))
    else:
        d.add(_board, "U2")
    docs.append(fr.document(fr.DocumentPreset.PCB_SCHEMATIC, "demo-board", cover=cover))
    model = fr.build(d, *docs).model
    unit = next(
        u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == "demo-board"
    )
    own = {
        p.id: (items(model)[functions(model)[p.function].item].tag, p.name)
        for p in ports(model).values()
        if items(model)[functions(model)[p.function].item].unit == unit
    }
    laid, _ = stage_results(model, read_inputs(model, options=OPTIONS))
    return {own[p.function] for p in laid.layout.placed if p.function in own}


def test_a_pin_only_the_container_wires_is_not_placed() -> None:
    inside = _board_pins(container=True)
    assert ("J1", "1") in inside  # positive half: a pin the board wires itself stays
    assert ("J1", "2") not in inside
    assert ("J2", "3") not in inside
    assert _board_pins(container=False) <= inside
