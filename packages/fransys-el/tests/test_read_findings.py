"""`read_findings` (R258, R267): sheet unused, text too small, connection to undrawn."""

from decimal import Decimal
from typing import NamedTuple

import fransys as fr
from fransys_el import Skipped, read_findings
from fransys_el.placement_skips import FUNCTION_WITHOUT_SYMBOL
from placement_fixtures import planted_model

from fransys_model.kernel import Severity, render_id
from fransys_model.vocab import conductors, ports

_SHEET = {
    "width_mm": 420,
    "height_mm": 297,
    "content_x_mm": 10,
    "content_y_mm": 10,
    "content_width_mm": 400,
    "content_height_mm": 277,
    "frame_columns": 8,
    "frame_rows": 6,
    "module_mm": Decimal("2.5"),
}


def _built(*, sheet: bool = False, text: Decimal | None = None) -> fr.Design:
    d = fr.design("demo_parts")
    if sheet:
        d.layout.sheet("Spare", **_SHEET)
    if text is not None:
        d.layout.profile(text_height_mm=text)
    lamp = d.device("P1", "DEMO-LAMP-24")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    d.detail.wire(x1.run("SIG", 1)[1], lamp.lamp["1"], wire=("WH", 0.75))
    return d


def _codes(model: object, code: str) -> list[fr.Finding]:
    return [f for f in read_findings(model, ()) if f.code == code]  # ty: ignore[invalid-argument-type] - a Model


def test_a_sheet_format_no_profile_names_is_one_warning() -> None:
    model = fr.build(_built(sheet=True)).model
    (found,) = _codes(model, "SHEET_FORMAT_UNUSED")
    assert found.severity is Severity.WARNING
    assert "house sheet" in found.message
    assert found.fix


def test_no_authored_sheet_gives_no_sheet_warning() -> None:
    assert _codes(fr.build(_built()).model, "SHEET_FORMAT_UNUSED") == []


def test_a_text_height_under_the_floor_is_one_warning_naming_the_profile() -> None:
    model = fr.build(_built(text=Decimal(1))).model
    (found,) = _codes(model, "TEXT_TOO_SMALL")
    assert "text height of 1 mm" in found.message
    assert "minimum of 1.8 mm" in found.message
    assert _codes(fr.build(_built()).model, "TEXT_TOO_SMALL") == []


def test_a_conductor_with_a_skipped_end_is_one_warning_naming_that_end() -> None:
    model = planted_model()
    conductor = next(iter(conductors(model).values()))
    function = ports(model)[conductor.a].function
    skipped = [Skipped("function", render_id(function), FUNCTION_WITHOUT_SYMBOL)]
    found = [f for f in read_findings(model, skipped) if f.code == "CONNECTION_TO_UNDRAWN"]
    assert found
    assert all(f.severity is Severity.WARNING and f.fix for f in found)
    assert any(conductor.a in f.subjects for f in found)
    assert _codes(model, "CONNECTION_TO_UNDRAWN") == []


class _Io(NamedTuple):
    J1: fr.Device


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-10-19", text="first", by="XX")
def _crowded_board(u: fr.Design) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    u.device("H9", "DEMO-LAMP-24")
    j1 = u.device("J1", "DEMO-CONN-2P", parent=pcb)
    h1 = u.device("H1", "DEMO-LAMP-24", parent=pcb)
    u.detail.net("SIG_A", j1["1"], h1["1"], kind=fr.SIGNAL)
    return _Io(j1)


@fr.unit("demo-board", revision=1, interface_version=1, date="2026-10-19", text="first", by="XX")
def _lone_board(u: fr.Design) -> _Io:
    pcb = u.device("A1", "DEMO-PCB-IO")
    j1 = u.device("J1", "DEMO-CONN-2P", parent=pcb)
    h1 = u.device("H1", "DEMO-LAMP-24", parent=pcb)
    u.detail.net("SIG_A", j1["1"], h1["1"], kind=fr.SIGNAL)
    return _Io(j1)


def _board_model(unit: fr.UnitDef) -> object:
    d = fr.design("demo_parts")
    d.add(unit, "U1")
    return fr.build(d).model


def test_a_board_beside_another_top_level_device_names_its_undrawn_net() -> None:
    model = _board_model(_crowded_board)
    (found,) = _codes(model, "BOARD_NETS_NOT_DRAWN")
    assert found.severity is Severity.WARNING
    assert "A1" in found.message
    assert "SIG_A" in found.message
    assert "only top-level device" in found.fix


def test_a_board_that_is_its_units_only_root_has_no_such_finding() -> None:
    assert _codes(_board_model(_lone_board), "BOARD_NETS_NOT_DRAWN") == []
