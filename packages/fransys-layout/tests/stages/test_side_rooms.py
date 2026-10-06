"""S11: Room's first call for a reference beside an E or W port (`references.side_rooms`).

Hand-made values, no model. Function 1 is the through symbol with a third port, `aux`, on its
body's right edge facing E and no slots, so its keep-out ends at the port. `aux` is wired to
function 3's `in`, in another column. The profile pads a marker by 4 G: the box is 38 + 8 = 46 G
wide and reaches 8 + 46 = 54 G past the port, past the 48 G column gap, as the house profile's
50 G reach does (S11's Width).

No wired E or W port exists on the goldens, the example or any other fixture (measured over
every engine run of the layout and root suites), so this page is S11's own can-fail fixture.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from samples import NO_HINTS, PROFILE, SHEET, drawn, hid, page_plan, through_geometry

from fransys_layout.geometry import Box, Facing, Point, PortGeometry, translate
from fransys_layout.stages import (
    Cell,
    Column,
    Connection,
    DrawnFunction,
    DrawnPort,
    PlacedFunction,
    PortRef,
    Role,
)
from fransys_layout.stages.pagerun import PageInputs, PageSlices, _place_page
from fransys_layout.stages.partition import column_widths
from fransys_layout.stages.references import Wiring, side_reference_rooms
from fransys_layout.stages.references.side_rooms import REFERENCE_SLOT
from fransys_layout.stages.sizing import grown

if TYPE_CHECKING:
    from fransys_model.kernel import Id

_PROFILE = dataclasses.replace(PROFILE, marker_padding=4)
# `reference_box_width` (38 G of "#99-p99:8F" at text height 8, plus 2 * 4 G) by one line,
# one wiring-grid step E of `aux` at (8, 0), centred on it
_BOX = Box(x=16, y=-8, width=46, height=16)
_AUX = hid("port", 13)


def _with_aux(number: int) -> DrawnFunction:
    """Function `number` drawn with `aux` on the E edge of its body and no slots."""
    one = drawn(number)
    g = through_geometry()
    geometry = dataclasses.replace(
        g,
        keepout=g.body,
        slots=(),
        ports=(*g.ports, PortGeometry(name="aux", at=Point(x=8, y=0), facing=Facing.E)),
    )
    return dataclasses.replace(
        one, geometry=geometry, ports=(*one.ports, DrawnPort(port=_AUX, symbol_port="aux"))
    )


def _cell(number: int, index: int = 0, *, carrier: int | None = None) -> Cell:
    """Function `number`'s cell in row `index`; a side element beside `carrier` when given."""
    return Cell(
        function=hid("function", number),
        index=index,
        side=carrier is not None,
        carrier=None if carrier is None else hid("function", carrier),
    )


def _column(name: str, *cells: Cell) -> Column:
    return Column(
        key=("invented", name),
        cells=cells,
        group=hid("aspect_node", 1),
        role=Role.CONTROL,
        location=hid("aspect_node", 100),
    )


def _to(function: int, port: int) -> Connection:
    """The conductor from function 1's `aux` to port `port` of `function`."""
    return Connection(
        handle=hid("conductor", 1),
        physical_net=hid("net", 1),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", 1), port=_AUX),
        b=PortRef(function=hid("function", function), port=hid("port", port)),
    )


def _rooms(columns: tuple[Column, ...], functions: tuple, wire: Connection) -> dict:
    return side_reference_rooms(
        columns, functions, Wiring((wire,), ()), sheet=SHEET, profile=_PROFILE
    )


def _page(first: int, second: int) -> tuple[Box, int, dict[Id[Any], PlacedFunction]]:
    """Columns `a` and `b` holding functions `first` and `second` (1 and 3), placed.

    Sized and placed as the engine does (S11's two sites): `column_widths` on the keep-outs
    grown by Room's boxes, then `place_page`, on a sheet exactly as wide as the two estimates,
    as `partition` packs a page. Returns the reference's box at function 1's placed `aux`, the
    content width and the placed functions.
    """
    columns = (_column("a", _cell(first)), _column("b", _cell(second)))
    functions = (_with_aux(1), drawn(3))
    wire = _to(3, 31)
    rooms = _rooms(columns, functions, wire)
    widths = column_widths(columns, grown(functions, (), _PROFILE, rooms=rooms), profile=_PROFILE)
    sheet = dataclasses.replace(SHEET, content_width=sum(one.width for one in widths))
    inputs = PageInputs(
        functions=(),
        connections=(wire,),
        net_groups=(),
        groups=(),
        locations=(),
        units=(),
        hints=NO_HINTS,
        profile=_PROFILE,
        sheet=sheet,
        top_headroom_lanes=0,
        bottom_headroom_lanes=0,
    )
    page = PageSlices(page_plan(("a", "b")), columns, functions, (), inputs)
    placed, _, _ = _place_page(page)
    by = {one.function: one for one in placed}
    at = by[hid("function", 1)].at
    return translate(_BOX, dx=at.x, dy=at.y), sheet.content_width, by


def test_a_wired_e_port_owns_its_references_first_candidate_one_stub_step_out() -> None:
    """The box stands one wiring-grid step E of `aux`, centred on it, one line high."""
    columns = (_column("a", _cell(1)), _column("b", _cell(3)))
    rooms = _rooms(columns, (_with_aux(1), drawn(3)), _to(3, 31))
    assert rooms == {hid("function", 1): [(REFERENCE_SLOT, _BOX)]}


def test_an_adjacent_cell_and_a_side_elements_join_are_wires_and_own_no_room() -> None:
    """D1's first two wire cases, both known from `columns`: no reference, so no room."""
    adjacent = (_column("a", _cell(1), _cell(2, 1)),)
    assert _rooms(adjacent, (_with_aux(1), drawn(2)), _to(2, 21)) == {}
    beside = (_column("a", _cell(1), _cell(4, 0, carrier=1)),)
    assert _rooms(beside, (_with_aux(1), drawn(4)), _to(4, 41)) == {}


def test_a_reference_beside_an_e_port_of_the_last_column_stays_inside_the_content_box() -> None:
    """S11's Width: the last column's reference stands inside the width `partition` packed."""
    # UNDO: `side_reference_rooms` giving no room (Room's first call disabled) leaves the box
    # 6 G past the content box's right edge (174 > 168): this turns red.
    box, content_width, _ = _page(3, 1)
    assert box.x + box.width <= content_width


def test_the_next_column_stands_clear_of_a_reference_beside_an_e_port() -> None:
    """S11: `place` holds the reference's box in the cell's keep-out, so the gap follows it."""
    # UNDO: as above, the box then reaches 6 G over column `b`'s keep-out (70 > 64): red.
    box, _, by = _page(1, 3)
    neighbour = by[hid("function", 3)]
    assert box.x + box.width < neighbour.at.x + neighbour.geometry.keepout.x
