"""On the records: the study board's connectors at a line's end are boxes, not pins.

Built through `fr` from `demo_parts`: the board of `ha_study_board.build()` once, and a tiny
design with a connector at no line's end once (module fixtures).
"""

import sys
from pathlib import Path

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from fransys.colours import BK

from fransys_model import derive

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
    d.detail.wire(psu.output["+"], j20[1], wire=(BK, 0.5))
    d.detail.wire(j20[2], lamp["1"], wire=(BK, 0.5))
    d.detail.wire(lamp["2"], psu.output["-"], wire=(BK, 0.5))
    cover = tmp_path_factory.mktemp("lone") / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _designation(result: fr.BuildResult, function) -> str:
    item = derive.connector_item(result.model, function)
    return "-" + derive.item_designation(result.model, item)


def _boxes(result: fr.BuildResult) -> dict:
    """Each connector function with a generic box on the core path's pages naming it."""
    model = result.model
    designations = {
        f.id: _designation(result, f.id)
        for f in derive.functions(model).values()
        if f.kind is derive.FunctionKind.CONNECTOR
    }
    return {
        function: symbol
        for drawing in drawn_pages(model).values()
        for symbol in drawing.symbols
        if symbol.key == "generic-box"
        for function, name in designations.items()
        if any(name in cell for row in symbol.texts for cell in row)
    }


def _connector(result: fr.BuildResult, designation: str) -> derive.Function:
    (function,) = (
        f
        for f in derive.functions(result.model).values()
        if f.kind is derive.FunctionKind.CONNECTOR and _designation(result, f.id) == designation
    )
    return function


def _pin_views(result: fr.BuildResult, designation: str) -> list:
    """The pin symbols (`connector-fixed`) printing a pin of the connector `designation`."""
    return [
        symbol
        for drawing in drawn_pages(result.model).values()
        for symbol in drawing.symbols
        if symbol.key == "connector-fixed"
        and any(value.startswith(designation) for _, value in symbol.slots)
    ]


def test_every_interface_of_u1_and_every_plug_has_a_box(board: fr.BuildResult) -> None:
    boxed = {_designation(board, function) for function in _boxes(board)}
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
    named = {f: box for f, box in _boxes(board).items() if f in plugs | interfaces}
    assert {_designation(board, f) for f in named} == INTERFACES | PLUGS
    assert [box.n for box in named.values()] == [1] * len(named)
    assert [len(box.texts) for box in named.values()] == [1] * len(named)


def test_j10_wired_inside_the_cabinet_has_a_cell_for_each_pin(board: fr.BuildResult) -> None:
    j10 = _connector(board, "-K1-J10")
    pins = {p.name for p in derive.ports(board.model).values() if p.function == j10.id}
    box = _boxes(board).get(j10.id)
    assert box is not None
    cells = [cell for row in box.texts for cell in row]
    assert cells
    assert len(cells) == len(set(cells))
    assert {cell.split(".")[-1] for cell in cells} >= pins


def test_no_boxed_pin_view_draws_a_symbol_unless_a_marker_stands_at_it(
    board: fr.BuildResult,
) -> None:
    model = board.model
    boxed = _boxes(board)
    marked = {(m.x, m.y) for drawing in drawn_pages(model).values() for m in drawing.markers}
    views = [(f, view) for f in boxed for view in _pin_views(board, _designation(board, f))]
    drawn = sorted(
        (_designation(board, f), view.id) for f, view in views if (view.x, view.y) not in marked
    )
    assert drawn == []
    # positive: most boxed pins draw no symbol at all
    boxed_pins = [p for p in derive.ports(model).values() if p.function in boxed]
    assert len(views) < len(boxed_pins)


def test_a_connector_at_no_line_end_keeps_its_pins_and_gets_no_box(lone: fr.BuildResult) -> None:
    j20 = _connector(lone, "-J20")
    assert not derive.connector_at_line_end(lone.model, j20.id)
    assert _boxes(lone) == {}
    pins = _pin_views(lone, "-J20")
    assert len(pins) == 2
