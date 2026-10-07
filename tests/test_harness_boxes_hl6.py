"""HL5, HL6 on the records: the study board's connectors at a line's end are boxes, not pins.

Built through `fr` from `demo_parts`: the board of `ha_study_board.build()` once, and a tiny
design with a connector at no line's end once (module fixtures).
"""

import sys
from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model import derive
from fransys_model.layout import (
    ConnectorBox,
    LinkMarker,
    PlacementView,
    PowerSymbol,
    SymbolPlacement,
    layout_of,
)

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from ha_study_board import build  # noqa: E402 -- needs the tests folder on sys.path first

INTERFACES = {"-U1-J1", "-U1-J2", "-U1-J3", "-U1-J5", "-U1-J7"}
PLUGS = {"-W11-P11", "-W12-P12", "-W13-P13", "-W15-P15", "-W17-P17", "-W17-P18"}


@pytest.fixture(scope="module")
def board() -> fr.BuildResult:
    return build()


@pytest.fixture(scope="module")
def lone(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    """A connector J20 wired between a supply and a lamp, on no harness: at no line's end."""
    d = fr.design("demo_parts", place="C1")
    cab = d.location("C1", "Cabinet")
    psu = d.device("T1", "DEMO-PSU-24")
    d.dc_supply("S", psu)
    j20 = d.device("J20", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    lamp = d.device("H1", "DEMO-LAMP-24")
    d.wire(psu.output["+"], j20[1], wire=(BK, 0.5))
    d.wire(j20[2], lamp["1"], wire=(BK, 0.5))
    d.wire(lamp["2"], psu.output["-"], wire=(BK, 0.5))
    cover = tmp_path_factory.mktemp("lone") / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _boxes(result: fr.BuildResult) -> list[ConnectorBox]:
    return list(layout_of(result.model, ConnectorBox).values())


def _designation(result: fr.BuildResult, box: ConnectorBox) -> str:
    return derive.connector_box_lines(result.model, box.function)[0]


def _connector(result: fr.BuildResult, designation: str) -> derive.Function:
    model = result.model
    (function,) = (
        f
        for f in derive.functions(model).values()
        if f.kind is derive.FunctionKind.CONNECTOR
        and derive.connector_box_lines(model, f.id)[0] == designation
    )
    return function


def _pin_views(result: fr.BuildResult) -> list[SymbolPlacement]:
    placements = layout_of(result.model, SymbolPlacement).values()
    return [p for p in placements if p.view is PlacementView.PIN]


def test_every_interface_of_u1_and_every_plug_has_a_box(board: fr.BuildResult) -> None:
    boxed = {_designation(board, box) for box in _boxes(board)}
    assert boxed == INTERFACES | PLUGS | {"-K1-J10"}


def test_no_plug_box_and_no_unit_interface_box_has_cells(board: fr.BuildResult) -> None:
    """Q3 ruling: a plug and a unit interface never get cells."""
    model = board.model
    plugs = {
        end.plug
        for owner in derive.line_conductors(model)
        for end in derive.harness_line_ends(model, owner)
        if end.plug is not None
    }
    interfaces = {b.function for b in derive.boundaries(model).values()}
    named = [box for box in _boxes(board) if box.function in plugs | interfaces]
    assert {_designation(board, box) for box in named} == INTERFACES | PLUGS
    assert [box.cells for box in named] == [()] * len(named)


def test_j10_wired_inside_the_cabinet_has_a_cell_for_each_pin(board: fr.BuildResult) -> None:
    j10 = _connector(board, "-K1-J10")
    pins = {p.id for p in derive.ports(board.model).values() if p.function == j10.id}
    boxes = [box for box in _boxes(board) if box.function == j10.id]
    assert boxes
    for box in boxes:
        ports = [cell.port for cell in box.cells]
        assert ports
        assert len(ports) == len(set(ports))
    assert {cell.port for box in boxes for cell in box.cells} == pins


def test_each_box_has_one_text_per_box_line(board: fr.BuildResult) -> None:
    model = board.model
    for box in _boxes(board):
        assert len(box.texts) == len(derive.connector_box_lines(model, box.function))


def test_no_boxed_pin_view_draws_a_symbol_unless_a_marker_stands_at_it(
    board: fr.BuildResult,
) -> None:
    model = board.model
    boxed = {box.function for box in _boxes(board)}
    port_of = {(p.function, p.name): p.id for p in derive.ports(model).values()}
    # a link marker or a power symbol (a star marker) at a pin keeps its symbol as its owner
    marked = {m.port for kind in (LinkMarker, PowerSymbol) for m in layout_of(model, kind).values()}
    views = [view for view in _pin_views(board) if view.function in boxed]
    assert {view.key[-2] for view in views} <= {"pin"}  # a pin view's key ends in its pin name
    drawn = sorted(
        (derive.connector_box_lines(model, view.function)[0], view.key[-1])
        for view in views
        if port_of[view.function, view.key[-1]] not in marked
    )
    assert drawn == []
    # positive: most boxed pins draw no symbol at all
    boxed_pins = [port for (function, _), port in port_of.items() if function in boxed]
    assert len(views) < len(boxed_pins)


def test_a_connector_at_no_line_end_keeps_its_pins_and_gets_no_box(lone: fr.BuildResult) -> None:
    j20 = _connector(lone, "-J20")
    assert not derive.connector_at_line_end(lone.model, j20.id)
    assert _boxes(lone) == []
    pins = [view for view in _pin_views(lone) if view.function == j20.id]
    assert sorted(view.key[-1] for view in pins) == ["1", "2"]
